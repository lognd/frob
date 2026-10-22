//! Tool definitions as data (tool-binding.md section 2): a bindable tool is a TOML record in the std pack.
//!
//! A `[[check.tool]]` stage with `def = "<name>"` takes its command, argv, parser, version probe,
//! trusted range, exit classes, inputs and id map from the definition, so adding a tool needs data
//! plus a parser, never tool-specific stage code.

// frob:ticket 01M4DVRGX0KNTCDA8Q2YT46TP7

use std::collections::BTreeMap;
use std::sync::OnceLock;

use serde::Deserialize;

use crate::config::ToolParser;
use crate::tool_parse::{compare, parse_version};

/// The token in a definition's argv that stands for the pinned version.
const VERSION_TOKEN: &str = "{version}";

/// Exit-status classes of a tool; any other status is a tool error (`TOOL001`).
#[derive(Debug, Clone, Default, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ExitClasses {
    /// Statuses meaning a clean run.
    #[serde(default)]
    pub success: Vec<i32>,
    /// Statuses meaning the tool ran and reported findings.
    #[serde(default)]
    pub findings: Vec<i32>,
}

/// An argv that replaces the default one for tool versions in an inclusive range.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CommandVariant {
    /// Lowest tool version (inclusive) this variant applies to; unbounded when unset.
    #[serde(default)]
    pub min_version: Option<String>,
    /// Highest tool version (inclusive) this variant applies to; unbounded when unset.
    #[serde(default)]
    pub max_version: Option<String>,
    /// The argv, with `{version}` for the pinned version.
    pub args: Vec<String>,
}

/// A fix command of a tool and whether it may run without a person watching.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FixCommand {
    /// The fix argv, with `{version}` for the pinned version.
    pub args: Vec<String>,
    /// True when the fix is safe to run unattended inside a ticket scope.
    #[serde(default)]
    pub unattended: bool,
}

/// One bindable tool: everything frob needs to run it and read its result, as data.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ToolDef {
    /// The definition name a stage selects with `def`.
    pub name: String,
    /// The program, found on `PATH`.
    pub command: String,
    /// The known-good tool version substituted for `{version}`.
    pub pinned_version: String,
    /// Output parser id.
    pub parser: ToolParser,
    /// Arguments of `command` that print the version.
    pub version_args: Vec<String>,
    /// Lowest trusted version (inclusive).
    #[serde(default)]
    pub min_version: Option<String>,
    /// Highest trusted version (inclusive).
    #[serde(default)]
    pub max_version: Option<String>,
    /// The default argv.
    pub args: Vec<String>,
    /// Argv variants keyed by version range; the first one containing the probed version wins over `args`.
    #[serde(default, rename = "variant")]
    pub variants: Vec<CommandVariant>,
    /// Exit-status classes.
    #[serde(default)]
    pub exit: ExitClasses,
    /// Globs of the files the tool reads.
    #[serde(default)]
    pub inputs: Vec<String>,
    /// Globs of configuration files that change its results (part of the cache key).
    #[serde(default)]
    pub config_files: Vec<String>,
    /// Regex of the tool's native suppression comment (for EXC017).
    #[serde(default)]
    pub suppression_pattern: Option<String>,
    /// Tool finding id to frob rule id, merged under a stage's own `id_map`.
    #[serde(default)]
    pub id_map: BTreeMap<String, String>,
    /// The tool's own fix command, if any.
    #[serde(default)]
    pub fix: Option<FixCommand>,
}

/// Substitute the pinned version into `args`.
fn fill(args: &[String], version: &str) -> Vec<String> {
    args.iter()
        .map(|a| a.replace(VERSION_TOKEN, version))
        .collect()
}

/// True when `found` lies inside the inclusive `min`..`max` range (an unset bound is open).
fn in_range(found: &[u64], min: Option<&str>, max: Option<&str>) -> bool {
    let at_least = min
        .and_then(parse_version)
        .is_none_or(|m| compare(found, &m).is_ge());
    let at_most = max
        .and_then(parse_version)
        .is_none_or(|m| compare(found, &m).is_le());
    at_least && at_most
}

impl ToolDef {
    /// The default argv with the pinned version filled in.
    #[must_use]
    pub fn default_args(&self) -> Vec<String> {
        fill(&self.args, &self.pinned_version)
    }

    /// The version probe argv with the pinned version filled in.
    #[must_use]
    pub fn probe_args(&self) -> Vec<String> {
        fill(&self.version_args, &self.pinned_version)
    }

    /// The argv for tool `version`: the first matching variant, else the default.
    #[must_use]
    pub fn args_for(&self, version: Option<&str>) -> Vec<String> {
        let found = version.and_then(parse_version);
        let hit = found.as_deref().and_then(|v| {
            self.variants
                .iter()
                .find(|c| in_range(v, c.min_version.as_deref(), c.max_version.as_deref()))
        });
        match hit {
            Some(variant) => {
                tracing::info!(def = %self.name, version = version.unwrap_or(""), "tool command variant selected");
                fill(&variant.args, &self.pinned_version)
            }
            None => self.default_args(),
        }
    }

