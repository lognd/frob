//! The library behind the `rule test`, `rule check`, `rule catalog` and `rule fmt` verbs
//! (grl-spec.md section 11): every product registers thin commands over these functions.
//!
//! Each function takes rule text and returns plain serializable data plus the lines the text view
//! prints, so the products only read files, map the data to an envelope and pick the exit code.

// frob:ticket 01M3ZX7FCFBJSWMTZGCQMW7215

pub mod catalog;
pub mod check;
pub mod fmt;
// frob:ticket 01M3ZX7HCQYMTNB9S8ANCZA04W
pub mod new;
pub mod test;
// frob:ticket 01M3ZX7H8FPEAY1X1WVW1PNXXN
pub mod why;

use std::path::Path;

use gob_text::SourceText;

/// Directories rule discovery never descends into.
const SKIPPED_DIRS: [&str; 4] = [".git", "target", "node_modules", ".jj"];

/// Every `.grl` file under `dir`, as `/`-separated paths relative to `root`, sorted.
///
/// # Errors
/// The I/O error of the first directory that cannot be read.
pub fn discover_rules(root: &Path, dir: &Path) -> std::io::Result<Vec<String>> {
    fn walk(root: &Path, dir: &Path, out: &mut Vec<String>) -> std::io::Result<()> {
        for entry in std::fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();
            if entry.file_type()?.is_dir() {
                if !SKIPPED_DIRS.iter().any(|s| entry.file_name() == *s) {
                    walk(root, &path, out)?;
                }
            } else if path.extension().is_some_and(|e| e == "grl") {
                let rel = path.strip_prefix(root).unwrap_or(&path);
                out.push(
                    gob_path::Shown::with_home(rel, None)
                        .to_string()
                        .replace('\\', "/"),
                );
            }
        }
        Ok(())
    }
    let mut out = Vec::new();
    walk(root, dir, &mut out)?;
    out.sort();
    Ok(out)
}

/// One compiler diagnostic, located.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, schemars::JsonSchema)]
pub struct Diag {
    /// The code such as `GRL001`; empty for a syntax error.
    pub code: String,
    /// `error` or `warning`.
    pub severity: String,
    /// 1-based line of the primary label (0 when it cannot be located).
    pub line: u32,
    /// 1-based byte column of the primary label (0 when it cannot be located).
    pub col: u32,
    /// The message.
    pub message: String,
}

/// Parse and check one rule file: the located diagnostics, and whether any is an error.
pub fn diagnostics(path: &str, source: &str) -> (Vec<Diag>, bool) {
    let found = crate::check::compile_diagnostics(path, source);
    let text = SourceText::new(source.to_owned()).ok();
    let mut has_error = false;
    let diags = found
        .iter()
        .map(|d| {
            let error = d.severity == crate::check::Severity::Error;
            has_error |= error;
            let lc = text
                .as_ref()
                .and_then(|t| t.line_col(d.primary.span.range.start()));
            Diag {
                code: d.code.map(|c| c.as_str().to_owned()).unwrap_or_default(),
                severity: if error { "error" } else { "warning" }.to_owned(),
                line: lc.map_or(0, |l| l.line),
                col: lc.map_or(0, |l| l.col),
                message: d.message.clone(),
            }
        })
        .collect();
    (diags, has_error)
}

/// The rule file parsed, or `None` when it has syntax errors (the checker reports those).
pub(crate) fn parse_clean(path: &str, source: &str) -> Option<crate::grl::ast::File> {
    let parsed = crate::grl::parse(gob_text::FileInterner::new().intern(path), source);
    parsed.is_ok().then_some(parsed.file)
}
