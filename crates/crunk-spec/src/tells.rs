//! Tell lists: the dated, sourced term lists the SLOP rules match (research: blocklists rot, so
//! every entry carries the day it was added and where it came from).
//!
//! A list is a TOML file of `[[tell]]` tables (`term`, `added`, `source`). The std lists are
//! bundled under `data/`; a project refreshes one without a code change by dropping a file at
//! `tells/<RULE>.toml` under its root, which replaces the bundled list.

// frob:ticket 01M4CXT6663TSPQQGGS5CY4DCA

use std::path::Path;

use serde::Deserialize;

/// The bundled lists, `(rule id, TOML text)`.
const BUNDLED: &[(&str, &str)] = &[("SLOP060", include_str!("../data/SLOP060.toml"))];

/// One tell: a term with the day it was added and where it came from.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
pub struct Tell {
    /// The lowercase term matched against copy.
    pub term: String,
    /// The `YYYY-MM-DD` day the term was added.
    pub added: String,
    /// Where the term comes from (a research note, a link).
    pub source: String,
}

impl Tell {
    /// The one-line provenance: `term (added DAY, source: SOURCE)`.
    pub fn provenance(&self) -> String {
        format!(
            "{} (added {}, source: {})",
            self.term, self.added, self.source
        )
    }
}

/// Why a tell list could not be loaded.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum TellError {
    /// The text is not valid TOML of `[[tell]]` tables.
    #[error("tell list {list} is malformed: {detail}")]
    Malformed {
        /// The rule id the list belongs to.
        list: String,
        /// The parser's message.
        detail: String,
    },
    /// An entry has an empty term, a bad day or an empty source.
    #[error("tell list {list}: entry {index} is invalid: {detail}")]
    Invalid {
        /// The rule id the list belongs to.
        list: String,
        /// 1-based entry position.
        index: usize,
        /// What is wrong.
        detail: String,
    },
    /// No bundled list is named for the rule.
    #[error("no tell list for rule {0}")]
    Unknown(String),
}

#[derive(Deserialize)]
struct Raw {
    #[serde(default)]
    tell: Vec<Tell>,
}

/// True for a plausible `YYYY-MM-DD` day.
fn is_day(text: &str) -> bool {
    let parts: Vec<&str> = text.split('-').collect();
    let [y, m, d] = parts.as_slice() else {
        return false;
    };
    let num = |s: &str, len: usize, max: u32| {
        s.len() == len
            && s.bytes().all(|b| b.is_ascii_digit())
            && s.parse::<u32>().is_ok_and(|n| (1..=max).contains(&n))
    };
    y.len() == 4 && y.bytes().all(|b| b.is_ascii_digit()) && num(m, 2, 12) && num(d, 2, 31)
}

/// A rule's tell list: entries in file order.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TellList {
    /// The rule id the list belongs to.
    pub rule: String,
    /// The entries.
    pub tells: Vec<Tell>,
}

impl TellList {
    /// Parse and validate `text` as the list for `rule`.
    ///
    /// # Errors
    /// [`TellError::Malformed`] for bad TOML, [`TellError::Invalid`] for a bad entry.
    pub fn parse(rule: &str, text: &str) -> Result<Self, TellError> {
        let raw: Raw = toml_edit::de::from_str(text).map_err(|e| TellError::Malformed {
            list: rule.to_owned(),
            detail: e.message().to_owned(),
        })?;
        for (i, t) in raw.tell.iter().enumerate() {
            let detail = if t.term.trim().is_empty() {
                Some("term is empty")
            } else if !is_day(&t.added) {
                Some("added is not a YYYY-MM-DD day")
            } else if t.source.trim().is_empty() {
                Some("source is empty")
            } else {
                None
            };
            if let Some(detail) = detail {
                return Err(TellError::Invalid {
                    list: rule.to_owned(),
                    index: i + 1,
                    detail: detail.to_owned(),
                });
            }
        }
        tracing::debug!(rule, entries = raw.tell.len(), "tell list parsed");
        Ok(Self {
            rule: rule.to_owned(),
            tells: raw.tell,
        })
    }

