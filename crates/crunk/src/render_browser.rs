//! `render --engine browser`: a hashed PNG and a boxes JSON per cell, through the gallery renderer.
//!
//! The solver runs first, so every cell has its `<platform>.layout.json`; the cell's scene is then
//! loaded from a `file://` URL in Playwright (the `crunk-gallery` renderer, never a second one),
//! screenshotted, and every solved node id is measured in the page. The files land under
//! `<out>/<screen>/<state>/`:
//!
//! - `<platform>.layout.json`: the solve output, shared with `--engine solve`;
//! - `<platform>.png`: the screenshot, its SHA-256 reported as `sha256`;
//! - `<platform>.boxes.json`: the browser boxes in the layout-solve shape, so both engines name
//!   the same node ids. A solved id the page does not contain fails the cell.
//!
//! Without the `gallery` feature the engine refuses with `E-GALLERY-NOT-BUILT` and the install
//! remedy, exit 2. With it but without Playwright it refuses with `E-PLAYWRIGHT-MISSING` and the
//! install command, exit 2, and writes nothing: there is never a fake PNG or empty boxes file.

// frob:ticket 01M5XCXVAR2WSR1H6X5X7ETR1R

use std::path::Path;
#[cfg(any(feature = "gallery", test))]
use std::path::PathBuf;

use gob_cli::CliError;

#[cfg(any(feature = "gallery", test))]
use crate::render::Item;
#[cfg(feature = "gallery")]
use crate::render::posix;

/// Remedy for a build without the gallery feature.
pub const NOT_BUILT_REMEDY: &str = "cargo install crunk --features gallery";

/// The usage error (exit 2) for `--engine browser` in a build without the gallery feature.
#[must_use]
pub fn not_built() -> CliError {
    tracing::info!("render: browser engine not built in");
    CliError::Usage(format!(
        "E-GALLERY-NOT-BUILT: --engine browser is not built into this crunk binary; rebuild with: {NOT_BUILT_REMEDY}"
    ))
}

/// The usage error (exit 2) for a missing Node or Playwright, naming the install command.
#[must_use]
pub fn playwright_missing(reason: &str, remedy: &str) -> CliError {
    tracing::info!(reason, "render: playwright not available");
    CliError::Usage(format!(
        "E-PLAYWRIGHT-MISSING: --engine browser needs Playwright ({reason}); install it with: {remedy}"
    ))
}

/// The node ids of a layout-solve document, in document order.
///
/// # Errors
///
/// Text that is not JSON, or has no `nodes` array of objects with string `id`s.
pub fn solved_ids(json: &str) -> Result<Vec<String>, String> {
    let doc: serde_json::Value = serde_json::from_str(json).map_err(|e| e.to_string())?;
    let nodes = doc
        .get("nodes")
        .and_then(serde_json::Value::as_array)
        .ok_or_else(|| "solve output has no nodes array".to_owned())?;
    nodes
        .iter()
        .map(|n| {
            n.get("id")
                .and_then(serde_json::Value::as_str)
                .map(str::to_owned)
                .ok_or_else(|| "solve node without a string id".to_owned())
        })
        .collect()
}

/// The solved ids a browser document does not account for as measured nodes.
///
/// `measured` are the ids the page returned as nodes; every solved id absent from it, in solve
/// order, is a mismatch between the two engines.
#[must_use]
pub fn unshared_ids(solved: &[String], measured: &[String]) -> Vec<String> {
    solved
        .iter()
        .filter(|id| !measured.contains(id))
        .cloned()
        .collect()
}

/// The `file://` URL of `path`, with forward slashes and the extra slash a drive letter needs.
#[must_use]
pub fn file_url(path: &Path) -> String {
    // Not `Shown`: it folds the home directory into `~`, which a browser cannot open.
    let text = gob_path::forward_slashes(path);
    if text.starts_with('/') {
        format!("file://{text}")
    } else {
        format!("file:///{text}")
    }
}

/// The project-relative PNG and boxes files of a cell, beside its `<platform>.layout.json`.
#[cfg(any(feature = "gallery", test))]
pub(crate) fn browser_files(base: &str, item: &Item) -> (PathBuf, PathBuf) {
    let dir = Path::new(base).join(&item.screen).join(&item.state);
    (
        dir.join(format!("{}.png", item.platform)),
        dir.join(format!("{}.boxes.json", item.platform)),
    )
}

