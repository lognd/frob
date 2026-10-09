//! The `[check]` and `[perf]` config tables and the `[[check.tool]]` stage entries.

use std::collections::BTreeMap;
use std::path::Path;

use gob_config::{ConfigError, ConfigTable};
use gob_diagnostics::UnresolvedPolicy;
use gob_rules::Severity;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// Severity at which `frob check` fails (cli.md section 2, exit 1).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum FailOn {
    /// Never fail on findings.
    None,
    /// Fail on advisory findings and above.
    Advisory,
    /// Fail on warnings and above.
    Warn,
    /// Fail on errors only.
    Error,
}

impl FailOn {
    /// The lowest failing severity, or `None` when findings never fail the run.
    pub fn threshold(self) -> Option<Severity> {
        match self {
            Self::None => Option::None,
            Self::Advisory => Some(Severity::Advisory),
            Self::Warn => Some(Severity::Warn),
            Self::Error => Some(Severity::Error),
        }
    }

    /// Parse the `--fail-on` spelling (`error`, `warn`, `advisory`, `none`).
    pub fn parse(text: &str) -> Option<Self> {
        match text {
            "none" => Some(Self::None),
            "advisory" => Some(Self::Advisory),
            "warn" => Some(Self::Warn),
            "error" => Some(Self::Error),
            _ => Option::None,
        }
    }
}

/// How a tool stage's stdout becomes findings (`parser` of `[[check.tool]]`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize, JsonSchema)]
pub enum ToolParser {
    /// No parsing: only the exit status matters (`TOOL001`).
    #[default]
    #[serde(rename = "none")]
    None,
    /// zizmor `--format json-v1`: an array of audit findings with byte spans.
    #[serde(rename = "zizmor-json-v1")]
    ZizmorJsonV1,
    /// actionlint `-format '{{json .}}'`: an array of findings with line and column.
    #[serde(rename = "actionlint-json")]
    ActionlintJson,
}

/// One external tool stage: a command run after the built-in rules (`[[check.tool]]`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ToolStage {
    /// Stage name shown in findings and timing; also the allowlisted program name.
    pub name: String,
    /// The program, found on `PATH` (no path separators).
    pub command: String,
    /// Arguments passed without shell interpretation.
    #[serde(default)]
    pub args: Vec<String>,
    /// Wall-clock limit in seconds before the tool is killed.
    #[serde(default = "default_tool_timeout")]
    pub timeout_secs: u64,
    /// When true a nonzero exit (or a timeout) is an Error finding (`TOOL001`).
    #[serde(default = "default_true")]
    pub fail_on_nonzero: bool,
    /// Output format of the tool; anything but `none` turns its findings into frob findings.
    #[serde(default)]
    pub parser: ToolParser,
    /// Runner labels the repository defines (actionlint `runner-label` findings for these are dropped).
    #[serde(default)]
    pub labels: Vec<String>,
    /// Tool finding id to frob rule id overrides, merged over the parser's default map.
    #[serde(default)]
    pub id_map: BTreeMap<String, String>,
    /// Lowest tool version (inclusive, dotted numbers) whose output is trusted.
    #[serde(default)]
    pub min_version: Option<String>,
    /// Highest tool version (inclusive, dotted numbers) whose output is trusted.
    #[serde(default)]
    pub max_version: Option<String>,
    /// Arguments of `command` that print the tool version; defaults to the parser's flag.
    #[serde(default)]
    pub version_args: Option<Vec<String>>,
    /// When true a missing binary is a non-required Unresolved finding instead of a required one.
    #[serde(default)]
    pub optional: bool,
    /// Repo-relative globs of the files this stage reads; a `--ticket` run whose scope matches none of them skips the stage (CI still runs it). Empty means the stage always runs.
    #[serde(default)]
    pub inputs: Vec<String>,
}

fn default_tool_timeout() -> u64 {
    300
}

fn default_true() -> bool {
    true
}

/// Settings of `frob check`.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "check", materialize)]
pub struct CheckTable {
    /// Lowest severity that makes `frob check` exit 1; `none` never fails.
    #[config(default = FailOn::Error, enforcement)]
    pub fail_on: FailOn,
    /// Which Unresolved findings fail the gate: `required`, `never` or `all`.
    #[config(default = UnresolvedPolicy::Required, enforcement)]
    pub fail_on_unresolved: UnresolvedPolicy,
    /// Glob patterns of paths no rule inspects.
    #[config(default = Vec::new())]
    pub exclude: Vec<String>,
    /// Files larger than this many bytes are skipped.
    #[config(default = 4_194_304)]
    pub size_cap: u64,
    /// Hops of dependents (callers, via the symbol graph) added to a `--ticket` run.
    #[config(default = 1)]
    pub ticket_hops: u32,
    /// Append one JSON line per run to `.frob/telemetry.jsonl`.
    #[config(default = true)]
    pub telemetry: bool,
    /// Refuse `--fix` unless `--ticket` scopes the run.
    #[config(default = false)]
    pub fix_requires_scope: bool,
    /// Ref the diff of a `--ticket` run (SCOPE001, TICK002) is taken against.
    #[config(default = "main".to_owned(), enforcement)]
    pub base: String,
    /// External tool stages run after the built-in rules, outside the time budget.
    #[config(default = Vec::new())]
    pub tool: Vec<ToolStage>,
    /// Wall-clock bound in seconds of one sibling `check --json` run (sibling-contract.md section 7).
    #[config(default = 120, enforcement)]
    pub sibling_timeout_secs: u64,
    /// When true an unusable configured sibling is a required Unresolved (`SIB001`).
    #[config(default = true, enforcement)]
    pub require_siblings: bool,
    /// Crates (directories under `crates/`) allowed to spawn processes; empty turns `PROC001` off.
    #[config(default = Vec::new())]
    pub process_spawners: Vec<String>,
    /// Bytes a sibling or tool may print on one stream before it is killed (default 64 MiB).
    #[config(default = 67_108_864)]
    pub output_cap_bytes: u64,
}

/// The time budget of the built-in rules.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "perf")]
pub struct PerfTable {
    /// Turn an exceeded budget into a Warn finding (`PERF001`).
    #[config(default = false)]
    pub enforce: bool,
    /// Milliseconds the built-in stages of a warm run may take.
    #[config(default = 2000)]
    pub budget_ms: u64,
}

impl CheckTable {
    /// Load `[check]` from `<root>/<product>.toml` (a missing file means defaults).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load(root: &Path, product: &str) -> Result<Self, ConfigError> {
        Ok(gob_config::load::<Self>(root, product)?.value)
    }
}

impl PerfTable {
    /// Load `[perf]` from `<root>/<product>.toml` (a missing file means defaults).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load(root: &Path, product: &str) -> Result<Self, ConfigError> {
        Ok(gob_config::load::<Self>(root, product)?.value)
    }
}
