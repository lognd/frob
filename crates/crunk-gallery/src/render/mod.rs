//! Cell rendering: each `(screen, state, platform)` cell becomes a hashed PNG in the artifacts dir.
//!
//! Two renderers exist, picked by the platform's `renderer`: `web` drives Playwright through a
//! small Node script ([`playwright`]), `command` runs the platform's own capture command
//! ([`command`]). Both go through [`gob_exec::Runner`], so every child has a wall-clock timeout,
//! an output cap and a scrubbed environment. A cell that fails is recorded and the run goes on;
//! only a missing Playwright (which makes every web cell hopeless) stops the run, as a typed
//! [`RenderError::PlaywrightMissing`] whose [`RenderError::exit_code`] is 2.
//!
//! Playwright executes the project's own code (its pages and init scripts), so a web render is a
//! trust decision: [`TRUST_NOTICE`] is attached to every report that rendered a cell. A `command`
//! platform runs a shell command from `crunk.toml`, so it needs the same notice.

// frob:ticket 01M43ATDR7DWY5RZPB3QB3GE3K

pub mod command;
pub mod playwright;

use std::path::{Path, PathBuf};
use std::time::Duration;

use crunk_spec::DesignSpec;
use crunk_spec::model::{PlatformConfig, RendererParams};
use crunk_spec::table::{ScreenConfig, ScreenState};
use gob_exec::{EnvPolicy, ExecError, Limits, Outcome, Output, Program, Runner, Spec};
use gob_path::Shown;
use sha2::{Digest, Sha256};
use tracing::{debug, info, warn};

use crate::cells::Cell;

/// What a web render means: the project's pages and scripts run in a real browser.
pub const TRUST_NOTICE: &str = "rendering executes project code (pages and init scripts in a real browser, capture commands from crunk.toml in a shell); render only a project you trust";

/// Largest file the renderers read back whole (a PNG or a results JSON); a bigger one is refused.
pub(crate) const MAX_READ_BYTES: u64 = 64 * 1024 * 1024;

// frob:ticket 01M7X35VAR5GZ8AQ5NGPAD8WST
/// Read the regular file at `path`, refusing one larger than [`MAX_READ_BYTES`] before loading it.
pub(crate) fn read_capped(path: &Path) -> std::io::Result<Vec<u8>> {
    let len = std::fs::metadata(path)?.len();
    if len > MAX_READ_BYTES {
        return Err(std::io::Error::other(format!(
            "file is {len} bytes, over the {MAX_READ_BYTES} byte read cap"
        )));
    }
    std::fs::read(path)
}

// frob:ticket 01M7X35VAR5GZ8AQ5NGPAD8WST
/// [`read_capped`] as text.
pub(crate) fn read_text_capped(path: &Path) -> std::io::Result<String> {
    String::from_utf8(read_capped(path)?)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))
}

// frob:ticket 01M7X35VAR5GZ8AQ5NGPAD8WST
/// True when `id` is one plain file-name component: no separators, `..`, drive or stream `:`, or reserved name.
pub(crate) fn is_plain_component(id: &str) -> bool {
    !id.contains(['/', '\\']) && !id.contains("..") && gob_path::RelPath::new(id).is_ok()
}

/// The PNG file signature every rendered artifact must start with.
const PNG_MAGIC: &[u8] = &[0x89, b'P', b'N', b'G', 0x0d, 0x0a, 0x1a, 0x0a];

/// Environment names a renderer child may inherit on top of the gob-exec baseline.
const RENDER_ENV: &[&str] = &[
    "LANG",
    "LC_ALL",
    "TERM",
    "TMPDIR",
    "DISPLAY",
    "XDG_CACHE_HOME",
    "PLAYWRIGHT_BROWSERS_PATH",
    "NODE_PATH",
];

/// Knobs of one render run.
#[derive(Debug, Clone)]
pub struct RenderOptions {
    /// Artifacts directory; PNGs land directly in it.
    pub out_dir: PathBuf,
    /// Wall-clock limit per renderer child.
    pub timeout: Duration,
    /// Cap on a child's captured output, in bytes.
    pub output_cap: usize,
    /// The Node program that runs the Playwright script.
    pub node: Program,
}

