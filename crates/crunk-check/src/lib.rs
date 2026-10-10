//! `crunk check`: crunk's driver over the shared [`gob_check`] pipeline and the `gob.sibling/1`
//! document it prints (design: `sibling-contract.md`, `products.md` 1).
//!
//! The run walks the repository, ingests the styles under `crunk.toml` (`crunk-ingest`: CSS and
//! JSX sheets), applies the neutral pipeline groups and the `#[rule]` declarations of the crates
//! listed in [`product_rules`] (`crunk-rules`: WAIVE001, COLOR001-002, CONTRAST001).
//! `crunk:waive` comments with a reason suppress their rule at the declaration they cover, and
//! `[lint]` severities apply to every finding of a catalog rule. New rules are two files in a rule
//! crate; no legacy rule group is left in this crate.
//!
//! # Boundaries
//!
//! No frob crate is a dependency, direct or transitive (a test enforces it with the manifests),
//! so the crunk binary never links frob (boundaries.md).

// frob:ticket 01M43ARVS24254G85TMFYH8FGQ

// A rule crate that is a dependency but not in `product_rules!` is an unused dependency (D107).
#![cfg_attr(not(test), deny(unused_crate_dependencies))]

use gob_diagnostics as _; // unused today; removal tracked in ~MKG678C

mod product;
pub mod product_rules;
pub mod sibling;
mod tailwind;

use std::path::{Path, PathBuf};
use std::time::Instant;

pub use gob_check::{CheckError, CheckReport, FailOn};
pub use product::{Crunk, CrunkInputs, CrunkShared};
pub use sibling::{SCHEMA_VERSION, sibling_document};

use gob_config::ComputeTable;

/// Product name, the stem of `crunk.toml` and of the `.crunk/` state directory.
pub const PRODUCT: &str = "crunk";

/// What a `crunk check` run was asked to do.
#[derive(Debug, Clone, Default)]
pub struct CheckOptions {
    /// Rule families or rule ids to keep; empty keeps everything.
    pub only: Vec<String>,
    /// Overrides `[check] fail_on` of `crunk.toml` when deciding the exit code.
    pub fail_on: Option<FailOn>,
    /// `--base`: echoed in the document; no rule diffs against it yet.
    pub base: Option<String>,
    /// `--ticket-scope`: echoed in the document; no per-file rule exists yet to narrow.
    pub ticket_scope: Option<Vec<String>>,
}

/// Everything one run produced, enough to build the document and the verbs' views.
pub struct CrunkRun {
    /// Repository root.
    pub root: PathBuf,
    /// The pipeline report.
    pub report: CheckReport,
    /// The `[compute]` knobs in force.
    pub compute: ComputeTable,
    /// Echo of `--ticket-scope`.
    pub ticket_scope: Option<Vec<String>>,
    /// Echo of `--base`.
    pub base: Option<String>,
    /// Wall time of the run in milliseconds.
    pub elapsed_ms: u64,
    /// Non-fatal notes from the pipeline.
    pub warnings: Vec<String>,
}

/// True when `<root>/crunk.toml` exists (the one file that marks a crunk project).
pub fn has_config(root: &Path) -> bool {
    root.join(format!("{PRODUCT}.toml")).is_file()
}

/// Run `crunk check` for the repository at `root`.
///
/// # Errors
///
/// [`CheckError`] for a bad `crunk.toml` or `frob.toml` table, a failed walk or an unknown
/// `--only` name. Findings are never errors.
pub fn run(root: &Path, opts: &CheckOptions) -> Result<CrunkRun, CheckError> {
    let started = Instant::now();
    let (compute, source) = ComputeTable::load_for_product(root, PRODUCT)?;
    tracing::debug!(source, "crunk compute knobs resolved");
    let run_opts = gob_check::RunOptions {
        only: opts.only.clone(),
        fail_on: opts.fail_on,
        ..gob_check::RunOptions::default()
    };
    let report = gob_check::run(&Crunk, root, &run_opts)?;
    let elapsed_ms = u64::try_from(started.elapsed().as_millis()).unwrap_or(u64::MAX);
    tracing::info!(
        findings = report.findings.len(),
        suppressed = report.suppressed.len(),
        elapsed_ms,
        "crunk check finished"
    );
    Ok(CrunkRun {
        root: root.to_path_buf(),
        warnings: report.warnings.clone(),
        report,
        compute,
        ticket_scope: opts.ticket_scope.clone(),
        base: opts.base.clone(),
        elapsed_ms,
    })
}
