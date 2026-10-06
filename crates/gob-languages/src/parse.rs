//! Bounded parsing: size cap, timeout, never panics.

use std::ops::ControlFlow;
use std::sync::Arc;
use std::time::{Duration, Instant};

use gob_text::{TextRange, TextSize};

use crate::Language;
use crate::grammar::ts_language;

/// Knobs bounding a single parse.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ParseLimits {
    /// Largest accepted input in bytes (also capped at `u32::MAX`).
    pub max_bytes: u64,
    /// Wall-clock budget for the parse.
    pub timeout: Duration,
}

impl Default for ParseLimits {
    fn default() -> Self {
        Self {
            max_bytes: 2 * 1024 * 1024,
            timeout: Duration::from_secs(2),
        }
    }
}

/// Why a file could not be parsed into a tree.
#[derive(Debug, Clone, Copy, PartialEq, Eq, thiserror::Error)]
pub enum UnresolvedReason {
    /// The input exceeded the size cap.
    #[error("input is {size} bytes, over the cap of {cap} bytes")]
    TooLarge {
        /// Input size in bytes.
        size: u64,
        /// The cap that was exceeded.
        cap: u64,
    },
    /// The parse exceeded its time budget.
    #[error("parse timed out")]
    TimedOut,
    /// The grammar is not compiled in or failed to load.
    #[error("grammar unavailable")]
    GrammarUnavailable,
}

/// Marker returned instead of a tree when parsing was not possible.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Unresolved {
    /// The language that was requested.
    pub language: Language,
    /// Why no tree was produced.
    pub reason: UnresolvedReason,
}

/// A parsed syntax tree together with its source text.
#[derive(Debug, Clone)]
pub struct ParsedTree {
    /// The language the tree was parsed as.
    pub language: Language,
    /// The tree-sitter tree.
    pub tree: tree_sitter::Tree,
    /// The exact text the tree was parsed from.
    pub text: Arc<str>,
}

impl ParsedTree {
    /// The root node of the tree.
    pub fn root(&self) -> tree_sitter::Node<'_> {
        self.tree.root_node()
    }

    /// True when the tree contains syntax errors or missing nodes.
    pub fn has_errors(&self) -> bool {
        self.root().has_error()
    }

    /// Converts a node's byte range to a [`TextRange`].
    ///
    /// Offsets are saturated at `u32::MAX`; `parse` rejects larger inputs so
    /// saturation cannot occur for trees it produced.
    pub fn node_range(&self, node: &tree_sitter::Node<'_>) -> TextRange {
        let clamp = |n: usize| TextSize::new(u32::try_from(n).unwrap_or(u32::MAX));
        TextRange::new(clamp(node.start_byte()), clamp(node.end_byte()))
    }
}

/// Outcome of [`parse`].
#[derive(Debug, Clone)]
pub enum ParseResult {
    /// A tree was produced (it may still contain error nodes).
    Parsed(ParsedTree),
    /// No tree; see the reason.
    Unresolved(Unresolved),
}

/// Parses `text` as `language` within `limits`; never panics.
pub fn parse(language: Language, text: &str, limits: &ParseLimits) -> ParseResult {
    let unresolved = |reason| {
        tracing::debug!(language = language.name(), %reason, "parse unresolved");
        ParseResult::Unresolved(Unresolved { language, reason })
    };
    let size = text.len() as u64;
    let cap = limits.max_bytes.min(u64::from(u32::MAX));
    if size > cap {
        return unresolved(UnresolvedReason::TooLarge { size, cap });
    }
    let Some(ts) = ts_language(language) else {
        return unresolved(UnresolvedReason::GrammarUnavailable);
    };
    let mut parser = tree_sitter::Parser::new();
    if let Err(err) = parser.set_language(&ts) {
        tracing::warn!(language = language.name(), %err, "set_language failed");
        return unresolved(UnresolvedReason::GrammarUnavailable);
    }
    let bytes = text.as_bytes();
    let start = Instant::now();
    let timeout = limits.timeout;
    let mut on_progress = |_: &tree_sitter::ParseState| {
        if start.elapsed() >= timeout {
            ControlFlow::Break(())
        } else {
            ControlFlow::Continue(())
        }
    };
    let options = tree_sitter::ParseOptions::new().progress_callback(&mut on_progress);
    let tree = parser.parse_with_options(
        &mut |offset, _| bytes.get(offset..).unwrap_or_default(),
        None,
        Some(options),
    );
    match tree {
        Some(tree) => {
            tracing::debug!(language = language.name(), size, "parsed");
            ParseResult::Parsed(ParsedTree {
                language,
                tree,
                text: Arc::from(text),
            })
        }
        None => unresolved(UnresolvedReason::TimedOut),
    }
}

