//! Markdown inline structure: code span ranges from the inline grammar.

// frob:ticket 01M3ZZXAZ39410AVYQSRSYVF9C

use std::ops::Range;

use tree_sitter::{Node, Parser, Point};

use crate::{Language, ParsedTree};

/// Collect `inline` nodes (paragraph and heading text) of the block tree.
fn inline_nodes(root: Node<'_>) -> Vec<Node<'_>> {
    let mut out = Vec::new();
    let mut cursor = root.walk();
    let mut stack = vec![root];
    while let Some(n) = stack.pop() {
        if n.kind() == "inline" {
            out.push(n);
            continue;
        }
        stack.extend(n.children(&mut cursor));
    }
    out.sort_by_key(Node::start_byte);
    out
}

/// Byte ranges of Commonmark inline code spans (backticks included) in a markdown tree.
///
/// Each block-level `inline` node is re-parsed with the inline grammar, so
/// backtick-run matching, escapes and spans over soft line breaks follow the
/// grammar rather than a regex. Non-markdown trees and parser failures yield
/// an empty list.
pub fn markdown_code_spans(tree: &ParsedTree) -> Vec<Range<usize>> {
    if tree.language != Language::Markdown {
        return Vec::new();
    }
    let mut parser = Parser::new();
    if let Err(err) = parser.set_language(&tree_sitter_md::INLINE_LANGUAGE.into()) {
        tracing::warn!(%err, "inline grammar unavailable");
        return Vec::new();
    }
    let text: &str = &tree.text;
    let mut spans = Vec::new();
    for node in inline_nodes(tree.root()) {
        let range = tree_sitter::Range {
            start_byte: node.start_byte(),
            end_byte: node.end_byte(),
            start_point: Point::default(),
            end_point: Point::default(),
        };
        if parser.set_included_ranges(&[range]).is_err() {
            tracing::warn!("inline range rejected");
            continue;
        }
        let Some(inline) = parser.parse(text, None) else {
            tracing::warn!("inline parse failed");
            continue;
        };
        let mut cursor = inline.walk();
        let mut stack = vec![inline.root_node()];
        while let Some(n) = stack.pop() {
            if n.kind() == "code_span" {
                spans.push(n.byte_range());
            } else {
                stack.extend(n.children(&mut cursor));
            }
        }
    }
    spans.sort_by_key(|r| r.start);
    tracing::trace!(count = spans.len(), "markdown code spans");
    spans
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{ParseLimits, ParseResult, parse};

    fn spans(src: &str) -> Vec<String> {
        let ParseResult::Parsed(t) = parse(Language::Markdown, src, &ParseLimits::default()) else {
            panic!("parse")
        };
        markdown_code_spans(&t)
            .into_iter()
            .map(|r| src[r].to_owned())
            .collect()
    }

    #[test]
    fn single_and_double_backtick_spans() {
        assert_eq!(spans("a `b` c\n"), ["`b`"]);
        assert_eq!(spans("a ``x ` y`` c\n"), ["``x ` y``"]);
    }

    #[test]
    fn span_over_soft_break() {
        assert_eq!(spans("a `b\nc` d\n"), ["`b\nc`"]);
    }

    #[test]
    fn unmatched_run_is_not_a_span() {
        assert!(spans("a ` b\n").is_empty());
        assert!(spans("a \\`b` c\n").is_empty());
    }

    #[test]
    fn fenced_block_is_not_an_inline_span() {
        assert!(spans("```\n`x`\n```\n").is_empty());
    }
}
