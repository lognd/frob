//! The CI and DK rule families over GitHub Actions workflows and Dockerfiles (design:
//! `docs/design/cicd.md` section 5).
//!
//! [`analyze`] reads the repository's files through [`CiInput`] and returns every verdict as a
//! [`CiFinding`]; the product converts them to its own findings. Rules are declared with `#[rule]`
//! ([`rules`]) and staged, like the architecture rules.
//!
//! | Rule | Polarity | Fires |
//! |---|---|---|
//! | `CI002` | P- | no top-level `permissions` and a job without its own |
//! | `CI003` | P+ | top-level `permissions` grant write |
//! | `CI004` | P- | push or pull request workflow with no `concurrency` |
//! | `CI005` | P- | a job with no `timeout-minutes`, or one above `max_timeout` |
//! | `CI008` | P+ | a registry publish on a trigger not limited to release tags |
//! | `CI009` | P+ | a long-lived token publish where trusted publishing exists |
//! | `CI011` | P- | `pull_request_target` without explicit read-only `permissions` |
//! | `CI012` | P0 | toolchain, MSRV, Dependabot or CODEOWNERS disagree with the manifests |
//! | `DK001` | P- | the final stage runs as root |
//! | `DK002` | P+ | a base image is not pinned by digest (opt-in: `require_digest`) |
//! | `DK003` | P+ | a base image has no tag or `latest` |
//! | `DK004` | P+ | a download piped into a shell |
//!
//! A file that does not parse is an Unresolved finding (`parse-failed`), never a clean verdict.
//!
//! # Known limits
//!
//! - `CI012` reads a YAML float matrix entry (`1.70`) as `1.7`; quote versions in matrices.
//! - `CI012` does not yet compare frob verbs with the commands a workflow runs.
//! - `CI001`, `CI006`, `CI007`, `CI010`, `CI013` to `CI015` belong to the bound zizmor and
//!   actionlint stages; their grimble fallbacks are not implemented here.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

mod ci;
mod consistency;
mod dk;
mod docker;
mod finding;
pub mod host;
pub mod rules;
mod workflow;

use std::collections::BTreeMap;

pub use finding::CiFinding;

/// The workflow rules that judge each parsed workflow (CI012 is joined separately).
const WORKFLOW_RULES: [&str; 8] = [
    ci::CI002,
    ci::CI003,
    ci::CI004,
    ci::CI005,
    ci::CI008,
    ci::CI009,
    ci::CI011,
    consistency::CI012,
];

/// The Dockerfile rules.
const DOCKER_RULES: [&str; 4] = [dk::DK001, dk::DK002, dk::DK003, dk::DK004];

/// Knobs of the CI and DK rules.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CiConfig {
    /// A `timeout-minutes` above this fires `CI005` (default 60).
    pub max_timeout: u32,
    /// An external `FROM` without `@sha256:` fires `DK002` (default off; the rule is opt-in).
    pub require_digest: bool,
    /// URL hosts whose downloads may be piped into a shell (`DK004`).
    pub allow_pipe_hosts: Vec<String>,
}

impl Default for CiConfig {
    /// The shipped defaults.
    fn default() -> Self {
        Self {
            max_timeout: 60,
            require_digest: false,
            allow_pipe_hosts: Vec::new(),
        }
    }
}

/// Everything the CI pass reads.
pub struct CiInput<'a> {
    /// Every repo-relative file path of the walk.
    pub files: &'a [String],
    /// The text of a repo-relative file, `None` when unreadable.
    pub read: &'a dyn Fn(&str) -> Option<String>,
    /// The rule knobs.
    pub config: &'a CiConfig,
}

/// What the CI pass found and examined.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct CiReport {
    /// Findings, sorted by file, rule and anchor.
    pub findings: Vec<CiFinding>,
    /// Subjects examined per rule (workflows, jobs, Dockerfiles); a rule with no scope has none.
    pub subjects: BTreeMap<&'static str, usize>,
    /// Rules whose whole scope is absent here (rule id to the reason), so zero subjects is not a gap.
    pub not_applicable: BTreeMap<&'static str, String>,
}

/// Run the CI and DK rules over `input`.
pub fn analyze(input: &CiInput<'_>) -> CiReport {
    let mut report = CiReport::default();
    let texts = |pred: fn(&str) -> bool| -> Vec<(&str, String)> {
        input
            .files
            .iter()
            .filter(|f| pred(f))
            .filter_map(|f| {
                let text = (input.read)(f);
                if text.is_none() {
                    tracing::warn!(file = f.as_str(), "unreadable file skipped");
                }
                text.map(|t| (f.as_str(), t))
            })
            .collect()
    };
    let workflows = texts(gob_symbols::is_workflow_path);
    let dockerfiles = texts(gob_symbols::is_dockerfile_path);
    workflow_pass(input, &workflows, &mut report);
    docker_pass(input.config, &dockerfiles, &mut report);
    report
        .findings
        .sort_by(|a, b| (&a.file, a.rule, &a.anchor).cmp(&(&b.file, b.rule, &b.anchor)));
    tracing::info!(findings = report.findings.len(), subjects = ?report.subjects, "CI pass done");
    report
}

/// Run the workflow rules and CI012.
fn workflow_pass(input: &CiInput<'_>, files: &[(&str, String)], report: &mut CiReport) {
    if files.is_empty() {
        tracing::debug!("no workflows in the walk; CI rules do not apply");
        for id in WORKFLOW_RULES {
            report
                .not_applicable
                .insert(id, "no GitHub Actions workflows in the walk".to_owned());
        }
        return;
    }
    let mut parsed = Vec::new();
    let mut subjects = ci::Subjects::default();
    for (path, text) in files {
        match workflow::Workflow::parse(path, text) {
            Ok(wf) => {
                report
                    .findings
                    .extend(ci::check(&wf, input.config, &mut subjects));
                parsed.push(wf);
            }
            Err(why) => {
                tracing::warn!(path, why, "workflow does not parse");
                report
                    .findings
                    .push(finding::parse_failed("CI002", path, &why));
            }
        }
    }
    let repo = consistency::Repo {
        files: input.files,
        read: input.read,
    };
    report.findings.extend(consistency::check(&repo, &parsed));
    for id in WORKFLOW_RULES {
        report.subjects.insert(id, files.len());
    }
    report.subjects.insert(ci::CI005, subjects.jobs);
}

/// Run the Dockerfile rules.
fn docker_pass(cfg: &CiConfig, files: &[(&str, String)], report: &mut CiReport) {
    if files.is_empty() {
        tracing::debug!("no Dockerfiles in the walk; DK rules do not apply");
        for id in DOCKER_RULES {
            report
                .not_applicable
                .insert(id, "no Dockerfiles in the walk".to_owned());
        }
        return;
    }
    for (path, text) in files {
        report.findings.extend(dk::check(path, text, cfg));
    }
    for id in DOCKER_RULES {
        report.subjects.insert(id, files.len());
    }
}
