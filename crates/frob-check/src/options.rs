//! What a check run was asked to do.

use std::sync::Arc;

use frob_lease::LeaseConfig;
use frob_ledger::LedgerConfig;

use crate::config::FailOn;
use crate::filecheck::FileCheck;

/// Inputs of [`crate::run`] besides the repository root; `Default` is a plain full check.
#[derive(Clone, Default)]
pub struct CheckOptions {
    /// Ticket reference (`~handle`, ULID or alias) that scopes the run.
    pub ticket: Option<String>,
    /// Rule families or rule ids to keep; empty keeps everything.
    pub only: Vec<String>,
    /// Apply Deterministic fixes and re-run once.
    pub fix: bool,
    /// Overrides the `[check] fail_on` of `frob.toml` when deciding the exit code.
    pub fail_on: Option<FailOn>,
    /// Overrides `[check] base` for the diff of a `--ticket` run.
    pub base: Option<String>,
    /// Ledger settings (the `[tickets]` and `[git]` tables live in the binary); defaults when absent.
    pub ledger: Option<LedgerConfig>,
    /// Lease settings (`[lease]`); loaded from `frob.toml` when absent.
    pub lease: Option<LeaseConfig>,
    /// Extra per-file checks run next to the built-in ones (tests, embedders).
    pub extra_checks: Vec<Arc<dyn FileCheck>>,
    /// Skip the `[[check.tool]]` stages (frob-land runs them itself).
    pub skip_tools: bool,
    /// Do not write `.frob/telemetry.jsonl` even when `[check] telemetry` is true.
    pub skip_telemetry: bool,
}
