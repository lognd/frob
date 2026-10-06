//! The [`Product`] trait: everything the generic verbs need to know about one goblin.

use std::path::Path;

use gob_check::{CheckError, CheckReport, FailOn};
use gob_cli::{Cli, Outcome};
use schemars::JsonSchema;
use serde::Serialize;
use serde_json::Value;

/// What a `check` run was asked to do (the same flags for every product).
#[derive(Debug, Clone, Default)]
pub struct CheckOptions {
    /// Rule families or rule ids to keep; empty keeps everything.
    pub only: Vec<String>,
    /// Overrides `[check] fail_on` when deciding the exit code.
    pub fail_on: Option<FailOn>,
    /// `--base`: echoed in the document.
    pub base: Option<String>,
    /// `--ticket-scope`: echoed in the document.
    pub ticket_scope: Option<Vec<String>>,
}

/// What a product's check produced: the report for gating and the `gob.sibling/1` document.
pub struct ProductRun {
    /// The pipeline report (counts, gate and exit code come from it).
    pub report: CheckReport,
    /// The sibling document, the `data` of the check envelope.
    pub document: Value,
    /// Non-fatal notes for the envelope.
    pub warnings: Vec<String>,
}

/// One goblin: its name, config root, check, extra doctor rows and extra verbs.
pub trait Product: Sized + 'static {
    /// Product name, also the config file stem (`<NAME>.toml`).
    const NAME: &'static str;
    /// Build version shown by `--version`.
    const VERSION: &'static str;
    /// One-line summary of this product's `doctor` verb.
    const DOCTOR_SUMMARY: &'static str;
    /// True when every verb but `doctor` and `schema` refuses without `<NAME>.toml`.
    const REQUIRES_CONFIG: bool;

    /// The `doctor` data type (its schema backs `doctor --schema`).
    type Doctor: Serialize + JsonSchema;

    /// True when `<root>/<NAME>.toml` exists.
    fn has_config(root: &Path) -> bool {
        root.join(format!("{}.toml", Self::NAME)).is_file()
    }

    /// Run the rules over the workspace at `root`.
    ///
    /// # Errors
    ///
    /// [`CheckError`] for a bad config table, a failed walk or an unknown `--only` name.
    fn check(root: &Path, opts: &CheckOptions) -> Result<ProductRun, CheckError>;

    /// Report the environment and config state, including the product's extra rows.
    ///
    /// # Errors
    ///
    /// Any [`gob_cli::CliError`] the survey raises.
    fn doctor(root: &Path) -> Outcome<Self::Doctor>;

    /// Register the product's own verbs on the root that already carries `check` and `doctor`.
    fn register(cli: Cli) -> Cli {
        cli
    }
}
