//! The land ratchet: land refuses only findings the ticket introduces (rules.md section 6, ~QAFRXM3).
//!
//! The base side is the same check run without a ticket scope on the base tip,
//! in a persistent detached checkout (`<git common dir>/frob/land-checkout`, moved to each base tip under a lock, its `target/` shared with the ticket worktree through `frob/land-target`). Its finding
//! fingerprints are cached per code tree (the base tree without the ledger directory), engine version and
//! config digest in `<git common dir>/frob/land-base/<tree>-<key>.json`, shared by every worktree, so a second land on
//! the same code (from any ticket, a ledger-only base commit, or a `--wait` retry that did not move it) costs
//! one tool-free exact-commit pass; a base with changed code, a new engine or a changed config has a new key and so is recomputed (~F4YA3S9).
//! Findings are compared as multisets: a second occurrence of a fingerprint the base has once is new.
//! The base checkout's check opens the repository-shared cache (gob-cache), so every file
//! unchanged since an earlier check is a cache hit (~TSK0M4Y).

use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};

use frob_check::CheckOptions;
use frob_check::CheckReport;
use frob_ledger::LedgerConfig;
use gob_git::Repo;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::error::LandError;
use crate::git::git;

/// Directory under `<common>/frob/` holding the per-base finding sets.
pub const LAND_BASE_DIR: &str = "land-base";

/// One finding as land's report lists it (pre-existing or resolved).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct FindingNote {
    /// Finding fingerprint (lowercase hex, namespaced for a sibling finding).
    pub fingerprint: String,
    /// Rule id.
    pub rule: String,
    /// File the finding is in, when it has a location.
    pub path: Option<String>,
    /// Finding message.
    pub message: String,
}

/// The finding fingerprints of one commit, as cached.
#[derive(Debug, Serialize, Deserialize)]
struct BaseSet {
    /// Digest of the base tree without the ledger directory the set belongs to.
    oid: String,
    /// Cache key (engine version and config digest) the set was computed under.
    key: String,
    /// Every finding of the unscoped check at that commit.
    findings: Vec<FindingNote>,
}

/// What the ratchet found beside the refusal: pre-existing blocking findings and resolved ones.
#[derive(Debug, Clone, Default)]
pub(crate) struct Ratchet {
    /// Blocking head findings already on the base tip.
    pub pre_existing: Vec<FindingNote>,
    /// Base findings the ticket fixed.
    pub resolved: Vec<FindingNote>,
}

/// The notes of every finding in `report`, with fingerprints as the report prints them.
pub(crate) fn notes(report: &CheckReport) -> Vec<FindingNote> {
    report
        .findings
        .iter()
        .map(|f| FindingNote {
            fingerprint: report.fingerprint_of(f),
            rule: f.rule.to_string(),
            path: f
                .span
                .as_ref()
                .and_then(|s| report.files.path(s.file))
                .map(str::to_owned),
            message: f.message.clone(),
        })
        .collect()
}

/// The cache key of a base set: the running engine fingerprint plus a digest of the ledger config the check runs with.
///
/// The engine is the gob-cache default (crate version plus executable size and mtime), so a
/// refreshed binary that adds rules or atoms misses and recomputes the base (~VNK49V8).
// frob:ticket 01M42MGPC19KXFQ0DS2F4YA3S9
// frob:ticket 01M4HDXNTJQ77R9Z81VVNK49V8
#[must_use]
pub fn cache_key(ledger: &LedgerConfig) -> String {
    cache_key_for(gob_cache::default_engine(), ledger)
}

/// [`cache_key`] under an explicit engine fingerprint (a filename-safe digest of engine and config).
fn cache_key_for(engine: &str, ledger: &LedgerConfig) -> String {
    let mut h = blake3::Hasher::new();
    h.update(engine.as_bytes());
    h.update(b"\0");
    h.update(format!("{ledger:?}").as_bytes());
    let digest = h.finalize().to_hex();
    format!("{}-{}", env!("CARGO_PKG_VERSION"), &digest.as_str()[..16])
}

