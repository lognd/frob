//! `DOC006`: a prose citation of a markdown file (`tickets.md section 6`, `tickets.md#anchor`)
//! names a file, section or anchor that does not exist, and `docs/MOVED.toml` does not move it.

// frob:ticket 01M4H0RE1Q9A1M47ZT7Q1ZG43K
// frob:ticket 01M5NFNV4SC3DTH5PMHP4DMPY9

use std::collections::{HashMap, HashSet};
use std::path::Path;

use frob_doc::{MOVED_PATH, MovedMap, Resolved};
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

/// Follow `file`/`locator` through the shared relocation map and check where it ends up.
fn follow(map: &MovedMap, index: &mut Index<'_>, file: &str, locator: &Locator) -> Followed {
    match map.resolve(file, Some(locator), false) {
        Ok(Resolved::Unmapped) => Followed::Unmapped,
        Ok(Resolved::Retired(_)) => Followed::Resolved,
        Ok(Resolved::Moved(to)) => {
            let at = to.locator.unwrap_or_else(|| locator.clone());
            if index.check("", &to.file, &at) == Check::Ok {
                Followed::Resolved
            } else {
                Followed::Broken(display(&to.file, &at))
            }
        }
        Err(e) => {
            tracing::warn!(error = %e, "citation does not settle in MOVED.toml");
            Followed::Broken(e.to_string())
        }
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

/// The relocation map; a missing file is an empty map, a parse failure is a finding.
fn load_moved(root: &Path, files: &mut FileInterner, out: &mut Vec<Finding>) -> MovedMap {
    let Ok(text) = std::fs::read_to_string(root.join(MOVED_PATH)) else {
        tracing::debug!("no {MOVED_PATH}; no citations are remapped");
        return MovedMap::default();
    };
    MovedMap::parse(&text).unwrap_or_else(|e| {
        tracing::warn!(error = %e, "MOVED.toml does not parse");
        let span = Span::new(files.intern(MOVED_PATH), range(0, 0));
        out.push(finding_def(
            Doc006::DEF,
            Some(span),
            e.to_string(),
            MOVED_PATH,
        ));
        MovedMap::default()
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
    let moved = load_moved(root, files, &mut out);
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
            match follow(&moved, &mut index, &c.file, &c.locator) {
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
