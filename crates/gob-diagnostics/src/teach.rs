//! Teaching state: `[ui] teach` and the local `.frob/seen.toml` (diagnostics.md sections 5 and 7.1).
//!
//! The first time a rule fires in a repository its full explain text is printed inline; the
//! state is a per-rule count in a disposable local file, so later runs print the one-line form.

// frob:ticket 01M3ZX7ZNF2PJ2E8WJH3CSCDFK

use std::collections::BTreeMap;
use std::path::Path;
use std::str::FromStr;

use serde::{Deserialize, Serialize};

/// What the `[ui] teach` knob allows inline.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum TeachMode {
    /// Full text on a rule's first occurrence in the repository, the one-line form after.
    #[default]
    First,
    /// Never inline: help lines only.
    Never,
    /// Full text on every occurrence.
    Always,
}

impl FromStr for TeachMode {
    type Err = TeachError;

    /// Parse `first`, `never` or `always`; anything else is a typed error naming the value.
    fn from_str(s: &str) -> Result<Self, TeachError> {
        match s {
            "first" => Ok(Self::First),
            "never" => Ok(Self::Never),
            "always" => Ok(Self::Always),
            other => Err(TeachError::BadMode(other.to_owned())),
        }
    }
}

/// How one finding's explain text is shown.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Disclosure {
    /// Print the full explain text inline.
    Full,
    /// Print only the one-line `= explain:` pointer.
    OneLine,
    /// Print no explain line (`teach = "never"`).
    Hidden,
}

impl Disclosure {
    /// The `= explain:` line body for `rule` run through `tool` (`frob`/`grimble`), if one is shown.
    pub fn explain_line(self, tool: &str, rule: &str) -> Option<String> {
        match self {
            Self::Full => Some(format!("{tool} explain {rule}")),
            Self::OneLine => Some(format!(
                "{tool} explain {rule} (shown in full on first occurrence)"
            )),
            Self::Hidden => None,
        }
    }
}

/// Failures reading or writing teaching state, or parsing the knob.
#[derive(Debug, thiserror::Error)]
pub enum TeachError {
    /// `[ui] teach` held something other than `first`, `never` or `always`.
    #[error("[ui] teach = {0:?} is not one of \"first\", \"never\", \"always\"")]
    BadMode(String),
    /// The seen file could not be read or written.
    #[error("seen file {path}: {source}")]
    Io {
        /// File involved.
        path: String,
        /// Underlying error.
        source: std::io::Error,
    },
    /// The seen file is not valid TOML of the expected shape.
    #[error("seen file {path} is not valid: {source}")]
    Parse {
        /// File involved.
        path: String,
        /// Underlying error.
        source: toml::de::Error,
    },
    /// The seen state could not be encoded.
    #[error("seen state could not be encoded: {0}")]
    Encode(#[from] toml::ser::Error),
}

/// Per-rule occurrence counts, persisted as `.frob/seen.toml`.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct SeenStore {
    #[serde(default)]
    seen: BTreeMap<String, u32>,
}

