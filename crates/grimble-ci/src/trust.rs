//! CI016: a privileged workflow runs frob, grimble or crunk with trust that is not `--trust-from`
//! a protected ref.
//!
//! A `pull_request_target` or `workflow_run` workflow holds a write token and secrets while it may
//! check out attacker-chosen files, so a check that reads its trust from the working tree (the
//! lock the pull request itself edits) lets the pull request grant itself tool execution. The only
//! CI trust flag is `check --trust-from <ref>`, which reads the lock at the ref (security.md 2.3
//! and 2.11, D82). The scan is lexical over `run:` scripts (`crate::verbs::calls`):
//!
//! - fires on `check` with no `--trust-from`, on `--trust-from` a ref that names the pull request
//!   head, on any other `--trust*` flag, and on the `trust` verb;
//! - is Unresolved when the ref is an expression or variable that is neither a head nor a base
//!   context, or when an `if:` guards the step on `head.repo.fork` or `ref_protected` (a condition
//!   this scan does not evaluate);
//! - skips `check --skip-tools` (no tool runs, so there is nothing to trust) and every workflow
//!   that is not triggered by a privileged event; a literal ref is taken as protected, because the
//!   workflow text cannot show branch protection.

// frob:ticket 01M5F010V5GV0B7KJ7M5QQG70Q

use gob_rules::{Severity, UnresolvedReason};
use grimble_verdict::Verdict;

use crate::finding::fire;
use crate::supply::{HEAD_MARKERS, PRIVILEGED_TRIGGERS};
use crate::verbs::{Call, calls};
use crate::workflow::{Workflow, key, run_of, scalar};

/// Rule id: privileged workflow trust must come from a protected ref.
pub const CI016: &str = "CI016";

/// The programs whose trust CI016 judges.
const PROGRAMS: [&str; 3] = ["frob", "grimble", "crunk"];

/// Lowercase context fragments that name the protected (base) side of a pull request.
const BASE_MARKERS: [&str; 3] = [
    "github.base_ref",
    "github.event.repository.default_branch",
    "github.event.pull_request.base.",
];

/// Refs git itself resolves to the checked-out head.
const HEAD_REFS: [&str; 4] = ["HEAD", "FETCH_HEAD", "MERGE_HEAD", "ORIG_HEAD"];

/// Condition fragments (lowercase) that gate a step on who opened the pull request or on ref protection.
const GUARDS: [&str; 2] = ["head.repo.fork", "ref_protected"];

/// What a `--trust-from` value names.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum RefKind {
    /// A ref the base repository controls.
    Protected,
    /// The pull request head or a pull request ref.
    Head,
    /// An expression or variable this scan cannot resolve.
    Unknown,
}

/// What one invocation does about trust.
#[derive(Debug, Clone, PartialEq, Eq)]
enum Trust {
    /// Nothing to report.
    Fine,
    /// The invocation breaks the rule, with the reason and the text to anchor the finding on.
    Bad(String, String),
    /// The invocation cannot be judged, with the reason and the anchor text.
    Unknown(String, String),
}

/// Classify the value of `--trust-from`.
fn classify(value: &str) -> RefKind {
    let value = value.trim();
    if value.is_empty() {
        return RefKind::Unknown;
    }
    let lower = value.to_ascii_lowercase();
    if value.contains('$') {
        return if HEAD_MARKERS.iter().any(|m| lower.contains(m)) {
            RefKind::Head
        } else if BASE_MARKERS.iter().any(|m| lower.contains(m)) {
            RefKind::Protected
        } else {
            RefKind::Unknown
        };
    }
    if HEAD_REFS.contains(&value) || lower.contains("refs/pull/") || lower.starts_with("pull/") {
        RefKind::Head
    } else {
        RefKind::Protected
    }
}

/// The value of `--trust-from` in `args` (`--trust-from X` or `--trust-from=X`), `Some("")` when it has none.
fn trust_from(args: &[String]) -> Option<String> {
    let mut it = args.iter();
    while let Some(a) = it.next() {
        if a == "--trust-from" {
            return Some(it.next().cloned().unwrap_or_default());
        }
        if let Some(v) = a.strip_prefix("--trust-from=") {
            return Some(v.to_owned());
        }
    }
    None
}

