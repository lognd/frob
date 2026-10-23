//! CI013, CI014 and CI015: reusable-workflow secrets, workflow structure and action currency.
//!
//! These are the grimble fallbacks of the bound tool rules (zizmor `secrets-inherit` and
//! `archived-uses`, and actionlint): a lexical, offline reading of the parsed workflow that exists
//! when the tools are not installed. When a bound tool reports the same rule for a file, the
//! product keeps the tool's finding and drops this one.

// frob:ticket 01M5F010V5GV0B7KJ7M5QQG70Q

use gob_rules::Severity;

use crate::finding::fire;
use crate::workflow::{Job, Workflow, key, scalar, uses_of};
use grimble_verdict::Verdict;

/// Rule id: a call to an external reusable workflow passes every secret.
pub const CI013: &str = "CI013";
/// Rule id: the workflow breaks the Actions syntax.
pub const CI014: &str = "CI014";
/// Rule id: an external action is archived or on an end-of-life Node runtime.
pub const CI015: &str = "CI015";

/// Actions whose repository is archived (lowercase `owner/name`).
const ARCHIVED: [&str; 8] = [
    "actions/create-release",
    "actions/upload-release-asset",
    "actions/setup-ruby",
    "actions-rs/toolchain",
    "actions-rs/cargo",
    "actions-rs/clippy-check",
    "actions-rs/audit-check",
    "actions-rs/install",
];

/// Actions and the newest major that still runs on an end-of-life Node runtime (Node 16 and older).
const EOL_NODE: [(&str, u64); 9] = [
    ("actions/checkout", 3),
    ("actions/setup-node", 3),
    ("actions/cache", 3),
    ("actions/upload-artifact", 3),
    ("actions/download-artifact", 3),
    ("actions/setup-python", 4),
    ("actions/setup-go", 4),
    ("actions/setup-java", 3),
    ("actions/github-script", 6),
];

/// Findings of CI013, CI014 and CI015 for one parsed workflow.
pub(crate) fn check(wf: &Workflow<'_>, out: &mut Vec<Verdict>) {
    let jobs = wf.jobs();
    secrets_inherit(wf, &jobs, out);
    structure(wf, &jobs, out);
    action_currency(wf, &jobs, out);
}

/// True for a local reusable workflow or action (`./path`).
fn is_local(uses: &str) -> bool {
    uses.starts_with("./") || uses.starts_with(".\\")
}

/// CI013.
fn secrets_inherit(wf: &Workflow<'_>, jobs: &[Job<'_>], out: &mut Vec<Verdict>) {
    for job in jobs {
        let Some(uses) = uses_of(job.value).map(str::trim) else {
            continue;
        };
        let inherits = key(job.value, "secrets")
            .and_then(scalar)
            .is_some_and(|s| s.trim() == "inherit");
        if inherits && !is_local(uses) && !uses.contains("${{") {
            out.push(fire(
                CI013,
                Severity::Advisory,
                (wf.path, wf.within_job(job.id, "secrets")),
                format!("job `{}` calls the external workflow `{uses}` with `secrets: inherit`, handing it every secret of the caller; pass only the secrets it needs by name", job.id),
                format!("{}:{}:secrets-inherit", wf.path, job.id),
            ));
        }
    }
}