impl SeenStore {
    /// Load the store at `path`; a missing file is an empty store.
    ///
    /// # Errors
    /// [`TeachError::Io`] on a read failure, [`TeachError::Parse`] on malformed content.
    pub fn load(path: &Path) -> Result<Self, TeachError> {
        let text = match std::fs::read_to_string(path) {
            Ok(t) => t,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                tracing::debug!(path = %gob_path::Shown::of(path), "no seen file, starting empty");
                return Ok(Self::default());
            }
            Err(source) => {
                return Err(TeachError::Io {
                    path: gob_path::Shown::of(path).to_string(),
                    source,
                });
            }
        };
        toml::from_str(&text).map_err(|source| TeachError::Parse {
            path: gob_path::Shown::of(path).to_string(),
            source,
        })
    }

    /// Write the store to `path`, creating parent directories.
    ///
    /// # Errors
    /// [`TeachError::Io`] on a write failure, [`TeachError::Encode`] if encoding fails.
    pub fn save(&self, path: &Path) -> Result<(), TeachError> {
        let io = |source| TeachError::Io {
            path: gob_path::Shown::of(path).to_string(),
            source,
        };
        if let Some(dir) = path.parent() {
            std::fs::create_dir_all(dir).map_err(io)?;
        }
        std::fs::write(path, toml::to_string(self)?).map_err(io)?;
        tracing::debug!(path = %gob_path::Shown::of(path), "seen file saved");
        Ok(())
    }

    /// How many times `rule` has been shown.
    pub fn count(&self, rule: &str) -> u32 {
        self.seen.get(rule).copied().unwrap_or(0)
    }

    /// Decide how to show `rule` under `mode` and record the occurrence (`Never` records nothing).
    pub fn disclose(&mut self, mode: TeachMode, rule: &str) -> Disclosure {
        match mode {
            TeachMode::Never => Disclosure::Hidden,
            TeachMode::Always => {
                *self.seen.entry(rule.to_owned()).or_insert(0) += 1;
                Disclosure::Full
            }
            TeachMode::First => {
                let n = self.seen.entry(rule.to_owned()).or_insert(0);
                *n += 1;
                if *n == 1 {
                    tracing::debug!(rule, "first occurrence, full explain");
                    Disclosure::Full
                } else {
                    Disclosure::OneLine
                }
            }
        }
    }

    /// Forget `rule` (or every rule when `None`), as `frob teach reset` does.
    pub fn reset(&mut self, rule: Option<&str>) {
        match rule {
            Some(r) => {
                self.seen.remove(r);
            }
            None => self.seen.clear(),
        }
        tracing::debug!(?rule, "seen state reset");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-diagnostics/src/teach.rs::SeenStore.disclose
    #[test]
    fn first_prints_full_once_and_seen_file_records_it() {
        let dir = std::env::temp_dir().join(format!("teach-first-{}", std::process::id()));
        let path = dir.join(".frob").join("seen.toml");
        let mut s = SeenStore::load(&path).unwrap();
        assert_eq!(s.disclose(TeachMode::First, "SYS003"), Disclosure::Full);
        s.save(&path).unwrap();
        let mut s = SeenStore::load(&path).unwrap();
        assert_eq!(s.count("SYS003"), 1);
        let d = s.disclose(TeachMode::First, "SYS003");
        assert_eq!(d, Disclosure::OneLine);
        assert_eq!(
            d.explain_line("grimble", "SYS003").unwrap(),
            "grimble explain SYS003 (shown in full on first occurrence)"
        );
        std::fs::remove_dir_all(dir).unwrap();
    }

    // frob:tests crates/gob-diagnostics/src/teach.rs::TeachMode.from_str
    #[test]
    fn never_hides_and_always_repeats_full() {
        let mut s = SeenStore::default();
        for _ in 0..3 {
            assert_eq!(s.disclose(TeachMode::Never, "R"), Disclosure::Hidden);
        }
        assert_eq!(s.count("R"), 0);
        for _ in 0..3 {
            assert_eq!(s.disclose(TeachMode::Always, "R"), Disclosure::Full);
        }
        assert_eq!("never".parse::<TeachMode>().unwrap(), TeachMode::Never);
        assert!("sometimes".parse::<TeachMode>().is_err());
    }

    // frob:tests crates/gob-diagnostics/src/teach.rs::SeenStore.reset
    #[test]
    fn reset_one_or_all_restores_first_occurrence() {
        let mut s = SeenStore::default();
        s.disclose(TeachMode::First, "A");
        s.disclose(TeachMode::First, "B");
        s.reset(Some("A"));
        assert_eq!(s.disclose(TeachMode::First, "A"), Disclosure::Full);
        s.reset(None);
        assert_eq!(s.disclose(TeachMode::First, "B"), Disclosure::Full);
    }
}
