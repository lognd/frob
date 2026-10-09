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

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
/// A directive's position, for binding.
#[derive(Debug, Clone, Copy)]
pub(crate) struct Site {
    /// Byte offset where the directive text starts.
    pub(crate) start: usize,
    /// Byte offset where the directive text ends.
    pub(crate) end: usize,
    /// When false, only the enclosing symbol or the file can be chosen.
    pub(crate) allow_following: bool,
    /// True for languages whose comments are `#` lines (YAML, TOML): such lines
    /// belong to the directive block like `//` lines do in Rust.
    pub(crate) hash_comments: bool,
}

fn line_of(index: &LineIndex, offset: usize) -> Option<u32> {
    let off = TextSize::new(u32::try_from(offset).ok()?);
    index.line_col(off).map(|lc| lc.line)
}

fn span_range(s: &SymbolRecord) -> std::ops::Range<usize> {
    usize::try_from(u32::from(s.span.start())).unwrap_or(usize::MAX)
        ..usize::try_from(u32::from(s.span.end())).unwrap_or(usize::MAX)
}

/// Net open `[` brackets on `line` (attribute continuation tracking).
fn bracket_delta(line: &str) -> i32 {
    line.chars().fold(0, |d, c| match c {
        '[' => d + 1,
        ']' => d - 1,
        _ => d,
    })
}

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
/// True when code precedes the comment on its own line (`on: # note`).
///
/// A trailing `#` comment describes its own line, so it never binds forward.
fn is_trailing(index: &LineIndex, text: &str, line: u32, at: usize) -> bool {
    let Some(start) = index.line_start(line) else {
        return false;
    };
    let start = usize::try_from(u32::from(start)).unwrap_or(usize::MAX);
    !text[start..at].trim_start().starts_with('#')
}

// frob:ticket 01M40H2JYVEHBZD62WV8Z6EXFW
/// The last line of the directive block that starts on `from`.
///
/// A block is the run of lines after `from` that carry no item of their own
/// and no blank line: line comments, doc comments, block-comment lines and
/// attributes (including multi-line ones). The returned line is the first
/// line that ends the run (the item line, a blank line or other code); a
/// symbol starting on or before it is "next" for every directive in the block.
fn block_limit(index: &LineIndex, text: &str, from: u32, hash_comments: bool) -> u32 {
    let mut line = from;
    let mut open = 0i32;
    loop {
        let next = line + 1;
        let Some(start) = index.line_start(next) else {
            return line;
        };
        let start = usize::try_from(u32::from(start)).unwrap_or(usize::MAX);
        let l = text[start..].lines().next().unwrap_or_default().trim();
        let attribute = l.starts_with("#[") || l.starts_with("#![");
        let preamble = open > 0
            || l.starts_with("//")
            || l.starts_with("/*")
            || l.starts_with('*')
            || attribute
            || (hash_comments && l.starts_with('#'));
        if !preamble {
            return next;
        }
        if open > 0 || attribute {
            open = (open + bracket_delta(l)).max(0);
        }
        line = next;
    }
}

// frob:ticket 01M40H2JYVEHBZD62WV8Z6EXFW
// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
/// The symbol a directive at `site` binds to, or `None` for the file.
///
/// Order: the outermost symbol that starts after the directive within its
/// directive block (the directive's own line, then comment and attribute
/// lines, up to and including the first other line; when allowed), else the
/// innermost symbol whose span contains the directive, else `None`. A blank
/// line ends the block.
pub(crate) fn bind<'s>(
    index: &LineIndex,
    text: &str,
    symbols: &'s [SymbolRecord],
    site: Site,
) -> Option<&'s SymbolRecord> {
    let dline = line_of(index, site.start)?;
    if site.allow_following && !(site.hash_comments && is_trailing(index, text, dline, site.start))
    {
        let limit = block_limit(index, text, dline, site.hash_comments);
        let next = symbols
            .iter()
            .filter(|s| {
                let r = span_range(s);
                r.start >= site.end && line_of(index, r.start).is_some_and(|l| l <= limit)
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
    // frob:ticket 01M43A5DJT8XBQYEK36F0KSGKF
    if gob_symbols::is_python_test_fn(sym) {
        return true;
    }
    // frob:ticket 01M4FCB5W45KZSXZ0AWHT9HBY2
    if gob_symbols::is_csharp_test_fn(sym, text) {
        return true;
    }
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
