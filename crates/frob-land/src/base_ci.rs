//! The base-CI gate: land refuses onto a base whose latest CI run is red (audit H1, ~GHMWDGG).
//!
//! The commit inspected is the tip of `refs/remotes/origin/<base>` (what GitHub has run CI for;
//! the local tip when there is no remote-tracking ref). CI is read through a [`CiReader`], by
//! default the GitHub CLI via `frob_release::ci::check_tip`, so tests inject a canned reader and
//! never touch the network.
//!
//! Which checks count is configured by `[land]` read from the committed base `frob.toml`:
//! `ci_required` (name patterns; empty means every check) minus `ci_ignore` (default
//! `*publish*` and `*release*`, so a failing publish or release job does not block a land
//! while a failing build or test job does). A pattern is a case-insensitive glob where `*`
//! matches any run of characters. An unreadable CI state (no `gh`, no network, no origin, no
//! checks) is never treated as green: by default it is reported as Unresolved in the warnings
//! and the land proceeds; `block_on_unknown_ci = true` refuses instead.

// frob:ticket 01M4CTDWJRKBC64EBQPGHMWDGG
use std::fmt::Debug;
use std::path::Path;

use frob_ledger::Ledger;
use frob_ledger::index::ListFilter;
use frob_ledger::model::{Category, TicketType};
use frob_ledger::ops::NewTicket;
use frob_release::ci::{CiState, check_tip, list_runs};
use frob_release::culprit::{BLOCKS_LANDS_LABEL, Commit, RunRecord, find_culprit};
use gob_config::ConfigTable;
use gob_exec::Program;
use gob_git::Repo;

use crate::error::{LandError, needs_action};
use crate::git::git;

/// Stable code of the refusal when a required base CI check failed.
pub const CODE_BASE_RED: &str = "E-LAND-BASE-RED";

/// Stable code of the refusal when base CI is unreadable and `block_on_unknown_ci` is set.
pub const CODE_BASE_UNKNOWN: &str = "E-LAND-BASE-CI-UNKNOWN";

/// The `[land]` table: which base CI checks gate a land and what an unreadable state does.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "land")]
pub struct LandConfig {
    /// Refuse a land whose base tip has a failing required CI check; false turns the whole gate off.
    #[config(default = true, enforcement)]
    pub require_base_green: bool,
    /// Check-name patterns (`*` wildcard, case-insensitive) that count toward the gate; empty means every check.
    #[config(default = Vec::<String>::new(), enforcement)]
    pub ci_required: Vec<String>,
    /// Check-name patterns that never block a land (publish and release jobs by default, which test no code).
    #[config(default = vec!["*publish*".to_owned(), "*release*".to_owned()], enforcement)]
    pub ci_ignore: Vec<String>,
    /// When base CI cannot be read: false reports it as Unresolved and lands anyway, true refuses.
    #[config(default = false, enforcement)]
    pub block_on_unknown_ci: bool,
}

/// Reads the CI state of one commit; injectable so tests never use the network.
pub trait CiReader: Send + Sync + Debug {
    /// The CI verdict of `sha` for the repository `repo` (`cwd` is a checkout of it).
    fn read(&self, repo: &Repo, cwd: &Path, sha: &str) -> CiState;

    /// The latest workflow runs of `branch`, newest first, for culprit finding; `None` when they cannot be read.
    fn runs(&self, _repo: &Repo, _cwd: &Path, _branch: &str) -> Option<Vec<RunRecord>> {
        None
    }
}

/// The production reader: the GitHub CLI against origin.
#[derive(Debug, Clone, Copy, Default)]
pub struct GhCli;

impl CiReader for GhCli {
    fn read(&self, repo: &Repo, cwd: &Path, sha: &str) -> CiState {
        check_tip(
            repo.runner(),
            &Program::Tool {
                name: "gh".to_owned(),
            },
            cwd,
            repo.remote_url("origin").as_deref(),
            sha,
        )
    }

    fn runs(&self, repo: &Repo, cwd: &Path, branch: &str) -> Option<Vec<RunRecord>> {
        match list_runs(
            repo.runner(),
            &Self::gh(),
            cwd,
            repo.remote_url("origin").as_deref(),
            branch,
        ) {
            Ok(runs) => Some(runs),
            Err(u) => {
                tracing::warn!(reason = %u.reason, "workflow runs unreadable; no culprit finding");
                None
            }
        }
    }
}

impl GhCli {
    fn gh() -> Program {
        Program::Tool {
            name: "gh".to_owned(),
        }
    }
}

/// What the gate decided when it did not refuse.
#[derive(Debug, Default)]
pub(crate) struct Gate {
    /// Notices for the land result.
    pub warnings: Vec<String>,
    /// The audit note to record on the ticket when the gate was overridden.
    pub override_note: Option<String>,
}

