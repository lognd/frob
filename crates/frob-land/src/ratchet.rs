//! The land ratchet: land refuses only findings the ticket introduces (rules.md section 6, ~QAFRXM3).
//!
//! The base side is the same check run without a ticket scope on the base tip,
//! in a throwaway detached worktree under the git common dir. Its finding
//! fingerprints are cached per code tree (the base tree without the ledger directory), engine version and
//! config digest in `<git common dir>/frob/land-base/<tree>-<key>.json`, shared by every worktree, so a second land on
//! the same code (from any ticket, a ledger-only base commit, or a `--wait` retry that did not move it) costs
//! one cheap ledger-only run; a base with changed code, a new engine or a changed config has a new key and so is recomputed (~F4YA3S9).
//! Findings are compared as multisets: a second occurrence of a fingerprint the base has once is new.
//! The throwaway worktree's check opens the repository-shared cache (gob-cache), so every file
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

/// The cache key of a base set: engine version plus a digest of the ledger config the check runs with.
// frob:ticket 01M42MGPC19KXFQ0DS2F4YA3S9
#[must_use]
pub fn cache_key(ledger: &LedgerConfig) -> String {
    let mut h = blake3::Hasher::new();
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
/// Code-family findings (located outside the ledger directory, or without a
/// location) are cached under [`code_tree_key`], so ledger-only base commits hit.
/// Findings located inside the ledger directory depend on the exact commit and are
/// never cached: they come from the fresh run, or on a cache hit from a cheap
/// run at `oid` without the tool stages (the shared file cache makes it fast).
pub(crate) fn base_findings(
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
    let in_ledger = |n: &FindingNote| n.path.as_deref().is_some_and(|p| ledger.is_ledger_path(p));
    if let Some(set) = read_cache(&cache, &tree, &key) {
        tracing::info!(
            oid,
            tree,
            findings = set.findings.len(),
            "land base set from cache"
        );
        let mut findings = set.findings;
        let fresh = run_at_base(wt, wt_path, oid, ledger, true)?;
        findings.extend(fresh.into_iter().filter(|n| in_ledger(n)));
        return Ok(findings);
    }
    let all = run_at_base(wt, wt_path, oid, ledger, false)?;
    let code: Vec<FindingNote> = all.iter().filter(|n| !in_ledger(n)).cloned().collect();
    write_cache(
        &cache,
        &BaseSet {
            oid: tree,
            key,
            findings: code,
        },
    );
    Ok(all)
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

/// Check out `oid` detached in a throwaway worktree, run the unscoped check there and remove it again.
fn run_at_base(
    wt: &Repo,
    wt_path: &Path,
    oid: &str,
    ledger: &LedgerConfig,
    skip_tools: bool,
) -> Result<Vec<FindingNote>, LandError> {
    let dir: PathBuf = wt.common_dir().join("frob").join(format!(
        "land-base-{}-{}",
        &oid[..oid.len().min(12)],
        std::process::id()
    ));
    let dir_text = dir.to_string_lossy().into_owned();
    if let Some(parent) = dir.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| LandError::Config(format!("{}: {e}", parent.display())))?;
    }
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
    tracing::info!(oid, dir = %dir.display(), "land base checkout");
    share_build_dir(wt_path, &dir);
    let result = frob_check::run(
        &dir,
        &CheckOptions {
            ledger: Some(ledger.clone()),
            skip_telemetry: true,
            skip_tools,
            ..CheckOptions::default()
        },
    );
    let removed = git(wt, wt_path, &["worktree", "remove", "--force", &dir_text]);
    if !removed.as_ref().is_ok_and(crate::git::GitRun::ok) {
        tracing::warn!(dir = %dir.display(), "base checkout not removed; deleting directly");
        let _ = std::fs::remove_dir_all(&dir);
        let _ = git(wt, wt_path, &["worktree", "prune"]);
    }
    Ok(notes(&result?))
}

/// Point the base checkout's `target/` at the ticket worktree's, so the cargo tool stages of the
/// base check reuse the dependency builds the head checks just made instead of compiling the
/// workspace from nothing in a fresh directory (measured: minutes in a debug build, ~TSK0M4Y).
/// Only for a real `target/` directory; failures are logged and the base check simply runs cold.
// frob:ticket 01M42B6T28RX9PVM3X6TSK0M4Y
fn share_build_dir(wt_path: &Path, base_dir: &Path) {
    let from = wt_path.join("target");
    if !std::fs::symlink_metadata(&from).is_ok_and(|m| m.is_dir()) {
        tracing::debug!(from = %from.display(), "no build directory to share with the base checkout");
        return;
    }
    #[cfg(unix)]
    match std::os::unix::fs::symlink(&from, base_dir.join("target")) {
        Ok(()) => {
            tracing::info!(from = %from.display(), "base checkout shares the worktree's build directory");
        }
        Err(e) => {
            tracing::warn!(error = %e, "base checkout build directory not shared; its cargo stages run cold");
        }
    }
    #[cfg(not(unix))]
    tracing::debug!(base = %base_dir.display(), "build directory sharing is unix-only");
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
    fn the_base_checkout_shares_a_real_target_directory_and_only_then() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let (wt, base) = (tmp.path().join("wt"), tmp.path().join("base"));
        std::fs::create_dir_all(&wt).expect("wt");
        std::fs::create_dir_all(&base).expect("base");
        share_build_dir(&wt, &base);
        assert!(!base.join("target").exists(), "no target to share");
        std::fs::create_dir_all(wt.join("target")).expect("target");
        std::fs::write(wt.join("target").join("marker"), "x").expect("marker");
        share_build_dir(&wt, &base);
        assert!(base.join("target").join("marker").is_file());
        assert!(
            std::fs::symlink_metadata(base.join("target"))
                .expect("meta")
                .file_type()
                .is_symlink()
        );
    }
}
