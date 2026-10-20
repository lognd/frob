//! The shared engine: banners, atomic writes, backups, idempotence, drift and reversibility.
//!
//! Agent-neutral by construction: it only talks to an [`Emitter`] for target paths, rendering and hook
//! registration. A hash of every file it wrote is kept in `<home>/.frob-agent.json`, which is how it tells
//! a pristine file (safe to remove) from one the user edited (kept).

// frob:ticket 01M5BJ2EVKDA4RYRDFRVHZ1FDQ

use std::collections::BTreeMap;
use std::path::Path;

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use super::{AgentError, Emitter, Item, Kind, Manifest, Reg, RegState};

/// Name of the state file recording the hash of every file frob wrote.
pub const STATE_FILE: &str = ".frob-agent.json";
/// Suffix of the backup written beside a file before it is replaced.
pub const BACKUP_SUFFIX: &str = ".frob-bak";
/// Text that makes a file recognisable as frob-managed.
pub const BANNER_TAG: &str = "frob-managed: do not edit";

/// An item with its destination and the exact bytes the destination must hold.
#[derive(Debug, Clone)]
pub struct Planned {
    /// The canonical item.
    pub item: Item,
    /// Destination relative to the home directory, with `/` separators.
    pub dest: String,
    /// The content the destination must hold.
    pub expected: Vec<u8>,
    /// True when the source file is executable.
    pub executable: bool,
}

fn banner(src: &str, dest: &Path) -> String {
    let text = format!("{BANNER_TAG}; source {src}; update with `frob agent sync`");
    if dest.extension().is_some_and(|e| e == "md" || e == "html") {
        format!("<!-- {text} -->\n")
    } else {
        format!("# {text}\n")
    }
}

/// Byte length of a leading shebang line or front-matter block, which the banner must follow.
fn head_len(src: &[u8]) -> usize {
    if src.starts_with(b"#!") {
        return src
            .iter()
            .position(|&b| b == b'\n')
            .map_or(src.len(), |i| i + 1);
    }
    if src.starts_with(b"---\n")
        && let Some(i) = src[4..].windows(5).position(|w| w == b"\n---\n")
    {
        return 4 + i + 5;
    }
    0
}

/// `src` with a do-not-edit banner (comment style chosen by `dest`'s extension) after any shebang or front matter.
pub fn with_banner(src_path: &str, dest: &Path, src: &[u8]) -> Vec<u8> {
    let at = head_len(src);
    let mut out = Vec::with_capacity(src.len() + 96);
    out.extend_from_slice(&src[..at]);
    out.extend_from_slice(banner(src_path, dest).as_bytes());
    out.extend_from_slice(&src[at..]);
    out
}

#[cfg(unix)]
fn is_executable(path: &Path) -> bool {
    use std::os::unix::fs::PermissionsExt;
    std::fs::metadata(path).is_ok_and(|m| m.permissions().mode() & 0o111 != 0)
}

#[cfg(not(unix))]
fn is_executable(_path: &Path) -> bool {
    false
}

/// An [`AgentError::Io`] for `path`.
pub fn io(path: &Path, source: std::io::Error) -> AgentError {
    AgentError::Io {
        path: path.to_path_buf(),
        source,
    }
}

/// Read every item this emitter places, below `root`, and render its destination content.
///
/// # Errors
/// [`AgentError::Io`] when a source file cannot be read.
pub fn plan(
    em: &dyn Emitter,
    root: &Path,
    manifest: &Manifest,
) -> Result<Vec<Planned>, AgentError> {
    let mut out = Vec::new();
    for item in &manifest.items {
        let Some(rel) = em.target(item) else {
            tracing::debug!(agent = em.id(), name = %item.name, "no target for item; skipped");
            continue;
        };
        let path = root.join(&item.src);
        let bytes = std::fs::read(&path).map_err(|e| io(&path, e))?;
        out.push(Planned {
            expected: em.render(item, &rel, &bytes),
            executable: is_executable(&path),
            dest: rel.to_string_lossy().replace('\\', "/"),
            item: item.clone(),
        });
    }
    Ok(out)
}

/// The hook registrations that apply to this emitter, resolved against `home`.
pub fn regs(home: &Path, manifest: &Manifest, planned: &[Planned]) -> Vec<Reg> {
    manifest
        .hooks
        .iter()
        .filter_map(|h| {
            planned
                .iter()
                .find(|p| p.item.kind == Kind::Hook && p.item.name == h.name)
                .map(|p| Reg {
                    hook: h.clone(),
                    script: home.join(&p.dest),
                })
        })
        .collect()
}

