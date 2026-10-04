//! `frob release bump VERSION`: set one lockstep version across the workspace and the wheel.
//!
//! Design: `releases.md` sections 4 and 5, `monorepo.md` section 4. [`run`] makes the
//! workspace manifest declare `[workspace.package] version`, makes every member inherit it
//! (`version.workspace = true`), rewrites the version requirement of every intra-workspace
//! path dependency that also carries a `version` (the pin crates.io needs), rewrites a static
//! wheel `[project] version`, and refreshes `Cargo.lock` offline through `gob-exec`.
//!
//! Members inherit instead of carrying their own copy: after one bump the version lives in a
//! single line, so the next cut edits the workspace manifest, not every crate, and a member
//! cannot drift (`REL002` is equal by construction). Discovery (members, wheel metadata,
//! the workspace version) is `rel002`'s, not a second implementation. All TOML edits go
//! through `toml_edit` and keep comments and layout. A repeat run changes nothing.

use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use semver::Version;
use similar::TextDiff;
use toml_edit::{DocumentMut, InlineTable, Item, Table, TableLike, Value};

use crate::rel002::{self, Evaluation, Wheel};

/// The dependency tables of a manifest, at the top level and under `target.<cfg>`.
const DEP_TABLES: [&str; 3] = ["dependencies", "dev-dependencies", "build-dependencies"];

/// How long the offline lockfile refresh may run.
const CARGO_TIMEOUT: Duration = Duration::from_secs(300);

/// Inputs of one bump.
#[derive(Debug, Clone)]
pub struct BumpOptions {
    /// The new lockstep version (semver).
    pub version: String,
    /// Compute and report the changes, write nothing.
    pub dry_run: bool,
    /// Allow a version lower than the current workspace version.
    pub allow_downgrade: bool,
}

/// One file the bump changes (or would change) and its unified diff.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FileChange {
    /// Path relative to the repository root, with `/` separators.
    pub path: String,
    /// Unified diff of the edit.
    pub diff: String,
}

/// What happened to `Cargo.lock`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LockState {
    /// `cargo update --workspace --offline` ran and the lockfile changed.
    Refreshed,
    /// It ran and the lockfile was already right.
    Unchanged,
    /// A dry run: it would be refreshed.
    WouldRefresh,
    /// No manifest changed, so cargo was not run.
    NotNeeded,
    /// The repository has no `Cargo.lock`; none was created.
    Absent,
}

/// What a bump did, or in a dry run would do.
#[derive(Debug, Clone)]
pub struct BumpReport {
    /// The version set.
    pub version: String,
    /// The workspace version before, when it declared one.
    pub previous: Option<String>,
    /// True when nothing needed to change.
    pub already: bool,
    /// True when nothing was written because of `--dry-run`.
    pub dry_run: bool,
    /// Manifest and metadata files changed (or that would be), with diffs; excludes `Cargo.lock`.
    pub files: Vec<FileChange>,
    /// What happened to `Cargo.lock`.
    pub lock: LockState,
    /// `REL002` findings re-checked after the write; `None` for a dry run.
    pub rel002: Option<Vec<String>>,
}

/// Why a bump refused or failed.
#[derive(Debug, thiserror::Error)]
pub enum BumpError {
    /// The version is not semver.
    #[error("invalid version `{0}`; use semver MAJOR.MINOR.PATCH[-pre], e.g. 0.532.0")]
    InvalidVersion(String),
    /// The version is lower than the current workspace version.
    #[error(
        "{requested} is lower than the current workspace version {current}; pass the next version, or `--allow-downgrade` if going back is intended"
    )]
    Downgrade {
        /// The workspace version now.
        current: String,
        /// The version asked for.
        requested: String,
    },
    /// The root has no `Cargo.toml` with a `[workspace]` table.
    #[error("no Cargo workspace at {}; run from the repository root", .0.display())]
    NotWorkspace(PathBuf),
    /// Discovery could not read a manifest; nothing was changed.
    #[error("cannot bump, manifests are unreadable (nothing was changed):\n{}", .0.join("\n"))]
    Unresolved(Vec<String>),
    /// A file operation failed.
    #[error("{op} {}: {reason}", path.display())]
    Io {
        /// What was attempted.
        op: &'static str,
        /// The path involved.
        path: PathBuf,
        /// The failure text.
        reason: String,
    },
    /// A manifest has a shape the edit cannot handle.
    #[error("{path}: {reason}")]
    Shape {
        /// Manifest path relative to the root.
        path: String,
        /// What is wrong.
        reason: String,
    },
    /// The offline lockfile refresh failed; the edited files were restored.
    #[error(
        "`cargo update --workspace --offline` failed ({reason}); manifests were restored; make sure the dependencies are in the local cargo cache, then rerun"
    )]
    Cargo {
        /// Exit status or spawn failure and the stderr tail.
        reason: String,
    },
}