/// A digest of the base tree with the ledger directory removed (frob:ticket 01M4CTDXHZ5B85NXCN1KJ95784).
///
/// Every ticket write is a new base commit in trunk mode, so the commit oid
/// never repeats; this digest does, as long as no code file, mode or path changed.
///
/// # Errors
/// Fails when `git ls-tree` cannot list `oid`.
pub fn code_tree_key(
    wt: &Repo,
    wt_path: &Path,
    oid: &str,
    ledger: &LedgerConfig,
) -> Result<String, LandError> {
    let listing = git(wt, wt_path, &["ls-tree", "-r", oid])?;
    if !listing.ok() {
        return Err(LandError::Config(format!(
            "could not list base {oid}: {}",
            listing.text
        )));
    }
    let mut h = blake3::Hasher::new();
    let mut kept = 0_usize;
    for line in listing.text.lines() {
        let path = line.split_once('\t').map_or("", |(_, p)| p);
        if !ledger.is_ledger_path(path) {
            h.update(line.as_bytes());
            h.update(b"\n");
            kept += 1;
        }
    }
    tracing::debug!(oid, kept, "land base code tree digest");
    Ok(h.finalize().to_hex().as_str()[..32].to_owned())
}

/// The unscoped findings at the base commit `oid`, from the cache or a fresh run.
///
/// The cache (under [`code_tree_key`]) holds only what the ledger cannot change: findings
/// located outside the ledger directory, and the findings only the tool stages produce (tools
/// do not read the ledger). Everything else, ledger-located and location-less (the PM, TICK
/// and REL repository-level findings), is recomputed for the exact `oid` by a pass without the
/// tool stages; the shared file cache makes that pass cheap. On a miss the full run adds the
/// tool-only findings, found as what the full run has beyond the exact pass.
///
/// # Errors
/// Fails when the base cannot be listed, checked out or checked.
pub fn base_findings(
    wt: &Repo,
    wt_path: &Path,
    oid: &str,
    ledger: &LedgerConfig,
) -> Result<Vec<FindingNote>, LandError> {
    let key = cache_key(ledger);
    let tree = code_tree_key(wt, wt_path, oid, ledger)?;
    let cache = wt
        .common_dir()
        .join(gob_cache::SHARED_DIR)
        .join(LAND_BASE_DIR)
        .join(format!("{tree}-{key}.json"));
    let stable = |n: &FindingNote| n.path.as_deref().is_some_and(|p| !ledger.is_ledger_path(p));
    let exact = run_at_base(wt, wt_path, oid, ledger, true)?;
    let mut exact_rest: Vec<FindingNote> = exact.into_iter().filter(|n| !stable(n)).collect();
    if let Some(set) = read_cache(&cache, &tree, &key) {
        tracing::info!(
            oid,
            tree,
            cached = set.findings.len(),
            exact = exact_rest.len(),
            "land base set from cache"
        );
        let mut findings = set.findings;
        findings.append(&mut exact_rest);
        return Ok(findings);
    }
    let all = run_at_base(wt, wt_path, oid, ledger, false)?;
    let mut cached: Vec<FindingNote> = all.iter().filter(|n| stable(n)).cloned().collect();
    // Tool-only findings: what the full run has beyond the exact pass, as a multiset.
    let mut budget = counts(&exact_rest);
    for n in all.into_iter().filter(|n| !stable(n)) {
        match budget.get_mut(n.fingerprint.as_str()) {
            Some(left) if *left > 0 => *left -= 1,
            _ => cached.push(n),
        }
    }
    let mut findings = cached.clone();
    findings.append(&mut exact_rest);
    write_cache(
        &cache,
        &BaseSet {
            oid: tree,
            key,
            findings: cached,
        },
    );
    Ok(findings)
}

/// Read a cached set, ignoring a missing, unreadable or mismatched file.
fn read_cache(path: &Path, oid: &str, key: &str) -> Option<BaseSet> {
    let text = std::fs::read_to_string(path).ok()?;
    match serde_json::from_str::<BaseSet>(&text) {
        Ok(set) if set.oid == oid && set.key == key => Some(set),
        Ok(_) | Err(_) => {
            tracing::warn!(path = %path.display(), "land base cache unusable; recomputing");
            None
        }
    }
}

