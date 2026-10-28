//! Rules declared by this crate: `PROC001`, `TOOL001`, `TOOL002`, `PERF001` and `READ001`.

use gob_rules::Rule;

/// A crate outside the repository's declared spawners uses a process-spawning API.
///
/// A repository-local policy: only repositories that list crates in
/// `[check] process_spawners` are checked, so consumers never see it. Matches
/// `Command`, `Child`, `Stdio` and exec/spawn APIs, never `ExitCode`, `exit`
/// or `id`. Move the call into a listed crate or route it through
/// `gob_exec::Runner`.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PROC001",
    slug = "process-outside-exec",
    family = "PROC",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pplus,
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
    polarity = Pplus,
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
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Perf001;

// frob:ticket 01M42M1KK02KFZG39CXKAD47SZ
/// A walked file could not be read, so no rule examined it.
///
/// Raised as a required Unresolved finding for every file the walk includes
/// but the analysis cannot read: content that is not UTF-8, a permission
/// failure or any other read error, or a file over `[check] size_cap`. Such a
/// file must never look clean. Fix the encoding or permissions, raise
/// `size_cap`, or list the file under `[check] exclude` when it is binary or
/// generated; an excluded file is never walked, read or reported.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "READ001",
    slug = "unreadable-file",
    family = "READ",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Read001;

/// A bound tool reported a finding that no frob rule id covers.
///
/// The message starts with `tool/id` (for example `zizmor/self-repository`).
/// Map the tool id to a rule through the stage's `id_map`, or accept the
/// finding with `frob:accept TOOL002`. Always Advisory.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "TOOL002",
    slug = "tool-finding-unmapped",
    family = "TOOL",
    severity = Error,
    tier = Universal,
    scope = File,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Tool002;
