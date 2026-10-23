//! `DOC006`: a prose citation of a markdown file (`tickets.md section 6`, `tickets.md#anchor`)
//! names a file, section or anchor that does not exist, and `docs/MOVED.toml` does not move it.

// frob:ticket 01M4H0RE1Q9A1M47ZT7Q1ZG43K

use std::collections::{HashMap, HashSet};
use std::path::Path;

use gob_languages::Language;
use gob_rules::{Finding, RuleDecl as _};
use gob_symbols::{DocStatus, is_generated, parse_header};
use gob_text::{Citation, FileInterner, Headings, Locator, Span, scan_line, scan_markdown};

use crate::comments::comment_lines;
use crate::rules::doc006::Doc006;
use crate::todo::range;
use crate::unity::tracked_paths;
use crate::util::finding_def;

/// Directories whose markdown is scanned for citations.
const PROSE_DIRS: [&str; 2] = ["docs", "notes"];
/// The directory whose Rust comments are scanned.
const CODE_DIR: &str = "crates";
/// The relocation map, relative to the repo root.
const MOVED_PATH: &str = "docs/MOVED.toml";
/// Most map rows followed for one citation (guards against cycles).
const MAX_HOPS: usize = 4;

/// One side of a `MOVED.toml` row: a file and an optional locator.
#[derive(Debug, Clone, PartialEq, Eq)]
struct Ref {
    /// The file as written.
    file: String,
    /// The section or anchor, when the row names one.
    locator: Option<Locator>,
}

/// What a `MOVED.toml` row does with its key.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Kind {
    /// The target is a new home and must exist.
    Moved,
    /// The key was removed or archived on purpose; citations of it are accepted.
    Retired,
}

/// One parsed `MOVED.toml` row.
#[derive(Debug, Clone)]
struct Row {
    /// The old place.
    from: Ref,
    /// The new place (unused for retired rows).
    to: Ref,
    /// How to treat the row.
    kind: Kind,
}

/// How a citation chain through the relocation map ended.
#[derive(Debug, PartialEq, Eq)]
enum Followed {
    /// No row matches the citation.
    Unmapped,
    /// The chain ends at a real target or a retired row.
    Resolved,
    /// The chain ends at a target that does not exist; the text names it.
    Broken(String),
}

/// Split `file.md`, `file.md#a` or `file.md section N` into a [`Ref`].
fn parse_ref(text: &str) -> Option<Ref> {
    let text = text.trim();
    let end = text.find(".md")? + 3;
    let mut found = Vec::new();
    scan_line(&format!("{text} "), 0, &mut found);
    let locator = found.into_iter().find(|c| c.start == 0).map(|c| c.locator);
    Some(Ref {
        file: text[..end].to_owned(),
        locator,
    })
}

/// Parse the `[moved]` table of `MOVED.toml`; the error text is the parse failure.
fn parse_moved(text: &str) -> Result<Vec<Row>, String> {
    let table: gob_config::toml::Table = text
        .parse()
        .map_err(|e: gob_config::toml::de::Error| e.to_string())?;
    let mut rows = Vec::new();
    let Some(moved) = table.get("moved").and_then(|v| v.as_table()) else {
        return Ok(rows);
    };
    for (key, value) in moved {
        let Some(value) = value.as_str() else {
            tracing::warn!(%key, "MOVED.toml row is not a string; skipped");
            continue;
        };
        let (kind, rest) = match value.split_once(':') {
            Some(("removed" | "archive", _)) => (Kind::Retired, value),
            Some(("merged", rest)) => (Kind::Moved, rest),
            _ => (Kind::Moved, value),
        };
        let Some(from) = parse_ref(key) else {
            tracing::warn!(%key, "MOVED.toml key names no markdown file; skipped");
            continue;
        };
        let to = parse_ref(rest).unwrap_or_else(|| from.clone());
        if kind == Kind::Moved && parse_ref(rest).is_none() {
            tracing::warn!(%key, %value, "MOVED.toml value names no markdown file; skipped");
            continue;
        }
        rows.push(Row { from, to, kind });
    }
    Ok(rows)
}

/// True when two file names are the same path or one is a path suffix of the other.
fn same_file(a: &str, b: &str) -> bool {
    let a = a.trim_start_matches("./");
    let b = b.trim_start_matches("./");
    a == b || a.ends_with(&format!("/{b}")) || b.ends_with(&format!("/{a}"))
}