/// Replace the cache directory's contents with `set` (only the latest base is useful); failures are logged.
fn write_cache(path: &Path, set: &BaseSet) {
    let Some(dir) = path.parent() else { return };
    if let Ok(entries) = std::fs::read_dir(dir) {
        for e in entries.flatten() {
            let _ = std::fs::remove_file(e.path());
        }
    }
    let result = std::fs::create_dir_all(dir).and_then(|()| {
        let json = serde_json::to_string(set).map_err(std::io::Error::other)?;
        std::fs::write(path, json)
    });
    match result {
        Ok(()) => tracing::info!(path = %path.display(), "land base set cached"),
        Err(e) => tracing::warn!(path = %path.display(), error = %e, "land base set not cached"),
    }
}

/// Directory (under `<common>/frob/`) of the persistent ratchet base checkout.
///
/// The name deliberately does not start with `land-base-`, the prefix the garbage
/// collector sweeps as abandoned per-process checkouts.
pub const BASE_CHECKOUT_DIR: &str = "land-checkout";

/// Directory (under `<common>/frob/`) of the cargo target directory every land checkout shares.
pub const SHARED_TARGET_DIR: &str = "land-target";

/// The persistent checkout path and its lock path for the repository whose git dir is `common`.
fn base_checkout_paths(common: &Path) -> (PathBuf, PathBuf) {
    let frob = common.join("frob");
    (
        frob.join(BASE_CHECKOUT_DIR),
        frob.join(format!("{BASE_CHECKOUT_DIR}.lock")),
    )
}

/// Move the persistent base checkout to `oid`, creating it on first use or when it is unusable.
///
/// A stable path keeps cargo's path-dependent fingerprints of the workspace crates valid from
/// one land to the next, which a fresh per-process directory never did.
fn checkout_base(wt: &Repo, wt_path: &Path, dir: &Path, oid: &str) -> Result<(), LandError> {
    let dir_text = dir.to_string_lossy().into_owned();
    if dir.join(".git").exists() {
        let moved = git(
            wt,
            dir,
            &["checkout", "--detach", "--force", "--quiet", oid],
        );
        if moved.as_ref().is_ok_and(crate::git::GitRun::ok) {
            // Untracked leftovers of an earlier check; ignored files (target/) stay.
            let _ = git(wt, dir, &["clean", "-fdq"]);
            tracing::info!(oid, dir = %dir.display(), "land base checkout reused");
            return Ok(());
        }
        tracing::warn!(dir = %dir.display(), "land base checkout unusable; recreating");
        let _ = git(wt, wt_path, &["worktree", "remove", "--force", &dir_text]);
    }
    if dir.exists() {
        let _ = std::fs::remove_dir_all(dir);
    }
    let _ = git(wt, wt_path, &["worktree", "prune"]);
    let add = git(
        wt,
        wt_path,
        &["worktree", "add", "--detach", "--force", &dir_text, oid],
    )?;
    if !add.ok() {
        return Err(LandError::Config(format!(
            "could not check out base {oid} to compute the ratchet: {}",
            add.text
        )));
    }
    tracing::info!(oid, dir = %dir.display(), "land base checkout created");
    Ok(())
}

/// Hold the exclusive lock of the persistent base checkout until the returned file is dropped.
fn lock_base_checkout(lock: &Path) -> Result<std::fs::File, LandError> {
    if let Some(parent) = lock.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| LandError::io(format!("creating {}", parent.display()), e))?;
    }
    let file = std::fs::OpenOptions::new()
        .create(true)
        .truncate(false)
        .write(true)
        .open(lock)
        .map_err(|e| LandError::io(format!("opening {}", lock.display()), e))?;
    file.lock()
        .map_err(|e| LandError::io(format!("locking {}", lock.display()), e))?;
    Ok(file)
}

/// Check out `oid` detached in the persistent base checkout and run the unscoped check there.
fn run_at_base(
    wt: &Repo,
    wt_path: &Path,
    oid: &str,
    ledger: &LedgerConfig,
    skip_tools: bool,
) -> Result<Vec<FindingNote>, LandError> {
    let common = wt.common_dir();
    let (dir, lock) = base_checkout_paths(common);
    if let Some(parent) = dir.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| LandError::Config(format!("{}: {e}", parent.display())))?;
    }
    let _guard = lock_base_checkout(&lock)?;
    checkout_base(wt, wt_path, &dir, oid)?;
    share_build_dir(common, &dir);
    let result = frob_check::run(
        &dir,
        &CheckOptions {
            ledger: Some(ledger.clone()),
            skip_telemetry: true,
            skip_tools,
            ..CheckOptions::default()
        },
    );
    Ok(notes(&result?))
}

