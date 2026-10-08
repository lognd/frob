//! Utility-token tokenization: a class-list literal (or the static segments of a template
//! literal) to [`LocatedUtility`] entries (the Python `jsx._tokens`).
//!
//! Everything here works on text already read out of a literal; nothing scans source.

// frob:ticket 01M43ARYFVG86PAGGM78JGRZY3

use crate::model::LocatedUtility;

/// A run of literal text and how it sits in its literal.
///
/// A plain string is one segment with no boundaries. A template literal contributes one segment
/// per static fragment; a fragment that touches a `${}` substitution without whitespace between
/// has a boundary on that side, and the token next to it is half a name and is dropped.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) struct Segment {
    /// The raw text, escapes unresolved.
    pub text: String,
    /// Byte offset of the text in the source (its first byte).
    pub start: usize,
    /// A `${}` substitution immediately precedes this fragment.
    pub left: bool,
    /// A `${}` substitution immediately follows this fragment.
    pub right: bool,
    /// The text is a fragment of a template literal (not of a plain string).
    pub template: bool,
}

/// Split the variant prefixes off `token`: `(final utility, variants in order)`.
///
/// A `:` inside `[...]` is part of an arbitrary variant, not a separator.
pub(super) fn split_variants(token: &str) -> (String, Vec<String>) {
    let mut depth = 0usize;
    let mut last = 0usize;
    let mut segments: Vec<&str> = Vec::new();
    for (i, ch) in token.char_indices() {
        match ch {
            '[' => depth += 1,
            ']' => depth = depth.saturating_sub(1),
            ':' if depth == 0 => {
                segments.push(&token[last..i]);
                last = i + 1;
            }
            _ => {}
        }
    }
    segments.push(&token[last..]);
    let name = segments.pop().unwrap_or_default().to_owned();
    (name, segments.into_iter().map(str::to_owned).collect())
}

/// Whitespace-separated tokens of `text`, dropping the outermost token that touches a template
/// boundary without whitespace in between (a half-token is never fabricated into a name).
pub(super) fn tokenize_text(text: &str, left: bool, right: bool) -> Vec<&str> {
    let mut spans: Vec<(usize, usize)> = Vec::new();
    let mut open: Option<usize> = None;
    for (i, ch) in text.char_indices() {
        match (ch.is_whitespace(), open) {
            (false, None) => open = Some(i),
            (true, Some(s)) => {
                spans.push((s, i));
                open = None;
            }
            _ => {}
        }
    }
    if let Some(s) = open {
        spans.push((s, text.len()));
    }
    if left && spans.first().is_some_and(|&(s, _)| s == 0) {
        spans.remove(0);
    }
    if right && spans.last().is_some_and(|&(_, e)| e == text.len()) {
        spans.pop();
    }
    spans.into_iter().map(|(s, e)| &text[s..e]).collect()
}

/// True when `token` has only utility characters (`a-z 0-9 : / [ ] -`) and at least one letter.
pub(super) fn is_utility_shaped(token: &str) -> bool {
    !token.is_empty()
        && token
            .bytes()
            .all(|b| matches!(b, b'a'..=b'z' | b'0'..=b'9' | b':' | b'/' | b'[' | b']' | b'-'))
        && token.bytes().any(|b| b.is_ascii_lowercase())
}

/// True when `text` looks like a Tailwind class list: two or more utility-shaped tokens, or one
/// arbitrary-value utility (it contains `[...]`).
pub(super) fn is_utility_class_list(text: &str) -> bool {
    let tokens: Vec<&str> = text.split_whitespace().collect();
    match tokens.as_slice() {
        [] => false,
        [one] => one.contains('[') && one.contains(']'),
        many => many.iter().all(|t| is_utility_shaped(t)),
    }
}

/// The utilities of `tokens`, all on `line`.
pub(super) fn utilities_of(tokens: &[&str], line: u32) -> Vec<LocatedUtility> {
    tokens
        .iter()
        .map(|t| {
            let (name, variants) = split_variants(t);
            LocatedUtility {
                name,
                line,
                variants,
            }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-ingest/src/jsx/tokens.rs::split_variants
    #[test]
    fn variants_split_outside_brackets_only() {
        assert_eq!(split_variants("p-4"), ("p-4".to_owned(), vec![]));
        assert_eq!(
            split_variants("md:hover:bg-red-500"),
            (
                "bg-red-500".to_owned(),
                vec!["md".to_owned(), "hover".to_owned()]
            )
        );
        assert_eq!(
            split_variants("[&>x]:text-sm"),
            ("text-sm".to_owned(), vec!["[&>x]".to_owned()])
        );
        assert_eq!(
            split_variants("w-[calc(1:2)]"),
            ("w-[calc(1:2)]".to_owned(), vec![])
        );
    }

    // frob:tests crates/crunk-ingest/src/jsx/tokens.rs::tokenize_text
    #[test]
    fn boundary_touching_tokens_are_dropped() {
        assert_eq!(tokenize_text("a b", false, false), ["a", "b"]);
        assert_eq!(tokenize_text("z- ", true, false), Vec::<&str>::new());
        assert_eq!(tokenize_text("bg-red ", false, true), ["bg-red"]);
        assert_eq!(tokenize_text("-x bg-red", true, false), ["bg-red"]);
        assert_eq!(tokenize_text(" a b", true, false), ["a", "b"]);
        assert_eq!(tokenize_text("a b", false, true), ["a"]);
    }

    // frob:tests crates/crunk-ingest/src/jsx/tokens.rs::is_utility_class_list
    #[test]
    fn the_class_list_gate() {
        assert!(is_utility_class_list("flex gap-2"));
        assert!(is_utility_class_list("p-[7px]"));
        assert!(!is_utility_class_list("flex"));
        assert!(!is_utility_class_list("Hello World"));
        assert!(!is_utility_class_list(""));
    }
}
