//! CI001, CI006, CI007 and CI010: the workflow supply-chain and injection rules.
//!
//! These are the grimble fallbacks of the zizmor-bound rules (`unpinned-uses`,
//! `dangerous-triggers`, `template-injection`, `artipacked`): a lexical, offline reading of the
//! parsed workflow, so the verdict exists when zizmor is not installed.

// frob:ticket 01M5F010QB00AR00D4HYVYYPWH

use gob_rules::Severity;
use serde_yaml_ng::Value;

use crate::CiConfig;
use crate::finding::{CiFinding, fire};
use crate::workflow::{Job, Workflow, run_of, uses_of, with_of};

/// Rule id: an external `uses:` not pinned to a full commit SHA.
pub const CI001: &str = "CI001";
/// Rule id: a privileged trigger checks out the pull request head.
pub const CI006: &str = "CI006";
/// Rule id: an attacker-influenced expression interpolated into a `run:` script.
pub const CI007: &str = "CI007";
/// Rule id: `actions/checkout` leaves credentials in the workspace.
pub const CI010: &str = "CI010";

/// Triggers that run with a privileged token in the base repository context.
const PRIVILEGED_TRIGGERS: [&str; 2] = ["pull_request_target", "workflow_run"];

/// Substrings (lowercase) of a checkout `ref` or `repository` that name the pull request head.
const HEAD_MARKERS: [&str; 5] = [
    "github.event.pull_request.head",
    "github.event.pull_request.merge_commit_sha",
    "github.head_ref",
    "github.event.workflow_run.head",
    "refs/pull/",
];

/// Context paths (lowercase, `*` matches one segment) whose value an outsider chooses; a match in
/// a `run:` script is the narrow, Error-level CI007 set.
const NARROW_CONTEXTS: [&str; 24] = [
    "github.event.issue.title",
    "github.event.issue.body",
    "github.event.pull_request.title",
    "github.event.pull_request.body",
    "github.event.pull_request.head.ref",
    "github.event.pull_request.head.label",
    "github.event.pull_request.head.repo.default_branch",
    "github.event.comment.body",
    "github.event.review.body",
    "github.event.review_comment.body",
    "github.event.discussion.title",
    "github.event.discussion.body",
    "github.event.release.name",
    "github.event.release.body",
    "github.event.pages.*.page_name",
    "github.event.commits.*.message",
    "github.event.commits.*.author.email",
    "github.event.commits.*.author.name",
    "github.event.head_commit.message",
    "github.event.head_commit.author.email",
    "github.event.head_commit.author.name",
    "github.head_ref",
    "github.event.workflow_run.head_branch",
    "github.event.workflow_run.head_commit.message",
];

/// Last path segments of an event expression that hold a number or hash, never free text.
const SAFE_LEAVES: [&str; 9] = [
    "number",
    "id",
    "node_id",
    "sha",
    "run_id",
    "run_number",
    "run_attempt",
    "created_at",
    "updated_at",
];

/// Owners whose actions CI010 does not count as third-party code.
const FIRST_PARTY_OWNERS: [&str; 2] = ["actions", "github"];

/// Findings of CI001, CI006, CI007 and CI010 for one parsed workflow.
pub(crate) fn check(wf: &Workflow<'_>, cfg: &CiConfig, out: &mut Vec<CiFinding>) {
    let jobs = wf.jobs();
    pinned_refs(wf, &jobs, cfg, out);
    if PRIVILEGED_TRIGGERS
        .iter()
        .any(|t| wf.triggers().contains(*t))
    {
        head_checkouts(wf, &jobs, out);
    }
    injections(wf, &jobs, cfg, out);
    persisted_credentials(wf, &jobs, out);
}

/// True when `s` is a full 40-hex commit SHA.
fn is_sha(s: &str) -> bool {
    s.len() == 40 && s.bytes().all(|b| b.is_ascii_hexdigit())
}

/// True for a local `uses:` (`./path`), which is checked out with the repository itself.
fn is_local(uses: &str) -> bool {
    uses.starts_with("./") || uses.starts_with(".\\")
}

/// The action name of `uses` (the text before `@`, lowercased and trimmed).
fn action_of(uses: &str) -> String {
    uses.split('@')
        .next()
        .unwrap_or_default()
        .trim()
        .to_ascii_lowercase()
}

/// The owner of an external action (`actions` of `actions/checkout`).
fn owner_of(uses: &str) -> String {
    action_of(uses)
        .split('/')
        .next()
        .unwrap_or_default()
        .to_owned()
}

/// True when `step` is `actions/checkout` (any ref or subpath-free form).
fn is_checkout(step: &Value) -> bool {
    uses_of(step).is_some_and(|u| action_of(u) == "actions/checkout")
}

