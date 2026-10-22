//! The shared engine behind `rename` and `extract-token`: a lexical scanner that finds token
//! references in stylesheets, scripts and TOML spec files, plus an all-or-nothing file commit.
//!
//! References are found structurally rather than by blind substring search: comments are skipped,
//! CSS strings are skipped, and inside script or TOML strings only a real reference counts (a
//! `var(--x` call, or a string that is exactly the token name). Names are identifier-bounded, so
//! `--color` never matches inside `--color-bg`.

// frob:ticket 01M4CXRB2DX0B0BW7YJPAN1YXT

use std::io;
use std::path::{Path, PathBuf};

use crunk_spec::DesignSpec;
use crunk_tokens::export::Rendered;
use serde::Serialize;

use crate::dtcg::relative;

/// Directories never searched for references.
const NOISE_DIRS: &[&str] = &[
    "node_modules",
    "target",
    "dist",
    "build",
    "vendor",
    "__pycache__",
];

/// Stylesheet extensions scanned under `css_root`.
const CSS_EXTS: &[&str] = &["css", "scss", "sass", "less", "pcss"];

/// How a file's text is lexed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Lang {
    /// A stylesheet: `/* */` comments; strings are skipped; references live in code.
    Css,
    /// A script or markup source: `//` and `/* */` comments; references live in strings.
    Script,
    /// A TOML spec file: `#` comments; references live in strings.
    Toml,
}

/// Where the scanner stands when it offers a position to a matcher.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Site {
    /// Outside any string or comment.
    Code,
    /// Inside a string whose content spans `start..end` (bytes, quotes excluded).
    Str {
        /// First byte of the content.
        start: usize,
        /// One past the last byte of the content.
        end: usize,
    },
}

/// What a matcher returns for a hit: the byte length it consumes and its replacement.
pub type Hit = (usize, String);

/// True for bytes that continue a CSS identifier.
fn is_ident(b: u8) -> bool {
    b.is_ascii_alphanumeric() || b == b'_' || b == b'-'
}

/// Scan `text` as `lang`, offering every non-comment position to `at`; return the rewritten text
/// and the number of replacements. CSS strings are never offered.
pub fn scan(
    text: &str,
    lang: Lang,
    mut at: impl FnMut(&str, usize, Site) -> Option<Hit>,
) -> (String, usize) {
    let bytes = text.as_bytes();
    let n = bytes.len();
    let mut out = String::with_capacity(n);
    let mut copied = 0;
    let mut count = 0;
    let mut i = 0;
    while i < n {
        let b = bytes[i];
        if let Some(end) = comment_end(bytes, i, lang) {
            i = end;
            continue;
        }
        if let Some(quote) = string_quote(b, lang) {
            let end = string_end(bytes, i + 1, quote, lang);
            if lang == Lang::Css {
                i = (end + 1).min(n);
                continue;
            }
            let site = Site::Str { start: i + 1, end };
            let mut k = i + 1;
            while k < end {
                if let Some((len, rep)) = at(text, k, site) {
                    out.push_str(&text[copied..k]);
                    out.push_str(&rep);
                    k += len.max(1);
                    copied = k;
                    count += 1;
                } else {
                    k += 1;
                }
            }
            i = (end + 1).min(n);
            continue;
        }
        if let Some((len, rep)) = at(text, i, Site::Code) {
            out.push_str(&text[copied..i]);
            out.push_str(&rep);
            i += len.max(1);
            copied = i;
            count += 1;
        } else {
            i += 1;
        }
    }
    out.push_str(&text[copied..]);
    (out, count)
}