fn hash(bytes: &[u8]) -> String {
    blake3::hash(bytes).to_hex().to_string()
}

/// The file's bytes, or `None` when it does not exist.
///
/// # Errors
/// Any I/O failure other than not-found.
pub fn read_opt(path: &Path) -> Result<Option<Vec<u8>>, AgentError> {
    match std::fs::read(path) {
        Ok(b) => Ok(Some(b)),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(io(path, e)),
    }
}

/// Write `bytes` to `path` atomically: a sibling temp file, then a rename; the parent is created.
///
/// # Errors
/// Any I/O failure creating, writing or renaming.
pub fn write_atomic(path: &Path, bytes: &[u8], executable: bool) -> Result<(), AgentError> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| io(dir, e))?;
    }
    let mut tmp_name = path.file_name().unwrap_or_default().to_os_string();
    tmp_name.push(format!(".frob-tmp-{}", std::process::id()));
    let tmp = path.with_file_name(tmp_name);
    let result = (|| {
        std::fs::write(&tmp, bytes).map_err(|e| io(&tmp, e))?;
        #[cfg(unix)]
        if executable {
            use std::os::unix::fs::PermissionsExt;
            std::fs::set_permissions(&tmp, std::fs::Permissions::from_mode(0o755))
                .map_err(|e| io(&tmp, e))?;
        }
        #[cfg(not(unix))]
        let _ = executable;
        std::fs::rename(&tmp, path).map_err(|e| io(path, e))
    })();
    if result.is_err() {
        // Best effort: a leftover temp file is harmless but untidy.
        let _ = std::fs::remove_file(&tmp);
    }
    result
}

/// Copy the current content of `path` to `<path>.frob-bak` (no-op when `path` is absent).
///
/// # Errors
/// Any I/O failure reading or writing.
pub fn backup(path: &Path) -> Result<(), AgentError> {
    let Some(old) = read_opt(path)? else {
        return Ok(());
    };
    let mut name = path.file_name().unwrap_or_default().to_os_string();
    name.push(BACKUP_SUFFIX);
    let bak = path.with_file_name(name);
    std::fs::write(&bak, old).map_err(|e| io(&bak, e))?;
    tracing::info!(backup = %bak.display(), "backup written");
    Ok(())
}

/// What frob wrote last time: the content hash of every synced file, by destination.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
struct State {
    files: BTreeMap<String, String>,
}

fn load_state(home: &Path) -> Result<State, AgentError> {
    let path = home.join(STATE_FILE);
    match read_opt(&path)? {
        None => Ok(State::default()),
        Some(b) => serde_json::from_slice(&b).map_err(|source| AgentError::Json { path, source }),
    }
}

// frob:ticket 01M5BJ2EVKDA4RYRDFRVHZ1FDQ
// frob:tests crates/frob/tests/it/agent.rs::sync_into_empty_home_is_idempotent_and_byte_identical
/// True when `home` holds a state file, i.e. frob has synced into it before.
pub fn has_state(home: &Path) -> bool {
    home.join(STATE_FILE).is_file()
}

fn save_state(home: &Path, state: &State) -> Result<(), AgentError> {
    let path = home.join(STATE_FILE);
    let mut text = serde_json::to_string_pretty(state).map_err(|source| AgentError::Json {
        path: path.clone(),
        source,
    })?;
    text.push('\n');
    if read_opt(&path)?.as_deref() == Some(text.as_bytes()) {
        return Ok(());
    }
    write_atomic(&path, text.as_bytes(), false)
}

/// What `sync` did.
#[derive(Debug, Clone, Default, Serialize, JsonSchema)]
pub struct SyncReport {
    /// Destinations written (new or changed), relative to the home directory.
    pub written: Vec<String>,
    /// Destinations already up to date.
    pub unchanged: Vec<String>,
    /// Destinations removed because the manifest no longer lists them.
    pub removed: Vec<String>,
    /// Orphaned destinations left alone because they were edited after the last sync.
    pub kept_edited: Vec<String>,
    /// True when the emitter's registration file changed.
    pub registration_changed: bool,
}

