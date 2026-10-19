//! The `[check]`, `[perf]` and `[types]` config tables and the `[[check.tool]]` stage entries.

use std::collections::BTreeMap;
use std::path::Path;

use gob_config::{ConfigError, ConfigTable};
use gob_diagnostics::UnresolvedPolicy;
use gob_rules::Severity;
use gob_symbols::TypesTrust;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// How far Python type annotations are trusted when resolving calls (`docs/design/cohesion.md` 2.2).
// frob:ticket 01M4CXSWZ95SVDADAB97TYG963
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "types")]
pub struct TypesTable {
    /// `checked` (annotations are exact only in files the bound checker ran clean on), `annotated` (claimed, May) or `none` (hints only).
    #[config(default = "checked".to_owned())]
    pub trust: String,
}

impl TypesTable {
    /// Load `[types]` from `<root>/<product>.toml` (a missing file means defaults) and validate `trust`.
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or an unknown `trust` spelling.
    pub fn load(root: &Path, product: &str) -> Result<Self, ConfigError> {
        Self::from_document(&gob_config::ConfigDocument::read(root, product)?)
    }

    /// Load `[types]` from an already-parsed config document and validate `trust`.
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unknown key or an unknown `trust` spelling.
    pub fn from_document(doc: &gob_config::ConfigDocument) -> Result<Self, ConfigError> {
        let table = doc.table::<Self>()?.value;
        table.trust()?;
        Ok(table)
    }

    /// The parsed trust policy.
    ///
    /// # Errors
    ///
    /// [`ConfigError::Invalid`] when `trust` is not `checked`, `annotated` or `none`.
    pub fn trust(&self) -> Result<TypesTrust, ConfigError> {
        TypesTrust::parse(&self.trust).ok_or_else(|| ConfigError::Invalid {
            table: "types".to_owned(),
            message: format!(
                "trust = {:?}: expected checked, annotated or none",
                self.trust
            ),
        })
    }
}

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
    /// SARIF 2.1.0 on stdout (oxlint, Biome, golangci-lint, Roslyn, the eslint SARIF formatter); ids come from the stage `id_map`.
    #[serde(rename = "sarif")]
    Sarif,
    /// `cargo ... --message-format=json`: rustc and clippy diagnostics with byte spans; lint names map to `DEAD001`, `NEAT002`, `LOGIC001` or `LINT001`.
    #[serde(rename = "cargo-json")]
    CargoJson,
    /// stylelint `--formatter json`: an array of files with line and column warnings.
    // frob:ticket 01M4D95VS2KPK91REEZ8KA74BB
    #[serde(rename = "stylelint-json")]
    StylelintJson,
    /// `ruff check --output-format=json`: an array of findings with row and column; rule codes map to `DEAD001`, `ERR001`, `ERR003`, `CONC001`, `TESTQ001`, `LOGIC001` or `LINT001`.
    // frob:ticket 01M4D90ZDHTSR1JX06Z17FNR3C
    #[serde(rename = "ruff-json")]
    RuffJson,
    /// `ty check --output-format gitlab`: a code-quality array with line and column; findings are `LINT001` and mark a file as not type-clean.
    // frob:ticket 01M4CXSWZ95SVDADAB97TYG963
    #[serde(rename = "ty-gitlab")]
    TyGitlab,
    /// `pyright --outputjson`: `generalDiagnostics` with 0-based ranges; error and warning findings are `LINT001` and mark a file as not type-clean.
    // frob:ticket 01M4CXSWZ95SVDADAB97TYG963
    #[serde(rename = "pyright-json")]
    PyrightJson,
    /// `typos --format json`: one JSON object per line, each typo with its line, byte offset and corrections; findings are `SPELL001` (Advisory) and the repository's `typos.toml` allowlist is honoured by typos itself.
    // frob:ticket 01M4D92HMPWHFY5WGGY3KGFTNE
    #[serde(rename = "typos-json")]
    TyposJson,
    /// `eslint -f json`: an array of files with line and column messages; `jsx-a11y/*` map to `A11Y001`, `react-hooks/*` and `react/*` to `REACT001`, the typescript-eslint promise rules to `CONC001`, `no-explicit-any` and `no-unsafe-*` to `TYPING001`, the rest `LINT001`.
    // frob:ticket 01M4D91DTERJHX4TGJVV4KM7K8
    #[serde(rename = "eslint-json")]
    EslintJson,
}

