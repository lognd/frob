//! The `docs/MOVED.toml` relocation map: rows, parsing and following a place to its new home.
//!
//! ```toml
//! [moved]
//! "docs/design/tickets.md" = "docs/design/work.md"            # a file moved
//! "docs/design/tickets.md#lifecycle" = "docs/design/work.md#states"
//! "docs/design/tickets.md section 6" = "merged:docs/design/work.md#states"
//! "docs/design/old.md" = "removed:superseded-by docs/design/work.md"
//! "docs/design/older.md" = "archive:docs/archive/older.md"
//! ```
//!
//! A row naming only a file carries the cited section or anchor over to the new file; a row naming
//! a section or anchor wins over the file row for that place.

// frob:ticket 01M4H0WXVXJ18DX9SVX6EHT0AD

use gob_text::{Locator, scan_line};

/// The relocation map, relative to the repository root.
pub const MOVED_PATH: &str = "docs/MOVED.toml";
/// Most map rows followed for one place (guards against cycles).
pub const MAX_HOPS: usize = 4;

/// A file and an optional section or anchor, as a map key or value names it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Ref {
    /// The file as written.
    pub file: String,
    /// The section or anchor, when one is named.
    pub locator: Option<Locator>,
}

impl Ref {
    /// Split `file.md`, `file.md#a` or `file.md section N`; `None` when no markdown file is named.
    #[must_use]
    pub fn parse(text: &str) -> Option<Self> {
        let text = text.trim();
        let end = text.find(".md")? + 3;
        let mut found = Vec::new();
        scan_line(&format!("{text} "), 0, &mut found);
        let locator = found.into_iter().find(|c| c.start == 0).map(|c| c.locator);
        Some(Self {
            file: text[..end].to_owned(),
            locator,
        })
    }

    /// The place as a reader would quote it (`a.md`, `a.md#x`, `a.md section 3`).
    #[must_use]
    pub fn render(&self) -> String {
        match &self.locator {
            None => self.file.clone(),
            Some(Locator::Anchor(a)) => format!("{}#{a}", self.file),
            Some(Locator::Section(n)) => format!("{} section {n}", self.file),
        }
    }
}

/// What a row does with its key.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind {
    /// The place moved; the value is the new home.
    Moved,
    /// The place was folded into another (`merged:`); the value is the new home.
    Merged,
    /// The place is gone (`removed:`); citations of it are accepted, never rewritten.
    Removed,
    /// The place was archived (`archive:`); rewritten only when the value names a markdown file.
    Archive,
}

/// One parsed row.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Row {
    /// The key as written.
    pub key: String,
    /// The value as written.
    pub value: String,
    /// The old place.
    pub from: Ref,
    /// The new place; `None` for rows that name no markdown file.
    pub to: Option<Ref>,
    /// How the row is treated.
    pub kind: Kind,
}

impl Row {
    /// True when citations of the key are rewritten to [`Row::to`].
    #[must_use]
    pub fn moves(&self) -> bool {
        self.to.is_some() && self.kind != Kind::Removed
    }

    /// The row as written, for messages (`"key" = "value"`).
    #[must_use]
    pub fn shown(&self) -> String {
        format!("\"{}\" = \"{}\"", self.key, self.value)
    }
}

/// Why a map did not parse or follow.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum MovedError {
    /// The file is not valid TOML.
    #[error("{MOVED_PATH} does not parse: {0}")]
    Toml(String),
    /// A key names no markdown file.
    #[error("{MOVED_PATH} key `{0}` names no markdown file")]
    BadKey(String),
    /// A value of a moved or merged row names no markdown file, or is not a string.
    #[error("{MOVED_PATH} row `{key}`: value `{value}` names no markdown file")]
    BadValue {
        /// The row key.
        key: String,
        /// The offending value.
        value: String,
    },
    /// Following rows from a place never settles.
    #[error("{MOVED_PATH} row `{0}` leads in a cycle or through more than {MAX_HOPS} rows")]
    Cycle(String),
}

/// Where a place ended up.
#[derive(Debug, PartialEq, Eq)]
pub enum Resolved<'a> {
    /// No row matches.
    Unmapped,
    /// The place now lives here (locator carried over from the old place when the row has none).
    Moved(Ref),
    /// The place was removed or archived; the row says so.
    Retired(&'a Row),
}

/// The parsed `[moved]` table.
#[derive(Debug, Clone, Default)]
pub struct MovedMap {
    rows: Vec<Row>,
}