/// The byte just past a comment that starts at `i`, when one does.
fn comment_end(bytes: &[u8], i: usize, lang: Lang) -> Option<usize> {
    let rest = &bytes[i..];
    let block = |from: usize| {
        let body = &bytes[from..];
        body.windows(2)
            .position(|w| w == b"*/")
            .map_or(bytes.len(), |p| from + p + 2)
    };
    let line = |from: usize| {
        bytes[from..]
            .iter()
            .position(|&c| c == b'\n')
            .map_or(bytes.len(), |p| from + p)
    };
    match lang {
        Lang::Css | Lang::Script if rest.starts_with(b"/*") => Some(block(i + 2)),
        Lang::Script if rest.starts_with(b"//") => Some(line(i + 2)),
        Lang::Toml if rest.starts_with(b"#") => Some(line(i + 1)),
        _ => None,
    }
}

/// The quote byte when `b` opens a string in `lang`.
fn string_quote(b: u8, lang: Lang) -> Option<u8> {
    match b {
        b'"' | b'\'' => Some(b),
        b'`' if lang == Lang::Script => Some(b),
        _ => None,
    }
}

/// Index of the closing quote (or the end of the line / text when unterminated).
fn string_end(bytes: &[u8], from: usize, quote: u8, lang: Lang) -> usize {
    let literal = lang == Lang::Toml && quote == b'\'';
    let mut j = from;
    while j < bytes.len() {
        let c = bytes[j];
        if c == quote {
            return j;
        }
        if c == b'\n' && quote != b'`' {
            return j;
        }
        if c == b'\\' && !literal {
            j += 1;
        }
        j += 1;
    }
    bytes.len()
}

/// Rewrites `--old` to `--new` wherever it is a real reference.
#[derive(Debug, Clone)]
pub struct RenameMatcher {
    pairs: Vec<(String, String)>,
    code_ok: bool,
}

impl RenameMatcher {
    /// A matcher for `pairs` of (old, new) names in files of `lang`.
    #[must_use]
    pub fn new(pairs: Vec<(String, String)>, lang: Lang) -> Self {
        Self {
            pairs,
            code_ok: lang == Lang::Css,
        }
    }

    /// Offer position `k` of `text`; a hit consumes the old name.
    #[must_use]
    pub fn at(&self, text: &str, k: usize, site: Site) -> Option<Hit> {
        let bytes = text.as_bytes();
        if k > 0 && is_ident(bytes[k - 1]) {
            return None;
        }
        for (old, new) in &self.pairs {
            let end = k + old.len();
            if !bytes[k..].starts_with(old.as_bytes())
                || bytes.get(end).is_some_and(|&b| is_ident(b))
            {
                continue;
            }
            let real = match site {
                Site::Code => self.code_ok,
                Site::Str { start: s, end: e } => {
                    (s == k && end == e) || text[s..k].trim_end().ends_with("var(")
                }
            };
            if real {
                return Some((old.len(), new.clone()));
            }
        }
        None
    }
}

/// Rewrites one hex colour literal (any case, `#rgb` or `#rrggbb`) to a replacement.
#[derive(Debug, Clone)]
pub struct HexMatcher {
    wanted: String,
    replacement: String,
}

/// Normalise `#rgb` / `#rrggbb` to lowercase six digits, or None when it is not a hex colour.
#[must_use]
pub fn normalize_hex(literal: &str) -> Option<String> {
    let digits = literal.strip_prefix('#')?;
    if !digits.bytes().all(|b| b.is_ascii_hexdigit()) {
        return None;
    }
    match digits.len() {
        3 => Some(format!(
            "#{}",
            digits
                .chars()
                .flat_map(|c| [c, c])
                .collect::<String>()
                .to_ascii_lowercase()
        )),
        6 => Some(format!("#{}", digits.to_ascii_lowercase())),
        _ => None,
    }
}

impl HexMatcher {
    /// A matcher for the colour `literal`, replaced by `replacement`; None for a non-colour.
    #[must_use]
    pub fn new(literal: &str, replacement: String) -> Option<Self> {
        Some(Self {
            wanted: normalize_hex(literal)?,
            replacement,
        })
    }

