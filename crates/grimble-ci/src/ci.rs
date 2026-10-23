//! CI002, CI003, CI004, CI005, CI008, CI009 and CI011 over one workflow.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

use gob_rules::Severity;
use serde_yaml_ng::Value;

use crate::CiConfig;
use crate::finding::fire;
use crate::workflow::{Job, Workflow, key, run_of, scalar, uses_of};
use grimble_verdict::Verdict;

/// Rule id: no least-privilege `permissions`.
pub const CI002: &str = "CI002";
/// Rule id: write permissions granted workflow-wide.
pub const CI003: &str = "CI003";
/// Rule id: no `concurrency` group.
pub const CI004: &str = "CI004";
/// Rule id: a job has no sane `timeout-minutes`.
pub const CI005: &str = "CI005";
/// Rule id: a registry publish outside a tag-gated trigger.
pub const CI008: &str = "CI008";
/// Rule id: a long-lived token where trusted publishing exists.
pub const CI009: &str = "CI009";
/// Rule id: `pull_request_target` without read-only permissions.
pub const CI011: &str = "CI011";

/// Registry publish commands: (substring of a `run` line, registry name, supports trusted publishing).
const PUBLISH_COMMANDS: &[(&str, &str, bool)] = &[
    ("cargo publish", "crates.io", true),
    ("npm publish", "npm", true),
    ("pnpm publish", "npm", true),
    ("yarn npm publish", "npm", true),
    ("twine upload", "PyPI", true),
    ("uv publish", "PyPI", true),
    ("poetry publish", "PyPI", true),
    ("gem push", "RubyGems", true),
    ("docker push", "a container registry", false),
    ("dotnet nuget push", "NuGet", false),
];

/// Publish actions: (`uses` prefix, registry name, supports trusted publishing).
const PUBLISH_ACTIONS: &[(&str, &str, bool)] = &[
    ("pypa/gh-action-pypi-publish", "PyPI", true),
    ("rubygems/release-gem", "RubyGems", true),
];

/// Counts of subjects examined by [`check`].
#[derive(Debug, Default, Clone, Copy)]
pub(crate) struct Subjects {
    /// Jobs judged for CI005.
    pub jobs: usize,
}

/// Findings of the CI rules this module owns for one parsed workflow.
pub(crate) fn check(wf: &Workflow<'_>, cfg: &CiConfig, subjects: &mut Subjects) -> Vec<Verdict> {
    let mut out = Vec::new();
    let jobs = wf.jobs();
    tracing::debug!(path = wf.path, jobs = jobs.len(), "checking workflow");
    subjects.jobs += jobs.iter().filter(|j| !j.is_call()).count();
    permissions(wf, &jobs, &mut out);
    concurrency(wf, &jobs, &mut out);
    timeouts(wf, &jobs, cfg, &mut out);
    publishes(wf, &jobs, &mut out);
    out
}

/// True when permission value `v` grants any write.
fn grants_write(v: &Value) -> bool {
    match v {
        Value::String(s) => s == "write-all",
        Value::Mapping(m) => m.values().any(|x| x.as_str() == Some("write")),
        _ => false,
    }
}

/// True when `v` grants `id-token: write` (or everything).
fn grants_id_token(v: Option<&Value>) -> bool {
    match v {
        Some(Value::String(s)) => s == "write-all",
        Some(m @ Value::Mapping(_)) => key(m, "id-token").and_then(Value::as_str) == Some("write"),
        _ => false,
    }
}

/// CI002, CI003 and CI011.
fn permissions(wf: &Workflow<'_>, jobs: &[Job<'_>], out: &mut Vec<Verdict>) {
    let top = wf.permissions();
    let uncovered = top.is_none() && jobs.iter().any(|j| j.permissions().is_none());
    if uncovered {
        out.push(fire(
            CI002,
            Severity::Warn,
            (wf.path, wf.top_range("jobs")),
            "the workflow has no top-level `permissions` and not every job sets its own, so the token gets the repository default; add `permissions: contents: read` at the top and widen per job".to_owned(),
            format!("{}:permissions", wf.path),
        ));
    }
    if top.is_some_and(grants_write) {
        out.push(fire(
            CI003,
            Severity::Warn,
            (wf.path, wf.top_range("permissions")),
            "the top-level `permissions` grants write to every job; set `contents: read` here and give the one job that needs write its own `permissions`".to_owned(),
            format!("{}:write-permissions", wf.path),
        ));
    }
    if wf.triggers().contains("pull_request_target") {
        let job_write = jobs
            .iter()
            .any(|j| j.permissions().is_some_and(grants_write));
        if uncovered || top.is_some_and(grants_write) || job_write {
            out.push(fire(
                CI011,
                Severity::Error,
                (wf.path, wf.top_range("on")),
                "`pull_request_target` runs with a privileged token on untrusted input without explicit read-only `permissions`; add `permissions: contents: read` to the workflow and every job".to_owned(),
                format!("{}:pull-request-target", wf.path),
            ));
        }
    }
}

