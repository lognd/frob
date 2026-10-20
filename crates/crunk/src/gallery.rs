//! `gallery check`: the gallery approval gate (opt-in behind the `gallery` cargo feature).
//!
//! Built with `--features gallery` it enumerates the cells of `crunk.toml`, reads the manifest
//! (`--manifest`, default `gallery/manifest.json`) and runs GALLERY001 to GALLERY005; error
//! findings exit 1. The default build keeps the verb so it can say how to get it: it refuses with
//! `E-GALLERY-NOT-BUILT` and the remedy. The default binary and the Python wheel stay small.

// frob:ticket 01M43ATDG0RG5DP9PVFAKETJJH

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
    use super::{Context, GalleryCheck, GalleryData, Outcome, refusal};
    use gob_diagnostics::RemedyCommand;

    /// Refuse: this binary was built without the gallery.
    pub(super) fn run(_cmd: &GalleryCheck, _ctx: &Context) -> Outcome<GalleryData> {
        tracing::info!("gallery check: feature not built in");
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
}

#[cfg(feature = "gallery")]
mod imp {
    use super::{CliError, Context, GalleryCheck, GalleryData, Outcome, Value, refusal};
    use gob_cli::Payload;

    /// Load the spec and manifest, run the gallery rules and map errors to a gate failure.
    pub(super) fn run(cmd: &GalleryCheck, ctx: &Context) -> Outcome<GalleryData> {
        let root = gob_product::workspace::locate_root(crate::PRODUCT, &ctx.cwd);
        let spec = crunk_spec::load_spec(&root).map_err(|e| {
            tracing::info!(error = %e, "gallery check: spec did not load");
            refusal(
                "E-SPEC",
                &format!("crunk.toml is not a valid design spec: {e}"),
            )
            .with_remedy("fix crunk.toml as described, then rerun")
        })?;
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
