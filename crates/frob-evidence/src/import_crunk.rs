//! Selective import of the crunk repository's v1 tickets (`lognd/crunk`, `tickets/`), ~JBTM6EF.
//!
//! The crunk ledger is a v1 ledger, so the conversion is [`crate::import_v1`] unchanged; this module
//! adds the three things that are specific to a second source: fetching the tickets read-only
//! through `gh` ([`fetch`], one shallow clone, so there is no pagination),
//! the options that namespace every alias by source (`crunk:T-0042`, so it can never equal a
//! frob `T-0042`) and stamp `component:crunk`, and the per-ticket disposition listing of a dry run
//! ([`render_dispositions`]), which shows every ticket kept out of open work together with its reason.
//!
//! Re-running is safe: with `merge` set the second run finds its aliases already in the ledger and
//! refuses (`ImportError::Collision`) instead of writing duplicates.

// frob:ticket 01M43AVMN1DWBVTYW37JBTM6EF
use std::path::{Path, PathBuf};
use std::time::Duration;

use crate::import_v1::{ImportError, ImportOptions, ImportReport};
use frob_ledger::model::Category;
use gob_exec::{Limits, Outcome, Program, Runner, Spec};

/// The GitHub repository the tickets come from.
pub const REPO: &str = "lognd/crunk";

/// Namespace of every imported alias: `crunk:` plus the source id.
pub const ALIAS_PREFIX: &str = "crunk:";

/// Label every imported ticket carries so the source stays queryable.
pub const COMPONENT_LABEL: &str = "component:crunk";

/// Label naming the source repository of an imported ticket.
pub const SOURCE_LABEL: &str = "source:crunk";

fn io(path: &Path, message: impl Into<String>) -> ImportError {
    ImportError::Io {
        path: gob_path::Shown::with_home(path, None).to_string(),
        message: message.into(),
    }
}

/// Import options for a crunk run: `from` is the extracted `tickets/` directory, `to` the v2 ledger.
#[must_use]
pub fn options(
    from: PathBuf,
    to: PathBuf,
    selection: PathBuf,
    dry_run: bool,
    privacy_dir: Option<PathBuf>,
) -> ImportOptions {
    ImportOptions {
        from,
        to,
        dry_run,
        selection: Some(selection),
        privacy_dir,
        merge: true,
        open_category: Category::Todo,
        alias_prefix: Some(ALIAS_PREFIX.to_owned()),
        extra_labels: vec![COMPONENT_LABEL.to_owned(), SOURCE_LABEL.to_owned()],
    }
}

/// Arguments of the shallow, read-only `gh repo clone` that fetches `repo` at `git_ref` into `dest`.
#[must_use]
pub fn clone_args(repo: &str, git_ref: &str, dest: &Path) -> Vec<String> {
    vec![
        "repo".to_owned(),
        "clone".to_owned(),
        repo.to_owned(),
        gob_path::Shown::with_home(dest, None).to_string(),
        "--".to_owned(),
        "--depth=1".to_owned(),
        "--single-branch".to_owned(),
        format!("--branch={git_ref}"),
    ]
}

/// Shallow-clone `repo` at `git_ref` with `gh` (read-only) into `work`; returns its `tickets` directory.
///
/// A clone rather than the REST contents API: no pagination, no truncated trees, one request.
///
/// # Errors
///
/// [`ImportError::Io`] when `gh` cannot run or fails, or the clone has no `tickets/` directory.
pub fn fetch(repo: &str, git_ref: &str, work: &Path) -> Result<PathBuf, ImportError> {
    let dest = work.join("src");
    tracing::info!(repo, git_ref, "cloning with gh");
    let spec = Spec {
        program: Program::Tool {
            name: "gh".to_owned(),
        },
        args: clone_args(repo, git_ref, &dest),
        cwd: None,
        env: Vec::new(),
        timeout: Duration::from_secs(300),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 })
        .run(&spec)
        .map_err(|e| io(work, format!("gh: {e}")))?;
    if out.status != Outcome::Exited(0) {
        return Err(io(work, format!("gh failed: {}", out.stderr.trim())));
    }
    let tickets = dest.join("tickets");
    if !tickets.is_dir() {
        return Err(io(&dest, "the repository has no tickets/ directory"));
    }
    Ok(tickets)
}

/// Lines listing every ticket kept out of open work with its disposition, cluster and reason.
///
/// Covers both the tickets not imported at all (skips) and the ones imported closed as wont-fix history.
#[must_use]
pub fn render_dispositions(report: &ImportReport) -> Vec<String> {
    let mut rows: Vec<_> = report.skipped.iter().chain(&report.wont_fix).collect();
    rows.sort_by(|a, b| a.v1.cmp(&b.v1));
    let mut out = vec![format!(
        "== open tickets kept out of open work ({}) ==",
        rows.len()
    )];
    out.push("id       disposition              cluster reason".to_owned());
    out.extend(rows.iter().map(|r| {
        format!(
            "{:<8} {:<24} {:<7} {}",
            r.v1, r.disposition, r.cluster, r.reason
        )
    }));
    out
}
