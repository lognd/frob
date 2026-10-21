//! The `web` renderer: Playwright, out of process, driven by a small embedded Node script.

// frob:ticket 01M43ATDR7DWY5RZPB3QB3GE3K

use std::path::Path;

use crunk_spec::DesignSpec;
use crunk_spec::model::WebRendererParams;
use gob_exec::{Outcome, Runner};
use gob_path::Shown;
use serde_json::{Value, json};
use tracing::{debug, warn};

use super::{RenderError, RenderOptions, Resolved, arg, render_env, require_success, spec_for};
use crate::cells::Cell;

/// The Node script, shipped inside the crate and written next to the artifacts at render time.
pub const SCRIPT: &str = include_str!("../../node/render.mjs");

/// The command that installs Playwright and a browser.
pub const REMEDY: &str = "npm install --save-dev playwright && npx playwright install chromium";

/// Hidden directory inside the artifacts dir that holds the script and request files.
const WORK_DIR: &str = ".crunk";

/// Check that Node can resolve `playwright` from the project root.
///
/// # Errors
/// [`RenderError::PlaywrightMissing`] when Node is absent or cannot resolve the package.
pub(crate) fn probe(runner: &Runner, opts: &RenderOptions, root: &Path) -> Result<(), RenderError> {
    let exec = spec_for(
        opts.node.clone(),
        vec!["-e".to_owned(), "require.resolve('playwright')".to_owned()],
        Some(root),
        Vec::new(),
        opts.timeout,
    );
    let missing = |reason: String| RenderError::PlaywrightMissing {
        reason,
        remedy: REMEDY.to_owned(),
    };
    match runner.run_with_env(&exec, &render_env()) {
        Ok(out) if out.status == Outcome::Exited(0) => {
            debug!("playwright resolved");
            Ok(())
        }
        Ok(out) => {
            warn!(status = ?out.status, "playwright did not resolve");
            Err(missing("the `playwright` package was not found".to_owned()))
        }
        Err(gob_exec::ExecError::NotFound { program }) => {
            Err(missing(format!("`{program}` was not found on PATH")))
        }
        Err(e) => Err(RenderError::Exec(e)),
    }
}

/// The request document the script reads: the resolved web platform plus the state's script.
fn request(
    spec: &DesignSpec,
    resolved: &Resolved<'_>,
    web: &WebRendererParams,
    target: &Path,
) -> Result<Value, RenderError> {
    let entry = &resolved.screen.entry;
    let url = if entry.contains("://") {
        entry.clone()
    } else {
        let base = web.base_url.as_deref().ok_or_else(|| {
            RenderError::BadCell(format!(
                "platform `{}` has no base_url for entry `{entry}`",
                resolved.platform.id
            ))
        })?;
        format!(
            "{}/{}",
            base.trim_end_matches('/'),
            entry.trim_start_matches('/')
        )
    };
    let state = resolved.state;
    let media = state.media.as_ref().unwrap_or(&web.media);
    debug!(root = %Shown::of(&spec.root), %url, "built playwright request");
    Ok(json!({
        "engine": web.engine,
        "url": url,
        "viewport": web.viewport,
        "device_scale": web.device_scale,
        "media": media,
        "locale": web.locale,
        "java_script_enabled": web.java_script_enabled,
        "init_scripts": web.init_scripts,
        "cpu_throttle": web.cpu_throttle,
        "network_throttle": web.network_throttle,
        "settle_ms": state.settle_ms.unwrap_or(web.settle_ms),
        "actions": state.actions,
        "network": state.network,
        "expect_url": state.expect_url,
        "output": target,
    }))
}

/// Screenshot one cell with Playwright into `target`.
///
/// # Errors
/// [`RenderError::BadCell`] without a usable URL, [`RenderError::TimedOut`] when the browser
/// outlives the timeout (it is killed), [`RenderError::Failed`] on a script failure.
pub(crate) fn render(
    runner: &Runner,
    spec: &DesignSpec,
    cell: &Cell,
    resolved: &Resolved<'_>,
    web: &WebRendererParams,
    opts: &RenderOptions,
    target: &Path,
) -> Result<(), RenderError> {
    let body = request(spec, resolved, web, target)?;
    let work = opts.out_dir.join(WORK_DIR);
    std::fs::create_dir_all(&work)?;
    let script = work.join("render.mjs");
    std::fs::write(&script, SCRIPT)?;
    let req = work.join(format!(
        "{}__{}__{}.request.json",
        cell.screen, cell.state, cell.platform
    ));
    std::fs::write(&req, body.to_string())?;
    let exec = spec_for(
        opts.node.clone(),
        vec![arg(&script)?, arg(&req)?],
        Some(&spec.root),
        vec![("CRUNK_OUTPUT".to_owned(), arg(target)?)],
        opts.timeout,
    );
    let out = runner.run_with_env(&exec, &render_env())?;
    require_success(out, opts.timeout).map(|_| ())
}
