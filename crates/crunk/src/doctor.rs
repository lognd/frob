//! `doctor` rows: the environment crunk runs in and the state of `crunk.toml`.

use gob_cli::Payload;
use schemars::JsonSchema;
use serde::Serialize;

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

/// One line of the Tailwind runtime presence table.
#[derive(Debug, Serialize, JsonSchema)]
pub struct TailwindRow {
    /// What was checked (`node`, `tailwindcss`, `helper`).
    pub item: String,
    /// `ok`, `missing`, `failed` or `skipped`.
    pub state: String,
    /// The path, version or reason.
    pub detail: String,
}

/// The Tailwind runtime presence table.
#[derive(Debug, Serialize, JsonSchema)]
pub struct TailwindTable {
    /// The table rows, in `node`, `tailwindcss`, `helper` order.
    pub rows: Vec<TailwindRow>,
    /// Anything that blocks node-verified Tailwind truth.
    pub issues: Vec<String>,
    /// Expected notices, such as the static fallback.
    pub info: Vec<String>,
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
    /// The Tailwind runtime presence table.
    pub tailwind: TailwindTable,
}

fn tailwind_table(root: &std::path::Path) -> TailwindTable {
    let report = crunk_check::tailwind_doctor(root);
    TailwindTable {
        rows: report
            .rows
            .into_iter()
            .map(|r| TailwindRow {
                item: r.item,
                state: r.state,
                detail: r.detail,
            })
            .collect(),
        issues: report.issues,
        info: report.info,
    }
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

/// The crunk doctor report for the repository at `root`.
pub fn report(root: &std::path::Path) -> Payload<DoctorData> {
    let config = config_row(root);
    tracing::info!(status = %config.status, "doctor finished");
    Payload::new(DoctorData {
        version: env!("CARGO_PKG_VERSION").to_owned(),
        root: root.display().to_string(),
        config,
        tailwind: tailwind_table(root),
    })
}