/// CI004.
fn concurrency(wf: &Workflow<'_>, jobs: &[Job<'_>], out: &mut Vec<Verdict>) {
    let triggers = wf.triggers();
    if !(triggers.contains("push") || triggers.contains("pull_request")) {
        return;
    }
    let per_job = !jobs.is_empty() && jobs.iter().all(|j| key(j.value, "concurrency").is_some());
    if wf.has_concurrency() || per_job {
        return;
    }
    out.push(fire(
        CI004,
        Severity::Advisory,
        (wf.path, wf.top_range("on")),
        "the workflow has no `concurrency`, so superseded runs keep burning minutes; add `concurrency: { group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true }`".to_owned(),
        format!("{}:concurrency", wf.path),
    ));
}

/// CI005.
fn timeouts(wf: &Workflow<'_>, jobs: &[Job<'_>], cfg: &CiConfig, out: &mut Vec<Verdict>) {
    for job in jobs.iter().filter(|j| !j.is_call()) {
        let message = match key(job.value, "timeout-minutes") {
            None => Some(format!(
                "job `{}` has no `timeout-minutes`, so a hung step runs for six hours; add `timeout-minutes: {}`",
                job.id,
                cfg.max_timeout.min(30)
            )),
            Some(Value::Number(n))
                if n.as_f64().is_some_and(|m| m > f64::from(cfg.max_timeout)) =>
            {
                Some(format!(
                    "job `{}` allows {n} minutes, above the {} minute limit; lower `timeout-minutes` to a measured bound",
                    job.id, cfg.max_timeout
                ))
            }
            Some(_) => None,
        };
        if let Some(message) = message {
            out.push(fire(
                CI005,
                Severity::Advisory,
                (wf.path, wf.job_range(job.id)),
                message,
                format!("{}:{}:timeout", wf.path, job.id),
            ));
        }
    }
}

/// A publish a step performs: (registry, supports trusted publishing, matched text).
fn publish_of(step: &Value) -> Option<(&'static str, bool, &'static str)> {
    if let Some(uses) = uses_of(step)
        && let Some((p, r, t)) = PUBLISH_ACTIONS.iter().find(|(p, _, _)| uses.starts_with(p))
    {
        return Some((r, *t, p));
    }
    let run = run_of(step)?;
    PUBLISH_COMMANDS
        .iter()
        .find(|(c, _, _)| run.contains(c))
        .map(|(c, r, t)| (*r, *t, *c))
}

/// True when the `if:` of `v` gates on a tag ref.
fn tag_gated(v: &Value) -> bool {
    key(v, "if")
        .and_then(scalar)
        .is_some_and(|s| s.contains("refs/tags") || s.contains("ref_type"))
}

/// The token-like secret names (`NAME` of `secrets.NAME`) mentioned in `text`.
fn token_secrets(text: &str) -> Vec<String> {
    let mut found = Vec::new();
    for (at, _) in text.match_indices("secrets.") {
        let name: String = text[at + 8..]
            .chars()
            .take_while(|c| c.is_ascii_alphanumeric() || *c == '_')
            .collect();
        let up = name.to_ascii_uppercase();
        if ["TOKEN", "KEY", "PASSWORD"].iter().any(|w| up.contains(w)) && !found.contains(&name) {
            found.push(name);
        }
    }
    found
}

/// CI008 and CI009.
fn publishes(wf: &Workflow<'_>, jobs: &[Job<'_>], out: &mut Vec<Verdict>) {
    let triggers = wf.triggers();
    let push_untagged = triggers.contains("push")
        && wf
            .trigger_config("push")
            .is_none_or(|c| key(c, "tags").is_none() && key(c, "tags-ignore").is_none());
    let risky = triggers.contains("pull_request")
        || triggers.contains("pull_request_target")
        || push_untagged;
    for job in jobs {
        for step in job.steps() {
            let Some((registry, trusted, needle)) = publish_of(step) else {
                continue;
            };
            let range = wf.within_job(job.id, needle);
            if risky && !tag_gated(job.value) && !tag_gated(step) {
                out.push(fire(
                    CI008,
                    Severity::Warn,
                    (wf.path, range),
                    format!("job `{}` publishes to {registry} on a trigger that is not limited to release tags; trigger on `push: tags: ['v*']` (or `release`) or gate the step with `if: startsWith(github.ref, 'refs/tags/')`", job.id),
                    format!("{}:{}:publish", wf.path, job.id),
                ));
            }
            if trusted {
                let text = serde_yaml_ng::to_string(step).unwrap_or_default();
                let secrets = token_secrets(&text);
                let oidc = grants_id_token(job.permissions()) || grants_id_token(wf.permissions());
                if let (Some(secret), false) = (secrets.first(), oidc) {
                    out.push(fire(
                        CI009,
                        Severity::Advisory,
                        (wf.path, range),
                        format!("job `{}` publishes to {registry} with the long-lived `secrets.{secret}`; register a trusted publisher and add `permissions: id-token: write` to the job", job.id),
                        format!("{}:{}:token", wf.path, job.id),
                    ));
                }
            }
        }
    }
}
