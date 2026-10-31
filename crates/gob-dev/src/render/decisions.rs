//! `docs/decisions/README.md`: the decision log, rendered from `docs/decisions/decisions.toml`.
//!
//! The TOML file is the one source: one `[[decision]]` per decision with its id, date, one-line
//! summary, status and home. The full record lives in the home section (`### D4` under a design
//! page) and this generator refuses a log whose home heading is missing, so a row can never point
//! at nothing. Supersession is a status (`amended` or `superseded`) naming the deciding ids.

// frob:ticket 01M4H0X29ZW591D2AX69V9PQ94

use std::collections::BTreeSet;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use serde::Deserialize;

use super::{cell, md_header};
use crate::files::GenFile;

/// Repository path of the generated log.
const PATH: &str = "docs/decisions/README.md";
/// Repository path of the TOML source.
const SOURCE: &str = "docs/decisions/decisions.toml";
/// The documentation directory, relative to the workspace root.
const DOCS_DIR: &str = "docs";
/// Where the generated log sits relative to `docs/`, used to relativize home links.
const LOG_DIR_FROM_DOCS: &str = "decisions";

/// Why the decision log could not be generated.
#[derive(Debug, thiserror::Error)]
pub enum DecisionsError {
    /// The source or a home page could not be read.
    #[error("read {}: {source}", gob_path::Shown::with_home(path, None))]
    Io {
        /// The path.
        path: PathBuf,
        /// Underlying error.
        source: std::io::Error,
    },
    /// The source is not valid TOML of the expected shape.
    #[error("{SOURCE}: {0}")]
    Parse(#[from] toml::de::Error),
    /// The log breaks one of its own rules (duplicate id, unknown `by`, missing home heading).
    #[error("{SOURCE}: {0}")]
    Invalid(String),
}

/// How a decision stands today.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "lowercase")]
enum Status {
    /// Decided and in force.
    Accepted,
    /// Proposed, pending review.
    Draft,
    /// Partly changed by the decisions in `by`; the rest stands.
    Amended,
    /// Replaced by the decisions in `by`.
    Superseded,
    /// Kept only as a pointer; its content became statuses on other rows.
    Folded,
}

impl Status {
    /// The word shown in the status column.
    fn word(self) -> &'static str {
        match self {
            Self::Accepted => "accepted",
            Self::Draft => "draft",
            Self::Amended => "amended",
            Self::Superseded => "superseded",
            Self::Folded => "folded",
        }
    }

    /// Whether this status must name the deciding ids in `by`.
    fn needs_by(self) -> bool {
        matches!(self, Self::Amended | Self::Superseded)
    }
}

/// One `[[decision]]` table.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Decision {
    /// The id, `D<number>`.
    id: String,
    /// The day the decision was recorded, `YYYY-MM-DD`.
    date: String,
    /// One line saying what was decided.
    #[serde(rename = "decision")]
    summary: String,
    /// How the decision stands.
    status: Status,
    /// The decisions that amend or supersede this one.
    #[serde(default)]
    by: Vec<String>,
    /// The page (relative to `docs/`, optional `#anchor`) holding the full record.
    home: String,
    /// Other pages the decision touches.
    #[serde(default)]
    see: Vec<String>,
}

/// The whole source file.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Log {
    /// Every decision, in order.
    decision: Vec<Decision>,
}

/// The lower-case anchor a `#`-heading with `text` gets (single-word headings such as `D4`).
fn heading_anchor(text: &str) -> String {
    text.trim().to_lowercase()
}