/// One planned file edit.
struct Edit {
    path: String,
    old: String,
    new: String,
}

fn io(op: &'static str, path: &Path, e: &std::io::Error) -> BumpError {
    BumpError::Io {
        op,
        path: path.to_owned(),
        reason: e.to_string(),
    }
}

/// Replace a string value in place with `new`, keeping its comments and spacing; true when it changed.
fn set_str(item: &mut Item, new: &str) -> bool {
    if item.as_str() == Some(new) {
        return false;
    }
    let mut value = Value::from(new);
    if let Some(old) = item.as_value() {
        *value.decor_mut() = old.decor().clone();
    }
    *item = Item::Value(value);
    true
}

/// True when `item` is `{ workspace = true }` in any spelling (dotted key or inline table).
fn inherits(item: &Item) -> bool {
    item.as_table_like()
        .and_then(|t| t.get("workspace"))
        .and_then(Item::as_bool)
        == Some(true)
}

/// Make `package.version` read `version.workspace = true`; true when it changed.
fn inherit(package: &mut dyn TableLike) -> bool {
    if package.get("version").is_some_and(inherits) {
        return false;
    }
    let decor = package
        .get("version")
        .and_then(Item::as_value)
        .map(|v| v.decor().clone());
    // A dotted key renders its leaf value's decor, so the old trailing comment goes there.
    let mut leaf = Value::from(true);
    if let Some(d) = decor {
        *leaf.decor_mut() = d;
    }
    let mut inline = InlineTable::new();
    inline.insert("workspace", leaf);
    inline.set_dotted(true);
    let value = Value::InlineTable(inline);
    package.insert("version", Item::Value(value));
    true
}

/// The requirement for `version`, keeping a leading `=`, `^` or `~` of the old requirement.
fn requirement(old: &str, version: &str) -> String {
    match old.chars().next() {
        Some(op @ ('=' | '^' | '~')) => format!("{op}{version}"),
        _ => version.to_owned(),
    }
}

/// Rewrite the version of path dependencies on workspace members inside one dependency table.
fn pin_deps(deps: &mut dyn TableLike, names: &BTreeSet<String>, version: &str) -> bool {
    let mut changed = false;
    for (key, item) in deps.iter_mut() {
        let Some(dep) = item.as_table_like_mut() else {
            continue;
        };
        let target = dep
            .get("package")
            .and_then(Item::as_str)
            .map_or_else(|| key.get().to_owned(), str::to_owned);
        if !names.contains(&target) || dep.get("path").is_none() {
            continue;
        }
        let Some(pin) = dep.get_mut("version") else {
            continue;
        };
        let Some(old) = pin.as_str() else { continue };
        let new = requirement(old, version);
        if set_str(pin, &new) {
            tracing::debug!(dep = %target, %new, "bump: rewrote dependency requirement");
            changed = true;
        }
    }
    changed
}

/// Pin the dependency tables of one manifest document.
fn pin_manifest(doc: &mut DocumentMut, names: &BTreeSet<String>, version: &str) -> bool {
    let root = doc.as_table_mut();
    let mut changed = false;
    for name in DEP_TABLES {
        if let Some(t) = root.get_mut(name).and_then(Item::as_table_like_mut) {
            changed |= pin_deps(t, names, version);
        }
    }
    if let Some(targets) = root.get_mut("target").and_then(Item::as_table_like_mut) {
        for (_, cfg) in targets.iter_mut() {
            let Some(cfg) = cfg.as_table_like_mut() else {
                continue;
            };
            for name in DEP_TABLES {
                if let Some(t) = cfg.get_mut(name).and_then(Item::as_table_like_mut) {
                    changed |= pin_deps(t, names, version);
                }
            }
        }
    }
    if let Some(t) = root
        .get_mut("workspace")
        .and_then(Item::as_table_like_mut)
        .and_then(|w| w.get_mut("dependencies"))
        .and_then(Item::as_table_like_mut)
    {
        changed |= pin_deps(t, names, version);
    }
    changed
}

/// Set `[workspace.package] version`, creating the table when absent; true when it changed.
fn set_workspace_version(doc: &mut DocumentMut, version: &str) -> bool {
    let Some(ws) = doc
        .as_table_mut()
        .get_mut("workspace")
        .and_then(Item::as_table_like_mut)
    else {
        return false;
    };
    if ws.get("package").is_none() {
        ws.insert("package", Item::Table(Table::new()));
    }
    let Some(package) = ws.get_mut("package").and_then(Item::as_table_like_mut) else {
        return false;
    };
    if let Some(item) = package.get_mut("version") {
        set_str(item, version)
    } else {
        package.insert("version", Item::Value(Value::from(version)));
        true
    }
}