/// The `/`-joined form of [`browser_files`], as reported in the data.
#[cfg(feature = "gallery")]
pub(crate) fn browser_paths(base: &str, item: &Item) -> (String, String) {
    let (png, boxes) = browser_files(base, item);
    (posix(&png), posix(&boxes))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::render::cell_file;

    // frob:tests crates/crunk/src/render_browser.rs::browser_files
    #[test]
    fn browser_files_sit_beside_the_layout_file() {
        let item = Item {
            screen: "home".into(),
            state: "default".into(),
            platform: "desk.v2".into(),
            scene: PathBuf::new(),
            viewport: (1.0, 1.0),
        };
        let (png, boxes) = browser_files("out", &item);
        let layout = cell_file("out", &item);
        assert_eq!(png.parent(), layout.parent());
        assert_eq!(boxes.parent(), layout.parent());
        assert!(png.ends_with("desk.v2.png"), "{png:?}");
        assert!(boxes.ends_with("desk.v2.boxes.json"), "{boxes:?}");
    }
}

#[cfg(feature = "gallery")]
pub(crate) use imp::run;

#[cfg(feature = "gallery")]
mod imp {
    use super::{browser_files, file_url, playwright_missing, solved_ids, unshared_ids};
    use crate::render::{
        Item, Plan, RenderData, RenderedCell, Solved, cell_file, posix, solve_all, write_file,
    };
    use crunk_gallery::boxes::{BoxesError, capture_boxes};
    use crunk_gallery::cells::Cell;
    use crunk_gallery::render::{RenderError, RenderOptions, render as render_cells};
    use crunk_spec::DesignSpec;
    use gob_cli::{CliError, Outcome, Payload};
    use std::path::Path;

    /// A cell's PNG (path inside the stage dir, SHA-256) and measured boxes document.
    struct Captured {
        png: std::path::PathBuf,
        sha256: String,
        boxes: crunk_gallery::boxes::BrowserBoxes,
    }

    /// `spec` with the screen's entry pointed at the cell's scene file.
    fn spec_for_scene(spec: &DesignSpec, item: &Item) -> DesignSpec {
        let mut cell_spec = spec.clone();
        if let Some(screen) = cell_spec.screens.get_mut(&item.screen) {
            screen.entry = file_url(&item.scene);
        }
        cell_spec
    }

    /// How one cell failed: Playwright is absent (stop the run) or just this cell.
    enum Failure {
        NoPlaywright { reason: String, remedy: String },
        Cell(String),
    }

    impl From<RenderError> for Failure {
        fn from(e: RenderError) -> Self {
            match e {
                RenderError::PlaywrightMissing { reason, remedy } => {
                    Self::NoPlaywright { reason, remedy }
                }
                other => Self::Cell(other.to_string()),
            }
        }
    }

    impl From<BoxesError> for Failure {
        fn from(e: BoxesError) -> Self {
            match e {
                BoxesError::Render(r) => r.into(),
                other => Self::Cell(other.to_string()),
            }
        }
    }

    /// Screenshot and measure one cell into `stage`.
    fn capture(
        spec: &DesignSpec,
        item: &Item,
        ids: &[String],
        stage: &Path,
    ) -> Result<Captured, Failure> {
        let cell_spec = spec_for_scene(spec, item);
        let cell = Cell {
            screen: item.screen.clone(),
            state: item.state.clone(),
            platform: item.platform.clone(),
        };
        let opts = RenderOptions::new(stage);
        let report = render_cells(&cell_spec, std::slice::from_ref(&cell), &opts)?;
        let rendered = report
            .results
            .into_iter()
            .next()
            .ok_or_else(|| Failure::Cell("the renderer returned no result".to_owned()))?
            .outcome?;
        let boxes = capture_boxes(&cell_spec, &cell, ids, &opts)?;
        let measured: Vec<String> = boxes.nodes.iter().map(|n| n.id.clone()).collect();
        let lost = unshared_ids(ids, &measured);
        if !lost.is_empty() {
            return Err(Failure::Cell(format!(
                "the browser page has no node with id {}",
                lost.join(", ")
            )));
        }
        Ok(Captured {
            png: stage.join(&rendered.path),
            sha256: rendered.sha256,
            boxes,
        })
    }

