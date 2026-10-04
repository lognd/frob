//! Rules declared by this crate: `PROC001`, `TOOL001`, `TOOL002`, `PERF001`, `READ001` and the bound `CI` ids.

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
    severity = Warn,
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
    severity = Warn,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Read001;

/// An external `uses:` reference is not pinned to a full commit SHA.
///
/// Bound to zizmor `unpinned-uses`. Pin the action to its 40-hex commit SHA and keep the version in a trailing comment; Dependabot or Renovate can then bump both together. Raised by a `[[check.tool]]` stage with `parser = "zizmor-json-v1"`.
///
/// Declared here until the grimble-ci crate owns the CI family; the id and meaning stay.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "CI001",
    slug = "pinned-ref",
    family = "CI",
    severity = Warn,
    tier = Universal,
    scope = File,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Ci001;

/// A workflow or job grants a broader `GITHUB_TOKEN` scope than it needs.
///
/// Bound to zizmor `excessive-permissions`. Declare `permissions: contents: read` at the top of the workflow and widen single jobs only. Raised by a `[[check.tool]]` stage with `parser = "zizmor-json-v1"`.
///
/// Declared here until the grimble-ci crate owns the CI family; the id and meaning stay.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "CI003",
    slug = "no-top-level-write",
    family = "CI",
    severity = Warn,
    tier = Universal,
    scope = File,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Ci003;

/// A dangerous trigger (`pull_request_target`, `workflow_run`) runs with untrusted pull request content.
///
/// Bound to zizmor `dangerous-triggers`. Do not check out or run the pull request head in a privileged workflow; split the untrusted build from the privileged step. Raised by a `[[check.tool]]` stage with `parser = "zizmor-json-v1"`.
///
/// Declared here until the grimble-ci crate owns the CI family; the id and meaning stay.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "CI006",
    slug = "no-prt-head-checkout",
    family = "CI",
    severity = Error,
    tier = Universal,
    scope = File,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Ci006;

/// A `run:` script interpolates an expression an attacker can influence.
///
/// Bound to zizmor `template-injection`. Pass the value through an `env:` variable and read it as a shell variable instead of splicing `${{ ... }}` into the script. Raised by a `[[check.tool]]` stage with `parser = "zizmor-json-v1"`.
///
/// Declared here until the grimble-ci crate owns the CI family; the id and meaning stay.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "CI007",
    slug = "no-event-interpolation-in-run",
    family = "CI",
    severity = Error,
    tier = Universal,
    scope = File,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Ci007;

/// `actions/checkout` leaves credentials in the workspace.
///
/// Bound to zizmor `artipacked`. Set `persist-credentials: false` on the checkout unless a later step must push. Raised by a `[[check.tool]]` stage with `parser = "zizmor-json-v1"`.
///
/// Declared here until the grimble-ci crate owns the CI family; the id and meaning stay.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "CI010",
    slug = "checkout-no-persist",
    family = "CI",
    severity = Advisory,
    tier = Universal,
    scope = File,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Ci010;

/// actionlint rejects the workflow syntax, schema, expression or runner label.
///
/// Bound to actionlint (every finding kind). Fix the reported line; for a custom self-hosted runner label add it to the stage's `labels` list. When the tool is outside its `min_version`..`max_version` range the stage reports one Unresolved `TOOL001` (schema lag) instead. Raised by a `[[check.tool]]` stage with `parser = "actionlint-json"`.
///
/// Declared here until the grimble-ci crate owns the CI family; the id and meaning stay.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "CI014",
    slug = "gha-syntax-and-schema",
    family = "CI",
    severity = Warn,
    tier = Universal,
    scope = File,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Ci014;

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
    severity = Advisory,
    tier = Universal,
    scope = File,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Tool002;
