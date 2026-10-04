//! The land ratchet: land refuses only findings the ticket introduces (rules.md section 6, ~QAFRXM3).
//!
//! The base side is the same check run without a ticket scope on the base tip,
//! in a throwaway detached worktree under the git common dir. Its finding
//! fingerprints are cached per base commit in `<worktree>/.frob/land-base/<oid>.json`,
//! so a second land on the same base (or a `--wait` retry that did not move it)
//! costs nothing; a moved base has a new oid and so is recomputed.

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
    let cache = wt_path
        .join(".frob")
        .join("land-base")
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

/// Findings of `head` that are absent from `base` (new) and present in it (pre-existing).
pub(crate) fn split<'a, T>(
    head: impl IntoIterator<Item = (T, &'a str)>,
    base: &[FindingNote],
) -> (Vec<T>, Vec<T>) {
    let known: HashSet<&str> = base.iter().map(|n| n.fingerprint.as_str()).collect();
    let (mut new, mut old) = (Vec::new(), Vec::new());
    for (item, fp) in head {
        if known.contains(fp) {
            old.push(item);
        } else {
            new.push(item);
        }
    }
    (new, old)
}

/// Base findings gone at the head: located in a path the ticket changed and absent from `head`.
///
/// Location-free findings are never reported resolved: the scoped head run and the
/// unscoped base run do not evaluate the same repository-level rules.
pub(crate) fn resolved(
    base: &[FindingNote],
    head: &[FindingNote],
    changed: &HashSet<String>,
) -> Vec<FindingNote> {
    let now: HashSet<&str> = head.iter().map(|n| n.fingerprint.as_str()).collect();
    base.iter()
        .filter(|n| !now.contains(n.fingerprint.as_str()))
        .filter(|n| n.path.as_ref().is_some_and(|p| changed.contains(p)))
        .cloned()
        .collect()
}