#[cfg(test)]
#[allow(dead_code)] // helpers are unused when no grammar feature is enabled
pub(crate) mod tests {
    use super::*;

    pub(crate) fn parsed(language: Language, text: &str) -> ParsedTree {
        match parse(language, text, &ParseLimits::default()) {
            ParseResult::Parsed(t) => t,
            ParseResult::Unresolved(u) => panic!("unresolved: {u:?}"),
        }
    }

    fn too_large(language: Language) {
        let limits = ParseLimits {
            max_bytes: 8,
            ..ParseLimits::default()
        };
        match parse(language, "0123456789", &limits) {
            ParseResult::Unresolved(Unresolved {
                reason: UnresolvedReason::TooLarge { size: 10, cap: 8 },
                ..
            }) => {}
            other => panic!("expected TooLarge, got {other:?}"),
        }
    }

    fn tiny_timeout(language: Language, unit: &str) {
        let text = unit.repeat(20_000);
        let limits = ParseLimits {
            timeout: Duration::from_nanos(1),
            ..ParseLimits::default()
        };
        match parse(language, &text, &limits) {
            ParseResult::Parsed(_)
            | ParseResult::Unresolved(Unresolved {
                reason: UnresolvedReason::TimedOut,
                ..
            }) => {}
            other @ ParseResult::Unresolved(_) => panic!("unexpected {other:?}"),
        }
    }

    #[test]
    fn default_limits() {
        let l = ParseLimits::default();
        assert_eq!(l.max_bytes, 2 * 1024 * 1024);
        assert_eq!(l.timeout, Duration::from_secs(2));
    }

    #[cfg(feature = "rust")]
    #[test]
    fn rust_parses_and_limits() {
        let t = parsed(Language::Rust, "fn main() { let x = 1; }\n");
        assert!(!t.has_errors());
        assert!(parsed(Language::Rust, "fn (").has_errors());
        too_large(Language::Rust);
        tiny_timeout(Language::Rust, "fn f() { 1 + 2; }\n");
    }

    #[cfg(feature = "markdown")]
    #[test]
    fn markdown_parses_and_limits() {
        assert!(!parsed(Language::Markdown, "# Title\n\ntext\n").has_errors());
        too_large(Language::Markdown);
        tiny_timeout(Language::Markdown, "- item *emph*\n");
    }

    #[cfg(feature = "toml")]
    #[test]
    fn toml_parses_and_limits() {
        assert!(!parsed(Language::Toml, "[a]\nb = 1\n").has_errors());
        too_large(Language::Toml);
        tiny_timeout(Language::Toml, "k = [1, 2, 3]\n");
    }

    #[cfg(not(feature = "toml"))]
    #[test]
    fn disabled_feature_is_unavailable() {
        match parse(Language::Toml, "a = 1", &ParseLimits::default()) {
            ParseResult::Unresolved(u) => {
                assert_eq!(u.reason, UnresolvedReason::GrammarUnavailable);
            }
            other @ ParseResult::Parsed(_) => panic!("{other:?}"),
        }
    }

    #[test]
    fn web_grammars_parse_clean_and_report_errors() {
        let cases: [(Language, &str, &str); 5] = [
            (Language::TypeScript, "let x: number = 1;\n", "let x: = ;"),
            (Language::Tsx, "const a = <b>{1}</b>;\n", "const a = <b>{;"),
            (Language::JavaScript, "let x = 1;\n", "let = ;"),
            (Language::Jsx, "const a = <b>{1}</b>;\n", "const a = <b>{;"),
            (Language::Css, "a { color: red; }\n", "a { color: ;; { "),
        ];
        for (l, good, bad) in cases {
            assert!(!parsed(l, good).has_errors(), "{l:?}");
            assert!(parsed(l, bad).has_errors(), "{l:?}");
            too_large(l);
            tiny_timeout(l, good);
        }
    }
}