/// True when `name` matches the case-insensitive wildcard `pattern`.
fn wild(pattern: &str, name: &str) -> bool {
    let (p, n) = (pattern.to_lowercase(), name.to_lowercase());
    let parts: Vec<&str> = p.split('*').collect();
    let [first, rest @ ..] = parts.as_slice() else {
        return false;
    };
    let Some(mut tail) = n.strip_prefix(first) else {
        return false;
    };
    let Some((last, middle)) = rest.split_last() else {
        return tail.is_empty();
    };
    for part in middle {
        match tail.find(part) {
            Some(i) => tail = &tail[i + part.len()..],
            None => return false,
        }
    }
    tail.ends_with(last)
}

impl LandConfig {
    /// True when a check called `name` counts toward the gate.
    fn counts(&self, name: &str) -> bool {
        let wanted = self.ci_required.is_empty() || self.ci_required.iter().any(|p| wild(p, name));
        wanted && !self.ci_ignore.iter().any(|p| wild(p, name))
    }
}

/// Judge `state` of `sha` under `cfg`; `override_reason` lets a red or unreadable base through, audited.
pub(crate) fn judge(
    cfg: &LandConfig,
    state: CiState,
    sha: &str,
    override_reason: Option<&str>,
) -> Result<Gate, LandError> {
    let mut gate = Gate::default();
    let short = &sha[..sha.len().min(12)];
    match state {
        CiState::Green { checks } => {
            tracing::info!(sha = short, checks, "base CI green");
        }
        CiState::Pending { running } => {
            let relevant: Vec<&String> = running.iter().filter(|n| cfg.counts(n)).collect();
            if !relevant.is_empty() {
                gate.warnings.push(format!(
                    "base CI at {short} has not finished: {}",
                    join(relevant)
                ));
            }
        }
        CiState::Red { failures } => {
            let (counted, ignored): (Vec<_>, Vec<_>) =
                failures.into_iter().partition(|f| cfg.counts(&f.name));
            if !ignored.is_empty() {
                gate.warnings.push(format!(
                    "base CI at {short} has failing checks that do not gate a land: {}",
                    join(ignored.iter().map(|f| &f.name))
                ));
            }
            if !counted.is_empty() {
                let named = counted
                    .iter()
                    .map(|f| {
                        format!(
                            "{} ({}){}",
                            f.name,
                            f.conclusion,
                            f.url
                                .as_deref()
                                .map(|u| format!(" {u}"))
                                .unwrap_or_default()
                        )
                    })
                    .collect::<Vec<_>>()
                    .join("; ");
                if let Some(reason) = override_reason {
                    tracing::warn!(sha = short, %named, reason, "base CI red; land overridden");
                    gate.warnings.push(format!(
                        "base CI at {short} is red but the land was overridden: {named}"
                    ));
                    gate.override_note = Some(format!(
                        "land overrode a red base CI at {short} ({named}): {reason}"
                    ));
                } else {
                    tracing::warn!(sha = short, %named, "base CI red; land refused");
                    return Err(needs_action(
                        CODE_BASE_RED,
                        format!("the latest CI run on the base at {short} is red: {named}"),
                        "fix the base (a fix-forward ticket), wait for green, add the job to `[land] ci_ignore` if it tests no code, or rerun with `--override-base-ci --reason <text>`",
                    ));
                }
            }
        }
        CiState::Unknown(u) => {
            let msg = format!(
                "base CI at {short} could not be read: {} ({})",
                u.reason, u.remedy
            );
            if cfg.block_on_unknown_ci && override_reason.is_none() {
                return Err(needs_action(
                    CODE_BASE_UNKNOWN,
                    msg,
                    "make CI readable (`gh auth login`, network, origin), set `[land] block_on_unknown_ci = false`, or rerun with `--override-base-ci --reason <text>`",
                ));
            }
            tracing::warn!(sha = short, reason = %u.reason, "base CI unreadable; Unresolved");
            gate.warnings.push(format!("Unresolved: {msg}"));
            if cfg.block_on_unknown_ci {
                gate.override_note = override_reason
                    .map(|r| format!("land overrode an unreadable base CI at {short}: {r}"));
            }
        }
    }
    Ok(gate)
}

/// Names joined for a message.
fn join<'a>(names: impl IntoIterator<Item = &'a String>) -> String {
    names
        .into_iter()
        .map(String::as_str)
        .collect::<Vec<_>>()
        .join(", ")
}