/// True when two files are the same; `exact` compares whole paths, otherwise a path suffix matches too.
fn same_file(a: &str, b: &str, exact: bool) -> bool {
    let a = a.trim_start_matches("./");
    let b = b.trim_start_matches("./");
    a == b || (!exact && (a.ends_with(&format!("/{b}")) || b.ends_with(&format!("/{a}"))))
}

impl MovedMap {
    /// Parse the text of `docs/MOVED.toml`.
    ///
    /// # Errors
    /// [`MovedError`] for invalid TOML, a key naming no markdown file, or a moved row whose value names none.
    pub fn parse(text: &str) -> Result<Self, MovedError> {
        let table: gob_config::toml::Table = text
            .parse()
            .map_err(|e: gob_config::toml::de::Error| MovedError::Toml(e.to_string()))?;
        let mut rows = Vec::new();
        let Some(moved) = table.get("moved").and_then(|v| v.as_table()) else {
            return Ok(Self { rows });
        };
        for (key, value) in moved {
            let value = value.as_str().ok_or_else(|| MovedError::BadValue {
                key: key.clone(),
                value: value.to_string(),
            })?;
            let (kind, rest) = match value.split_once(':') {
                Some(("removed", r)) => (Kind::Removed, r),
                Some(("archive", r)) => (Kind::Archive, r),
                Some(("merged", r)) => (Kind::Merged, r),
                _ => (Kind::Moved, value),
            };
            let from = Ref::parse(key).ok_or_else(|| MovedError::BadKey(key.clone()))?;
            let to = Ref::parse(rest);
            if matches!(kind, Kind::Moved | Kind::Merged) && to.is_none() {
                return Err(MovedError::BadValue {
                    key: key.clone(),
                    value: value.to_owned(),
                });
            }
            rows.push(Row {
                key: key.clone(),
                value: value.to_owned(),
                from,
                to,
                kind,
            });
        }
        tracing::debug!(rows = rows.len(), "MOVED.toml parsed");
        Ok(Self { rows })
    }

    /// Read `docs/MOVED.toml` under `root`; absent or malformed means an empty map (the remap and DOC006 report those).
    #[must_use]
    pub fn load(root: &std::path::Path) -> Self {
        let Ok(text) = std::fs::read_to_string(root.join(MOVED_PATH)) else {
            return Self::default();
        };
        Self::parse(&text).unwrap_or_else(|e| {
            tracing::warn!(error = %e, "MOVED.toml ignored");
            Self::default()
        })
    }

    /// The rows in file order.
    #[must_use]
    pub fn rows(&self) -> &[Row] {
        &self.rows
    }

    /// The row for `file` and `locator`: a row naming that locator beats the bare-file row.
    fn find(&self, file: &str, locator: Option<&Locator>, exact: bool) -> Option<&Row> {
        let of_file = |r: &&Row| same_file(&r.from.file, file, exact);
        locator
            .and_then(|l| {
                self.rows
                    .iter()
                    .filter(of_file)
                    .find(|r| r.from.locator.as_ref() == Some(l))
            })
            .or_else(|| {
                self.rows
                    .iter()
                    .filter(of_file)
                    .find(|r| r.from.locator.is_none())
            })
    }

