//! T2/T3 browser boxes: Playwright measures each `data-id` node of a cell, in the layout-solve shape.
//!
//! The result is a [`BrowserBoxes`]: the same fields as the solver's `crunk-layout-solve-v1`
//! document (`version`, viewport, `nodes` with `id`, `parent`, `kind`, `x`, `y`, `width`, `height`,
//! `focus_order`) so a solver box and a browser box compare field for field, plus two browser-only
//! additions: `hidden` on a node and a top-level `missing` list. Coordinates sit on the solver's
//! 1/64 px grid.
//!
//! The browser half is `node/boxes.mjs`, run through the same [`gob_exec::Runner`], probe, request
//! builder, timeout and scrubbed environment as a render; only the page measurement is new.
//!
//! # Edge cases
//!
//! - Settling is enforced in the page (fixed clock, animations off, network idle, fonts ready); a
//!   page whose fonts are not ready or whose animations keep running is [`BoxesError::Unsettled`].
//! - A requested id absent from the DOM is listed in `missing`, never dropped; an id that is in
//!   neither `nodes` nor `missing` makes the report [`BoxesError::BadReport`].
//! - A `display: none` node (or one with no layout box) is emitted with `hidden: true` and zeros.
//! - Playwright missing is [`RenderError::PlaywrightMissing`] (exit code 2).
//! - A page that never settles hits the wall-clock timeout, is killed, and is
//!   [`RenderError::TimedOut`].
//! - The capture runs [`RUNS`] times and the documents must be identical, else
//!   [`BoxesError::Unstable`].

// frob:ticket 01M5XCXV74XZTCK4N56B46PAY4

use std::collections::BTreeSet;
use std::path::Path;

use crunk_spec::DesignSpec;
use crunk_spec::model::{RendererParams, WebRendererParams};
use gob_exec::{Limits, Runner};
use serde::{Deserialize, Serialize};
use tracing::{debug, info, warn};

use crate::cells::Cell;
use crate::render::playwright::{self, WORK_DIR};
use crate::render::{
    RenderError, RenderOptions, Resolved, arg, render_env, require_success, resolve, spec_for,
};

/// The Node script, shipped inside the crate and written next to the artifacts at capture time.
pub const SCRIPT: &str = include_str!("../node/boxes.mjs");

/// How many times a capture runs; all runs must agree.
pub const RUNS: usize = 3;

/// Why a box capture produced no document.
#[derive(Debug, thiserror::Error)]
pub enum BoxesError {
    /// The cell's platform is not a `web` renderer, so there is no browser to measure in.
    #[error("platform `{platform}` is not a web renderer; browser boxes need a browser")]
    NotWeb {
        /// The platform id.
        platform: String,
    },
    /// The page refused to settle (fonts not ready or animations still running).
    #[error("page did not settle: {0}")]
    Unsettled(String),
    /// Two runs of the same cell produced different documents.
    #[error("boxes differ between run 1 and run {run}; the page is not stable")]
    Unstable {
        /// The 1-based run that differed from the first.
        run: usize,
    },
    /// The document is unreadable or does not account for every requested id.
    #[error("boxes report is unusable: {0}")]
    BadReport(String),
    /// Rendering infrastructure failed (Playwright missing, timeout, script failure, bad cell).
    #[error(transparent)]
    Render(#[from] RenderError),
}

impl BoxesError {
    /// The process exit code the CLI should use: 2 for a missing Playwright, else 1.
    #[must_use]
    pub const fn exit_code(&self) -> i32 {
        match self {
            Self::Render(e) => e.exit_code(),
            _ => 1,
        }
    }
}

/// What a node is, as in the solver document.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum BoxKind {
    /// A container or leaf rectangle.
    Box,
    /// A run of text.
    Text,
}

/// One measured node.
#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct BrowserNode {
    /// The `data-id`.
    pub id: String,
    /// The nearest ancestor `data-id`; `None` for a root.
    pub parent: Option<String>,
    /// `box` or `text`.
    pub kind: BoxKind,
    /// Left edge in page coordinates.
    pub x: f64,
    /// Top edge in page coordinates.
    pub y: f64,
    /// Width.
    pub width: f64,
    /// Height.
    pub height: f64,
    /// True when the node has no layout box (`display: none`); its box is all zeros.
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub hidden: bool,
}

/// The browser's box document for one cell.
#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct BrowserBoxes {
    /// Schema version of the solver shape, always 1.
    pub version: u32,
    /// Viewport width.
    pub viewport_width: f64,
    /// Viewport height.
    pub viewport_height: f64,
    /// Measured nodes, in the requested order (or document order when no ids were requested).
    pub nodes: Vec<BrowserNode>,
    /// `data-id`s of focusable visible nodes, in the order measured.
    pub focus_order: Vec<String>,
    /// Requested ids that are not in the DOM.
    pub missing: Vec<String>,
}

/// Parse a boxes document and check it accounts for every id in `wanted`.
///
/// # Errors
/// [`BoxesError::BadReport`] for non-JSON text, a wrong version, or a requested id that is
/// neither measured nor listed as missing.
pub fn parse_boxes(json: &str, wanted: &[String]) -> Result<BrowserBoxes, BoxesError> {
    let doc: BrowserBoxes =
        serde_json::from_str(json).map_err(|e| BoxesError::BadReport(e.to_string()))?;
    if doc.version != 1 {
        return Err(BoxesError::BadReport(format!(
            "unsupported version {}",
            doc.version
        )));
    }
    let seen: BTreeSet<&str> = doc
        .nodes
        .iter()
        .map(|n| n.id.as_str())
        .chain(doc.missing.iter().map(String::as_str))
        .collect();
    if let Some(lost) = wanted.iter().find(|id| !seen.contains(id.as_str())) {
        return Err(BoxesError::BadReport(format!(
            "requested id `{lost}` is neither measured nor listed as missing"
        )));
    }
    Ok(doc)
}