    /// The bundled list for `rule`.
    ///
    /// # Errors
    /// [`TellError::Unknown`] when none is bundled; parse errors as in [`Self::parse`].
    pub fn bundled(rule: &str) -> Result<Self, TellError> {
        let (_, text) = BUNDLED
            .iter()
            .find(|(id, _)| *id == rule)
            .ok_or_else(|| TellError::Unknown(rule.to_owned()))?;
        Self::parse(rule, text)
    }

    /// The project's `tells/<rule>.toml` under `root` when present, else the bundled list.
    ///
    /// # Errors
    /// As [`Self::parse`] and [`Self::bundled`].
    pub fn load(rule: &str, root: &Path) -> Result<Self, TellError> {
        let path = root.join("tells").join(format!("{rule}.toml"));
        match std::fs::read_to_string(&path) {
            Ok(text) => {
                tracing::info!(rule, path = %path.display(), "project tell list overrides the bundled one");
                Self::parse(rule, &text)
            }
            Err(_) => Self::bundled(rule),
        }
    }

    /// The lowercase terms, for matching.
    pub fn terms(&self) -> Vec<String> {
        self.tells.iter().map(|t| t.term.to_lowercase()).collect()
    }

    /// Provenance lines for `explain`: a header then one line per entry.
    pub fn provenance_lines(&self) -> Vec<String> {
        let mut lines = vec![format!(
            "{}: {} tells (each dated, with source)",
            self.rule,
            self.tells.len()
        )];
        lines.extend(self.tells.iter().map(|t| format!("  {}", t.provenance())));
        lines
    }
}

/// True when `rule` has a bundled tell list.
pub fn has_list(rule: &str) -> bool {
    BUNDLED.iter().any(|(id, _)| *id == rule)
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-spec/src/tells.rs::TellList
    // frob:tests crates/crunk-spec/src/tells.rs::has_list
    #[test]
    fn bundled_slop060_parses_with_dates_and_sources() {
        let list = TellList::bundled("SLOP060").unwrap();
        assert!(list.tells.len() >= 14);
        assert!(has_list("SLOP060") && !has_list("NOPE"));
        assert!(list.terms().contains(&"seamless".to_owned()));
    }

    // frob:tests crates/crunk-spec/src/tells.rs::TellList
    #[test]
    fn provenance_prints_date_and_source() {
        let text = "[[tell]]\nterm = \"x\"\nadded = \"2026-01-02\"\nsource = \"S9\"\n";
        let lines = TellList::parse("SLOP060", text).unwrap().provenance_lines();
        assert_eq!(lines[1], "  x (added 2026-01-02, source: S9)");
    }

    // frob:tests crates/crunk-spec/src/tells.rs::TellList
    #[test]
    fn bad_day_and_empty_source_are_rejected() {
        let bad = "[[tell]]\nterm = \"x\"\nadded = \"yesterday\"\nsource = \"s\"\n";
        assert!(matches!(
            TellList::parse("R", bad),
            Err(TellError::Invalid { index: 1, .. })
        ));
        let bad = "[[tell]]\nterm = \"x\"\nadded = \"2026-01-02\"\nsource = \" \"\n";
        assert!(TellList::parse("R", bad).is_err());
        assert!(matches!(
            TellList::parse("R", "tell = 3"),
            Err(TellError::Malformed { .. })
        ));
    }

    // frob:tests crates/crunk-spec/src/tells.rs::TellList
    #[test]
    fn project_file_overrides_bundled() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::create_dir(dir.path().join("tells")).unwrap();
        std::fs::write(
            dir.path().join("tells/SLOP060.toml"),
            "[[tell]]\nterm = \"Synergy\"\nadded = \"2026-10-15\"\nsource = \"house\"\n",
        )
        .unwrap();
        let list = TellList::load("SLOP060", dir.path()).unwrap();
        assert_eq!(list.terms(), vec!["synergy".to_owned()]);
        let empty = tempfile::tempdir().unwrap();
        assert!(TellList::load("SLOP060", empty.path()).unwrap().tells.len() >= 14);
    }
}
