//! `crates/gob-dev/profile.toml`: one scenario (or one skip reason) per leaf command.

use std::collections::BTreeMap;

use serde::Deserialize;

/// The shipped scenario file, compiled in so `cargo dev profile` works from any directory.
pub const BUILTIN: &str = include_str!("../../profile.toml");

/// Where a scenario runs.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum FixtureKind {
    /// A throwaway local clone of this checkout at HEAD, with `experimental` as a local branch.
    Repo,
    /// A fresh git repository with one empty commit and nothing else.
    Tmp,
}

impl FixtureKind {
    /// The name used in `profile.toml` and `report.json`.
    pub fn name(self) -> &'static str {
        match self {
            Self::Repo => "repo",
            Self::Tmp => "tmp",
        }
    }
}

/// How one leaf command is run, or why it is not.
#[derive(Debug, Clone, PartialEq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Scenario {
    /// Arguments after the binary name; `{ticket}` expands to a handle of the clone's ledger.
    #[serde(default)]
    pub args: Vec<String>,
    /// Where it runs.
    #[serde(default = "default_fixture")]
    pub fixture: FixtureKind,
    /// The verb leaves the clone unchanged, so one clone serves every read-only scenario; every
    /// other scenario gets a clone of its own.
    #[serde(default)]
    pub readonly: bool,
    /// Delete `.frob/` and time the first run too.
    #[serde(default)]
    pub cold: bool,
    /// Run once more with `--timing` and record the stage tree.
    #[serde(default)]
    pub timing: bool,
    /// Cap on the warm runs for a slow command (the `--runs` value is used when smaller).
    pub runs: Option<u32>,
    /// Exit codes that count as success (default: 0).
    #[serde(default = "default_exit")]
    pub exit: Vec<i32>,
    /// Warm median budget in milliseconds (before the budget factor).
    pub budget_ms: Option<u64>,
    /// Cold run budget in milliseconds, for scenarios with `cold`.
    pub cold_budget_ms: Option<u64>,
    /// Do not run this leaf, for this reason.
    pub skip: Option<String>,
}

fn default_fixture() -> FixtureKind {
    FixtureKind::Repo
}

fn default_exit() -> Vec<i32> {
    vec![0]
}

/// The parsed scenario file.
#[derive(Debug, Clone, PartialEq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ScenarioFile {
    /// Scenarios keyed by leaf command, product first (`frob ticket show`).
    pub scenario: BTreeMap<String, Scenario>,
}

/// Why `profile.toml` was rejected.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum ScenarioError {
    /// The file is not valid TOML for the schema.
    #[error("profile.toml: {0}")]
    Parse(String),
    /// A scenario neither runs nor says why it does not.
    #[error("profile.toml: scenario {command:?} {problem}")]
    Invalid {
        /// The offending leaf command.
        command: String,
        /// What is wrong with it.
        problem: &'static str,
    },
}

impl ScenarioFile {
    /// Parse and validate `text`.
    ///
    /// # Errors
    /// [`ScenarioError`] for malformed TOML, a measured scenario with no budget, or a skip with
    /// an empty reason.
    pub fn parse(text: &str) -> Result<Self, ScenarioError> {
        let file: Self = toml::from_str(text).map_err(|e| ScenarioError::Parse(e.to_string()))?;
        for (command, s) in &file.scenario {
            let invalid = |problem| ScenarioError::Invalid {
                command: command.clone(),
                problem,
            };
            match &s.skip {
                Some(reason) if reason.trim().is_empty() => {
                    return Err(invalid("has an empty skip reason"));
                }
                Some(_) => {}
                None => {
                    if s.budget_ms.is_none() {
                        return Err(invalid("has neither skip nor budget_ms"));
                    }
                    if s.cold && s.cold_budget_ms.is_none() {
                        return Err(invalid("sets cold without cold_budget_ms"));
                    }
                }
            }
        }
        tracing::debug!(scenarios = file.scenario.len(), "profile.toml parsed");
        Ok(file)
    }

    /// The shipped scenarios.
    ///
    /// # Errors
    /// [`ScenarioError`] when the compiled-in file is invalid (a repository bug a test catches).
    pub fn builtin() -> Result<Self, ScenarioError> {
        Self::parse(BUILTIN)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-dev/src/profile/scenarios.rs::ScenarioFile.parse
    #[test]
    fn measured_scenarios_need_a_budget_and_skips_a_reason() {
        let ok = ScenarioFile::parse("[scenario.\"frob doctor\"]\nbudget_ms = 500\n").unwrap();
        assert_eq!(ok.scenario["frob doctor"].exit, vec![0]);
        assert_eq!(ok.scenario["frob doctor"].fixture, FixtureKind::Repo);
        assert!(matches!(
            ScenarioFile::parse("[scenario.\"frob doctor\"]\n"),
            Err(ScenarioError::Invalid { .. })
        ));
        assert!(matches!(
            ScenarioFile::parse("[scenario.\"frob land\"]\nskip = \" \"\n"),
            Err(ScenarioError::Invalid { .. })
        ));
        assert!(matches!(
            ScenarioFile::parse("[scenario.\"x y\"]\nbudget_ms = 1\ncold = true\n"),
            Err(ScenarioError::Invalid { .. })
        ));
        assert!(ScenarioFile::parse("[scenario.\"x y\"]\nbudget_ms = 1\nbogus = 1\n").is_err());
    }

    // frob:tests crates/gob-dev/src/profile/scenarios.rs::ScenarioFile.builtin
    #[test]
    fn shipped_file_parses() {
        ScenarioFile::builtin().unwrap();
    }
}