/// Publish the planned files into `home`, register the hooks, and record what was written.
///
/// With `dry_run` nothing is written; the report says what would be.
///
/// # Errors
/// [`AgentError`] on an unreadable or unwritable path or an unparseable registration file.
pub fn sync(
    em: &dyn Emitter,
    home: &Path,
    manifest: &Manifest,
    planned: &[Planned],
    dry_run: bool,
) -> Result<SyncReport, AgentError> {
    let mut report = SyncReport::default();
    let mut state = load_state(home)?;
    for p in planned {
        let dest = home.join(&p.dest);
        if read_opt(&dest)?.as_deref() == Some(p.expected.as_slice()) {
            report.unchanged.push(p.dest.clone());
        } else {
            if !dry_run {
                backup(&dest)?;
                write_atomic(&dest, &p.expected, p.executable)?;
            }
            tracing::info!(agent = em.id(), dest = %p.dest, dry_run, "file synced");
            report.written.push(p.dest.clone());
        }
        state.files.insert(p.dest.clone(), hash(&p.expected));
    }
    let orphans: Vec<String> = state
        .files
        .keys()
        .filter(|d| !planned.iter().any(|p| &p.dest == *d))
        .cloned()
        .collect();
    for dest in orphans {
        let path = home.join(&dest);
        let recorded = state.files.remove(&dest).unwrap_or_default();
        match read_opt(&path)? {
            None => {}
            Some(b) if hash(&b) == recorded => {
                if !dry_run {
                    std::fs::remove_file(&path).map_err(|e| io(&path, e))?;
                }
                tracing::info!(agent = em.id(), %dest, "orphaned file removed");
                report.removed.push(dest);
            }
            Some(_) => {
                tracing::warn!(agent = em.id(), %dest, "orphaned file edited since sync; kept");
                report.kept_edited.push(dest);
            }
        }
    }
    report.registration_changed = em.register(home, &regs(home, manifest, planned), dry_run)?;
    if !dry_run {
        save_state(home, &state)?;
    }
    Ok(report)
}

/// How one synced file stands against the repository.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum FileState {
    /// Byte-identical to what sync would write.
    Ok,
    /// Not present in the home directory.
    Missing,
    /// Present but different: edited in the home directory, or the repository moved on.
    Differs,
    /// Recorded by an earlier sync but no longer in the manifest.
    Orphaned,
}

/// One file row of the status report.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct FileRow {
    /// Destination relative to the home directory.
    pub dest: String,
    /// Its state.
    pub state: FileState,
}

/// One hook row of the status report.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct HookRow {
    /// Hook name.
    pub name: String,
    /// Event name.
    pub event: String,
    /// Its registration state.
    pub state: RegState,
}

/// The read-only drift report.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct StatusReport {
    /// One row per planned file and per orphan.
    pub files: Vec<FileRow>,
    /// One row per hook registration.
    pub hooks: Vec<HookRow>,
    /// True when anything is not in sync.
    pub drift: bool,
}

/// Compare `home` with what sync would produce; reads only.
///
/// # Errors
/// [`AgentError`] on an unreadable path or an unparseable registration file.
pub fn status(
    em: &dyn Emitter,
    home: &Path,
    manifest: &Manifest,
    planned: &[Planned],
) -> Result<StatusReport, AgentError> {
    let mut files = Vec::new();
    for p in planned {
        let state = match read_opt(&home.join(&p.dest))? {
            None => FileState::Missing,
            Some(b) if b == p.expected => FileState::Ok,
            Some(_) => FileState::Differs,
        };
        files.push(FileRow {
            dest: p.dest.clone(),
            state,
        });
    }
    for dest in load_state(home)?.files.keys() {
        if !planned.iter().any(|p| &p.dest == dest) && home.join(dest).exists() {
            files.push(FileRow {
                dest: dest.clone(),
                state: FileState::Orphaned,
            });
        }
    }
    let regs = regs(home, manifest, planned);
    let states = em.registration_state(home, &regs)?;
    let hooks: Vec<HookRow> = regs
        .iter()
        .zip(states)
        .map(|(r, state)| HookRow {
            name: r.hook.name.clone(),
            event: r.hook.event.clone(),
            state,
        })
        .collect();
    let drift = files.iter().any(|f| f.state != FileState::Ok)
        || hooks.iter().any(|h| h.state != RegState::Registered);
    Ok(StatusReport {
        files,
        hooks,
        drift,
    })
}

/// What `uninstall` did.
#[derive(Debug, Clone, Default, Serialize, JsonSchema)]
pub struct UninstallReport {
    /// Destinations removed.
    pub removed: Vec<String>,
    /// Destinations kept because they were edited after the last sync.
    pub kept_edited: Vec<String>,
    /// Frob-owned registrations removed.
    pub registrations_removed: usize,
}

