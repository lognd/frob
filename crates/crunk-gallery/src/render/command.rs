//! The `command` renderer: run the platform's own capture command and collect its PNG.

// frob:ticket 01M43ATDR7DWY5RZPB3QB3GE3K

use std::path::Path;

use crunk_spec::DesignSpec;
use crunk_spec::model::CommandRendererParams;
use gob_exec::{Program, Runner};
use gob_path::Shown;
use tracing::debug;

use super::{RenderError, RenderOptions, Resolved, arg, render_env, require_success, spec_for};
use crate::cells::Cell;

/// Run `params.command` under `sh -c` and expect it to write a PNG to `$CRUNK_OUTPUT`.
///
/// The child also sees `CRUNK_SCREEN`, `CRUNK_STATE`, `CRUNK_PLATFORM` and `CRUNK_ENTRY`, plus the
/// platform's own `env`; it runs in the platform's `cwd` (relative to the project root).
///
/// # Errors
/// [`RenderError::TimedOut`] when the command outlives the timeout (it is killed),
/// [`RenderError::Failed`] on a non-zero exit, [`RenderError::Exec`] when `sh` cannot run.
pub(crate) fn render(
    runner: &Runner,
    spec: &DesignSpec,
    cell: &Cell,
    resolved: &Resolved<'_>,
    params: &CommandRendererParams,
    opts: &RenderOptions,
    target: &Path,
) -> Result<(), RenderError> {
    let mut env: Vec<(String, String)> = params
        .env
        .iter()
        .map(|(k, v)| (k.clone(), v.clone()))
        .collect();
    env.extend([
        ("CRUNK_OUTPUT".to_owned(), arg(target)?),
        ("CRUNK_SCREEN".to_owned(), cell.screen.clone()),
        ("CRUNK_STATE".to_owned(), cell.state.clone()),
        ("CRUNK_PLATFORM".to_owned(), cell.platform.clone()),
        ("CRUNK_ENTRY".to_owned(), resolved.screen.entry.clone()),
    ]);
    let cwd = params
        .cwd
        .as_ref()
        .map_or_else(|| spec.root.clone(), |c| spec.root.join(c));
    debug!(command = %params.command, cwd = %Shown::of(&cwd), "running command renderer");
    let exec = spec_for(
        Program::Tool {
            name: "sh".to_owned(),
        },
        vec!["-c".to_owned(), params.command.clone()],
        Some(&cwd),
        env,
        opts.timeout,
    );
    let out = runner.run_with_env(&exec, &render_env())?;
    require_success(out, opts.timeout).map(|_| ())
}