/// Measure the `ids` (every `data-id` when empty) of `cell` in a browser, three times, and return
/// the stable document.
///
/// # Errors
/// See [`BoxesError`]; the cell is failed, never guessed.
pub fn capture_boxes(
    spec: &DesignSpec,
    cell: &Cell,
    ids: &[String],
    opts: &RenderOptions,
) -> Result<BrowserBoxes, BoxesError> {
    let plan = plan_capture(spec, cell)?;
    let runner = Runner::new(Limits { jobs: 1 }).output_cap(opts.output_cap);
    playwright::probe(&runner, opts, &spec.root)?;
    let texts = run_all(&runner, spec, opts, &plan, ids)?;
    let text = stable_text(texts).inspect_err(|e| warn!(stem = %plan.stem, "{e}"))?;
    let boxes = parse_boxes(&text, ids)?;
    info!(stem = %plan.stem, nodes = boxes.nodes.len(), missing = boxes.missing.len(), "boxes stable");
    Ok(boxes)
}

/// Writes the script once, then runs the capture `RUNS` times and returns each run's text.
fn run_all(
    runner: &Runner,
    spec: &DesignSpec,
    opts: &RenderOptions,
    plan: &Plan<'_>,
    ids: &[String],
) -> Result<Vec<String>, BoxesError> {
    let work = opts.out_dir.join(WORK_DIR);
    std::fs::create_dir_all(&work).map_err(RenderError::from)?;
    let script = work.join("boxes.mjs");
    std::fs::write(&script, SCRIPT).map_err(RenderError::from)?;
    let stem = &plan.stem;
    let results = opts.out_dir.join(format!("{stem}.boxes.json"));
    let req = work.join(format!("{stem}.boxes-request.json"));
    (1..=RUNS)
        .map(|run| {
            let mut body = playwright::request(spec, &plan.resolved, plan.web, &results)?;
            body["output"] = serde_json::Value::Null;
            body["boxes_output"] = serde_json::Value::String(arg(&results)?);
            body["ids"] = serde_json::json!(ids);
            std::fs::write(&req, body.to_string()).map_err(RenderError::from)?;
            clear_results(&results)?;
            let text = run_once(runner, spec, opts, &script, &req, &results)?;
            debug!(%stem, run, bytes = text.len(), "boxes captured");
            Ok(text)
        })
        .collect()
}

/// The decided facts of one capture: resolved cell, its web params and file-name stem.
struct Plan<'a> {
    resolved: Resolved<'a>,
    web: &'a WebRendererParams,
    stem: String,
}

/// Decides, without effects, whether the cell can be captured and what it is named.
fn plan_capture<'a>(spec: &'a DesignSpec, cell: &Cell) -> Result<Plan<'a>, BoxesError> {
    let resolved = resolve(spec, cell)?;
    let RendererParams::Web(web) = &resolved.platform.params else {
        return Err(BoxesError::NotWeb {
            platform: cell.platform.clone(),
        });
    };
    let stem = format!("{}__{}__{}", cell.screen, cell.state, cell.platform);
    if stem.contains(['/', '\\']) {
        return Err(
            RenderError::BadCell(format!("cell `{stem}` cannot be used in a file name")).into(),
        );
    }
    Ok(Plan {
        resolved,
        web,
        stem,
    })
}

/// Decides, purely, whether every run produced the same text; the first differing run is the error.
fn stable_text(texts: Vec<String>) -> Result<String, BoxesError> {
    let mut it = texts.into_iter();
    let first = it.next().unwrap_or_default();
    match it.position(|t| t != first) {
        Some(i) => Err(BoxesError::Unstable { run: i + 2 }),
        None => Ok(first),
    }
}

/// Removes a stale results file; an absent file is fine.
fn clear_results(results: &Path) -> Result<(), BoxesError> {
    match std::fs::remove_file(results) {
        Err(e) if e.kind() != std::io::ErrorKind::NotFound => Err(RenderError::from(e).into()),
        _ => Ok(()),
    }
}

/// One script run: returns the results file's text.
fn run_once(
    runner: &Runner,
    spec: &DesignSpec,
    opts: &RenderOptions,
    script: &Path,
    req: &Path,
    results: &Path,
) -> Result<String, BoxesError> {
    let exec = spec_for(
        opts.node.clone(),
        vec![arg(script)?, arg(req)?],
        Some(&spec.root),
        Vec::new(),
        opts.timeout,
    );
    let out = runner
        .run_with_env(&exec, &render_env())
        .map_err(RenderError::from)?;
    require_success(out, opts.timeout).map_err(|e| match e {
        RenderError::Failed { stderr, .. } if stderr.contains("unsettled:") => {
            warn!("page did not settle");
            BoxesError::Unsettled(stderr)
        }
        other => BoxesError::Render(other),
    })?;
    std::fs::read_to_string(results)
        .map_err(|_| BoxesError::BadReport("the capture wrote no results file".to_owned()))
}
