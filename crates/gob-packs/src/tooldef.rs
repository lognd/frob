//! Tool definitions as data (tool-binding.md section 2): the std pack's bindable tools.
//!
//! A definition names the program, a pinned version and probe, command variants keyed by
//! version range, exit-code classes, a parser id, config files that affect results, the
//! native suppression pattern, the id map and an optional fix command. The host (gob-check)
//! runs any definition; only the named parser is tool-specific code.

use std::collections::BTreeMap;

use serde::Deserialize;

/// Exit-code classes of a tool; any other status is a tool error (`TOOL001`).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ExitClasses {
    /// Statuses meaning a clean run.
    #[serde(default)]
    pub success: Vec<i32>,
    /// Statuses meaning the tool ran and reported findings.
    #[serde(default)]
    pub findings: Vec<i32>,
}

impl Default for ExitClasses {
    fn default() -> Self {
        Self {
            success: vec![0],
            findings: Vec::new(),
        }
    }
}

impl ExitClasses {
    /// Every status that is not a tool error (success then findings).
    pub fn declared(&self) -> Vec<i32> {
        self.success
            .iter()
            .chain(self.findings.iter())
            .copied()
            .collect()
    }
}

/// One command line, used when the tool version is in `min_version..=max_version`.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Variant {
    /// Lowest version (inclusive) this command applies to; open below when absent.
    #[serde(default)]
    pub min_version: Option<String>,
    /// Highest version (inclusive) this command applies to; open above when absent.
    #[serde(default)]
    pub max_version: Option<String>,
    /// Arguments passed to the tool's command.
    pub args: Vec<String>,
}

/// The tool's own fix command and whether it may run without a person watching.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FixCommand {
    /// Arguments passed to the tool's command.
    pub args: Vec<String>,
    /// True when the fix is safe to run unattended (tier A).
    #[serde(default)]
    pub unattended: bool,
}

/// A bindable tool (one `std/tools/<name>.toml`).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ToolDef {
    /// Definition name; a `[[check.tool]]` stage selects it with `tool = "<name>"`.
    pub name: String,
    /// The program, found on the project's own path first, then `PATH`.
    pub command: String,
    /// Pinned known-good version.
    pub version: String,
    /// Lowest version whose output is trusted.
    #[serde(default)]
    pub min_version: Option<String>,
    /// Highest version whose output is trusted.
    #[serde(default)]
    pub max_version: Option<String>,
    /// Arguments of `command` that print its version (the version probe).
    pub version_args: Vec<String>,
    /// Parser id of the output format (`zizmor-json-v1`, `actionlint-json`, `ruff-json`).
    pub parser: String,
    /// Exit-code classes.
    #[serde(default)]
    pub exit: ExitClasses,
    /// Command variants keyed by version range; the first whose range holds the version wins.
    #[serde(default)]
    pub variants: Vec<Variant>,
    /// Files (repo-relative) whose content changes results: part of the cache key.
    #[serde(default)]
    pub config_files: Vec<String>,
    /// Regex of the tool's native suppression comment (for EXC017).
    #[serde(default)]
    pub suppression: Option<String>,
    /// Tool finding id to frob rule id.
    #[serde(default)]
    pub id_map: BTreeMap<String, String>,
    /// The tool's own fix command, if any.
    #[serde(default)]
    pub fix: Option<FixCommand>,
}

impl ToolDef {
    /// Parse one definition from TOML text.
    ///
    /// # Errors
    ///
    /// The TOML error for bad syntax, an unknown key or a missing field.
    pub fn parse(text: &str) -> Result<Self, toml::de::Error> {
        toml::from_str(text)
    }
}

/// The definitions shipped in the std pack, parsed once per call.
pub fn std_tools() -> Vec<ToolDef> {
    const SOURCES: [(&str, &str); 3] = [
        ("zizmor", include_str!("../std/tools/zizmor.toml")),
        ("actionlint", include_str!("../std/tools/actionlint.toml")),
        ("ruff", include_str!("../std/tools/ruff.toml")),
    ];
    SOURCES
        .iter()
        .map(|(name, text)| {
            ToolDef::parse(text)
                .unwrap_or_else(|e| unreachable!("std tool definition {name} is valid: {e}"))
        })
        .collect()
}

/// The std definition named `name`, if any.
pub fn std_tool(name: &str) -> Option<ToolDef> {
    tracing::debug!(name, "looking up std tool definition");
    std_tools().into_iter().find(|d| d.name == name)
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-packs/src/tooldef.rs::std_tools
    #[test]
    fn std_definitions_parse_and_are_named_uniquely() {
        let defs = std_tools();
        let names: Vec<_> = defs.iter().map(|d| d.name.as_str()).collect();
        assert_eq!(names, ["zizmor", "actionlint", "ruff"]);
        assert!(defs.iter().all(|d| !d.variants.is_empty()));
    }

    // frob:tests crates/gob-packs/src/tooldef.rs::ToolDef.parse
    #[test]
    fn unknown_keys_are_refused() {
        assert!(ToolDef::parse("name = 'x'\nbogus = 1").is_err());
    }

    // frob:tests crates/gob-packs/src/tooldef.rs::std_tool
    #[test]
    fn ruff_carries_a_fix_and_a_renamed_flag_variant() {
        let ruff = std_tool("ruff").expect("ruff");
        assert!(ruff.fix.is_some_and(|f| f.unattended));
        assert_eq!(ruff.variants.len(), 2);
        assert_eq!(ruff.exit.declared(), [0, 1]);
        assert!(std_tool("nope").is_none());
    }
}