/// The first-parent history of `base`, newest first, as culprit finding wants it.
fn history(wt: &Repo, cwd: &Path, base: &str) -> Vec<Commit> {
    let range = format!("refs/heads/{base}");
    let run = git(
        wt,
        cwd,
        &[
            "log",
            "--first-parent",
            "-n",
            "200",
            "--format=%H%x09%s",
            &range,
        ],
    );
    let Ok(run) = run else {
        return Vec::new();
    };
    run.text
        .lines()
        .filter_map(|l| l.split_once('\t'))
        .map(|(sha, subject)| Commit {
            sha: sha.to_owned(),
            subject: subject.to_owned(),
        })
        .collect()
}

/// Open tickets that block lands (carry [`BLOCKS_LANDS_LABEL`]) other than the one landing.
fn open_blockers(ledger: &Ledger, landing: &str) -> Vec<String> {
    let filter = ListFilter {
        label: Some(BLOCKS_LANDS_LABEL.to_owned()),
        ..ListFilter::default()
    };
    match ledger.list(&filter) {
        Ok(all) => all
            .into_iter()
            .filter(|t| t.category != Category::Done && t.handle != landing)
            .map(|t| t.handle)
            .collect(),
        Err(e) => {
            tracing::warn!(error = %e, "blocking tickets unreadable; not gating on them");
            Vec::new()
        }
    }
}

// frob:ticket 01M4GWS3GBJTFXFEGSNFB7J4FQ
/// Add the culprit range to a red-base refusal and file the blocking fix ticket (idempotent on the first-red sha).
///
/// Any failure to read runs, find the range or file the ticket leaves the refusal as it was.
fn with_culprit(
    err: LandError,
    reader: &dyn CiReader,
    (wt, cwd, base): (&Repo, &Path, &str),
    ledger: &Ledger,
) -> LandError {
    let Some(refusal) = err.refusal() else {
        return err;
    };
    let Some(runs) = reader.runs(wt, cwd, base) else {
        return err;
    };
    let culprit = match find_culprit(&runs, &history(wt, cwd, base)) {
        Ok(c) => c,
        Err(e) => {
            tracing::info!(error = %e, "no culprit range named");
            return err;
        }
    };
    let mut req = NewTicket::new(culprit.fix.title.clone(), TicketType::Bug);
    req.body.clone_from(&culprit.fix.body);
    req.labels.clone_from(&culprit.fix.labels);
    req.idempotency_key = Some(culprit.fix.idempotency_key.clone());
    req.priority = frob_ledger::model::Priority::High;
    let handle = match ledger.new_ticket(req) {
        Ok(applied) => {
            tracing::info!(handle = %applied.handle, already = applied.already, "fix ticket for the red base");
            applied.handle
        }
        Err(e) => {
            tracing::warn!(error = %e, "fix ticket not filed");
            return err;
        }
    };
    let lands = culprit
        .lands
        .iter()
        .map(|c| format!("{} {}", &c.sha[..c.sha.len().min(9)], c.subject))
        .collect::<Vec<_>>()
        .join("; ");
    let message = format!(
        "{}; land commits since the last green run: {}; fix ticket {handle} blocks lands until it closes",
        refusal.message,
        if lands.is_empty() { "none" } else { &lands }
    );
    needs_action(
        CODE_BASE_RED,
        message,
        format!("land the fix for {handle} (it may land while the base is red), then rerun"),
    )
}

