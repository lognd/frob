//! `gallery enumerate|render|triage|check`: the gallery pipeline (opt-in behind the `gallery` cargo feature).
//!
//! Built with `--features gallery` it enumerates the cells of `crunk.toml`, reads the manifest
//! (`--manifest`, default `gallery/manifest.json`) and runs GALLERY001 to GALLERY005; error
//! findings exit 1. The default build keeps the verb so it can say how to get it: it refuses with
//! `E-GALLERY-NOT-BUILT` and the remedy. `enumerate` lists the cells, `render` writes the PNGs and
//! the manifest, `triage` serves a local contact sheet on 127.0.0.1 and saves keyboard verdicts to
//! the manifest. The default binary and the Python wheel stay small.

// frob:ticket 01M43ATDG0RG5DP9PVFAKETJJH
// frob:ticket 01M43ATE06MNRNVJJ314KW24RJ

use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;
use serde_json::Value;

/// Check the gallery manifest against the spec's cells (needs the `gallery` feature).
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "gallery check",
    product = "crunk",
    idempotent = true,
    exits(ok, negative, refused, usage, internal)
)]
#[cfg_attr(not(feature = "gallery"), allow(dead_code))]
pub struct GalleryCheck {
    manifest: String,
    routes: Vec<String>,
}

/// Output of `gallery check`: the check report (`crunk-gallery-check-v1.json`).
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct GalleryData {
    /// Cells the spec enumerates.
    pub cells: usize,
    /// Findings at `error`.
    pub errors: usize,
    /// Findings at `warn`.
    pub warnings: usize,
    /// Every finding (rule, severity, message, screen, state, platform).
    pub findings: Vec<Value>,
}

/// `gallery check` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct GalleryArgs {
    #[arg(
        long,
        value_name = "PATH",
        default_value = "gallery/manifest.json",
        help = "Gallery manifest (v1, v2 or v3), relative to the project root"
    )]
    manifest: String,
    #[arg(
        long = "route",
        value_name = "ROUTE",
        help = "A route the router declares, for GALLERY005 (repeatable)"
    )]
    routes: Vec<String>,
}

