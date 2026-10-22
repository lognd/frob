//! T3 accessibility: axe-core run in a real browser, one finding per violating node.
//!
//! The browser half sits behind [`AxeScanner`], so the check and the report parser are pure and
//! tested against recorded axe JSON. [`PlaywrightAxe`] is the real scanner: it runs the shared
//! Playwright script (`node/render.mjs`) in axe mode through [`gob_exec::Runner`], so it has the
//! same timeout, output cap and scrubbed environment as a render. axe-core itself is resolved from
//! the project, never bundled.
//!
//! # Edge cases
//!
//! - A report that is not JSON, or has no `violations` array, is [`A11yError::BadReport`]: a
//!   scan that produced nothing readable is never reported as clean.
//! - A violation with an empty id is refused; one with no nodes still yields one finding (without
//!   a node) so the violation is not lost.
//! - A node target that crosses an iframe or shadow root (a nested array in axe's output) is
//!   joined with ` >> `.
//! - Severity follows axe's impact: `critical` and `serious` are errors; `moderate`, `minor`, a
//!   missing impact and any impact this module does not know are warnings.
//! - Only `violations` count; axe's `incomplete` (needs review) and `passes` are ignored.
//! - A cell on a platform that is not a `web` renderer cannot be scanned: [`A11yError::NotWeb`].

// frob:ticket 01M4CXRZAE5N45BP0RJPT56WSN

use std::path::Path;
use std::time::Duration;

use crunk_spec::model::RendererParams;
use crunk_spec::{DesignSpec, Severity};
use gob_exec::{Limits, Runner};
use serde::{Deserialize, Serialize};
use tracing::{debug, info, warn};

use crate::cells::Cell;
use crate::render::playwright::{self, SCRIPT, WORK_DIR};
use crate::render::{
    RenderError, RenderOptions, arg, render_env, require_success, resolve, spec_for,
};

/// The command that installs axe-core next to Playwright.
pub const AXE_REMEDY: &str = "npm install --save-dev axe-core";

/// Separator between the parts of a node target that crosses a frame or shadow boundary.
const BOUNDARY: &str = " >> ";

/// Why a T3 scan could not produce findings.
#[derive(Debug, thiserror::Error)]
pub enum A11yError {
    /// The axe report is unreadable or lacks `violations`.
    #[error("axe report is unusable: {0}")]
    BadReport(String),
    /// The cell's platform is not a `web` renderer, so there is no browser to scan in.
    #[error("platform `{platform}` is not a web renderer; T3 axe needs a browser")]
    NotWeb {
        /// The platform id.
        platform: String,
    },
    /// axe-core is not installed in the project.
    #[error("axe-core is not available; install it with: {remedy}")]
    AxeMissing {
        /// The install command.
        remedy: String,
    },
    /// Rendering infrastructure failed (Playwright missing, timeout, script failure, bad cell).
    #[error(transparent)]
    Render(#[from] RenderError),
}

/// One axe violation on one node of one cell.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct AxeFinding {
    /// The axe rule id, for example `color-contrast`.
    pub rule: String,
    /// Effective severity (never `off`), from axe's impact.
    pub severity: Severity,
    /// What is wrong, with axe's help text.
    pub message: String,
    /// The node: its CSS selector, frames and shadow roots joined with ` >> `.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub node: Option<String>,
    /// The node's HTML snippet as axe reported it.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub html: Option<String>,
    /// axe's impact word, when it gave one.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub impact: Option<String>,
    /// axe's documentation link for the rule.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub help_url: Option<String>,
    /// Screen concerned.
    pub screen: String,
    /// State concerned.
    pub state: String,
    /// Platform concerned.
    pub platform: String,
}

/// Runs axe-core against one cell and returns the raw axe results JSON.
pub trait AxeScanner {
    /// Scan `cell` of `spec` in a browser; the text is axe's results object (or its `violations`).
    ///
    /// # Errors
    /// Any [`A11yError`]; the check does not guess a clean result when this fails.
    fn scan(&self, spec: &DesignSpec, cell: &Cell) -> Result<String, A11yError>;
}

/// An axe target part: a selector, or a chain of them through frames and shadow roots.
#[derive(Debug, Deserialize)]
#[serde(untagged)]
enum Target {
    One(String),
    Chain(Vec<String>),
}

/// One node of a violation as axe writes it.
#[derive(Debug, Deserialize)]
struct RawNode {
    #[serde(default)]
    target: Vec<Target>,
    #[serde(default)]
    html: Option<String>,
}

/// One violation as axe writes it.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RawViolation {
    id: String,
    #[serde(default)]
    impact: Option<String>,
    #[serde(default)]
    help: Option<String>,
    #[serde(default)]
    help_url: Option<String>,
    #[serde(default)]
    nodes: Vec<RawNode>,
}

/// The slice of axe's results object this module reads.
#[derive(Debug, Deserialize)]
struct RawReport {
    violations: Vec<RawViolation>,
}

/// The severity of an axe impact word.
fn severity_of(impact: Option<&str>) -> Severity {
    match impact {
        Some("critical" | "serious") => Severity::Error,
        _ => Severity::Warn,
    }
}

/// A node's selector, with frame and shadow boundaries joined; `None` when axe gave none.
fn node_selector(node: &RawNode) -> Option<String> {
    let parts: Vec<String> = node
        .target
        .iter()
        .map(|t| match t {
            Target::One(s) => s.clone(),
            Target::Chain(c) => c.join(BOUNDARY),
        })
        .filter(|s| !s.is_empty())
        .collect();
    (!parts.is_empty()).then(|| parts.join(BOUNDARY))
}