/// Run the gate for `base`: read the config from the committed base, the CI of its pushed tip, and judge.
///
/// `landing` is the handle of the ticket being landed: an open `blocks-lands` ticket other than it
/// blocks the land (the fix ticket itself may land).
pub(crate) fn gate(
    wt: &Repo,
    cwd: &Path,
    base: &str,
    reader: Option<&dyn CiReader>,
    override_reason: Option<&str>,
    (ledger, landing): (&Ledger, &str),
) -> Result<Gate, LandError> {
    let label = Path::new("frob.toml");
    let base_ref = format!("refs/heads/{base}");
    let text = match wt.read_blob_at(&base_ref, "frob.toml")? {
        Some(bytes) => String::from_utf8(bytes)
            .map_err(|e| LandError::Config(format!("{base}:frob.toml is not UTF-8: {e}")))?,
        None => String::new(),
    };
    let cfg = gob_config::load_str::<LandConfig>(&text, label)
        .map_err(|e| LandError::Config(format!("{base}:frob.toml: {e}")))?
        .value;
    if !cfg.require_base_green {
        tracing::info!("base CI gate off ([land] require_base_green = false)");
        return Ok(Gate::default());
    }
    let blockers = open_blockers(ledger, landing);
    if !blockers.is_empty() && override_reason.is_none() {
        let named = blockers.join(", ");
        tracing::warn!(%named, "lands blocked by an open fix ticket");
        return Err(needs_action(
            CODE_BASE_RED,
            format!("lands are blocked until the fix ticket closes: {named}"),
            format!("land and close {named}, or rerun with `--override-base-ci --reason <text>`"),
        ));
    }
    let sha = wt
        .rev_parse(&format!("refs/remotes/origin/{base}"))
        .or_else(|_| wt.rev_parse(&base_ref))?
        .to_string();
    let default_reader = GhCli;
    let reader: &dyn CiReader = reader.unwrap_or(&default_reader);
    let state = reader.read(wt, cwd, &sha);
    match judge(&cfg, state, &sha, override_reason) {
        Err(e) if e.refusal().is_some_and(|r| r.code == CODE_BASE_RED) => {
            Err(with_culprit(e, reader, (wt, cwd, base), ledger))
        }
        other => other,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use frob_release::ci::{CiFailure, CiUnknown};

    fn cfg() -> LandConfig {
        gob_config::load_str::<LandConfig>("", Path::new("frob.toml"))
            .expect("defaults")
            .value
    }

    fn fail(name: &str) -> CiFailure {
        CiFailure {
            name: name.to_owned(),
            conclusion: "failure".to_owned(),
            url: Some(format!("https://example.test/run/{name}")),
        }
    }

    // frob:tests crates/frob-land/src/base_ci.rs::wild
    #[test]
    fn wildcards_match_case_insensitively() {
        assert!(wild("*publish*", "dev-Publish"));
        assert!(wild("rust (*)", "rust (windows-latest)"));
        assert!(wild("exact", "EXACT"));
        assert!(!wild("exact", "exact2"));
        assert!(!wild("*publish*", "rust (windows-latest)"));
        assert!(wild("a*b*c", "aXbYc"));
        assert!(!wild("a*b*c", "aXcYb"));
    }

    // frob:tests crates/frob-land/src/base_ci.rs::judge
    #[test]
    fn a_failing_code_job_refuses_naming_the_run_url() {
        let red = CiState::Red {
            failures: vec![fail("rust (windows-latest)")],
        };
        let e = judge(&cfg(), red, "abcdef0123456789", None).expect_err("refused");
        let r = e.refusal().expect("refusal");
        assert_eq!(r.code, CODE_BASE_RED);
        assert!(
            r.message
                .contains("https://example.test/run/rust (windows-latest)")
        );
    }

    // frob:tests crates/frob-land/src/base_ci.rs::judge
    #[test]
    fn a_publish_only_failure_does_not_block() {
        let red = CiState::Red {
            failures: vec![fail("dev-publish")],
        };
        let g = judge(&cfg(), red, "abcdef0123456789", None).expect("not blocked");
        assert!(
            g.warnings.iter().any(|w| w.contains("dev-publish")),
            "{:?}",
            g.warnings
        );
    }

    // frob:tests crates/frob-land/src/base_ci.rs::judge
    #[test]
    fn a_required_list_narrows_the_gate_to_the_named_jobs() {
        let mut c = cfg();
        c.ci_required = vec!["rust *".to_owned()];
        let lint = CiState::Red {
            failures: vec![fail("docs")],
        };
        assert!(judge(&c, lint, "abcdef0123456789", None).is_ok());
        let rust = CiState::Red {
            failures: vec![fail("rust (linux)")],
        };
        assert!(judge(&c, rust, "abcdef0123456789", None).is_err());
    }

    // frob:tests crates/frob-land/src/base_ci.rs::judge
    #[test]
    fn unknown_is_unresolved_by_default_and_refuses_when_configured() {
        let unknown = || {
            CiState::Unknown(CiUnknown {
                reason: "gh missing".to_owned(),
                remedy: "install gh".to_owned(),
            })
        };
        let g = judge(&cfg(), unknown(), "abcdef0123456789", None).expect("proceeds");
        assert!(g.warnings[0].starts_with("Unresolved:"), "{:?}", g.warnings);
        let mut strict = cfg();
        strict.block_on_unknown_ci = true;
        let e = judge(&strict, unknown(), "abcdef0123456789", None).expect_err("blocked");
        assert_eq!(e.refusal().expect("refusal").code, CODE_BASE_UNKNOWN);
    }

    // frob:tests crates/frob-land/src/base_ci.rs::judge
    #[test]
    fn an_override_lets_a_red_base_through_with_an_audit_note() {
        let red = CiState::Red {
            failures: vec![fail("rust (windows-latest)")],
        };
        let g = judge(&cfg(), red, "abcdef0123456789", Some("hotfix")).expect("overridden");
        assert!(g.override_note.expect("note").contains("hotfix"));
    }
}