fn parse(path: &str, text: &str) -> Result<DocumentMut, BumpError> {
    text.parse::<DocumentMut>().map_err(|e| BumpError::Shape {
        path: path.to_owned(),
        reason: format!("is not valid TOML: {}", e.to_string().replace('\n', " ")),
    })
}

/// Edit one cargo manifest: the workspace version (root only), inheritance, dependency pins.
fn edit_manifest(
    rel: &str,
    text: &str,
    names: &BTreeSet<String>,
    version: &str,
    is_root: bool,
    is_member: bool,
) -> Result<String, BumpError> {
    let mut doc = parse(rel, text)?;
    let mut changed = false;
    if is_root {
        changed |= set_workspace_version(&mut doc, version);
    }
    if is_member {
        let Some(package) = doc
            .as_table_mut()
            .get_mut("package")
            .and_then(Item::as_table_like_mut)
        else {
            return Err(BumpError::Shape {
                path: rel.to_owned(),
                reason: "has no [package] table".to_owned(),
            });
        };
        changed |= inherit(package);
    }
    changed |= pin_manifest(&mut doc, names, version);
    Ok(if changed {
        doc.to_string()
    } else {
        text.to_owned()
    })
}

/// Edit the wheel's static `[project] version`.
fn edit_wheel(rel: &str, text: &str, version: &str) -> Result<String, BumpError> {
    let mut doc = parse(rel, text)?;
    let changed = doc
        .as_table_mut()
        .get_mut("project")
        .and_then(Item::as_table_like_mut)
        .and_then(|p| p.get_mut("version"))
        .is_some_and(|v| set_str(v, version));
    Ok(if changed {
        doc.to_string()
    } else {
        text.to_owned()
    })
}

fn read(root: &Path, rel: &str) -> Result<String, BumpError> {
    let path = root.join(rel);
    fs::read_to_string(&path).map_err(|e| io("read", &path, &e))
}

/// Write `text` to `path` through a sibling temp file and a rename.
fn write_atomic(path: &Path, text: &str) -> Result<(), BumpError> {
    gob_fs::write_atomic(path, text.as_bytes()).map_err(|e| io("write", path, &e))
}

/// Plan every edit; nothing is written.
fn plan(
    root: &Path,
    version: &str,
    allow_downgrade: bool,
) -> Result<(Vec<Edit>, Option<String>), BumpError> {
    let root_rel = "Cargo.toml";
    let root_path = root.join(root_rel);
    if !root_path.is_file() {
        return Err(BumpError::NotWorkspace(root.to_owned()));
    }
    let table = rel002::read_table(&root_path)
        .map_err(|e| BumpError::Unresolved(vec![format!("{root_rel} {e}")]))?;
    let mut found = Evaluation::default();
    let ws = rel002::workspace(root, &table, &mut found)
        .ok_or_else(|| BumpError::NotWorkspace(root.to_owned()))?;
    if !found.findings.is_empty() {
        return Err(BumpError::Unresolved(
            found.findings.into_iter().map(|f| f.message).collect(),
        ));
    }
    let requested =
        Version::parse(version).map_err(|_| BumpError::InvalidVersion(version.to_owned()))?;
    if let Some(current) = ws.version.as_deref().and_then(|v| Version::parse(v).ok())
        && requested < current
        && !allow_downgrade
    {
        return Err(BumpError::Downgrade {
            current: current.to_string(),
            requested: requested.to_string(),
        });
    }
    let mut members = Vec::new();
    let mut problems = Vec::new();
    for dir in &ws.members {
        match rel002::member(root, dir, Some(version)) {
            Ok(m) => members.push(m),
            Err((manifest, e)) => problems.push(format!("{manifest} {e}")),
        }
    }
    if !problems.is_empty() {
        return Err(BumpError::Unresolved(problems));
    }
    let names: BTreeSet<String> = members.iter().map(|m| m.name.clone()).collect();
    let mut edits = Vec::new();
    let mut manifests: Vec<(String, bool)> = vec![(root_rel.to_owned(), true)];
    manifests.extend(
        members
            .iter()
            .filter(|m| m.manifest != root_rel)
            .map(|m| (m.manifest.clone(), false)),
    );
    for (rel, is_root) in manifests {
        let old = read(root, &rel)?;
        let is_member = members.iter().any(|m| m.manifest == rel);
        let new = edit_manifest(&rel, &old, &names, version, is_root, is_member)?;
        if new != old {
            edits.push(Edit {
                path: rel,
                old,
                new,
            });
        }
    }
    if let Some(path) = rel002::wheel_path(root) {
        let rel = path
            .strip_prefix(root)
            .unwrap_or(&path)
            .to_string_lossy()
            .replace('\\', "/");
        match rel002::wheel_version(&path) {
            Ok(Wheel::Static(_)) => {
                let old = read(root, &rel)?;
                let new = edit_wheel(&rel, &old, version)?;
                if new != old {
                    edits.push(Edit {
                        path: rel,
                        old,
                        new,
                    });
                }
            }
            Ok(Wheel::Absent | Wheel::FollowsCargo) => {
                tracing::debug!(wheel = %rel, "bump: wheel needs no edit");
            }
            Err(e) => return Err(BumpError::Unresolved(vec![format!("{rel} {e}")])),
        }
    }
    Ok((edits, ws.version))
}

