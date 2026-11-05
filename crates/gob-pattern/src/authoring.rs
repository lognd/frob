//! Rule authoring helpers: next free `GPOLnnn` id for a rules dir, and embedded test cases.
//!
//! A rule file may carry `[[test]]` tables: `source` is run through the rule, `matches` lists
//! the exact source text of each expected finding in order (empty means the rule must stay
//! quiet), and `fixed` is the expected output after applying every fix.

// frob:ticket 01M4PPRHCTN3TZ0TJF8NRQ4KHD

use std::path::Path;

use serde::Deserialize;

use crate::grammar::apply;
use crate::{PatternError, RuleFile};

/// The id prefix of declarative code-policy rules.
const PREFIX: &str = "GPOL";

/// One embedded test case of a rule file.
#[derive(Debug, Clone, Default, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct TestCase {
    /// Optional case name shown in failures.
    pub name: Option<String>,
    /// Source text the rule runs over.
    pub source: String,
    /// Source text of each expected finding, in order; empty means no finding.
    #[serde(default)]
    pub matches: Vec<String>,
    /// Expected source after applying every fix, when the rule has one.
    pub fixed: Option<String>,
}

/// Why one embedded test case failed.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum CaseFailure {
    /// The rule could not run over the case source.
    #[error("case `{case}`: rule failed: {error}")]
    Run {
        /// Case label.
        case: String,
        /// The underlying error text.
        error: String,
    },
    /// The findings differ from the expected matches.
    #[error("case `{case}`: expected findings {expected:?}, got {got:?}")]
    Matches {
        /// Case label.
        case: String,
        /// Expected matched texts.
        expected: Vec<String>,
        /// Actual matched texts.
        got: Vec<String>,
    },
    /// The fixed output differs from the expectation.
    #[error("case `{case}`: expected fixed output {expected:?}, got {got:?}")]
    Fixed {
        /// Case label.
        case: String,
        /// Expected output.
        expected: String,
        /// Actual output.
        got: String,
    },
}

/// The id after the highest `GPOLnnn` among `ids`, zero padded to at least three digits.
pub fn next_id_after<'a>(ids: impl IntoIterator<Item = &'a str>) -> String {
    let top = ids
        .into_iter()
        .filter_map(|id| id.strip_prefix(PREFIX))
        .filter(|d| !d.is_empty() && d.bytes().all(|b| b.is_ascii_digit()))
        .filter_map(|d| d.parse::<u64>().ok())
        .max()
        .unwrap_or(0);
    format!("{PREFIX}{:03}", top + 1)
}

/// Whether `path` is named `*.grl.toml`.
fn is_rule_file(path: &Path) -> bool {
    path.extension().is_some_and(|x| x == "toml")
        && path
            .file_stem()
            .is_some_and(|stem| Path::new(stem).extension().is_some_and(|x| x == "grl"))
}

/// The id declared by the rule file at `path`, or `None` (logged) when it cannot be read.
fn declared_id(path: &Path) -> Option<String> {
    let id = std::fs::read_to_string(path)
        .ok()
        .and_then(|t| RuleFile::parse(&t).ok())
        .map(|file| file.id);
    if id.is_none() {
        tracing::warn!(?path, "skipping unreadable rule file");
    }
    id
}

/// The next free `GPOLnnn` id for the `*.grl.toml` files in `dir`; unreadable or malformed
/// files are skipped (their ids cannot be known), and a missing dir yields `GPOL001`.
pub fn next_id(dir: &Path) -> String {
    let ids: Vec<String> = std::fs::read_dir(dir)
        .into_iter()
        .flatten()
        .flatten()
        .map(|e| e.path())
        .filter(|p| is_rule_file(p))
        .filter_map(|p| declared_id(&p))
        .collect();
    let id = next_id_after(ids.iter().map(String::as_str));
    tracing::info!(?dir, %id, "allocated rule id");
    id
}

impl RuleFile {
    /// Run every embedded `[[test]]` case; returns one failure per failing case.
    ///
    /// Failures are data, not errors; a rule without `pattern` cannot run over source and
    /// reports [`CaseFailure::Run`] per case.
    pub fn run_tests(&self) -> Vec<CaseFailure> {
        let mut failures = Vec::new();
        for (i, case) in self.tests.iter().enumerate() {
            let label = case.name.clone().unwrap_or_else(|| format!("#{}", i + 1));
            match self.run_case(&label, case) {
                Ok(()) => tracing::debug!(rule = %self.id, case = %label, "case passed"),
                Err(f) => {
                    tracing::warn!(rule = %self.id, case = %label, "case failed");
                    failures.push(f);
                }
            }
        }
        failures
    }

    /// Run one case, returning its first failure.
    fn run_case(&self, label: &str, case: &TestCase) -> Result<(), CaseFailure> {
        let run = |e: PatternError| CaseFailure::Run {
            case: label.to_owned(),
            error: e.to_string(),
        };
        if self.rule.pattern.is_none() {
            return Err(run(PatternError::EmptyRule));
        }
        let found = self.find_source(&case.source).map_err(run)?;
        let got: Vec<String> = found
            .iter()
            .map(|f| case.source[f.range.clone()].to_owned())
            .collect();
        if got != case.matches {
            return Err(CaseFailure::Matches {
                case: label.to_owned(),
                expected: case.matches.clone(),
                got,
            });
        }
        if let Some(expected) = &case.fixed {
            let edits: Vec<_> = found.into_iter().filter_map(|f| f.edit).collect();
            let out = apply(&case.source, &edits);
            if &out != expected {
                return Err(CaseFailure::Fixed {
                    case: label.to_owned(),
                    expected: expected.clone(),
                    got: out,
                });
            }
        }
        Ok(())
    }
}