impl RenderOptions {
    /// Defaults (60 s per cell, 1 MiB of output, `node` from `PATH`) writing into `out_dir`.
    pub fn new(out_dir: impl Into<PathBuf>) -> Self {
        Self {
            out_dir: out_dir.into(),
            timeout: Duration::from_secs(60),
            output_cap: 1024 * 1024,
            node: Program::Tool {
                name: "node".to_owned(),
            },
        }
    }
}

/// Why a render, or one cell of it, failed.
#[derive(Debug, thiserror::Error)]
pub enum RenderError {
    /// Node or Playwright is not installed; `remedy` is the command that fixes it.
    #[error("playwright is not available ({reason}); install it with: {remedy}")]
    PlaywrightMissing {
        /// What was found missing.
        reason: String,
        /// The install command.
        remedy: String,
    },
    /// The renderer child ran past the timeout and was killed.
    #[error("renderer timed out after {0:?} and was killed")]
    TimedOut(Duration),
    /// The renderer child exited non-zero or was signaled.
    #[error("renderer failed ({status}): {stderr}")]
    Failed {
        /// How it ended, human readable.
        status: String,
        /// Its (redacted) stderr, trimmed.
        stderr: String,
    },
    /// The renderer succeeded but left no PNG at the expected path.
    #[error("renderer produced no PNG at {0}")]
    NoOutput(PathBuf),
    /// The cell names a screen, state or platform the spec does not have, or lacks a base URL.
    #[error("cell cannot be rendered: {0}")]
    BadCell(String),
    /// Process supervision failed.
    #[error(transparent)]
    Exec(#[from] ExecError),
    /// Reading or writing an artifact failed.
    #[error("artifact I/O failed: {0}")]
    Io(#[from] std::io::Error),
}

impl RenderError {
    /// The process exit code the CLI should use: 2 for a missing Playwright, else 1.
    #[must_use]
    pub const fn exit_code(&self) -> i32 {
        match self {
            Self::PlaywrightMissing { .. } => 2,
            _ => 1,
        }
    }
}

/// A rendered artifact: its path relative to the artifacts dir and the SHA-256 of its bytes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Rendered {
    /// File name inside the artifacts dir.
    pub path: String,
    /// Lowercase hex SHA-256 of the PNG.
    pub sha256: String,
}

/// The outcome of one cell.
#[derive(Debug)]
pub struct CellResult {
    /// The cell that was rendered.
    pub cell: Cell,
    /// The artifact, or why the cell is marked failed.
    pub outcome: Result<Rendered, RenderError>,
}

/// The outcome of a whole run.
#[derive(Debug)]
pub struct RenderReport {
    /// One result per requested cell, in request order.
    pub results: Vec<CellResult>,
    /// [`TRUST_NOTICE`] when any cell was attempted (web or command).
    pub notice: Option<&'static str>,
}

impl RenderReport {
    /// How many cells failed.
    #[must_use]
    pub fn failed(&self) -> usize {
        self.results.iter().filter(|r| r.outcome.is_err()).count()
    }
}

/// Render `cells` of `spec` into `opts.out_dir`; a failing cell is recorded, not fatal.
///
/// # Errors
/// [`RenderError::PlaywrightMissing`] when a web cell is requested and Playwright is not
/// installed, [`RenderError::Io`] when the artifacts dir cannot be created.
pub fn render(
    spec: &DesignSpec,
    cells: &[Cell],
    opts: &RenderOptions,
) -> Result<RenderReport, RenderError> {
    std::fs::create_dir_all(&opts.out_dir)?;
    let runner = Runner::new(Limits { jobs: 1 }).output_cap(opts.output_cap);
    let notice = prepare(&runner, spec, cells, opts)?;
    let mut results = Vec::with_capacity(cells.len());
    for cell in cells {
        let outcome = render_cell(&runner, spec, cell, opts);
        match &outcome {
            Ok(r) => {
                info!(screen = %cell.screen, state = %cell.state, platform = %cell.platform, path = %r.path, "cell rendered");
            }
            Err(e) => {
                warn!(screen = %cell.screen, state = %cell.state, platform = %cell.platform, error = %e, "cell failed");
            }
        }
        results.push(CellResult {
            cell: cell.clone(),
            outcome,
        });
    }
    Ok(RenderReport { results, notice })
}

// frob:ticket 01M7X35VAR5GZ8AQ5NGPAD8WST
/// Before any cell runs: log and return [`TRUST_NOTICE`] when a cell executes project code (every
/// renderer does, a browser page or a shell command), and probe Playwright when a web cell needs it.
fn prepare(
    runner: &Runner,
    spec: &DesignSpec,
    cells: &[Cell],
    opts: &RenderOptions,
) -> Result<Option<&'static str>, RenderError> {
    let platform_of = |c: &Cell| spec.platforms.get(&c.platform);
    let notice = cells
        .iter()
        .any(|c| platform_of(c).is_some())
        .then_some(TRUST_NOTICE);
    if let Some(n) = notice {
        warn!("{n}");
    }
    if cells
        .iter()
        .any(|c| platform_of(c).is_some_and(|p| matches!(p.params, RendererParams::Web(_))))
    {
        playwright::probe(runner, opts, &spec.root)?;
    }
    Ok(notice)
}