/// Point `checkout`'s `target/` at the repository-shared land target directory when it has none.
///
/// Every land checkout (the ticket worktree and the persistent base checkout) then reuses the
/// registry dependency builds of every earlier land instead of compiling from an empty
/// directory (measured: 45-200 s per cold pass, ~TSK0M4Y, ~8J3BE8W). An existing `target`
/// (a real directory or a link) is left alone. Failures are logged and the checks run cold.
// frob:ticket 01M4D6NFCDSW5E4FD9X8J3BE8W
// frob:ticket 01M4H8NECMX7XBS1J6FDWRJEZV
pub(crate) fn share_build_dir(common: &Path, checkout: &Path) {
    let link = checkout.join("target");
    if let Ok(meta) = std::fs::symlink_metadata(&link) {
        if meta.file_type().is_symlink() && std::fs::metadata(&link).is_err() {
            tracing::warn!(link = %link.display(), "dangling build directory link; repairing");
            if let Err(e) = std::fs::remove_file(&link) {
                tracing::warn!(error = %e, "dangling link not removed; cargo stages run cold");
                return;
            }
        } else {
            tracing::debug!(link = %link.display(), "checkout already has a build directory");
            return;
        }
    }
    let shared = common.join("frob").join(SHARED_TARGET_DIR);
    if let Err(e) = std::fs::create_dir_all(&shared) {
        tracing::warn!(error = %e, dir = %shared.display(), "shared build directory not created; cargo stages run cold");
        return;
    }
    // Canonical and absolute: `common` may be spelled through a worktree's git dir
    // (`.git/worktrees/<T>/../..`), which dangles once that worktree is removed.
    let shared = match gob_exec::canonical(&shared) {
        Ok(p) => p,
        Err(e) => {
            tracing::warn!(error = %e, dir = %shared.display(), "shared build directory not canonicalized; cargo stages run cold");
            return;
        }
    };
    exclude_target(common);
    #[cfg(unix)]
    match std::os::unix::fs::symlink(&shared, &link) {
        Ok(()) => {
            tracing::info!(shared = %shared.display(), checkout = %checkout.display(), "checkout shares the land build directory");
        }
        Err(e) => {
            tracing::warn!(error = %e, "build directory not shared; cargo stages run cold");
        }
    }
    #[cfg(not(unix))]
    tracing::debug!(shared = %shared.display(), checkout = %checkout.display(), "build directory sharing is unix-only");
}

/// Make git ignore a `/target` entry of any kind: the `target/` pattern of a `.gitignore` matches
/// directories only, so the shared-build symlink would show as an untracked file (and as a SCOPE001 target).
fn exclude_target(common: &Path) {
    let path = common.join("info").join("exclude");
    let text = std::fs::read_to_string(&path).unwrap_or_default();
    if text.lines().any(|l| l.trim() == "/target") {
        return;
    }
    let mut next = text;
    if !next.is_empty() && !next.ends_with('\n') {
        next.push('\n');
    }
    next.push_str("/target\n");
    let result =
        std::fs::create_dir_all(common.join("info")).and_then(|()| std::fs::write(&path, next));
    match result {
        Ok(()) => {
            tracing::info!(path = %path.display(), "excluded /target for the shared build link");
        }
        Err(e) => tracing::warn!(path = %path.display(), error = %e, "could not exclude /target"),
    }
}

/// The ratchet's decision for one land.
#[derive(Debug, Default)]
pub(crate) struct Verdict {
    /// Blocking findings absent from the base: ticket-only findings and head findings the base lacks.
    pub new: Vec<FindingNote>,
    /// Blocking head findings already on the base.
    pub pre_existing: Vec<FindingNote>,
    /// Base findings no longer present at the head.
    pub resolved: Vec<FindingNote>,
    /// Findings of the ticket-scoped run below the gate (counted in the refusal).
    pub non_blocking: usize,
}

