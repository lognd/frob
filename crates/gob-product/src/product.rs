//! The [`Product`] trait: everything the generic verbs need to know about one goblin.

use std::path::{Path, PathBuf};

use gob_check::{CheckReport, FailOn};
use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{Cli, Context, ExitCode, Outcome};
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
///
/// `check` and `doctor` receive the parsed shared flags and the verb's raw [`ArgMatches`], so a
/// product with its own flags and data types (frob) fits the same verbs as the sibling-document
/// products (crunk, grimble); those use [`crate::sibling_check`].
pub trait Product: Sized + 'static {
    /// Product name, also the config file stem (`<NAME>.toml`).
    const NAME: &'static str;
    /// Build version shown by `--version`.
    const VERSION: &'static str;
    /// One-line summary of this product's `doctor` verb.
    const DOCTOR_SUMMARY: &'static str;
    /// One-line summary of this product's `check` verb.
    const CHECK_SUMMARY: &'static str = "Run the rules over the repository and print the `gob.sibling/1` document; exit 1 when the gate fails.";
    /// True when `doctor` only reads (safe to repeat).
    const DOCTOR_IDEMPOTENT: bool = false;
    /// The exit codes `doctor` can return, for the command metadata.
    const DOCTOR_EXITS: &'static [ExitCode] = &[
        ExitCode::Ok,
        ExitCode::Refused,
        ExitCode::Usage,
        ExitCode::Internal,
    ];
    /// True when every verb but `doctor` and `schema` refuses without `<NAME>.toml`.
    const REQUIRES_CONFIG: bool;

    /// The `check` data type (its schema backs `check --schema`).
    type CheckData: Serialize + JsonSchema;
    /// The `doctor` data type (its schema backs `doctor --schema`).
    type Doctor: Serialize + JsonSchema;

    /// True when `<root>/<NAME>.toml` exists.
    fn has_config(root: &Path) -> bool {
        root.join(format!("{}.toml", Self::NAME)).is_file()
    }

    /// The workspace root a verb run from `cwd` operates on.
    fn locate_root(cwd: &Path) -> PathBuf {
        crate::workspace::locate_root(Self::NAME, cwd)
    }

    /// The `check` flags: the shared set by default, or the product's own complete set.
    #[must_use]
    fn configure_check(cmd: ClapCommand) -> ClapCommand {
        crate::check::shared_flags(cmd)
    }

    /// Add the product's own `doctor` flags.
    #[must_use]
    fn configure_doctor(cmd: ClapCommand) -> ClapCommand {
        cmd
    }

    /// Run the rules over the workspace at `root`.
    ///
    /// # Errors
    ///
    /// Any [`gob_cli::CliError`]: a failed gate, a bad config table, a failed walk or an
    /// unknown `--only` name.
    fn check(
        ctx: &Context,
        root: &Path,
        opts: &CheckOptions,
        matches: &ArgMatches,
    ) -> Outcome<Self::CheckData>;

    /// Report the environment and config state, including the product's extra rows.
    ///
    /// # Errors
    ///
    /// Any [`gob_cli::CliError`] the survey raises.
    fn doctor(ctx: &Context, root: &Path, matches: &ArgMatches) -> Outcome<Self::Doctor>;

    /// Register the product's own verbs on the root that already carries `check` and `doctor`.
    fn register(cli: Cli) -> Cli {
        cli
    }
}
