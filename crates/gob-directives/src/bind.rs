//! Binding rules (code-model section 4): which symbol a directive attaches to.

use gob_symbols::{SymbolRecord, Symref};
use gob_text::{LineIndex, TextSize};

/// What a directive is bound to.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Binding {
    /// A symbol (code symbol or markdown heading anchor).
    Symbol(Symref),
    /// The whole file.
    File,
}

/// A directive's position, for binding.
#[derive(Debug, Clone, Copy)]
pub(crate) struct Site {
    /// Byte offset where the directive text starts.
    pub(crate) start: usize,
    /// Byte offset where the directive text ends.
    pub(crate) end: usize,
    /// When false, only the enclosing symbol or the file can be chosen.
    pub(crate) allow_following: bool,
}

/// How many lines after the directive a symbol may start and still be "next".
pub(crate) const FOLLOW_LINES: u32 = 2;

fn line_of(index: &LineIndex, offset: usize) -> Option<u32> {
    let off = TextSize::new(u32::try_from(offset).ok()?);
    index.line_col(off).map(|lc| lc.line)
}

fn span_range(s: &SymbolRecord) -> std::ops::Range<usize> {
    usize::try_from(u32::from(s.span.start())).unwrap_or(usize::MAX)
        ..usize::try_from(u32::from(s.span.end())).unwrap_or(usize::MAX)
}

/// The symbol a directive at `site` binds to, or `None` for the file.
///
/// Order: the outermost symbol that starts after the directive and within
/// [`FOLLOW_LINES`] lines of it (when allowed), else the innermost symbol
/// whose span contains the directive, else `None`.
pub(crate) fn bind<'s>(
    index: &LineIndex,
    symbols: &'s [SymbolRecord],
    site: Site,
) -> Option<&'s SymbolRecord> {
    let dline = line_of(index, site.start)?;
    if site.allow_following {
        let next = symbols
            .iter()
            .filter(|s| {
                let r = span_range(s);
                r.start >= site.end
                    && line_of(index, r.start).is_some_and(|l| l - dline <= FOLLOW_LINES)
            })
            .min_by_key(|s| (s.span.start(), std::cmp::Reverse(s.span.len())));
        if let Some(s) = next {
            tracing::trace!(symref = %s.symref, "bound to following symbol");
            return Some(s);
        }
    }
    let enclosing = symbols
        .iter()
        .filter(|s| span_range(s).contains(&site.start))
        .min_by_key(|s| s.span.len());
    if let Some(s) = enclosing {
        tracing::trace!(symref = %s.symref, "bound to enclosing symbol");
    } else {
        tracing::trace!("bound to file");
    }
    enclosing
}

/// True when `sym` is a test item: it sits under a `tests` module or `tests/`
/// path, or an attribute line above it mentions `test`.
pub(crate) fn is_test_item(index: &LineIndex, text: &str, sym: &SymbolRecord) -> bool {
    let path = sym.symref.path();
    if path.starts_with("tests/") || path.contains("/tests/") {
        return true;
    }
    if sym
        .symref
        .segments()
        .iter()
        .any(|s| s == "tests" || s == "test")
    {
        return true;
    }
    let Some(mut line) = line_of(index, span_range(sym).start) else {
        return false;
    };
    while line > 1 {
        line -= 1;
        let Some(start) = index.line_start(line) else {
            return false;
        };
        let start = usize::try_from(u32::from(start)).unwrap_or(usize::MAX);
        let l = text[start..].lines().next().unwrap_or_default().trim();
        if l.starts_with("#[") {
            if l.contains("test") {
                return true;
            }
        } else if !l.starts_with("//") {
            return false;
        }
    }
    false
}
