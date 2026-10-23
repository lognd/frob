//! What the CRAFT presence rules share: a text mask that blanks comments and string contents, a
//! brace-block reader over the masked text, identifier-bounded word search, and the per-sheet
//! "is there a UI here" and "is this state styled" judgments. All of it is T0: source text and
//! ingested declarations, no render.

// frob:ticket 01M5HM3WE0PDTYAJ31B2C2A8A0

use crunk_ingest::{Bucket, ProjectStyles, Stylesheet};

use crate::slop::judged_sheets;

/// One `selector { body }` block of a masked stylesheet, as byte ranges into the masked text.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Block {
    /// The trimmed selector (or at-rule prelude) range.
    pub selector: (usize, usize),
    /// The range between the braces.
    pub body: (usize, usize),
}

impl Block {
    /// The selector text of this block in `text`.
    #[must_use]
    pub fn selector_text<'a>(&self, text: &'a str) -> &'a str {
        &text[self.selector.0..self.selector.1]
    }

    /// The body text of this block in `text`.
    #[must_use]
    pub fn body_text<'a>(&self, text: &'a str) -> &'a str {
        &text[self.body.0..self.body.1]
    }
}

/// `source` with every block comment and the inside of every quoted string replaced by spaces
/// (newlines kept), so the result has the same byte offsets and no keyword hides in either.
#[must_use]
pub fn mask(source: &str) -> String {
    let bytes = source.as_bytes();
    let mut out = bytes.to_vec();
    let mut i = 0;
    while i < bytes.len() {
        match bytes[i] {
            b'/' if bytes.get(i + 1) == Some(&b'*') => {
                let end = source[i + 2..]
                    .find("*/")
                    .map_or(bytes.len(), |e| i + 2 + e + 2);
                blank(&mut out, i, end);
                i = end;
            }
            quote @ (b'"' | b'\'') => {
                let mut j = i + 1;
                while j < bytes.len() && bytes[j] != quote && bytes[j] != b'\n' {
                    j += if bytes[j] == b'\\' { 2 } else { 1 };
                }
                let end = j.min(bytes.len());
                blank(&mut out, i + 1, end);
                i = end + 1;
            }
            _ => i += 1,
        }
    }
    String::from_utf8(out).unwrap_or_else(|_| source.to_owned())
}

/// Replace `from..to` of `out` with spaces, keeping newlines.
fn blank(out: &mut [u8], from: usize, to: usize) {
    let end = to.min(out.len());
    for byte in &mut out[from.min(end)..end] {
        if *byte != b'\n' {
            *byte = b' ';
        }
    }
}

/// Every brace block of `masked`, in closing order (an inner block comes before its parent).
#[must_use]
pub fn blocks(masked: &str) -> Vec<Block> {
    let mut found = Vec::new();
    let mut open: Vec<((usize, usize), usize)> = Vec::new();
    let mut start = 0;
    for (i, byte) in masked.bytes().enumerate() {
        match byte {
            b'{' => {
                let raw = &masked[start..i];
                let lead = raw.len() - raw.trim_start().len();
                open.push(((start + lead, start + lead + raw.trim().len()), i + 1));
                start = i + 1;
            }
            b'}' => {
                if let Some((selector, body_start)) = open.pop() {
                    found.push(Block {
                        selector,
                        body: (body_start, i),
                    });
                }
                start = i + 1;
            }
            b';' => start = i + 1,
            _ => {}
        }
    }
    found
}

/// Whether `byte` can continue a CSS identifier.
fn is_ident(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || byte == b'-' || byte == b'_'
}

/// The byte offsets where `word` occurs in `text` as a whole identifier (not inside a longer one).
#[must_use]
pub fn find_words(text: &str, word: &str) -> Vec<usize> {
    let bytes = text.as_bytes();
    text.match_indices(word)
        .map(|(at, _)| at)
        .filter(|&at| {
            let before_ok = at == 0 || !is_ident(bytes[at - 1]);
            let after = at + word.len();
            let after_ok = after >= bytes.len() || !is_ident(bytes[after]);
            before_ok && after_ok
        })
        .collect()
}

/// Whether `word` occurs in `text` as a whole identifier.
#[must_use]
pub fn has_word(text: &str, word: &str) -> bool {
    !find_words(text, word).is_empty()
}