impl Command for GalleryCheck {
    type Data = GalleryData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<GalleryArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<GalleryArgs>(m)?;
        Ok(Self {
            manifest: a.manifest,
            routes: a.routes,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<GalleryData> {
        imp::run(self, ctx)
    }
}

fn refusal(code: &str, message: &str) -> Refusal {
    Refusal::new(code, RefusalClass::GuardNeedsAction, message)
}

#[cfg(not(feature = "gallery"))]
mod imp {
    use super::{
        Context, EnumerateData, GalleryCheck, GalleryData, GalleryEnumerate, GalleryRender,
        GalleryTriage, Outcome, RenderData, TriageData, refusal,
    };
    use gob_diagnostics::RemedyCommand;

    /// Refuse: this binary was built without the gallery.
    fn not_built<T>(verb: &str) -> Outcome<T> {
        tracing::info!(verb, "gallery: feature not built in");
        Err(refusal(
            "E-GALLERY-NOT-BUILT",
            "gallery support is not built into this crunk binary",
        )
        .with_command(
            RemedyCommand::new("cargo", "install")
                .arg("crunk")
                .flag("features", "gallery"),
        )
        .into())
    }

    /// Refuse `gallery check`.
    pub(super) fn run(_cmd: &GalleryCheck, _ctx: &Context) -> Outcome<GalleryData> {
        not_built("gallery check")
    }

    /// Refuse `gallery enumerate`.
    pub(super) fn enumerate(_cmd: &GalleryEnumerate, _ctx: &Context) -> Outcome<EnumerateData> {
        not_built("gallery enumerate")
    }

    /// Refuse `gallery render`.
    pub(super) fn render(_cmd: &GalleryRender, _ctx: &Context) -> Outcome<RenderData> {
        not_built("gallery render")
    }

    /// Refuse `gallery triage`.
    pub(super) fn triage(_cmd: &GalleryTriage, _ctx: &Context) -> Outcome<TriageData> {
        not_built("gallery triage")
    }
}

#[cfg(feature = "gallery")]
mod imp {
    use super::{
        CellRow, CliError, Context, EnumerateData, FilterArgs, GalleryCheck, GalleryData,
        GalleryEnumerate, GalleryRender, GalleryTriage, Outcome, RenderData, TriageData, Value,
        refusal,
    };
    use crunk_gallery::cells::{Cell, CellFilter};
    use crunk_gallery::manifest::Status;
    use crunk_gallery::render::{RenderOptions, render as render_cells};
    use crunk_gallery::triage::server::{Session, bind, new_token, serve};
    use crunk_gallery::triage::store::{self, Reviewer};
    use crunk_spec::DesignSpec;
    use gob_cli::Payload;
    use std::path::PathBuf;

    /// Locate the project root and load its design spec.
    fn load(ctx: &Context) -> Result<(PathBuf, DesignSpec), CliError> {
        let root = gob_product::workspace::locate_root(crate::PRODUCT, &ctx.cwd);
        let spec = crunk_spec::load_spec(&root).map_err(|e| {
            tracing::info!(error = %e, "gallery: spec did not load");
            refusal(
                "E-SPEC",
                &format!("crunk.toml is not a valid design spec: {e}"),
            )
            .with_remedy("fix crunk.toml as described, then rerun")
        })?;
        Ok((root, spec))
    }

    fn filter(f: &FilterArgs) -> CellFilter {
        CellFilter {
            screen: f.screen.clone(),
            state: f.state.clone(),
            platform: f.platform.clone(),
        }
    }

    fn rows(cells: &[Cell]) -> Vec<CellRow> {
        cells
            .iter()
            .map(|c| CellRow {
                screen: c.screen.clone(),
                state: c.state.clone(),
                platform: c.platform.clone(),
            })
            .collect()
    }

    fn store_err(e: impl std::fmt::Display) -> CliError {
        tracing::info!(error = %e, "gallery: manifest store failed");
        refusal("E-GALLERY-MANIFEST", &e.to_string())
            .with_remedy("fix the manifest or pass --manifest PATH")
            .into()
    }

    /// List the selected cells.
    pub(super) fn enumerate(cmd: &GalleryEnumerate, ctx: &Context) -> Outcome<EnumerateData> {
        let (_, spec) = load(ctx)?;
        let cells = crunk_gallery::cells::cells(&spec, &filter(&cmd.filter));
        tracing::info!(cells = cells.len(), "gallery enumerate");
        let text: Vec<String> = cells
            .iter()
            .map(|c| format!("{}/{} on {}", c.screen, c.state, c.platform))
            .collect();
        Ok(Payload::new(EnumerateData {
            cells: rows(&cells),
        })
        .with_rendered(text))
    }

    /// Render the selected cells and fold the results into the manifest.
    pub(super) fn render(cmd: &GalleryRender, ctx: &Context) -> Outcome<RenderData> {
        let (root, spec) = load(ctx)?;
        let cells = crunk_gallery::cells::cells(&spec, &filter(&cmd.args.filter));
        let manifest_path = root.join(&cmd.args.manifest);
        let mut manifest = store::load_or_empty(&manifest_path).map_err(store_err)?;
        let all = crunk_gallery::cells::enumerate(&spec);
        store::expand_wildcards(&mut manifest, &all);
        let opts = RenderOptions::new(root.join(&cmd.args.out));
        let report = render_cells(&spec, &cells, &opts).map_err(|e| {
            tracing::info!(error = %e, "gallery render failed");
            refusal("E-GALLERY-RENDER", &e.to_string())
        })?;
        let mut rendered = 0;
        let mut text = Vec::new();
        for r in &report.results {
            match &r.outcome {
                Ok(done) => {
                    store::apply_render(&mut manifest, &r.cell, done);
                    rendered += 1;
                }
                Err(e) => text.push(format!(
                    "{}/{} on {}: {e}",
                    r.cell.screen, r.cell.state, r.cell.platform
                )),
            }
        }
        store::save(&manifest_path, &manifest).map_err(store_err)?;
        let failed = report.failed();
        let data = RenderData {
            rendered,
            failed,
            manifest: cmd.args.manifest.clone(),
        };
        if failed == 0 {
            return Ok(Payload::new(data).with_rendered(text));
        }
        let value: Value = serde_json::to_value(&data).map_err(CliError::internal)?;
        Err(CliError::Gate {
            message: format!("gallery render: {failed} cell(s) failed"),
            data: value,
            warnings: text,
        })
    }

    /// Serve the contact sheet until the reviewer finishes, saving every verdict.
    pub(super) fn triage(cmd: &GalleryTriage, ctx: &Context) -> Outcome<TriageData> {
        let (root, spec) = load(ctx)?;
        let a = &cmd.args;
        let cells = crunk_gallery::cells::cells(&spec, &filter(&a.pipeline.filter));
        let manifest_path = root.join(&a.pipeline.manifest);
        let mut manifest = store::load_or_empty(&manifest_path).map_err(store_err)?;
        store::expand_wildcards(&mut manifest, &crunk_gallery::cells::enumerate(&spec));
        let name = a
            .reviewer
            .clone()
            .unwrap_or_else(|| crunk_check::review::current_identity(&root));
        let session = Session {
            cells: cells.clone(),
            manifest,
            manifest_path,
            artifacts: root.join(&a.pipeline.out),
            reviewer: Reviewer {
                name,
                today: ctx.clock.today(),
                expires_in_days: a.expires_in,
            },
            token: new_token().map_err(CliError::internal)?,
            done: false,
        };
        let listener = bind(a.port).map_err(|e| {
            refusal("E-GALLERY-PORT", &e.to_string()).with_remedy("pass --port 0 or another port")
        })?;
        let addr = listener.local_addr().map_err(CliError::internal)?;
        let address = format!("http://{addr}/");
        tracing::info!(%address, "gallery triage: contact sheet serving; press Finish in the page to save and exit");
        let done = serve(&listener, session).map_err(CliError::internal)?;
        let mut data = TriageData {
            address,
            approved: 0,
            rejected: 0,
            pending: 0,
        };
        for c in &cells {
            let status = done
                .manifest
                .entries
                .iter()
                .find(|e| {
                    e.screen == c.screen
                        && e.platform == c.platform
                        && e.state.as_deref() == Some(c.state.as_str())
                })
                .and_then(|e| e.verdict.as_ref())
                .map_or(Status::Pending, |v| v.status);
            match status {
                Status::Approved => data.approved += 1,
                Status::Rejected => data.rejected += 1,
                Status::Pending => data.pending += 1,
            }
        }
        Ok(Payload::new(data))
    }

    /// Load the spec and manifest, run the gallery rules and map errors to a gate failure.
    pub(super) fn run(cmd: &GalleryCheck, ctx: &Context) -> Outcome<GalleryData> {
        let (root, spec) = load(ctx)?;
        let path = root.join(&cmd.manifest);
        let text = std::fs::read_to_string(&path).map_err(|e| {
            tracing::info!(path = %path.display(), error = %e, "gallery check: manifest unreadable");
            refusal(
                "E-GALLERY-MANIFEST",
                &format!("cannot read gallery manifest {}: {e}", path.display()),
            )
            .with_remedy("render the gallery first, or pass --manifest PATH")
        })?;
        let manifest = crunk_gallery::manifest::parse(&text).map_err(|e| {
            tracing::info!(error = %e, "gallery check: manifest invalid");
            refusal("E-GALLERY-MANIFEST", &e.to_string())
                .with_remedy("fix the manifest at the located path, then rerun")
        })?;
        let report =
            crunk_gallery::report::check_report(&spec, &manifest, &cmd.routes, ctx.clock.today());
        let findings: Vec<Value> = report
            .findings
            .iter()
            .map(|f| serde_json::to_value(f).map_err(CliError::internal))
            .collect::<Result<_, _>>()?;
        let rows: Vec<String> = report
            .findings
            .iter()
            .map(|f| format!("{} {:?}: {}", f.rule, f.severity, f.message))
            .collect();
        let data = GalleryData {
            cells: report.cells,
            errors: report.errors,
            warnings: report.warnings,
            findings,
        };
        if report.passed() {
            return Ok(Payload::new(data).with_rendered(rows));
        }
        let message = format!(
            "gallery: {} error(s), {} warning(s) over {} cell(s)",
            report.errors, report.warnings, report.cells
        );
        let value: Value = serde_json::to_value(&data).map_err(CliError::internal)?;
        Err(CliError::Gate {
            message,
            data: value,
            warnings: Vec::new(),
        })
    }
}

// ---- enumerate, render, triage (ticket 01M43ATE06MNRNVJJ314KW24RJ) ----

/// One `(screen, state, platform)` cell in a verb's output.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CellRow {
    /// Screen id.
    pub screen: String,
    /// State id.
    pub state: String,
    /// Platform id.
    pub platform: String,
}

/// Output of `gallery enumerate`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct EnumerateData {
    /// Every selected cell.
    pub cells: Vec<CellRow>,
}