/// Notes of the findings of `report` that fail the gate (its own `fail_on` predicate, one finding at a time).
fn blocking(report: &CheckReport) -> Vec<FindingNote> {
    if report.exit_code() == gob_diagnostics::ExitCode::Ok {
        return Vec::new();
    }
    report
        .findings
        .iter()
        .zip(notes(report))
        .filter(|(f, _)| {
            gob_diagnostics::fail_on(
                std::slice::from_ref(*f),
                report.fail_on.threshold(),
                report.fail_on_unresolved,
            ) != gob_diagnostics::ExitCode::Ok
        })
        .map(|(_, n)| n)
        .collect()
}

/// Decide the ratchet: compare the unscoped `head` run with the unscoped `base` set, and add the
/// ticket-only blocking findings of the `scoped` run (a located finding the unscoped run lacks, or a
/// location-free one of a rule the unscoped run never produces, such as SCOPE001); a location-free
/// finding of a rule both runs produce is judged on the unscoped side only, so repository-level text
/// that differs between the two runs cannot read as new.
pub(crate) fn verdict(scoped: &CheckReport, head: &CheckReport, base: &[FindingNote]) -> Verdict {
    let mut budget = counts(base);
    let head_notes = notes(head);
    let head_fps: HashSet<&str> = head_notes.iter().map(|n| n.fingerprint.as_str()).collect();
    let head_rules: HashSet<&str> = head_notes.iter().map(|n| n.rule.as_str()).collect();
    let scoped_blocking = blocking(scoped);
    let mut out = Verdict {
        non_blocking: scoped.findings.len() - scoped_blocking.len(),
        ..Verdict::default()
    };
    let mut seen = HashSet::new();
    for n in scoped_blocking {
        let ticket_only = !head_fps.contains(n.fingerprint.as_str())
            && (n.path.is_some() || !head_rules.contains(n.rule.as_str()));
        if ticket_only && seen.insert(n.fingerprint.clone()) {
            out.new.push(n);
        }
    }
    // Multiset comparison: each base occurrence of a fingerprint absorbs one head occurrence.
    for n in blocking(head) {
        match budget.get_mut(n.fingerprint.as_str()) {
            Some(left) if *left > 0 => {
                *left -= 1;
                out.pre_existing.push(n);
            }
            _ => out.new.push(n),
        }
    }
    let mut head_left = counts(&head_notes);
    for n in base {
        match head_left.get_mut(n.fingerprint.as_str()) {
            Some(left) if *left > 0 => *left -= 1,
            _ => out.resolved.push(n.clone()),
        }
    }
    out
}

/// How many times each fingerprint occurs in `notes`.
fn counts(notes: &[FindingNote]) -> HashMap<&str, usize> {
    let mut m = HashMap::new();
    for n in notes {
        *m.entry(n.fingerprint.as_str()).or_insert(0) += 1;
    }
    m
}

#[cfg(test)]
mod count_tests {
    use super::*;

    fn note(fp: &str) -> FindingNote {
        FindingNote {
            fingerprint: fp.to_owned(),
            rule: "X001".to_owned(),
            path: Some("a.rs".to_owned()),
            message: "m".to_owned(),
        }
    }

    // frob:tests crates/frob-land/src/ratchet.rs::counts
    #[test]
    fn counts_are_per_fingerprint_multiplicities() {
        let notes = [note("x"), note("x"), note("y")];
        let c = counts(&notes);
        assert_eq!((c["x"], c["y"]), (2, 1));
    }

    // frob:tests crates/frob-land/src/ratchet.rs::cache_key
    #[test]
    fn a_new_engine_invalidates_the_cached_base_set() {
        // frob:ticket 01M4HDXNTJQ77R9Z81VVNK49V8
        let cfg = LedgerConfig::default();
        let old = cache_key_for("gob-cache/0.532.0/exe:1-1", &cfg);
        let new = cache_key_for("gob-cache/0.532.0/exe:2-2", &cfg);
        assert_eq!(old, cache_key_for("gob-cache/0.532.0/exe:1-1", &cfg));
        assert_ne!(old, new, "same version, rebuilt binary");
        let tmp = tempfile::tempdir().expect("tempdir");
        let path = tmp.path().join("s.json");
        let set = BaseSet {
            oid: "o".to_owned(),
            key: old.clone(),
            findings: vec![note("x")],
        };
        write_cache(&path, &set);
        assert!(read_cache(&path, "o", &old).is_some());
        assert!(read_cache(&path, "o", &new).is_none());
    }