    /// Write the solve JSON, the PNG and the boxes JSON of one cell under the project root.
    fn write_cell(
        plan: &Plan,
        base: &str,
        item: &Item,
        json: &str,
        got: &Captured,
    ) -> Result<(), String> {
        let (png, boxes) = browser_files(base, item);
        write_file(&plan.root.join(cell_file(base, item)), json)?;
        let bytes = std::fs::read(&got.png).map_err(|e| format!("read screenshot: {e}"))?;
        let dest = plan.root.join(&png);
        gob_fs::write_atomic(&dest, &bytes).map_err(|e| format!("write png: {e}"))?;
        let text = serde_json::to_string_pretty(&got.boxes).map_err(|e| e.to_string())?;
        write_file(&plan.root.join(&boxes), &format!("{text}\n"))
    }

    /// The cells written so far, their report lines and the cells that failed.
    #[derive(Default)]
    struct Collected {
        data: Vec<RenderedCell>,
        text: Vec<String>,
        failures: Vec<String>,
    }

    /// Solve, screenshot, measure and write one cell; its report line is the label and paths.
    fn build_cell(
        plan: &Plan,
        out: &str,
        item: &Item,
        solved: Result<Solved, String>,
        stage: &Path,
    ) -> Result<RenderedCell, Failure> {
        let s = solved.map_err(Failure::Cell)?;
        let ids = solved_ids(&s.json).map_err(Failure::Cell)?;
        let got = capture(&plan.spec, item, &ids, stage)?;
        write_cell(plan, out, item, &s.json, &got).map_err(Failure::Cell)?;
        let (png, boxes) = super::browser_paths(out, item);
        Ok(RenderedCell {
            screen: item.screen.clone(),
            state: item.state.clone(),
            platform: item.platform.clone(),
            path: posix(&cell_file(out, item)),
            nodes: s.nodes,
            png: Some(png),
            sha256: Some(got.sha256),
            boxes: Some(boxes),
        })
    }

    /// Build every cell in order; only a missing Playwright stops the run.
    fn collect(plan: &Plan, out: &str, stage: &Path) -> Result<Collected, CliError> {
        let mut done = Collected {
            text: plan.skipped.clone(),
            ..Collected::default()
        };
        for (item, solved) in plan.items.iter().zip(solve_all(plan)) {
            let label = format!("{}/{} on {}", item.screen, item.state, item.platform);
            match build_cell(plan, out, item, solved, stage) {
                Ok(cell) => {
                    tracing::info!(cell = %label, nodes = cell.nodes, "render: browser cell written");
                    let files =
                        [cell.png.as_deref(), cell.boxes.as_deref()].map(Option::unwrap_or_default);
                    done.text.push(format!("{label}: {}", files.join(", ")));
                    done.data.push(cell);
                }
                Err(Failure::NoPlaywright { reason, remedy }) => {
                    return Err(playwright_missing(&reason, &remedy));
                }
                Err(Failure::Cell(e)) => {
                    tracing::info!(cell = %label, error = %e, "render: browser cell failed");
                    done.failures.push(format!("{label}: {e}"));
                }
            }
        }
        Ok(done)
    }

    /// Turn the collected cells into the verb's outcome: success, or a gate failure with the data.
    fn finish(done: Collected) -> Outcome<RenderData> {
        let data = RenderData {
            engine: "browser".to_owned(),
            cells: done.data,
        };
        if done.failures.is_empty() {
            return Ok(Payload::new(data).with_rendered(done.text));
        }
        let value = serde_json::to_value(&data).map_err(CliError::internal)?;
        Err(CliError::Gate {
            message: format!("render: {} cell(s) failed", done.failures.len()),
            data: value,
            warnings: done.failures,
        })
    }

    /// Solve every cell, then screenshot and measure it in the browser.
    pub(crate) fn run(plan: &Plan, out: &str) -> Outcome<RenderData> {
        let stage = plan.root.join(out).join(".browser-work");
        let collected = collect(plan, out, &stage);
        discard(&stage);
        finish(collected?)
    }

    /// Remove the staging directory; a leftover is only scratch, so failure is logged.
    fn discard(stage: &Path) {
        if let Err(e) = std::fs::remove_dir_all(stage)
            && e.kind() != std::io::ErrorKind::NotFound
        {
            tracing::warn!(error = %e, "render: could not remove the staging directory");
        }
    }
}