/// Refresh `Cargo.lock` with `cargo update --workspace --offline` through `gob-exec`.
fn refresh_lock(root: &Path) -> Result<LockState, BumpError> {
    let lock = root.join("Cargo.lock");
    let before = fs::read(&lock).map_err(|e| io("read", &lock, &e))?;
    let spec = Spec {
        program: Program::Cargo,
        args: ["update", "--workspace", "--offline"]
            .map(str::to_owned)
            .to_vec(),
        cwd: Some(root.to_owned()),
        env: vec![("CARGO_NET_OFFLINE".to_owned(), "true".to_owned())],
        timeout: CARGO_TIMEOUT,
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 })
        .run(&spec)
        .map_err(|e| BumpError::Cargo {
            reason: e.to_string(),
        })?;
    if out.status != Outcome::Exited(0) {
        let tail: String = out
            .stderr
            .lines()
            .rev()
            .take(5)
            .collect::<Vec<_>>()
            .into_iter()
            .rev()
            .collect::<Vec<_>>()
            .join(" | ");
        return Err(BumpError::Cargo {
            reason: format!("{:?}: {tail}", out.status),
        });
    }
    let after = fs::read(&lock).map_err(|e| io("read", &lock, &e))?;
    Ok(if before == after {
        LockState::Unchanged
    } else {
        LockState::Refreshed
    })
}

// frob:ticket 01M4069X2KPQ6RNV26SWSY4VA5
/// Set the lockstep version of every crate and the wheel under `root`; idempotent.
///
/// # Errors
/// [`BumpError`] for a non-semver version, a downgrade without `allow_downgrade`, an
/// unreadable manifest, an I/O failure, or a failed offline lockfile refresh (the edited
/// files are restored first, so a failure leaves the tree as it was).
pub fn run(root: &Path, opts: &BumpOptions) -> Result<BumpReport, BumpError> {
    let (edits, previous) = plan(root, &opts.version, opts.allow_downgrade)?;
    let files: Vec<FileChange> = edits
        .iter()
        .map(|e| FileChange {
            path: e.path.clone(),
            diff: TextDiff::from_lines(&e.old, &e.new)
                .unified_diff()
                .header(&format!("a/{}", e.path), &format!("b/{}", e.path))
                .to_string(),
        })
        .collect();
    let has_lock = root.join("Cargo.lock").is_file();
    let mut report = BumpReport {
        version: opts.version.clone(),
        previous,
        already: edits.is_empty(),
        dry_run: opts.dry_run,
        files,
        lock: LockState::NotNeeded,
        rel002: None,
    };
    if edits.is_empty() {
        tracing::info!(version = %opts.version, "bump: already at this version, nothing changed");
        report.rel002 = Some(rel002_messages(root));
        return Ok(report);
    }
    if opts.dry_run {
        report.lock = if has_lock {
            LockState::WouldRefresh
        } else {
            LockState::Absent
        };
        tracing::info!(files = edits.len(), "bump: dry run, nothing written");
        return Ok(report);
    }
    for (written, e) in edits.iter().enumerate() {
        let path = root.join(&e.path);
        if let Err(err) = write_atomic(&path, &e.new) {
            restore(root, &edits[..written]);
            return Err(err);
        }
        tracing::info!(path = %e.path, "bump: wrote");
    }
    report.lock = if has_lock {
        match refresh_lock(root) {
            Ok(state) => state,
            Err(err) => {
                tracing::error!(%err, "bump: lockfile refresh failed, restoring manifests");
                restore(root, &edits);
                return Err(err);
            }
        }
    } else {
        LockState::Absent
    };
    report.rel002 = Some(rel002_messages(root));
    tracing::info!(version = %opts.version, files = edits.len(), lock = ?report.lock, "bump: done");
    Ok(report)
}

/// Put the original text back into `edits`' files after a failure.
fn restore(root: &Path, edits: &[Edit]) {
    for e in edits {
        if let Err(err) = write_atomic(&root.join(&e.path), &e.old) {
            tracing::error!(path = %e.path, %err, "bump: could not restore");
        }
    }
}

/// `REL002` messages for the tree as it is now.
fn rel002_messages(root: &Path) -> Vec<String> {
    rel002::evaluate(root)
        .findings
        .into_iter()
        .map(|f| f.message)
        .collect()
}