    // frob:tests crates/frob-land/src/ratchet.rs::cache_key
    #[test]
    fn a_config_change_invalidates_the_cached_base_set() {
        let a = LedgerConfig::default();
        let b = LedgerConfig {
            dir: "other".to_owned(),
            ..LedgerConfig::default()
        };
        assert_eq!(cache_key(&a), cache_key(&a));
        assert_ne!(cache_key(&a), cache_key(&b));
        let tmp = tempfile::tempdir().expect("tempdir");
        let path = tmp.path().join("s.json");
        let set = BaseSet {
            oid: "o".to_owned(),
            key: cache_key(&a),
            findings: vec![note("x")],
        };
        write_cache(&path, &set);
        assert!(read_cache(&path, "o", &cache_key(&a)).is_some());
        assert!(read_cache(&path, "o", &cache_key(&b)).is_none());
    }
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;

    // frob:tests crates/frob-land/src/ratchet.rs::share_build_dir
    #[test]
    fn a_checkout_without_a_target_shares_the_land_target_and_one_with_keeps_its_own() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let (common, a, b) = (
            tmp.path().join("common"),
            tmp.path().join("a"),
            tmp.path().join("b"),
        );
        for d in [&common, &a, &b] {
            std::fs::create_dir_all(d).expect("dir");
        }
        share_build_dir(&common, &a);
        let shared = common.join("frob").join(SHARED_TARGET_DIR);
        std::fs::write(shared.join("marker"), "x").expect("marker");
        share_build_dir(&common, &b);
        assert!(a.join("target").join("marker").is_file());
        assert!(b.join("target").join("marker").is_file(), "same directory");
        // A real directory is never replaced.
        let c = tmp.path().join("c");
        std::fs::create_dir_all(c.join("target")).expect("own target");
        share_build_dir(&common, &c);
        assert!(
            !std::fs::symlink_metadata(c.join("target"))
                .expect("meta")
                .file_type()
                .is_symlink()
        );
    }

    // frob:tests crates/frob-land/src/ratchet.rs::share_build_dir
    #[test]
    fn the_link_is_canonical_and_a_dangling_link_is_repaired() {
        // frob:ticket 01M4H8NECMX7XBS1J6FDWRJEZV
        let tmp = tempfile::tempdir().expect("tempdir");
        let common = tmp.path().join("common");
        let a = tmp.path().join("a");
        for d in [&common, &a, &common.join("worktrees").join("T")] {
            std::fs::create_dir_all(d).expect("dir");
        }
        // The common dir spelled through a worktree git dir, as a worktree's own repo reports it.
        let via_wt = common.join("worktrees").join("T").join("..").join("..");
        share_build_dir(&via_wt, &a);
        let target = std::fs::read_link(a.join("target")).expect("link");
        let want = gob_exec::canonical(&common)
            .expect("canon")
            .join("frob")
            .join(SHARED_TARGET_DIR);
        assert_eq!(target, want, "absolute, no .. through the worktree dir");
        // A dangling link (its old target is gone) is replaced.
        let b = tmp.path().join("b");
        std::fs::create_dir_all(&b).expect("dir");
        std::os::unix::fs::symlink(
            tmp.path().join("gone").join("land-target"),
            b.join("target"),
        )
        .expect("dangling");
        share_build_dir(&common, &b);
        assert_eq!(std::fs::read_link(b.join("target")).expect("link"), want);
        assert!(b.join("target").is_dir());
    }

    // frob:tests crates/frob-land/src/ratchet.rs::base_checkout_paths
    #[test]
    fn the_base_checkout_path_is_stable_and_outside_the_gc_swept_prefix() {
        let (dir, lock) = base_checkout_paths(Path::new("/g"));
        assert_eq!(dir, Path::new("/g/frob").join(BASE_CHECKOUT_DIR));
        assert_ne!(dir, lock);
        assert!(!BASE_CHECKOUT_DIR.starts_with("land-base-"));
    }
}