    /// Follow `file` (and `locator`) through the rows up to [`MAX_HOPS`] hops, stopping at a fixed point.
    ///
    /// `exact` matches whole paths (links, directives); otherwise a path suffix matches too (prose
    /// citations, which cite `tickets.md` for `docs/design/tickets.md`).
    ///
    /// # Errors
    /// [`MovedError::Cycle`] when the hops revisit a place or run past the limit.
    pub fn resolve(
        &self,
        file: &str,
        locator: Option<&Locator>,
        exact: bool,
    ) -> Result<Resolved<'_>, MovedError> {
        let start = Ref {
            file: file.to_owned(),
            locator: locator.cloned(),
        };
        let mut cur = start.clone();
        let mut seen = vec![start.clone()];
        for _ in 0..=MAX_HOPS {
            let Some(row) = self.find(&cur.file, cur.locator.as_ref(), exact) else {
                break;
            };
            let Some(to) = row.to.as_ref().filter(|_| row.moves()) else {
                return Ok(Resolved::Retired(row));
            };
            let next = Ref {
                file: to.file.clone(),
                locator: to.locator.clone().or_else(|| cur.locator.clone()),
            };
            if next == cur {
                break;
            }
            if seen.contains(&next) {
                return Err(MovedError::Cycle(row.key.clone()));
            }
            seen.push(next.clone());
            cur = next;
            if seen.len() > MAX_HOPS + 1 {
                return Err(MovedError::Cycle(row.key.clone()));
            }
        }
        Ok(if cur == start {
            Resolved::Unmapped
        } else {
            Resolved::Moved(cur)
        })
    }

    /// A short "moved to ..." / "removed ..." clause for a diagnostic about the missing place, if the map knows it.
    #[must_use]
    pub fn hint(&self, file: &str, locator: Option<&Locator>) -> Option<String> {
        match self.resolve(file, locator, false).ok()? {
            Resolved::Unmapped => None,
            Resolved::Moved(to) => Some(format!("it moved to `{}` ({MOVED_PATH})", to.render())),
            Resolved::Retired(row) => Some(match row.kind {
                Kind::Archive => format!("it was archived: `{}` ({MOVED_PATH})", row.value),
                _ => format!("it was removed: `{}` ({MOVED_PATH})", row.value),
            }),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const MAP: &str = r#"
[moved]
"docs/a.md" = "docs/b.md"
"docs/a.md#x" = "docs/c.md#y"
"docs/b.md" = "merged:docs/d.md"
"docs/gone.md" = "removed:superseded-by docs/d.md"
"docs/old.md" = "archive:docs/archive/old.md"
"docs/shelf.md" = "archive:the shelf"
"docs/loop1.md" = "docs/loop2.md"
"docs/loop2.md" = "docs/loop1.md"
"#;

    // frob:tests crates/frob-doc/src/moved.rs::MovedMap.resolve
    #[test]
    fn follows_chains_and_prefers_specific_rows() {
        let m = MovedMap::parse(MAP).unwrap();
        let r = m.resolve("docs/a.md", None, true).unwrap();
        assert_eq!(
            r,
            Resolved::Moved(Ref {
                file: "docs/d.md".into(),
                locator: None
            })
        );
        let r = m
            .resolve("docs/a.md", Some(&Locator::Anchor("x".into())), true)
            .unwrap();
        assert_eq!(r, Resolved::Moved(Ref::parse("docs/c.md#y").unwrap()));
        let carried = m
            .resolve("docs/a.md", Some(&Locator::Section("3".into())), true)
            .unwrap();
        assert_eq!(
            carried,
            Resolved::Moved(Ref::parse("docs/d.md section 3").unwrap())
        );
    }

    // frob:tests crates/frob-doc/src/moved.rs::MovedMap.resolve
    #[test]
    fn retired_unmapped_and_cycles() {
        let m = MovedMap::parse(MAP).unwrap();
        assert!(matches!(
            m.resolve("docs/gone.md", None, true),
            Ok(Resolved::Retired(_))
        ));
        assert!(matches!(
            m.resolve("docs/shelf.md", None, true),
            Ok(Resolved::Retired(_))
        ));
        assert!(matches!(
            m.resolve("docs/old.md", None, true),
            Ok(Resolved::Moved(_))
        ));
        assert_eq!(m.resolve("docs/x.md", None, true), Ok(Resolved::Unmapped));
        assert!(m.resolve("docs/loop1.md", None, true).is_err());
        assert_eq!(m.resolve("a.md", None, true), Ok(Resolved::Unmapped));
        assert!(matches!(
            m.resolve("a.md", None, false),
            Ok(Resolved::Moved(_))
        ));
    }

    // frob:tests crates/frob-doc/src/moved.rs::MovedMap.parse
    #[test]
    fn parse_rejects_bad_rows() {
        assert!(MovedMap::parse("[moved]\n\"nofile\" = \"a.md\"").is_err());
        assert!(MovedMap::parse("[moved]\n\"a.md\" = \"nothing\"").is_err());
        assert!(MovedMap::parse("[moved\n").is_err());
        assert!(MovedMap::parse("").unwrap().rows().is_empty());
    }

    // frob:tests crates/frob-doc/src/moved.rs::MovedMap.hint
    #[test]
    fn hint_names_the_new_place() {
        let m = MovedMap::parse(MAP).unwrap();
        let h = m.hint("docs/a.md", None).unwrap();
        assert!(h.contains("docs/d.md"), "{h}");
        assert!(m.hint("docs/gone.md", None).unwrap().contains("removed"));
        assert!(m.hint("docs/zzz.md", None).is_none());
    }
}