/// CI014: the structural errors actionlint always reports.
fn structure(wf: &Workflow<'_>, jobs: &[Job<'_>], out: &mut Vec<Verdict>) {
    let mut report = |range: (usize, usize), anchor: String, message: String| {
        tracing::debug!(path = wf.path, anchor, "CI014 structural error");
        out.push(fire(
            CI014,
            Severity::Warn,
            (wf.path, range),
            message,
            anchor,
        ));
    };
    if wf.on().is_none() {
        report(
            wf.top_range("name"),
            format!("{}:on", wf.path),
            "the workflow has no `on:` trigger, so it never runs; add the events that start it"
                .to_owned(),
        );
    }
    if jobs.is_empty() {
        report(
            wf.top_range("jobs"),
            format!("{}:jobs", wf.path),
            "the workflow has no jobs; add a `jobs:` mapping with at least one job".to_owned(),
        );
    }
    for job in jobs {
        if !job.value.is_mapping() {
            continue;
        }
        let has = |k: &str| key(job.value, k).is_some();
        if job.is_call() && has("steps") {
            report(
                wf.job_range(job.id),
                format!("{}:{}:call-with-steps", wf.path, job.id),
                format!(
                    "job `{}` sets both `uses` and `steps`; a reusable-workflow call has no steps",
                    job.id
                ),
            );
        } else if !job.is_call() && !has("runs-on") {
            report(
                wf.job_range(job.id),
                format!("{}:{}:runs-on", wf.path, job.id),
                format!(
                    "job `{}` has no `runs-on`; name the runner it runs on",
                    job.id
                ),
            );
        } else if !job.is_call() && job.steps().is_empty() {
            report(
                wf.job_range(job.id),
                format!("{}:{}:steps", wf.path, job.id),
                format!("job `{}` has no `steps`; add at least one step", job.id),
            );
        }
        for (idx, step) in job.steps().into_iter().enumerate() {
            let body = (key(step, "run").is_some(), key(step, "uses").is_some());
            let problem = match body {
                (false, false) => Some(("no-body", "has neither `run` nor `uses`")),
                (true, true) => Some(("both-bodies", "sets both `run` and `uses`")),
                _ => None,
            };
            if let Some((tag, what)) = problem {
                report(
                    wf.job_range(job.id),
                    format!("{}:{}:{idx}:{tag}", wf.path, job.id),
                    format!(
                        "step {} of job `{}` {what}; a step runs one command or one action",
                        idx + 1,
                        job.id
                    ),
                );
            }
        }
    }
}

/// The major version of a `vN`, `vN.M.P` or `N` ref, `None` for a SHA, branch or expression.
fn major_of(git_ref: &str) -> Option<u64> {
    let digits = git_ref.strip_prefix('v').unwrap_or(git_ref);
    let major = digits.split('.').next()?;
    if major.is_empty() || major.len() > 4 || !major.bytes().all(|b| b.is_ascii_digit()) {
        return None;
    }
    major.parse().ok()
}

/// CI015.
fn action_currency(wf: &Workflow<'_>, jobs: &[Job<'_>], out: &mut Vec<Verdict>) {
    for job in jobs {
        for (idx, step) in job.steps().into_iter().enumerate() {
            let Some(uses) = uses_of(step).map(str::trim) else {
                continue;
            };
            if is_local(uses) || uses.starts_with("docker://") || uses.contains("${{") {
                continue;
            }
            let (path, git_ref) = uses.split_once('@').unwrap_or((uses, ""));
            let name: String = path
                .to_ascii_lowercase()
                .split('/')
                .take(2)
                .collect::<Vec<_>>()
                .join("/");
            let problem = if ARCHIVED.contains(&name.as_str()) {
                Some("its repository is archived and gets no fixes".to_owned())
            } else {
                EOL_NODE
                    .iter()
                    .find(|(action, _)| *action == name)
                    .and_then(|(_, newest)| {
                        major_of(git_ref)
                            .filter(|m| m <= newest)
                            .map(|m| (m, *newest))
                    })
                    .map(|(m, newest)| {
                        format!(
                            "major {m} runs on an end-of-life Node runtime; use major {} or later",
                            newest + 1
                        )
                    })
            };
            if let Some(why) = problem {
                out.push(fire(
                    CI015,
                    Severity::Advisory,
                    (wf.path, wf.within_job(job.id, uses)),
                    format!("job `{}` uses `{uses}`: {why}", job.id),
                    format!("{}:{}:{idx}:{name}", wf.path, job.id),
                ));
            }
        }
    }
}