/// The earliest check level that runs a tool stage (`tier` of `[[check.tool]]`).
///
/// Levels widen: `frob check --ticket --quick` runs `ticket` stages, a plain `--ticket` run (the
/// land and train check) adds `train`, and the unscoped CI run adds `ci`.
#[derive(
    Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Default, Serialize, Deserialize, JsonSchema,
)]
#[serde(rename_all = "kebab-case")]
pub enum ToolTier {
    /// Cheap enough for every run, including `--ticket --quick` (the default).
    #[default]
    Ticket,
    /// Runs in the land and train check and on CI, not under `--quick`.
    Train,
    /// Runs only in the unscoped CI check.
    Ci,
}

impl ToolTier {
    /// True when a run at `level` executes a stage of this tier; `None` is an unrestricted run.
    #[must_use]
    pub fn runs_at(self, level: Option<ToolTier>) -> bool {
        level.is_none_or(|l| self <= l)
    }
}

/// One external tool stage: a command run after the built-in rules (`[[check.tool]]`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ToolStage {
    /// Stage name shown in findings and timing; also the allowlisted program name.
    pub name: String,
    /// Name of a std-pack tool definition (`zizmor`, `actionlint`, `ruff`) that supplies every key this stage leaves unset.
    // frob:ticket 01M4DVRGX0KNTCDA8Q2YT46TP7
    #[serde(default)]
    pub def: Option<String>,
    /// The program, found on `PATH`: one fixed name, no path separators, whitespace or shell syntax; unset only with `def`.
    #[serde(default)]
    pub command: String,
    /// The argv template: fixed flags and typed placeholders (`{packages}`, `{file}`), passed without shell interpretation; required, `[]` when the program takes none.
    // frob:ticket 01M3ZX7VJE22Y68R184Y9WQC2N
    #[serde(default = "missing_template")]
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
    /// The earliest check level that runs this stage: `ticket` (default), `train` or `ci`.
    #[serde(default)]
    pub tier: ToolTier,
    /// What the `{packages}` argument token expands to outside a `--ticket` run (default `--workspace`); in a `--ticket` run it becomes `-p <name>` for each affected cargo package.
    #[serde(default = "default_unscoped_packages")]
    pub unscoped_packages: Vec<String>,
}

/// Sentinel `args` of a stage that declared no template; [`ToolStage::validate`] refuses it by name.
pub(crate) const MISSING_TEMPLATE: &str = "\u{0}missing-argv-template";

fn missing_template() -> Vec<String> {
    vec![MISSING_TEMPLATE.to_owned()]
}

/// The argument token a stage uses to ask for one tracked file, rendered as `./path`.
pub(crate) const FILE_TOKEN: &str = "{file}";