/// Every `uses:` of the workflow, step and job level, with the job id that owns it.
fn all_uses<'a>(jobs: &'a [Job<'a>]) -> Vec<(&'a str, &'a str)> {
    let mut found = Vec::new();
    for job in jobs {
        if let Some(u) = uses_of(job.value) {
            found.push((job.id, u));
        }
        found.extend(
            job.steps()
                .into_iter()
                .filter_map(uses_of)
                .map(|u| (job.id, u)),
        );
    }
    found
}

/// CI001.
fn pinned_refs(wf: &Workflow<'_>, jobs: &[Job<'_>], cfg: &CiConfig, out: &mut Vec<CiFinding>) {
    for (job, uses) in all_uses(jobs) {
        let uses = uses.trim();
        if uses.is_empty() || is_local(uses) {
            continue;
        }
        let message = if let Some(image) = uses.strip_prefix("docker://") {
            (!image.contains("@sha256:")).then(|| {
                format!("job `{job}` runs the image `{uses}` without a digest; pin it as `docker://{}@sha256:<digest>`", image.split('@').next().unwrap_or(image))
            })
        } else {
            let git_ref = uses.split_once('@').map(|(_, r)| r.trim());
            let allowed = cfg
                .allow_tag_pins_for
                .iter()
                .any(|o| o.eq_ignore_ascii_case(&owner_of(uses)));
            (!allowed && !matches!(git_ref, Some(r) if is_sha(r))).then(|| {
                format!("job `{job}` uses `{uses}` which is not pinned to a full 40-hex commit SHA, so the ref can be moved under you; pin `{}@<sha>` and keep the version in a trailing comment", uses.split('@').next().unwrap_or(uses))
            })
        };
        if let Some(message) = message {
            out.push(fire(
                CI001,
                Severity::Warn,
                (wf.path, wf.within_job(job, uses)),
                message,
                format!("{}:{job}:{uses}:unpinned", wf.path),
            ));
        }
    }
}

/// CI006 (only called for a privileged trigger).
fn head_checkouts(wf: &Workflow<'_>, jobs: &[Job<'_>], out: &mut Vec<CiFinding>) {
    for job in jobs {
        for (idx, step) in job.steps().into_iter().enumerate() {
            if !is_checkout(step) {
                continue;
            }
            let named = ["ref", "repository"].into_iter().find_map(|input| {
                let value = with_of(step, input)?;
                let lower = value.to_ascii_lowercase();
                HEAD_MARKERS
                    .iter()
                    .any(|m| lower.contains(m))
                    .then_some((input, value))
            });
            if let Some((input, value)) = named {
                out.push(fire(
                    CI006,
                    Severity::Error,
                    (wf.path, wf.within_job(job.id, &value)),
                    format!("job `{}` checks out the pull request head through `{input}: {value}` in a workflow that runs with a privileged token; build untrusted code in a `pull_request` workflow and hand the result to the privileged one as an artifact", job.id),
                    format!("{}:{}:{idx}:head-checkout", wf.path, job.id),
                ));
            }
        }
    }
}

/// The text of every `${{ ... }}` expression in `text` (an unterminated one runs to the end).
fn expressions(text: &str) -> Vec<&str> {
    let mut found = Vec::new();
    let mut rest = text;
    while let Some(at) = rest.find("${{") {
        let body = &rest[at + 3..];
        let end = body.find("}}").unwrap_or(body.len());
        found.push(&body[..end]);
        rest = &body[end..];
    }
    found
}

/// Normalise the bracket forms of a context token: `a['b']` becomes `a.b` and `a[0]` `a.*`.
fn normalise(token: &str) -> String {
    let mut out = String::new();
    let mut chars = token.chars();
    while let Some(c) = chars.next() {
        if c == '[' {
            let inner: String = chars.by_ref().take_while(|x| *x != ']').collect();
            let inner = inner.trim().trim_matches(['\'', '"']);
            out.push('.');
            out.push_str(if inner.chars().all(|x| x.is_ascii_digit()) {
                "*"
            } else {
                inner
            });
        } else {
            out.push(c);
        }
    }
    out.trim_matches(['.', '\'', '"']).to_ascii_lowercase()
}

/// The context tokens of expression `expr`, normalised, with their original spelling.
fn tokens(expr: &str) -> Vec<(String, &str)> {
    expr.split(|c: char| {
        !(c.is_ascii_alphanumeric() || matches!(c, '_' | '.' | '-' | '*' | '[' | ']' | '\'' | '"'))
    })
    .filter(|t| !t.is_empty())
    .map(|t| (normalise(t), t))
    .collect()
}