/// Whether the page at `path` has a heading whose anchor is `anchor`.
fn has_heading(path: &Path, anchor: &str) -> Result<bool, DecisionsError> {
    let text = std::fs::read_to_string(path).map_err(|source| DecisionsError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    Ok(text
        .lines()
        .filter_map(|l| l.strip_prefix('#'))
        .any(|l| heading_anchor(l.trim_start_matches('#')) == anchor))
}

/// A `YYYY-MM-DD` shape check; the calendar itself is not validated.
fn date_shaped(date: &str) -> bool {
    let b = date.as_bytes();
    b.len() == 10
        && b.iter().enumerate().all(|(i, c)| {
            if i == 4 || i == 7 {
                *c == b'-'
            } else {
                c.is_ascii_digit()
            }
        })
}

/// Check the log's own rules against the pages below `docs_dir`.
fn validate(log: &Log, docs_dir: &Path) -> Result<(), DecisionsError> {
    let invalid = |m: String| Err(DecisionsError::Invalid(m));
    let ids: BTreeSet<&str> = log.decision.iter().map(|d| d.id.as_str()).collect();
    if ids.len() != log.decision.len() {
        return invalid("duplicate decision id".to_owned());
    }
    for d in &log.decision {
        if !date_shaped(&d.date) {
            return invalid(format!("{}: date `{}` is not YYYY-MM-DD", d.id, d.date));
        }
        if d.status.needs_by() == d.by.is_empty() {
            return invalid(format!(
                "{}: status {} {} `by`",
                d.id,
                d.status.word(),
                if d.status.needs_by() {
                    "needs"
                } else {
                    "forbids"
                }
            ));
        }
        if let Some(missing) = d.by.iter().find(|b| !ids.contains(b.as_str())) {
            return invalid(format!("{}: `by` names unknown decision {missing}", d.id));
        }
        let (page, anchor) = split_home(&d.home);
        let path = docs_dir.join(page);
        if let Some(anchor) = anchor {
            if !has_heading(&path, anchor)? {
                return invalid(format!("{}: {page} has no heading for #{anchor}", d.id));
            }
        } else if !path.is_file() {
            return invalid(format!("{}: home page {page} does not exist", d.id));
        }
    }
    Ok(())
}

/// A home as page and optional anchor.
fn split_home(home: &str) -> (&str, Option<&str>) {
    match home.split_once('#') {
        Some((page, anchor)) => (page, Some(anchor)),
        None => (home, None),
    }
}

/// A markdown link to `target` (relative to `docs/`) from the generated log, labelled by file name.
fn link(target: &str) -> String {
    let (page, _) = split_home(target);
    let label = page.rsplit('/').next().unwrap_or(page);
    let up = "../".repeat(LOG_DIR_FROM_DOCS.matches('/').count() + 1);
    format!("[{label}]({up}{target})")
}

/// The status cell: the word, then the deciding ids as in-page links.
fn status_cell(d: &Decision) -> String {
    let mut out = d.status.word().to_owned();
    if !d.by.is_empty() {
        let by: Vec<String> =
            d.by.iter()
                .map(|b| format!("[{b}](#{})", b.to_lowercase()))
                .collect();
        let _ = write!(out, " by {}", by.join(", "));
    }
    out
}

/// The home cell: the record link, then the other pages.
fn home_cell(d: &Decision) -> String {
    let mut links = vec![link(&d.home)];
    links.extend(d.see.iter().map(|s| link(s)));
    links.join(", ")
}

/// The log page for `log`.
fn render(log: &Log) -> String {
    let mut out = md_header("decisions");
    out.push_str("\n# Decision log\n\n");
    out.push_str(
        "One row per decision, from `decisions.toml`. The full record is under the `### Dn` heading of the first page in the Home column; supersession is the status, never a rewritten row. Dated ADRs live next to this file.\n\n",
    );
    out.push_str("| # | Date | Decision | Status | Home |\n|---|---|---|---|---|\n");
    for d in &log.decision {
        let _ = writeln!(
            out,
            "| <a id=\"{}\"></a>{} | {} | {} | {} | {} |",
            d.id.to_lowercase(),
            d.id,
            d.date,
            cell(&d.summary),
            status_cell(d),
            home_cell(d)
        );
    }
    out
}

/// The decision log under the standard generated marker, read from `docs/decisions/decisions.toml` below `root`.
///
/// # Errors
/// [`DecisionsError`] when the source is unreadable, malformed or breaks the log's own rules.
pub fn generate(root: &Path) -> Result<Vec<GenFile>, DecisionsError> {
    tracing::debug!(path = PATH, "rendering decision log");
    let source = root.join(SOURCE);
    let text = std::fs::read_to_string(&source).map_err(|e| DecisionsError::Io {
        path: source.clone(),
        source: e,
    })?;
    let log: Log = toml::from_str(&text)?;
    validate(&log, &root.join(DOCS_DIR))?;
    tracing::info!(decisions = log.decision.len(), "rendered decision log");
    Ok(vec![GenFile {
        path: PATH.to_owned(),
        content: render(&log),
    }])
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A root with a design page holding `### D1` and the given decisions source.
    fn root_with(source: &str) -> tempfile::TempDir {
        let dir = tempfile::tempdir().expect("tempdir");
        let design = dir.path().join(DOCS_DIR).join("design");
        std::fs::create_dir_all(&design).expect("mkdir design");
        std::fs::write(design.join("a.md"), "# A\n\n### D1\n\nbody\n").expect("a");
        let decisions = dir.path().join(DOCS_DIR).join("decisions");
        std::fs::create_dir_all(&decisions).expect("mkdir decisions");
        std::fs::write(decisions.join("decisions.toml"), source).expect("toml");
        dir
    }

    const GOOD: &str = r#"
[[decision]]
id = "D1"
date = "2026-10-02"
decision = "Pipes | are escaped"
status = "amended"
by = ["D2"]
home = "design/a.md#d1"

[[decision]]
id = "D2"
date = "2026-10-03"
decision = "Newer"
status = "accepted"
home = "design/a.md#d1"
see = ["design/a.md"]
"#;

    #[test]
    // frob:tests crates/gob-dev/src/render/decisions.rs::generate
    fn renders_one_anchored_row_per_decision_with_supersession_as_status() {
        let dir = root_with(GOOD);
        let files = generate(dir.path()).expect("generate");
        assert_eq!(files.len(), 1);
        assert_eq!(files[0].path, PATH);
        let text = &files[0].content;
        assert!(text.contains("| <a id=\"d1\"></a>D1 | 2026-10-02 | Pipes \\| are escaped | amended by [D2](#d2) | [a.md](../design/a.md#d1) |"), "{text}");
        assert!(text.contains("<a id=\"d2\"></a>D2"), "{text}");
        assert_eq!(crate::files::marker_problem(text), None);
    }

    #[test]
    // frob:tests crates/gob-dev/src/render/decisions.rs::generate
    fn refuses_a_home_heading_that_does_not_exist() {
        let dir = root_with(&GOOD.replace("a.md#d1\"\n\n[[", "a.md#d9\"\n\n[["));
        let err = generate(dir.path()).expect_err("missing heading");
        assert!(err.to_string().contains("no heading for #d9"), "{err}");
    }

    #[test]
    // frob:tests crates/gob-dev/src/render/decisions.rs::generate
    fn refuses_amended_without_by_and_unknown_by() {
        let no_by = GOOD.replace("by = [\"D2\"]\n", "");
        let err = generate(root_with(&no_by).path()).expect_err("needs by");
        assert!(err.to_string().contains("needs `by`"), "{err}");
        let unknown = GOOD.replace("[\"D2\"]", "[\"D9\"]");
        let err = generate(root_with(&unknown).path()).expect_err("unknown by");
        assert!(err.to_string().contains("unknown decision D9"), "{err}");
    }

    #[test]
    // frob:tests crates/gob-dev/src/render/decisions.rs::generate
    fn refuses_duplicate_ids_and_unknown_keys() {
        let dup = GOOD.replace("id = \"D2\"", "id = \"D1\"");
        assert!(generate(root_with(&dup).path()).is_err());
        let extra = GOOD.replace("see = ", "bogus = 1\nsee = ");
        assert!(matches!(
            generate(root_with(&extra).path()),
            Err(DecisionsError::Parse(_))
        ));
    }
}