/// `base/rel` with `.` and `..` folded away, as a forward-slash path.
fn normalize(base: &str, rel: &str) -> Option<String> {
    let mut parts: Vec<&str> = Vec::new();
    for seg in base.split('/').chain(rel.split('/')) {
        match seg {
            "" | "." => {}
            ".." => {
                parts.pop()?;
            }
            s => parts.push(s),
        }
    }
    Some(parts.join("/"))
}

/// The tracked markdown files and their parsed headings, loaded on demand.
struct Index<'a> {
    /// Repo root.
    root: &'a Path,
    /// Every tracked markdown path.
    markdown: HashSet<String>,
    /// Headings per path; `None` when the file cannot be read.
    headings: HashMap<String, Option<Headings>>,
}

impl Index<'_> {
    /// The headings of tracked file `path`, parsed once.
    fn headings(&mut self, path: &str) -> Option<&Headings> {
        let root = self.root;
        self.headings
            .entry(path.to_owned())
            .or_insert_with(|| {
                std::fs::read_to_string(root.join(path))
                    .map(|t| Headings::parse(&t))
                    .map_err(|e| tracing::debug!(%path, error = %e, "cited file not readable"))
                    .ok()
            })
            .as_ref()
    }

    /// Tracked files a citation of `token` from a file in `dir` could mean.
    fn candidates(&self, dir: &str, token: &str) -> Vec<String> {
        let bare = token.trim_start_matches("./");
        let mut out: Vec<String> = [
            normalize(dir, token),
            normalize("", token),
            normalize("docs", token),
        ]
        .into_iter()
        .flatten()
        .filter(|p| self.markdown.contains(p))
        .collect();
        if !bare.starts_with("../") {
            let tail = format!("/{bare}");
            out.extend(self.markdown.iter().filter(|p| p.ends_with(&tail)).cloned());
        }
        out.sort();
        out.dedup();
        out
    }

    /// Whether `token` cited from `dir` has a target that offers `locator`.
    fn check(&mut self, dir: &str, token: &str, locator: &Locator) -> Check {
        let candidates = self.candidates(dir, token);
        if candidates.is_empty() {
            return Check::NoFile;
        }
        for path in &candidates {
            if self.headings(path).is_some_and(|h| h.offers(locator)) {
                return Check::Ok;
            }
        }
        Check::NoLocator
    }
}

/// Whether a citation's target exists.
#[derive(Debug, PartialEq, Eq)]
enum Check {
    /// File and locator resolve.
    Ok,
    /// The file exists but not the section or anchor.
    NoLocator,
    /// No such file.
    NoFile,
}

/// The place a citation or row target is reported as: `x.md section 6`.
fn display(file: &str, locator: &Locator) -> String {
    Citation {
        file: file.to_owned(),
        locator: locator.clone(),
        start: 0,
        len: 0,
    }
    .quoted()
}

/// Follow `file`/`locator` through the relocation map.
fn follow(rows: &[Row], index: &mut Index<'_>, file: &str, locator: &Locator) -> Followed {
    let mut at = (file.to_owned(), locator.clone());
    let mut mapped = false;
    for _ in 0..MAX_HOPS {
        let row = rows
            .iter()
            .find(|r| same_file(&r.from.file, &at.0) && r.from.locator.as_ref() == Some(&at.1))
            .or_else(|| {
                rows.iter()
                    .find(|r| same_file(&r.from.file, &at.0) && r.from.locator.is_none())
            });
        let Some(row) = row else {
            break;
        };
        mapped = true;
        if row.kind == Kind::Retired {
            return Followed::Resolved;
        }
        let next_locator = row.to.locator.clone().unwrap_or_else(|| at.1.clone());
        at = (row.to.file.clone(), next_locator);
        if index.check("", &at.0, &at.1) == Check::Ok {
            return Followed::Resolved;
        }
    }
    if mapped {
        Followed::Broken(display(&at.0, &at.1))
    } else {
        Followed::Unmapped
    }
}

/// The finding for one citation in `path`.
fn report(files: &mut FileInterner, path: &str, c: &Citation, why: &str) -> Finding {
    let span = Span::new(files.intern(path), range(c.start, c.len));
    let message = format!("citation `{}`: {why}", c.quoted());
    tracing::info!(%path, citation = %c.quoted(), "DOC006 finding");
    finding_def(Doc006::DEF, Some(span), message, &c.quoted())
}