/// True when `token` is, or reads below, the dotted `pattern` (`*` matches one segment).
fn matches_pattern(token: &str, pattern: &str) -> bool {
    let mut t = token.split('.');
    pattern
        .split('.')
        .all(|p| t.next().is_some_and(|s| p == "*" || p == s))
}

/// How CI007 classifies a context token.
enum Reach {
    /// A value an outsider chooses outright (Error).
    Narrow,
    /// Event data that may carry free text (Advisory).
    Broad,
}

/// Classify `token`, `None` when it is not event data or is a number or hash.
fn reach_of(token: &str, cfg: &CiConfig) -> Option<Reach> {
    let narrow = NARROW_CONTEXTS
        .iter()
        .copied()
        .chain(cfg.contexts.iter().map(String::as_str))
        .any(|p| matches_pattern(token, &p.to_ascii_lowercase()));
    if narrow {
        return Some(Reach::Narrow);
    }
    let event = token.starts_with("github.event.") || token.starts_with("inputs.");
    let leaf = token.rsplit('.').next().unwrap_or_default();
    (event && !SAFE_LEAVES.contains(&leaf)).then_some(Reach::Broad)
}

/// CI007.
fn injections(wf: &Workflow<'_>, jobs: &[Job<'_>], cfg: &CiConfig, out: &mut Vec<CiFinding>) {
    for job in jobs {
        for (idx, step) in job.steps().into_iter().enumerate() {
            let Some(run) = run_of(step) else { continue };
            let mut narrow: Vec<&str> = Vec::new();
            let mut broad: Vec<&str> = Vec::new();
            for (token, raw) in expressions(run).into_iter().flat_map(|e| tokens(e)) {
                let bucket = match reach_of(&token, cfg) {
                    Some(Reach::Narrow) => &mut narrow,
                    Some(Reach::Broad) => &mut broad,
                    None => continue,
                };
                if !bucket.contains(&raw) {
                    bucket.push(raw);
                }
            }
            let (severity, hits, what) = if narrow.is_empty() {
                (
                    Severity::Advisory,
                    &broad,
                    "event data that can carry free text",
                )
            } else {
                (Severity::Error, &narrow, "a value an outsider controls")
            };
            let Some(first) = hits.first() else { continue };
            out.push(fire(
                CI007,
                severity,
                (wf.path, wf.within_job(job.id, first)),
                format!("step {} of job `{}` splices {what} into its `run:` script (`{}`), so a crafted value runs as shell; pass it through `env:` and read it as a shell variable", idx + 1, job.id, hits.join("`, `")),
                format!("{}:{}:{idx}:injection", wf.path, job.id),
            ));
        }
    }
}

/// True when `step` uploads an artifact.
fn uploads(step: &Value) -> bool {
    uses_of(step).is_some_and(|u| action_of(u) == "actions/upload-artifact")
}

/// True when `step` runs an external action from outside `actions` and `github`, or a container.
fn third_party(step: &Value) -> bool {
    uses_of(step).is_some_and(|u| {
        let u = u.trim();
        !u.is_empty() && !is_local(u) && !FIRST_PARTY_OWNERS.contains(&owner_of(u).as_str())
    })
}

/// True when a `persist-credentials` input is `false` (or an expression we cannot resolve).
fn credentials_dropped(step: &Value) -> bool {
    with_of(step, "persist-credentials").is_some_and(|v| {
        let v = v.trim();
        v.eq_ignore_ascii_case("false") || v.starts_with("${{")
    })
}

/// CI010.
fn persisted_credentials(wf: &Workflow<'_>, jobs: &[Job<'_>], out: &mut Vec<CiFinding>) {
    let steps = || jobs.iter().flat_map(Job::steps);
    let risky = steps().any(|s| uploads(s) || third_party(s));
    if !risky {
        return;
    }
    for job in jobs {
        let pushes = job
            .steps()
            .into_iter()
            .filter_map(run_of)
            .any(|r| r.contains("git push"));
        for (idx, step) in job.steps().into_iter().enumerate() {
            if !is_checkout(step) || credentials_dropped(step) || pushes {
                continue;
            }
            out.push(fire(
                CI010,
                Severity::Advisory,
                (wf.path, wf.within_job(job.id, "actions/checkout")),
                format!("job `{}` checks out without `persist-credentials: false` in a workflow that uploads artifacts or runs third-party code, so the token stays in `.git/config`; add `with: persist-credentials: false` unless a later step pushes", job.id),
                format!("{}:{}:{idx}:persist-credentials", wf.path, job.id),
            ));
        }
    }
}