impl ToolStage {
    /// Refuse a stage that is not an argv template: a shell string or odd program name, or no declared `args`.
    ///
    /// # Errors
    ///
    /// [`ConfigError::Invalid`] for `[check.tool]` naming the stage and the defect.
    // frob:ticket 01M3ZX7VJE22Y68R184Y9WQC2N
    pub fn validate(&self) -> Result<(), ConfigError> {
        let bad = |why: &str| {
            tracing::warn!(stage = %self.name, why, "CFG tool stage refused");
            Err(ConfigError::Invalid {
                table: "check.tool".to_owned(),
                message: format!("stage `{}`: {why}", self.name),
            })
        };
        if let Some(d) = &self.def {
            if crate::tool_def::lookup(d).is_none() {
                return bad(&format!(
                    "`def` names no std-pack tool definition (known: {})",
                    crate::tool_def::names().join(", ")
                ));
            }
            return self.validate_with_def();
        }
        let c = &self.command;
        if c.is_empty() {
            return bad("`command` is empty");
        }
        if c.chars().any(|ch| {
            ch.is_whitespace() || "/\\;|&$<>(){}*?`\"'!~=".contains(ch) || ch.is_control()
        }) {
            return bad(
                "`command` must be one program name, not a shell string or path; put flags in `args`",
            );
        }
        if self.args.iter().any(|a| a == MISSING_TEMPLATE) {
            return bad("no `args` argv template declared (use `args = []` for none)");
        }
        Ok(())
    }
}

impl ToolStage {
    /// Validate the keys a stage with `def` sets itself (an explicit `command` must still be a bare program name).
    fn validate_with_def(&self) -> Result<(), ConfigError> {
        if self.command.is_empty() {
            return Ok(());
        }
        let own = Self {
            def: None,
            ..self.clone()
        };
        own.validate()
    }

    /// This stage with its `def` expanded: unset keys come from the definition, `id_map` and `inputs` are merged.
    ///
    /// A stage without `def` (or naming an unknown one, which [`ToolStage::validate`] refuses) is returned unchanged.
    #[must_use]
    // frob:ticket 01M4DVRGX0KNTCDA8Q2YT46TP7
    pub fn resolved(&self) -> Self {
        let Some(def) = self.def.as_deref().and_then(crate::tool_def::lookup) else {
            return self.clone();
        };
        let mut out = self.clone();
        if out.command.is_empty() {
            out.command.clone_from(&def.command);
        }
        if out.args.iter().any(|a| a == MISSING_TEMPLATE) {
            out.args = def.default_args();
        }
        if out.parser == ToolParser::None {
            out.parser = def.parser;
        }
        if out.version_args.is_none() {
            out.version_args = Some(def.probe_args());
        }
        if out.min_version.is_none() {
            out.min_version.clone_from(&def.min_version);
        }
        if out.max_version.is_none() {
            out.max_version.clone_from(&def.max_version);
        }
        for (tool_id, rule) in &def.id_map {
            out.id_map
                .entry(tool_id.clone())
                .or_insert_with(|| rule.clone());
        }
        // Config files are inputs too: editing one re-runs the stage and changes its cache key.
        for glob in def.inputs.iter().chain(&def.config_files) {
            if !out.inputs.contains(glob) {
                out.inputs.push(glob.clone());
            }
        }
        tracing::debug!(stage = %out.name, def = %def.name, "tool stage resolved from its definition");
        out
    }
}

fn default_unscoped_packages() -> Vec<String> {
    vec!["--workspace".to_owned()]
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
        Self::from_document(&gob_config::ConfigDocument::read(root, product)?)
    }

    /// Load `[check]` from an already-parsed config document and validate its tool stages.
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unknown key, mistyped value or invalid tool stage.
    pub fn from_document(doc: &gob_config::ConfigDocument) -> Result<Self, ConfigError> {
        let table = doc.table::<Self>()?.value;
        table.tool.iter().try_for_each(ToolStage::validate)?;
        Ok(table)
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

#[cfg(test)]
mod tier_tests {
    use super::ToolTier;

    // frob:tests crates/gob-check/src/config.rs::ToolTier.runs_at
    #[test]
    fn tiers_widen_with_the_run_level() {
        assert!(ToolTier::Ticket.runs_at(Some(ToolTier::Ticket)));
        assert!(!ToolTier::Train.runs_at(Some(ToolTier::Ticket)));
        assert!(ToolTier::Train.runs_at(Some(ToolTier::Train)));
        assert!(!ToolTier::Ci.runs_at(Some(ToolTier::Train)));
        assert!(ToolTier::Ci.runs_at(None));
    }
}