    /// Offer position `k` of `text`.
    #[must_use]
    pub fn at(&self, text: &str, k: usize) -> Option<Hit> {
        let bytes = text.as_bytes();
        if bytes[k] != b'#' || (k > 0 && (is_ident(bytes[k - 1]) || bytes[k - 1] == b'&')) {
            return None;
        }
        if text[..k].ends_with("url(") {
            return None;
        }
        let run = bytes[k + 1..]
            .iter()
            .take_while(|b| b.is_ascii_hexdigit())
            .count();
        let end = k + 1 + run;
        if bytes.get(end).is_some_and(|&b| is_ident(b)) {
            return None;
        }
        (normalize_hex(&text[k..end])? == self.wanted).then(|| (end - k, self.replacement.clone()))
    }
}

/// The table name of a TOML header line (`[palette.modes.dark]` gives `palette.modes.dark`), None
/// for any other line; array-of-tables headers give None too.
#[must_use]
pub fn header_of(line: &str) -> Option<&str> {
    let t = line.trim();
    let inner = t.strip_prefix('[')?;
    if inner.starts_with('[') {
        return None;
    }
    Some(inner.split(']').next()?.trim())
}

/// One file the verb will write.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Change {
    /// Absolute path.
    pub path: PathBuf,
    /// The current text, None when the file does not exist yet.
    pub before: Option<String>,
    /// The text to write.
    pub after: String,
    /// What the change is: `definition`, `reference` or `generated`.
    pub kind: &'static str,
    /// Replacements made in the file.
    pub replacements: usize,
}

/// One changed file in a verb's report.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, schemars::JsonSchema)]
pub struct FileChange {
    /// Path relative to the project root.
    pub path: String,
    /// `definition`, `reference` or `generated`.
    pub kind: String,
    /// Replacements made in the file.
    pub replacements: usize,
}

/// Output shared by `rename` and `extract-token`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, schemars::JsonSchema)]
pub struct RewriteData {
    /// The token (or literal) that was replaced.
    pub from: String,
    /// What replaced it.
    pub to: String,
    /// True when nothing was written.
    pub dry_run: bool,
    /// Total reference replacements across all files.
    pub replacements: usize,
    /// The files written (or that would be).
    pub files: Vec<FileChange>,
}

impl RewriteData {
    /// Build the report for `changes`.
    #[must_use]
    pub fn new(root: &Path, from: &str, to: &str, dry_run: bool, changes: &[Change]) -> Self {
        Self {
            from: from.to_owned(),
            to: to.to_owned(),
            dry_run,
            replacements: changes
                .iter()
                .filter(|c| c.kind == "reference")
                .map(|c| c.replacements)
                .sum(),
            files: changes
                .iter()
                .map(|c| FileChange {
                    path: relative(root, &c.path),
                    kind: c.kind.to_owned(),
                    replacements: c.replacements,
                })
                .collect(),
        }
    }

    /// One human line per file, then a total.
    #[must_use]
    pub fn lines(&self) -> Vec<String> {
        let verb = if self.dry_run {
            "would change"
        } else {
            "changed"
        };
        let mut lines: Vec<String> = self
            .files
            .iter()
            .map(|f| format!("{verb} {} ({}, {})", f.path, f.kind, f.replacements))
            .collect();
        lines.push(format!(
            "{} -> {}: {} reference(s) in {} file(s)",
            self.from,
            self.to,
            self.replacements,
            self.files.len()
        ));
        lines
    }
}

/// Why a commit failed.
#[derive(Debug, thiserror::Error)]
#[error("cannot write {}: {source} ({restored} earlier write(s) rolled back)", path.display())]
pub struct CommitError {
    /// The file that failed.
    pub path: PathBuf,
    /// The OS error.
    #[source]
    pub source: io::Error,
    /// Files restored to their previous text.
    pub restored: usize,
}