/// Remove only what frob wrote: pristine synced files and frob-owned registrations.
///
/// A file edited since the last sync is kept (it now holds user work).
///
/// # Errors
/// [`AgentError`] on an unreadable or unwritable path or an unparseable registration file.
pub fn uninstall(
    em: &dyn Emitter,
    home: &Path,
    manifest: &Manifest,
    planned: &[Planned],
    dry_run: bool,
) -> Result<UninstallReport, AgentError> {
    let mut report = UninstallReport::default();
    let state = load_state(home)?;
    for (dest, recorded) in &state.files {
        let path = home.join(dest);
        match read_opt(&path)? {
            None => {}
            Some(b) if hash(&b) == *recorded => {
                if !dry_run {
                    std::fs::remove_file(&path).map_err(|e| io(&path, e))?;
                }
                tracing::info!(agent = em.id(), %dest, "synced file removed");
                report.removed.push(dest.clone());
            }
            Some(_) => {
                tracing::warn!(agent = em.id(), %dest, "file edited since sync; kept");
                report.kept_edited.push(dest.clone());
            }
        }
    }
    report.registrations_removed = em.unregister(home, &regs(home, manifest, planned), dry_run)?;
    if !dry_run {
        let state_path = home.join(STATE_FILE);
        if report.kept_edited.is_empty() {
            match std::fs::remove_file(&state_path) {
                Ok(()) => {}
                Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
                Err(e) => return Err(io(&state_path, e)),
            }
        } else {
            // Keep the edited files recorded so a later uninstall still recognises them.
            let kept = State {
                files: state
                    .files
                    .into_iter()
                    .filter(|(d, _)| report.kept_edited.contains(d))
                    .collect(),
            };
            save_state(home, &kept)?;
        }
    }
    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::agent::Manifest;
    use std::path::PathBuf;

    /// A deliberately non-Claude agent: different layout, a plain-text registry, no settings.json.
    struct Fake;

    const REGISTRY: &str = "registry.txt";

    impl Emitter for Fake {
        fn id(&self) -> &'static str {
            "fake"
        }
        fn default_home(&self) -> Option<PathBuf> {
            None
        }
        fn target(&self, item: &Item) -> Option<PathBuf> {
            match item.kind {
                Kind::Skill => None,
                Kind::Hook => Some(PathBuf::from(format!("run/{}.sh", item.name))),
                _ => Some(PathBuf::from(format!("{:?}/{}.txt", item.kind, item.name))),
            }
        }
        fn registration_state(
            &self,
            home: &Path,
            regs: &[Reg],
        ) -> Result<Vec<RegState>, AgentError> {
            let text = read_opt(&home.join(REGISTRY))?.unwrap_or_default();
            let text = String::from_utf8_lossy(&text).into_owned();
            Ok(regs
                .iter()
                .map(|r| {
                    if text.lines().any(|l| l == format!("frob {}", r.hook.name)) {
                        RegState::Registered
                    } else {
                        RegState::Missing
                    }
                })
                .collect())
        }
        fn register(&self, home: &Path, regs: &[Reg], dry_run: bool) -> Result<bool, AgentError> {
            let path = home.join(REGISTRY);
            let old = String::from_utf8_lossy(&read_opt(&path)?.unwrap_or_default()).into_owned();
            let mut lines: Vec<String> = old
                .lines()
                .filter(|l| !l.starts_with("frob "))
                .map(str::to_owned)
                .collect();
            lines.extend(regs.iter().map(|r| format!("frob {}", r.hook.name)));
            let new = format!("{}\n", lines.join("\n"));
            if new == old || (old.is_empty() && lines.is_empty()) {
                return Ok(false);
            }
            if !dry_run {
                write_atomic(&path, new.as_bytes(), false)?;
            }
            Ok(true)
        }
        fn unregister(
            &self,
            home: &Path,
            _regs: &[Reg],
            dry_run: bool,
        ) -> Result<usize, AgentError> {
            let path = home.join(REGISTRY);
            let Some(old) = read_opt(&path)? else {
                return Ok(0);
            };
            let old = String::from_utf8_lossy(&old).into_owned();
            let keep: Vec<&str> = old.lines().filter(|l| !l.starts_with("frob ")).collect();
            let removed = old.lines().count() - keep.len();
            if removed > 0 && !dry_run {
                write_atomic(&path, format!("{}\n", keep.join("\n")).as_bytes(), false)?;
            }
            Ok(removed)
        }
    }

    fn fixture() -> (tempfile::TempDir, tempfile::TempDir, Manifest) {
        let root = tempfile::tempdir().unwrap();
        std::fs::write(root.path().join("h.sh"), "#!/bin/sh\necho hi\n").unwrap();
        std::fs::write(root.path().join("i.md"), "be kind\n").unwrap();
        std::fs::write(root.path().join("s.md"), "skill\n").unwrap();
        let m = Manifest::parse(
            &[
                "hook:h = h.sh".to_owned(),
                "instruction:i = i.md".to_owned(),
                "skill:s = s.md".to_owned(),
            ],
            &["h:Pre:*".to_owned()],
        )
        .unwrap();
        (root, tempfile::tempdir().unwrap(), m)
    }

    // frob:tests crates/frob/src/agent/engine.rs::sync
    // frob:tests crates/frob/src/agent/engine.rs::status
    // frob:tests crates/frob/src/agent/engine.rs::uninstall
    #[test]
    fn engine_drives_a_non_claude_emitter() {
        let (root, home, m) = fixture();
        let (h, em) = (home.path(), &Fake as &dyn Emitter);
        let planned = plan(em, root.path(), &m).unwrap();
        assert_eq!(planned.len(), 2, "skill has no target for this agent");
        assert!(status(em, h, &m, &planned).unwrap().drift);

        let first = sync(em, h, &m, &planned, false).unwrap();
        assert_eq!(first.written.len(), 2);
        assert!(first.registration_changed);
        let snap = |p: &Path| std::fs::read(p).unwrap();
        let before = (
            snap(&h.join("run/h.sh")),
            snap(&h.join(REGISTRY)),
            snap(&h.join(STATE_FILE)),
        );
        let second = sync(em, h, &m, &planned, false).unwrap();
        assert!(second.written.is_empty() && !second.registration_changed);
        let after = (
            snap(&h.join("run/h.sh")),
            snap(&h.join(REGISTRY)),
            snap(&h.join(STATE_FILE)),
        );
        assert_eq!(before, after, "double sync is byte-identical");
        assert!(String::from_utf8_lossy(&before.0).starts_with("#!/bin/sh\n# frob-managed"));
        assert!(!status(em, h, &m, &planned).unwrap().drift);

        std::fs::write(h.join("Instruction/i.txt"), "mine\n").unwrap();
        assert!(status(em, h, &m, &planned).unwrap().drift);
        let un = uninstall(em, h, &m, &planned, false).unwrap();
        assert_eq!(un.removed, vec!["run/h.sh".to_owned()]);
        assert_eq!(un.kept_edited, vec!["Instruction/i.txt".to_owned()]);
        assert_eq!(un.registrations_removed, 1);
        assert_eq!(snap(&h.join("Instruction/i.txt")), b"mine\n");
    }

    // frob:tests crates/frob/src/agent/mod.rs::Manifest
    #[test]
    fn manifest_rejects_escapes_and_dangling_hooks() {
        let p = |i: &[&str], h: &[&str]| {
            Manifest::parse(
                &i.iter().map(|s| (*s).to_owned()).collect::<Vec<_>>(),
                &h.iter().map(|s| (*s).to_owned()).collect::<Vec<_>>(),
            )
        };
        assert!(p(&["hook:a = ../x"], &[]).is_err());
        assert!(p(&["hook:a = /x"], &[]).is_err());
        assert!(p(&["nope:a = x"], &[]).is_err());
        assert!(p(&["hook:a = x", "hook:a = y"], &[]).is_err());
        assert!(p(&[], &["a:E:m"]).is_err());
        assert!(p(&["hook:a = x"], &["a:E:m"]).is_ok());
    }

    // frob:tests crates/frob/src/agent/engine.rs::with_banner
    #[test]
    fn banner_follows_shebang_and_front_matter() {
        let out = with_banner(
            "s.py",
            Path::new("d.py"),
            b"#!/usr/bin/env python3\nx = 1\n",
        );
        assert!(out.starts_with(b"#!/usr/bin/env python3\n# frob-managed"));
        let out = with_banner("s.md", Path::new("d.md"), b"---\nname: a\n---\nbody\n");
        assert!(out.starts_with(b"---\nname: a\n---\n<!-- frob-managed"));
        assert!(out.ends_with(b"body\n"));
    }
}
