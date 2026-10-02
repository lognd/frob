//! Rules declared by this crate: `PROC001`, `TOOL001` and `PERF001`.

use gob_rules::Rule;

/// A crate other than `gob-exec`, `gob-git` or the binary references `std::process`.
///
/// Every spawn goes through `gob-exec` so it is allowlisted, bounded and
/// counted; reading the git state goes through `gob-git`. Move the call into
/// one of those crates or route it through `gob_exec::Runner`.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PROC001",
    slug = "process-outside-exec",
    family = "PROC",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Proc001;

/// A configured tool stage (`[[check.tool]]`) exited nonzero, timed out or could not start.
///
/// The finding names the stage and its exit status. Run the stage's command
/// by hand to see its output, fix what it reports, or set `fail_on_nonzero`
/// to false when the stage is advisory.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "TOOL001",
    slug = "tool-stage-failed",
    family = "TOOL",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Tool001;

/// The built-in stages of a check run took longer than the `[perf]` budget.
///
/// Only raised when the enforcement knob of the perf table is on. The
/// breakdown from `frob check --timing` shows which stage grew; a cold cache
/// (first run, new checkout) legitimately exceeds the warm budget, so rerun
/// before treating it as a regression.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PERF001",
    slug = "check-over-budget",
    family = "PERF",
    severity = Warn,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Perf001;