/// Write every change through `write`; if one fails, put every earlier file back and report it.
///
/// # Errors
///
/// [`CommitError`] naming the first file that failed to write.
pub fn commit(
    changes: &[Change],
    write: impl Fn(&Path, &[u8]) -> io::Result<()>,
) -> Result<(), CommitError> {
    for (i, change) in changes.iter().enumerate() {
        if let Err(source) = write(&change.path, change.after.as_bytes()) {
            tracing::warn!(path = %change.path.to_string_lossy(), error = %source, "write failed; rolling back");
            let mut restored = 0;
            for done in changes[..i].iter().rev() {
                let ok = match &done.before {
                    Some(text) => write(&done.path, text.as_bytes()).is_ok(),
                    None => std::fs::remove_file(&done.path).is_ok(),
                };
                if ok {
                    restored += 1;
                } else {
                    tracing::error!(path = %done.path.to_string_lossy(), "rollback failed");
                }
            }
            return Err(CommitError {
                path: change.path.clone(),
                source,
                restored,
            });
        }
        tracing::debug!(path = %change.path.to_string_lossy(), "wrote");
    }
    Ok(())
}

/// Write `changes` with atomic per-file writes and all-or-nothing rollback.
///
/// # Errors
///
/// See [`commit`].
pub fn commit_atomic(changes: &[Change]) -> Result<(), CommitError> {
    commit(changes, gob_fs::write_atomic)
}

/// Every file that may hold references: (path, lang), sorted, generated outputs excluded.
#[must_use]
pub fn source_files(
    root: &Path,
    spec: &DesignSpec,
    generated: &[Rendered],
) -> Vec<(PathBuf, Lang)> {
    let mut all = Vec::new();
    walk(root, &mut all);
    all.sort();
    let css_root = root.join(&spec.project.css_root);
    let mut out = Vec::new();
    for path in all {
        if generated.iter().any(|g| g.path == path) {
            continue;
        }
        let rel = relative(root, &path).replace('\\', "/");
        let ext = path
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or_default();
        let lang = if path.starts_with(&css_root) && CSS_EXTS.contains(&ext) {
            Lang::Css
        } else if spec
            .jsx
            .globs
            .iter()
            .any(|g| crunk_ingest::glob::glob_match(&rel, g))
        {
            Lang::Script
        } else if ext == "toml" && rel.starts_with("design/") {
            Lang::Toml
        } else {
            continue;
        };
        out.push((path, lang));
    }
    out
}

/// Collect regular files under `dir`, skipping hidden and noise directories.
fn walk(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.filter_map(Result::ok) {
        let path = entry.path();
        let name = entry.file_name();
        let name = name.to_string_lossy();
        let Ok(kind) = entry.file_type() else {
            continue;
        };
        if kind.is_dir() {
            if !name.starts_with('.') && !NOISE_DIRS.contains(&name.as_ref()) {
                walk(&path, out);
            }
        } else if kind.is_file() {
            out.push(path);
        }
    }
}

/// Changes that bring the managed generated files in line with `spec`; only files that exist and
/// differ are included.
#[must_use]
pub fn generated_changes(generated: &[Rendered]) -> Vec<Change> {
    generated
        .iter()
        .filter_map(|g| {
            let before = std::fs::read_to_string(&g.path).ok()?;
            (before != g.content).then(|| Change {
                path: g.path.clone(),
                before: Some(before),
                after: g.content.clone(),
                kind: "generated",
                replacements: 0,
            })
        })
        .collect()
}