/// Output of `gallery render`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct RenderData {
    /// Cells rendered and recorded in the manifest.
    pub rendered: usize,
    /// Cells that failed to render.
    pub failed: usize,
    /// The manifest that was written.
    pub manifest: String,
}

/// Output of `gallery triage`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TriageData {
    /// Where the contact sheet was served.
    pub address: String,
    /// Selected cells now approved.
    pub approved: usize,
    /// Selected cells now rejected.
    pub rejected: usize,
    /// Selected cells still pending.
    pub pending: usize,
}

/// Cell filters shared by the pipeline verbs.
#[derive(Debug, Clone, Default, clap::Args)]
#[command(about = None, long_about = None)]
struct FilterArgs {
    #[arg(long, value_name = "ID", help = "Only this screen")]
    screen: Option<String>,
    #[arg(long, value_name = "ID", help = "Only this state")]
    state: Option<String>,
    #[arg(long, value_name = "ID", help = "Only this platform")]
    platform: Option<String>,
}

/// `gallery render` and `gallery triage` flags.
#[derive(Debug, Clone, Default, clap::Args)]
#[command(about = None, long_about = None)]
struct PipelineArgs {
    #[command(flatten)]
    filter: FilterArgs,
    #[arg(
        long,
        value_name = "PATH",
        default_value = "gallery/manifest.json",
        help = "Gallery manifest, relative to the project root"
    )]
    manifest: String,
    #[arg(
        long,
        value_name = "DIR",
        default_value = "gallery/renders",
        help = "Artifacts directory for the rendered PNGs, relative to the project root"
    )]
    out: String,
}