/// Everything a renderer needs about one cell, resolved from the spec.
pub(crate) struct Resolved<'a> {
    pub(crate) screen: &'a ScreenConfig,
    pub(crate) state: &'a ScreenState,
    pub(crate) platform: &'a PlatformConfig,
}

/// Look the cell up in the spec.
pub(crate) fn resolve<'a>(spec: &'a DesignSpec, cell: &Cell) -> Result<Resolved<'a>, RenderError> {
    let bad = |what: &str, id: &str| RenderError::BadCell(format!("unknown {what} `{id}`"));
    let screen = spec
        .screens
        .get(&cell.screen)
        .ok_or_else(|| bad("screen", &cell.screen))?;
    let state = screen
        .states
        .iter()
        .find(|s| s.id == cell.state)
        .ok_or_else(|| bad("state", &cell.state))?;
    let platform = spec
        .platforms
        .get(&cell.platform)
        .ok_or_else(|| bad("platform", &cell.platform))?;
    Ok(Resolved {
        screen,
        state,
        platform,
    })
}

/// The artifact file name of `cell`; ids carrying path syntax are refused.
fn artifact_name(cell: &Cell) -> Result<String, RenderError> {
    for id in [&cell.screen, &cell.state, &cell.platform] {
        if id.is_empty() || !is_plain_component(id) {
            return Err(RenderError::BadCell(format!(
                "id `{id}` cannot be used in an artifact name"
            )));
        }
    }
    Ok(format!(
        "{}__{}__{}.png",
        cell.screen, cell.state, cell.platform
    ))
}

/// Remove a previous artifact at `target` so a renderer that writes nothing is detected.
fn clear_stale_artifact(target: &Path) -> Result<(), RenderError> {
    match std::fs::remove_file(target) {
        Err(e) if e.kind() != std::io::ErrorKind::NotFound => Err(e.into()),
        _ => Ok(()),
    }
}

/// Render one cell through the renderer its platform names, then verify and hash the PNG.
fn render_cell(
    runner: &Runner,
    spec: &DesignSpec,
    cell: &Cell,
    opts: &RenderOptions,
) -> Result<Rendered, RenderError> {
    let resolved = resolve(spec, cell)?;
    let name = artifact_name(cell)?;
    let target = opts.out_dir.join(&name);
    clear_stale_artifact(&target)?;
    debug!(cell = ?cell, renderer = %resolved.platform.renderer, "rendering cell");
    match &resolved.platform.params {
        RendererParams::Web(web) => {
            playwright::render(runner, spec, cell, &resolved, web, opts, &target)?;
        }
        RendererParams::Command(cmd) => {
            command::render(runner, spec, cell, &resolved, cmd, opts, &target)?;
        }
    }
    let bytes = read_capped(&target).map_err(|_| RenderError::NoOutput(target.clone()))?;
    if !bytes.starts_with(PNG_MAGIC) {
        return Err(RenderError::Failed {
            status: "exit 0".to_owned(),
            stderr: format!("{} is not a PNG", Shown::of(&target)),
        });
    }
    Ok(Rendered {
        path: name,
        sha256: hex(&Sha256::digest(&bytes)),
    })
}

/// Lowercase hex of `bytes`.
fn hex(bytes: &[u8]) -> String {
    use std::fmt::Write as _;
    bytes.iter().fold(String::new(), |mut acc, b| {
        write!(acc, "{b:02x}").ok();
        acc
    })
}

/// The scrubbed environment every renderer child gets.
pub(crate) fn render_env() -> EnvPolicy {
    EnvPolicy::scrubbed(RENDER_ENV.iter().copied())
}