/// Rewrite `files` with `rewrite(text, lang)`, keeping those that change.
#[must_use]
pub fn reference_changes(
    files: &[(PathBuf, Lang)],
    rewrite: impl Fn(&str, Lang) -> (String, usize),
) -> Vec<Change> {
    files
        .iter()
        .filter_map(|(path, lang)| {
            let before = std::fs::read_to_string(path)
                .inspect_err(|e| tracing::debug!(path = %path.to_string_lossy(), error = %e, "skipped: unreadable"))
                .ok()?;
            let (after, replacements) = rewrite(&before, *lang);
            (replacements > 0 && after != before).then(|| Change {
                path: path.clone(),
                before: Some(before),
                after,
                kind: "reference",
                replacements,
            })
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rename(text: &str, lang: Lang, old: &str, new: &str) -> (String, usize) {
        let m = RenameMatcher::new(vec![(old.into(), new.into())], lang);
        scan(text, lang, |t, k, s| m.at(t, k, s))
    }

    // frob:tests crates/crunk/src/rewrite.rs::commit
    #[test]
    fn commit_rolls_back_earlier_writes_when_a_later_one_fails() {
        let dir = tempfile::tempdir().unwrap();
        let a = dir.path().join("a.txt");
        let b = dir.path().join("b.txt");
        std::fs::write(&a, "old-a").unwrap();
        std::fs::write(&b, "old-b").unwrap();
        let change = |path: &PathBuf, after: &str| Change {
            path: path.clone(),
            before: Some(std::fs::read_to_string(path).unwrap()),
            after: after.into(),
            kind: "reference",
            replacements: 1,
        };
        let changes = vec![change(&a, "new-a"), change(&b, "new-b")];
        let failing = b.clone();
        let err = commit(&changes, |p, bytes| {
            if p == failing && bytes == b"new-b" {
                Err(io::Error::other("disk full"))
            } else {
                std::fs::write(p, bytes)
            }
        })
        .unwrap_err();
        assert_eq!(err.path, b);
        assert_eq!(err.restored, 1);
        assert_eq!(std::fs::read_to_string(&a).unwrap(), "old-a");
        assert_eq!(std::fs::read_to_string(&b).unwrap(), "old-b");
    }

    // frob:tests crates/crunk/src/rewrite.rs::scan
    #[test]
    fn prefix_overlapping_names_are_left_alone() {
        let css = "a { color: var(--color); b: var(--color-bg); c: var(--color) var(--color); }";
        let (out, n) = rename(css, Lang::Css, "--color", "--hue");
        assert_eq!(n, 3);
        assert_eq!(
            out,
            "a { color: var(--hue); b: var(--color-bg); c: var(--hue) var(--hue); }"
        );
    }

    // frob:tests crates/crunk/src/rewrite.rs::scan
    #[test]
    fn comments_and_css_strings_are_not_rewritten() {
        let css = "/* --x */ a { content: \"--x\"; color: var(--x); }";
        let (out, n) = rename(css, Lang::Css, "--x", "--y");
        assert_eq!(n, 1);
        assert_eq!(out, "/* --x */ a { content: \"--x\"; color: var(--y); }");
    }

    // frob:tests crates/crunk/src/rewrite.rs::scan
    #[test]
    fn script_only_rewrites_real_references_in_strings() {
        let tsx = "// --x\nconst a = 'var(--x)'; const b = \"--x\"; const c = 'use --x here'; const d = --x;";
        let (out, n) = rename(tsx, Lang::Script, "--x", "--y");
        assert_eq!(n, 2);
        assert_eq!(
            out,
            "// --x\nconst a = 'var(--y)'; const b = \"--y\"; const c = 'use --x here'; const d = --x;"
        );
    }

    // frob:tests crates/crunk/src/rewrite.rs::scan
    #[test]
    fn toml_rewrites_exact_strings_and_skips_comments() {
        let toml = "# --x\ntoken = \"--x\"\nnote = \"see --x\"\n";
        let (out, n) = rename(toml, Lang::Toml, "--x", "--y");
        assert_eq!(n, 1);
        assert_eq!(out, "# --x\ntoken = \"--y\"\nnote = \"see --x\"\n");
    }

    // frob:tests crates/crunk/src/rewrite.rs::HexMatcher
    #[test]
    fn hex_matcher_normalises_case_and_shorthand_and_respects_boundaries() {
        let m = HexMatcher::new("#111111", "var(--c)".into()).unwrap();
        let css =
            "a { color: #111; b: #111111; c: #1111112; d: #111111AA; e: #11112; f: #111 #111; }";
        let (out, n) = scan(css, Lang::Css, |t, k, _| m.at(t, k));
        assert_eq!(n, 4);
        assert_eq!(
            out,
            "a { color: var(--c); b: var(--c); c: #1111112; d: #111111AA; e: #11112; f: var(--c) var(--c); }"
        );
    }
}