/// `gallery triage` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct TriageArgs {
    #[command(flatten)]
    pipeline: PipelineArgs,
    #[arg(
        long,
        value_name = "PORT",
        default_value_t = 8765,
        help = "Loopback port to serve on (0 picks a free one)"
    )]
    port: u16,
    #[arg(
        long,
        value_name = "NAME",
        help = "Reviewer name (default: the git identity)"
    )]
    reviewer: Option<String>,
    #[arg(
        long = "expires-in",
        value_name = "DAYS",
        help = "Approvals expire after this many days (default: never)"
    )]
    expires_in: Option<i64>,
}

/// List the cells the spec enumerates.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "gallery enumerate",
    product = "crunk",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
#[cfg_attr(not(feature = "gallery"), allow(dead_code))]
pub struct GalleryEnumerate {
    filter: FilterArgs,
}

/// Render the selected cells to PNGs and record them in the manifest.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "gallery render",
    product = "crunk",
    idempotent = true,
    exits(ok, negative, refused, usage, internal)
)]
#[cfg_attr(not(feature = "gallery"), allow(dead_code))]
pub struct GalleryRender {
    args: PipelineArgs,
}

/// Serve a local contact sheet and save keyboard verdicts to the manifest.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "gallery triage",
    product = "crunk",
    idempotent = false,
    exits(ok, refused, usage, internal)
)]
#[cfg_attr(not(feature = "gallery"), allow(dead_code))]
pub struct GalleryTriage {
    args: TriageArgs,
}

impl Default for GalleryTriage {
    fn default() -> Self {
        Self {
            args: TriageArgs {
                pipeline: PipelineArgs::default(),
                port: 8765,
                reviewer: None,
                expires_in: None,
            },
        }
    }
}

impl Command for GalleryEnumerate {
    type Data = EnumerateData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<FilterArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            filter: gob_cli::parse::<FilterArgs>(m)?,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<EnumerateData> {
        imp::enumerate(self, ctx)
    }
}

impl Command for GalleryRender {
    type Data = RenderData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<PipelineArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            args: gob_cli::parse::<PipelineArgs>(m)?,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<RenderData> {
        imp::render(self, ctx)
    }
}

impl Command for GalleryTriage {
    type Data = TriageData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<TriageArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            args: gob_cli::parse::<TriageArgs>(m)?,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<TriageData> {
        imp::triage(self, ctx)
    }
}