/// Turn a finished child into `Ok(output)` or the matching [`RenderError`].
pub(crate) fn require_success(out: Output, timeout: Duration) -> Result<Output, RenderError> {
    match out.status {
        Outcome::Exited(0) => Ok(out),
        Outcome::TimedOut => Err(RenderError::TimedOut(timeout)),
        other => Err(RenderError::Failed {
            status: format!("{other:?}"),
            stderr: out.stderr.trim().to_owned(),
        }),
    }
}

/// A [`Spec`] for a captured renderer child with the options' timeout.
pub(crate) fn spec_for(
    program: Program,
    args: Vec<String>,
    cwd: Option<&Path>,
    env: Vec<(String, String)>,
    timeout: Duration,
) -> Spec {
    Spec {
        program,
        args,
        cwd: cwd.map(Path::to_path_buf),
        env,
        timeout,
        capture: true,
    }
}

#[expect(
    clippy::disallowed_methods,
    reason = "gob_path::Arg does not exist yet; this is the one place paths become argv text"
)]
/// `path` as a command-line argument; a non-UTF-8 path is a [`RenderError::BadCell`].
pub(crate) fn arg(path: &Path) -> Result<String, RenderError> {
    path.to_str()
        .map(str::to_owned)
        .ok_or_else(|| RenderError::BadCell(format!("path {} is not UTF-8", Shown::of(path))))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crunk_spec::parse_spec;

    fn cell(screen: &str, state: &str, platform: &str) -> Cell {
        Cell {
            screen: screen.to_owned(),
            state: state.to_owned(),
            platform: platform.to_owned(),
        }
    }

    fn spec_with(platform: &str, dir: &Path) -> DesignSpec {
        let text = format!(
            "[project]\ncss_root = \".\"\ntokens_file = \"t.css\"\nroot_font_size = 10\n\n\
             [palette]\na = \"white\"\n\n[scales]\nspacing = [1]\nfont_sizes = [10]\n\n\
             [typography]\nfamilies = [\"x\"]\nweights = [400]\n\n[org]\nbuckets = [\"b\"]\n\n\
             {platform}\n\n[[screen]]\nid = \"home\"\nentry = \"/\"\n\n\
             [[screen.states]]\nid = \"default\"\n"
        );
        parse_spec(&text, &dir.join("design.toml"), dir).expect("spec parses")
    }

    // frob:ticket 01M7X35VAR5GZ8AQ5NGPAD8WST
    #[test]
    fn a_command_cell_gets_the_trust_notice() {
        let dir = tempfile::tempdir().expect("dir");
        let spec = spec_with(
            "[[platform]]\nid = \"shot\"\nrenderer = \"command\"\ncommand = \"true\"\n",
            dir.path(),
        );
        let runner = Runner::new(Limits { jobs: 1 });
        let opts = RenderOptions::new(dir.path().join("art"));
        let one = [cell("home", "default", "shot")];
        assert!(
            prepare(&runner, &spec, &one, &opts)
                .expect("prepare")
                .is_some()
        );
        assert!(
            prepare(&runner, &spec, &[], &opts)
                .expect("prepare")
                .is_none()
        );
    }

    // frob:ticket 01M7X35VAR5GZ8AQ5NGPAD8WST
    #[test]
    fn artifact_names_refuse_drive_relative_and_stream_ids() {
        assert!(artifact_name(&cell("home", "default", "web")).is_ok());
        for bad in ["C:x", "a:b", "a/b", "a\\b", "..", "a..b", "", "con"] {
            assert!(
                artifact_name(&cell(bad, "default", "web")).is_err(),
                "{bad}"
            );
            assert!(artifact_name(&cell("home", bad, "web")).is_err(), "{bad}");
            assert!(
                artifact_name(&cell("home", "default", bad)).is_err(),
                "{bad}"
            );
        }
    }

    // frob:ticket 01M7X35VAR5GZ8AQ5NGPAD8WST
    #[test]
    fn reads_over_the_cap_are_refused_without_loading() {
        let dir = tempfile::tempdir().expect("dir");
        let small = dir.path().join("small");
        std::fs::write(&small, "ok").expect("write");
        assert_eq!(read_text_capped(&small).expect("small"), "ok");
        let big = dir.path().join("big");
        std::fs::File::create(&big)
            .and_then(|f| f.set_len(MAX_READ_BYTES + 1))
            .expect("sparse file");
        assert!(read_capped(&big).is_err());
        assert!(read_text_capped(&big).is_err());
    }
}