    // frob:ticket 01M4D94J5J2TZEXTB8GH36992B
    /// The unattended fix argv with the pinned version filled in; `None` without a fix or when the fix needs a human.
    #[must_use]
    pub fn fix_args(&self) -> Option<Vec<String>> {
        self.fix
            .as_ref()
            .filter(|f| f.unattended)
            .map(|f| fill(&f.args, &self.pinned_version))
    }

    /// All exit statuses that are not a tool error.
    #[must_use]
    pub fn normal_exits(&self) -> Vec<i32> {
        self.exit
            .success
            .iter()
            .chain(&self.exit.findings)
            .copied()
            .collect()
    }
}

/// The embedded std tool definitions as `(name, toml text)`; kept here, below `gob-packs` in the layering.
const TOOL_DEFS: [(&str, &str); 10] = [
    ("zizmor", include_str!("tools/zizmor.toml")),
    ("actionlint", include_str!("tools/actionlint.toml")),
    ("ruff", include_str!("tools/ruff.toml")),
    ("rustfmt", include_str!("tools/rustfmt.toml")),
    ("ruff-format", include_str!("tools/ruff-format.toml")),
    ("prettier", include_str!("tools/prettier.toml")),
    ("dotnet-format", include_str!("tools/dotnet-format.toml")),
    (
        "cargo-semver-checks",
        include_str!("tools/cargo-semver-checks.toml"),
    ),
    ("griffe", include_str!("tools/griffe.toml")),
    ("api-extractor", include_str!("tools/api-extractor.toml")),
];

/// The std pack's tool definitions, parsed once; a malformed embedded record is a build defect.
fn all() -> &'static [ToolDef] {
    static DEFS: OnceLock<Vec<ToolDef>> = OnceLock::new();
    DEFS.get_or_init(|| {
        TOOL_DEFS
            .iter()
            .map(|(name, text)| {
                toml::from_str::<ToolDef>(text)
                    .unwrap_or_else(|e| unreachable!("embedded tool definition `{name}`: {e}"))
            })
            .collect()
    })
}

/// The std-pack definition named `name`, if any.
#[must_use]
pub fn lookup(name: &str) -> Option<&'static ToolDef> {
    all().iter().find(|d| d.name == name)
}

/// The names of every std-pack tool definition.
#[must_use]
pub fn names() -> Vec<&'static str> {
    all().iter().map(|d| d.name.as_str()).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-check/src/tool_def.rs::lookup
    #[test]
    fn std_definitions_parse_and_name_a_pinned_tool() {
        for name in [
            "zizmor",
            "actionlint",
            "ruff",
            "rustfmt",
            "ruff-format",
            "prettier",
            "dotnet-format",
            "cargo-semver-checks",
            "griffe",
            "api-extractor",
        ] {
            let def = lookup(name).expect("embedded");
            assert!(!def.pinned_version.is_empty());
            assert!(!def.normal_exits().is_empty());
        }
        assert_eq!(names().len(), 10);
    }

    // frob:tests crates/gob-check/src/tool_def.rs::ToolDef.default_args
    #[test]
    fn pinned_version_is_substituted_into_argv() {
        let def = lookup("zizmor").unwrap();
        assert_eq!(def.default_args()[0], "zizmor@1.30.1");
        assert_eq!(def.probe_args(), ["zizmor@1.30.1", "--version"]);
        assert_eq!(
            lookup("actionlint").unwrap().default_args()[1],
            "actionlint-py==1.7.12.25"
        );
    }

    // frob:tests crates/gob-check/src/tool_def.rs::ToolDef.fix_args
    #[test]
    fn formatter_defs_carry_an_unattended_fix() {
        for name in ["rustfmt", "ruff-format", "prettier", "dotnet-format"] {
            let def = lookup(name).unwrap();
            assert_eq!(def.parser, crate::config::ToolParser::FormatterList);
            assert!(def.fix_args().is_some(), "{name} has an unattended fix");
        }
        let fix = lookup("ruff-format").unwrap().fix_args().unwrap();
        assert_eq!(fix[0], "ruff@0.14.1");
        assert!(lookup("zizmor").unwrap().fix_args().is_none());
    }

    fn renamed() -> ToolDef {
        toml::from_str(
            r#"
name = "t"
command = "t"
pinned_version = "2.0.0"
parser = "none"
version_args = ["--version"]
args = ["new-flag"]
[[variant]]
max_version = "1.9.99"
args = ["old-flag", "{version}"]
"#,
        )
        .unwrap()
    }

    // frob:tests crates/gob-check/src/tool_def.rs::ToolDef.args_for
    #[test]
    fn version_in_a_renamed_flag_range_selects_the_variant() {
        let def = renamed();
        assert_eq!(def.args_for(Some("1.4.0")), ["old-flag", "2.0.0"]);
        assert_eq!(def.args_for(Some("1.9.99")), ["old-flag", "2.0.0"]);
        assert_eq!(def.args_for(Some("2.0.1")), ["new-flag"]);
        assert_eq!(def.args_for(None), ["new-flag"]);
    }
}