/// Turn an axe results document into findings for `cell`, one per violating node.
///
/// # Errors
/// [`A11yError::BadReport`] for text that is not an axe results object with `violations`, or a
/// violation without an id.
pub fn parse_axe(json: &str, cell: &Cell) -> Result<Vec<AxeFinding>, A11yError> {
    let report: RawReport =
        serde_json::from_str(json).map_err(|e| A11yError::BadReport(e.to_string()))?;
    let mut out = Vec::new();
    for v in report.violations {
        if v.id.trim().is_empty() {
            return Err(A11yError::BadReport(
                "a violation has an empty id".to_owned(),
            ));
        }
        let severity = severity_of(v.impact.as_deref());
        let help = v.help.clone().unwrap_or_else(|| v.id.clone());
        let nodes: Vec<Option<&RawNode>> = if v.nodes.is_empty() {
            vec![None]
        } else {
            v.nodes.iter().map(Some).collect()
        };
        for node in nodes {
            let selector = node.and_then(node_selector);
            let message = match &selector {
                Some(sel) => format!("{} (axe `{}`) at `{sel}`", help, v.id),
                None => format!("{} (axe `{}`)", help, v.id),
            };
            out.push(AxeFinding {
                rule: v.id.clone(),
                severity,
                message,
                node: selector,
                html: node.and_then(|n| n.html.clone()),
                impact: v.impact.clone(),
                help_url: v.help_url.clone(),
                screen: cell.screen.clone(),
                state: cell.state.clone(),
                platform: cell.platform.clone(),
            });
        }
    }
    Ok(out)
}

/// The T3 check: scan `cell` with `scanner` and return a finding per violating node.
///
/// # Errors
/// The scanner's error, or [`A11yError::BadReport`] when its output cannot be read.
pub fn check_a11y(
    spec: &DesignSpec,
    cell: &Cell,
    scanner: &dyn AxeScanner,
) -> Result<Vec<AxeFinding>, A11yError> {
    debug!(screen = %cell.screen, state = %cell.state, platform = %cell.platform, "axe scan");
    let text = scanner.scan(spec, cell)?;
    let findings = parse_axe(&text, cell)?;
    info!(screen = %cell.screen, state = %cell.state, count = findings.len(), "axe scan done");
    Ok(findings)
}

/// The real scanner: Playwright plus axe-core through [`gob_exec::Runner`].
#[derive(Debug)]
pub struct PlaywrightAxe {
    opts: RenderOptions,
    runner: Runner,
}

impl PlaywrightAxe {
    /// A scanner that keeps its request files and results under `opts.out_dir`.
    #[must_use]
    pub fn new(opts: RenderOptions) -> Self {
        let runner = Runner::new(Limits { jobs: 1 }).output_cap(opts.output_cap);
        Self { opts, runner }
    }

    /// The wall-clock limit of one scan.
    #[must_use]
    pub fn timeout(&self) -> Duration {
        self.opts.timeout
    }

    /// Write the script and request, run it, and return the results file's text.
    fn run(&self, spec: &DesignSpec, cell: &Cell, results: &Path) -> Result<String, A11yError> {
        let resolved = resolve(spec, cell)?;
        let RendererParams::Web(web) = &resolved.platform.params else {
            return Err(A11yError::NotWeb {
                platform: cell.platform.clone(),
            });
        };
        playwright::probe(&self.runner, &self.opts, &spec.root)?;
        let mut body = playwright::request(spec, &resolved, web, results)?;
        body["output"] = serde_json::Value::Null;
        body["axe_output"] = serde_json::Value::String(arg(results)?);
        let work = self.opts.out_dir.join(WORK_DIR);
        std::fs::create_dir_all(&work).map_err(RenderError::from)?;
        let script = work.join("render.mjs");
        std::fs::write(&script, SCRIPT).map_err(RenderError::from)?;
        let req = work.join(format!(
            "{}__{}__{}.axe-request.json",
            cell.screen, cell.state, cell.platform
        ));
        std::fs::write(&req, body.to_string()).map_err(RenderError::from)?;
        if results.exists() {
            std::fs::remove_file(results).map_err(RenderError::from)?;
        }
        let exec = spec_for(
            self.opts.node.clone(),
            vec![arg(&script)?, arg(&req)?],
            Some(&spec.root),
            vec![("CRUNK_AXE_OUTPUT".to_owned(), arg(results)?)],
            self.opts.timeout,
        );
        let out = self
            .runner
            .run_with_env(&exec, &render_env())
            .map_err(RenderError::from)?;
        require_success(out, self.opts.timeout).map_err(|e| match e {
            RenderError::Failed { stderr, .. } if stderr.contains("axe-core") => {
                warn!("axe-core could not be resolved");
                A11yError::AxeMissing {
                    remedy: AXE_REMEDY.to_owned(),
                }
            }
            other => A11yError::Render(other),
        })?;
        std::fs::read_to_string(results)
            .map_err(|_| A11yError::BadReport("the scan wrote no results file".to_owned()))
    }
}

impl AxeScanner for PlaywrightAxe {
    /// Run axe-core in the cell's browser page and return its results JSON.
    fn scan(&self, spec: &DesignSpec, cell: &Cell) -> Result<String, A11yError> {
        let name = format!(
            "{}__{}__{}.axe.json",
            cell.screen, cell.state, cell.platform
        );
        if name.contains(['/', '\\']) {
            return Err(A11yError::Render(RenderError::BadCell(format!(
                "cell `{}` cannot be used in a results name",
                cell.screen
            ))));
        }
        std::fs::create_dir_all(&self.opts.out_dir).map_err(RenderError::from)?;
        self.run(spec, cell, &self.opts.out_dir.join(name))
    }
}
