//! What a check run was asked to do, independent of the product driving it.

use crate::config::FailOn;

/// Inputs of [`crate::run`] besides the repository root and the product; `Default` is a plain full check.
#[derive(Debug, Clone, Default)]
pub struct RunOptions {
    /// Product-defined scope reference (frob: a ticket handle) that limits the run.
    pub scope: Option<String>,
    /// Rule families or rule ids to keep; empty keeps everything.
    pub only: Vec<String>,
    /// Apply Deterministic fixes and re-run once.
    pub fix: bool,
    /// Overrides the `[check] fail_on` of the product config when deciding the exit code.
    pub fail_on: Option<FailOn>,
    /// Highest tool tier to run; `None` runs every stage (the unscoped CI check).
    pub tool_tier: Option<crate::config::ToolTier>,
    /// Skip the `[[check.tool]]` stages (a caller that runs them itself).
    pub skip_tools: bool,
    /// Do not write the telemetry line even when `[check] telemetry` is true.
    pub skip_telemetry: bool,
    /// The command's clock; when absent the run pins the system clock once at its start.
    pub clock: Option<std::sync::Arc<dyn gob_time::Clock>>,
    /// Store that lets a tool stage reuse a recorded pass for byte-identical inputs; absent runs every stage.
    pub tool_memo: Option<std::sync::Arc<dyn crate::tools::ToolMemo>>,
    /// Trust source for tool programs; when present an untrusted program is Unresolved and not run,
    /// and one resolving inside the work tree is refused (security.md 2.4). Absent leaves stages unvetted.
    pub tool_trust: Option<std::sync::Arc<dyn crate::tools::ToolTrust>>,
}