/// Whether `selector` names the pseudo-class `:state` (the word right after a colon).
#[must_use]
pub fn has_pseudo(selector: &str, state: &str) -> bool {
    find_words(selector, state)
        .into_iter()
        .any(|at| at > 0 && selector.as_bytes()[at - 1] == b':')
}

/// Whether `body` applies the Tailwind variant `state:` (for example `@apply active:scale-95`).
#[must_use]
pub fn has_variant(body: &str, state: &str) -> bool {
    find_words(body, state)
        .into_iter()
        .any(|at| body.as_bytes().get(at + state.len()) == Some(&b':'))
}

/// The declaration property names inside `body`, lowercased, in order.
#[must_use]
pub fn body_props(body: &str) -> Vec<String> {
    body.split(';')
        .filter_map(|part| part.split_once(':'))
        .map(|(prop, _)| prop.trim().to_ascii_lowercase())
        .filter(|prop| !prop.is_empty() && !prop.contains('{'))
        .collect()
}

/// The judged sheets that carry something to style: at least one non-custom-property declaration
/// or one Tailwind utility. A project of only token files or empty sheets has no UI to judge.
pub fn ui_sheets(styles: &ProjectStyles) -> impl Iterator<Item = &Stylesheet> {
    judged_sheets(styles).filter(|sheet| {
        !sheet.utilities.is_empty()
            || sheet
                .declarations
                .iter()
                .any(|decl| !decl.prop.starts_with("--"))
    })
}

/// Whether `sheet` styles `state` (a pseudo-class such as `focus-visible`): a non-empty rule on
/// `:state`, an `@apply state:...` variant, or (for a JSX source) a utility with that variant.
#[must_use]
pub fn state_styled(sheet: &Stylesheet, state: &str) -> bool {
    if sheet.bucket == Some(Bucket::Jsx) {
        return sheet
            .utilities
            .iter()
            .any(|u| u.variants.iter().any(|v| v == state));
    }
    let masked = mask(&sheet.source);
    blocks(&masked).iter().any(|block| {
        (has_pseudo(block.selector_text(&masked), state)
            && !block.body_text(&masked).trim().is_empty())
            || has_variant(block.body_text(&masked), state)
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-rules/src/craft.rs::mask
    #[test]
    fn mask_blanks_comments_and_strings_and_keeps_offsets() {
        let src = "a { /* :active */ content: \":focus-visible\"; }";
        let masked = mask(src);
        assert_eq!(masked.len(), src.len());
        assert!(!masked.contains("active"));
        assert!(!masked.contains("focus"));
        assert!(masked.contains("content"));
    }

    // frob:tests crates/crunk-rules/src/craft.rs::mask
    #[test]
    fn mask_survives_unterminated_input() {
        assert_eq!(mask("a { /* open").len(), 11);
        assert_eq!(mask("a { b: \"open").len(), 12);
        assert_eq!(mask(""), "");
    }

    // frob:tests crates/crunk-rules/src/craft.rs::blocks
    #[test]
    fn blocks_reads_nested_selectors_and_bodies() {
        let text = "@media (min-width: 1px) { a:active { color: red; } }";
        let found = blocks(text);
        assert_eq!(found.len(), 2);
        assert_eq!(found[0].selector_text(text), "a:active");
        assert_eq!(found[0].body_text(text).trim(), "color: red;");
        assert!(found[1].selector_text(text).starts_with("@media"));
    }

    // frob:tests crates/crunk-rules/src/craft.rs::has_pseudo
    #[test]
    fn pseudo_needs_the_colon_and_a_whole_word() {
        assert!(has_pseudo("a:active", "active"));
        assert!(!has_pseudo(".active", "active"));
        assert!(!has_pseudo("a:inactive", "active"));
        assert!(!has_pseudo(".is-active", "active"));
    }

    // frob:tests crates/crunk-rules/src/craft.rs::has_variant
    #[test]
    fn variant_needs_a_trailing_colon() {
        assert!(has_variant("@apply active:scale-95", "active"));
        assert!(!has_variant("@apply is-active:scale-95", "active"));
        assert!(!has_variant("@apply active", "active"));
    }
}
