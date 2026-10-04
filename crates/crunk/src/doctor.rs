//! `doctor`: the environment crunk runs in and the state of `crunk.toml`.

use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use crate::workspace::locate_root;

/// Report the crunk version, the repository root and the state of crunk.toml.
#[derive(Debug, Clone, Copy, Default, gob_cli::Command)]
#[command(
    verb = "doctor",
    product = "crunk",
    exits(ok, refused, usage, internal)
)]
pub struct Doctor;

/// State of `crunk.toml`.
#[derive(Debug, Serialize, JsonSchema)]
pub struct ConfigRow {
    /// True when `crunk.toml` exists.
    pub present: bool,
    /// `ok`, `absent`, or the first config error.
    pub status: String,
    /// The product file `[compute]` is read from (`frob` or `crunk`).
    pub compute_source: Option<String>,
    /// The `compute_digest` in force.
    pub compute_digest: Option<String>,
}

/// Output of `doctor`.
#[derive(Debug, Serialize, JsonSchema)]
pub struct DoctorData {
    /// The crunk build version (the workspace lockstep version).
    pub version: String,
    /// Repository root.
    pub root: String,
    /// `crunk.toml` state.
    pub config: ConfigRow,
}

fn config_row(root: &std::path::Path) -> ConfigRow {
    let present = crunk_check::has_config(root);
    match gob_config::ComputeTable::load_for_product(root, crunk_check::PRODUCT) {
        Ok((compute, source)) => ConfigRow {
            present,
            status: if present { "ok" } else { "absent" }.to_owned(),
            compute_source: Some(source.to_owned()),
            compute_digest: Some(gob_config::compute_digest(&compute)),
        },
        Err(e) => ConfigRow {
            present,
            status: e.to_string(),
            compute_source: None,
            compute_digest: None,
        },
    }
}

impl Command for Doctor {
    type Data = DoctorData;

    fn from_matches(_matches: &gob_cli::clap::ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<DoctorData> {
        let root = locate_root(&ctx.cwd);
        let config = config_row(&root);
        tracing::info!(status = %config.status, "doctor finished");
        Ok(Payload::new(DoctorData {
            version: env!("CARGO_PKG_VERSION").to_owned(),
            root: root.display().to_string(),
            config,
        }))
    }
}