/// True for a document whose citations are not checked: generated, historical or superseded.
fn exempt(text: &str) -> bool {
    is_generated(text)
        || matches!(
            parse_header(text).status,
            Ok(DocStatus::Historical | DocStatus::SupersededBy(_))
        )
}

/// The citations of `path` and its text, or none when the file is out of scope.
fn citations_of(path: &str, text: &str) -> Vec<Citation> {
    let p = Path::new(path);
    if path == MOVED_PATH || !text.contains(".md") {
        return Vec::new();
    }
    if p.extension().is_some_and(|e| e == "md") {
        if !PROSE_DIRS.iter().any(|d| p.starts_with(d)) || exempt(text) {
            return Vec::new();
        }
        return scan_markdown(text);
    }
    let in_code = p.starts_with(CODE_DIR) && p.extension().is_some_and(|e| e == "rs");
    if !in_code {
        return Vec::new();
    }
    let mut out = Vec::new();
    for line in comment_lines(Language::Rust, text) {
        scan_line(line.text, line.offset, &mut out);
    }
    out
}

/// The relocation rows of `MOVED.toml`; a missing file is no rows, a parse failure is a finding.
fn load_moved(root: &Path, files: &mut FileInterner, out: &mut Vec<Finding>) -> Vec<Row> {
    let Ok(text) = std::fs::read_to_string(root.join(MOVED_PATH)) else {
        tracing::debug!("no {MOVED_PATH}; no citations are remapped");
        return Vec::new();
    };
    parse_moved(&text).unwrap_or_else(|why| {
        tracing::warn!(%why, "MOVED.toml does not parse");
        let span = Span::new(files.intern(MOVED_PATH), range(0, 0));
        out.push(finding_def(
            Doc006::DEF,
            Some(span),
            format!("{MOVED_PATH} does not parse: {why}"),
            MOVED_PATH,
        ));
        Vec::new()
    })
}

/// True for a path with a `.md` extension.
fn is_markdown(path: &str) -> bool {
    Path::new(path).extension().is_some_and(|e| e == "md")
}

/// DOC006 over every tracked prose document and Rust comment.
pub(crate) fn doc006(root: &Path, files: &mut FileInterner) -> Vec<Finding> {
    let tracked = tracked_paths(root);
    let mut index = Index {
        root,
        markdown: tracked.iter().filter(|p| is_markdown(p)).cloned().collect(),
        headings: HashMap::new(),
    };
    let mut out = Vec::new();
    let rows = load_moved(root, files, &mut out);
    for path in &tracked {
        let Ok(text) = std::fs::read_to_string(root.join(path)) else {
            continue;
        };
        let cites = citations_of(path, &text);
        if cites.is_empty() {
            continue;
        }
        let dir = path.rsplit_once('/').map_or("", |(d, _)| d);
        for c in &cites {
            let why = match index.check(dir, &c.file, &c.locator) {
                Check::Ok => continue,
                Check::NoFile => format!("no file `{}` exists", c.file),
                Check::NoLocator => match &c.locator {
                    Locator::Section(n) => format!("`{}` has no section {n}", c.file),
                    Locator::Anchor(a) => format!("`{}` has no heading or anchor `{a}`", c.file),
                },
            };
            match follow(&rows, &mut index, &c.file, &c.locator) {
                Followed::Resolved => {
                    tracing::debug!(%path, citation = %c.quoted(), "citation followed through MOVED.toml");
                }
                Followed::Broken(target) => {
                    let why = format!("{MOVED_PATH} moves it to `{target}`, which does not exist");
                    out.push(report(files, path, c, &why));
                }
                Followed::Unmapped => out.push(report(files, path, c, &why)),
            }
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests parse_moved
    #[test]
    fn rows_parse_with_prefixes_and_locators() {
        let rows = parse_moved(
            "[moved]\n\"a.md\" = \"b.md#x\"\n\"a.md section 2\" = \"merged:c.md section 4\"\n\"d.md\" = \"removed:e.md\"\n",
        )
        .unwrap();
        assert_eq!(rows.len(), 3);
        assert_eq!(rows[0].to.locator, Some(Locator::Anchor("x".into())));
        assert_eq!(rows[1].from.locator, Some(Locator::Section("2".into())));
        assert_eq!(rows[1].to.file, "c.md");
        assert_eq!(rows[2].kind, Kind::Retired);
        assert!(parse_moved("[moved\n").is_err());
        assert!(parse_moved("").unwrap().is_empty());
    }
}