/// Judge one invocation; `guarded` is true when an `if:` gates its step or job on the PR origin.
fn judge(call: &Call, guarded: bool) -> Trust {
    let name = call.name();
    match call.verb() {
        Some("trust") => {
            return Trust::Bad(
                format!(
                    "`{name} trust` extends trust from a privileged workflow; CI trusts only through `check --trust-from <protected ref>`"
                ),
                "trust".to_owned(),
            );
        }
        Some("check") => {}
        _ => return Trust::Fine,
    }
    if let Some(flag) = call
        .args
        .iter()
        .find(|a| a.starts_with("--trust") && !a.starts_with("--trust-from"))
    {
        let flag = flag.split('=').next().unwrap_or(flag).to_owned();
        return Trust::Bad(
            format!(
                "`{name} check {flag}` grants trust that does not come from a protected ref; use `--trust-from <protected ref>`"
            ),
            flag,
        );
    }
    match trust_from(&call.args) {
        Some(value) => match classify(&value) {
            RefKind::Protected => Trust::Fine,
            RefKind::Head => Trust::Bad(
                format!(
                    "`{name} check --trust-from {value}` reads trust from the pull request head, which the pull request controls; name a protected ref such as the base branch"
                ),
                value,
            ),
            RefKind::Unknown => Trust::Unknown(
                format!(
                    "`{name} check --trust-from {value}` names a ref this scan cannot resolve; CI016 cannot tell whether it is protected"
                ),
                value,
            ),
        },
        None if call.args.iter().any(|a| a == "--skip-tools") => Trust::Fine,
        None if guarded => Trust::Unknown(
            format!(
                "`{name} check` has no `--trust-from`, but an `if:` gates it on the pull request origin or ref protection, which CI016 does not evaluate"
            ),
            "check".to_owned(),
        ),
        None => Trust::Bad(
            format!(
                "`{name} check` in a privileged workflow reads trust from the checked-out lock, which the pull request can edit; pass `--trust-from <protected ref>` (or `--skip-tools`)"
            ),
            "check".to_owned(),
        ),
    }
}

/// True when an `if:` on `holder` mentions a pull-request-origin or ref-protection guard.
fn has_guard(holder: &serde_yaml_ng::Value) -> bool {
    key(holder, "if").and_then(scalar).is_some_and(|cond| {
        let cond = cond.to_ascii_lowercase();
        GUARDS.iter().any(|g| cond.contains(g))
    })
}

/// Findings of CI016 for one parsed workflow.
pub(crate) fn check(wf: &Workflow<'_>, out: &mut Vec<Verdict>) {
    if !PRIVILEGED_TRIGGERS
        .iter()
        .any(|t| wf.triggers().contains(*t))
    {
        return;
    }
    for job in wf.jobs() {
        for (idx, step) in job.steps().into_iter().enumerate() {
            let Some(script) = run_of(step) else {
                continue;
            };
            let guarded = has_guard(step) || has_guard(job.value);
            for call in calls(script, &PROGRAMS) {
                let anchor = format!("{}:{}:{idx}:{}", wf.path, job.id, call.name());
                match judge(&call, guarded) {
                    Trust::Fine => {}
                    Trust::Bad(msg, text) => {
                        tracing::debug!(path = wf.path, job = job.id, idx, "CI016 fires");
                        let site = (wf.path, wf.within_job(job.id, &text));
                        out.push(fire(CI016, Severity::Error, site, msg, anchor));
                    }
                    Trust::Unknown(msg, text) => {
                        tracing::debug!(path = wf.path, job = job.id, idx, "CI016 unresolved");
                        let site = (wf.path, wf.within_job(job.id, &text));
                        out.push(Verdict::unresolved(
                            CI016,
                            UnresolvedReason::DynamicUnresolvable,
                            site,
                            msg,
                            anchor,
                        ));
                    }
                }
            }
        }
    }
}
