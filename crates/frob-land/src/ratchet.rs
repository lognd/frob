//! The land ratchet: land refuses only findings the ticket introduces (rules.md section 6, ~QAFRXM3).
//!
//! The base side is the same check run without a ticket scope on the base tip,
//! in a throwaway detached worktree under the git common dir. Its finding
//! fingerprints are cached per base commit in `<git common dir>/frob/land-base/<oid>.json`,
//! shared by every worktree, so a second land on the same base (from any ticket, or a `--wait`
//! retry that did not move it) costs nothing; a moved base has a new oid and so is recomputed.
//! The throwaway worktree's check opens the repository-shared cache (gob-cache), so every file
//! unchanged since an earlier check is a cache hit (~TSK0M4Y).

use std::collections::HashSet;
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
    /// Full commit oid the set belongs to.
    oid: String,
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

/// The unscoped findings at the base commit `oid`, from the cache or a fresh run.
pub(crate) fn base_findings(
    wt: &Repo,
    wt_path: &Path,
    oid: &str,
    ledger: &LedgerConfig,
) -> Result<Vec<FindingNote>, LandError> {
    let cache = wt
        .common_dir()
        .join(gob_cache::SHARED_DIR)
        .join(LAND_BASE_DIR)
        .join(format!("{oid}.json"));
    if let Some(set) = read_cache(&cache, oid) {
        tracing::info!(
            oid,
            findings = set.findings.len(),
            "land base set from cache"
        );
        return Ok(set.findings);
    }
    let findings = run_at_base(wt, wt_path, oid, ledger)?;
    write_cache(
        &cache,
        &BaseSet {
            oid: oid.to_owned(),
            findings: findings.clone(),
        },
    );
    Ok(findings)
}

/// Read a cached set, ignoring a missing, unreadable or mismatched file.
fn read_cache(path: &Path, oid: &str) -> Option<BaseSet> {
    let text = std::fs::read_to_string(path).ok()?;
    match serde_json::from_str::<BaseSet>(&text) {
        Ok(set) if set.oid == oid => Some(set),
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
    let known: HashSet<&str> = base.iter().map(|n| n.fingerprint.as_str()).collect();
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
    for n in blocking(head) {
        if !seen.insert(n.fingerprint.clone()) {
            continue;
        }
        if known.contains(n.fingerprint.as_str()) {
            out.pre_existing.push(n);
        } else {
            out.new.push(n);
        }
    }
    out.resolved = base
        .iter()
        .filter(|n| !head_fps.contains(n.fingerprint.as_str()))
        .cloned()
        .collect();
    out
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
