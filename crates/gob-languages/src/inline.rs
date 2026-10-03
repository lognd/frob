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

/// Run `visit` over every node of every inline-grammar parse of a markdown tree.
///
/// Non-markdown trees and parser failures visit nothing.
fn for_each_inline_node<F: FnMut(Node<'_>)>(tree: &ParsedTree, mut visit: F) {
    if tree.language != Language::Markdown {
        return;
    }
    let mut parser = Parser::new();
    if let Err(err) = parser.set_language(&tree_sitter_md::INLINE_LANGUAGE.into()) {
        tracing::warn!(%err, "inline grammar unavailable");
        return;
    }
    let text: &str = &tree.text;
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
            visit(n);
            stack.extend(n.children(&mut cursor));
        }
    }
}

/// Byte ranges of Commonmark inline code spans (backticks included) in a markdown tree.
///
/// Each block-level `inline` node is re-parsed with the inline grammar, so
/// backtick-run matching, escapes and spans over soft line breaks follow the
/// grammar rather than a regex. Non-markdown trees and parser failures yield
/// an empty list.
pub fn markdown_code_spans(tree: &ParsedTree) -> Vec<Range<usize>> {
    let mut spans = Vec::new();
    for_each_inline_node(tree, |n| {
        if n.kind() == "code_span" {
            spans.push(n.byte_range());
        }
    });
    spans.sort_by_key(|r| r.start);
    tracing::trace!(count = spans.len(), "markdown code spans");
    spans
}

/// Byte ranges of fenced blocks, indented blocks and inline code spans, sorted by start.
///
/// Fence length, tilde fences and unclosed fences follow the block grammar.
/// Non-markdown trees yield an empty list.
pub fn markdown_code_ranges(tree: &ParsedTree) -> Vec<Range<usize>> {
    let mut out = Vec::new();
    if tree.language != Language::Markdown {
        return out;
    }
    let mut stack = vec![tree.root()];
    let mut cursor = tree.tree.walk();
    while let Some(n) = stack.pop() {
        if matches!(n.kind(), "fenced_code_block" | "indented_code_block") {
            out.push(n.byte_range());
        } else {
            stack.extend(n.children(&mut cursor));
        }
    }
    out.extend(markdown_code_spans(tree));
    out.sort_by_key(|r| r.start);
    out
}

/// Byte ranges of link and image destinations outside code, sorted by start.
///
/// Angle brackets around a destination are excluded. Only inline links and
/// images count, as Commonmark renders them; code blocks and spans hold text.
pub fn markdown_link_destinations(tree: &ParsedTree) -> Vec<Range<usize>> {
    let mut out = Vec::new();
    for_each_inline_node(tree, |n| {
        if n.kind() == "link_destination" {
            let r = n.byte_range();
            let raw = &tree.text[r.clone()];
            let inner = raw
                .strip_prefix('<')
                .and_then(|x| x.strip_suffix('>'))
                .map_or(r.clone(), |_| r.start + 1..r.end - 1);
            out.push(inner);
        }
    });
    out.sort_by_key(|r| r.start);
    out
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

    fn tree(src: &str) -> ParsedTree {
        let ParseResult::Parsed(t) = parse(Language::Markdown, src, &ParseLimits::default()) else {
            panic!("parse")
        };
        t
    }

    fn dests(src: &str) -> Vec<String> {
        markdown_link_destinations(&tree(src))
            .into_iter()
            .map(|r| src[r].to_owned())
            .collect()
    }

    fn code(src: &str) -> Vec<String> {
        markdown_code_ranges(&tree(src))
            .into_iter()
            .map(|r| src[r].to_owned())
            .collect()
    }

    #[test]
    fn nested_shorter_fence_stays_in_long_fence() {
        let src = "````md\n```\n[a](x.md)\n```\n[b](y.md)\n````\n[c](z.md)\n";
        assert_eq!(dests(src), ["z.md"]);
    }

    #[test]
    fn tilde_and_unclosed_fences_are_code() {
        assert!(dests("~~~\n[a](x.md)\n~~~\n").is_empty());
        assert!(dests("```\n[a](x.md)\n[b](y.md)\n").is_empty());
        assert!(dests("~~~\n```\n[a](x.md)\n~~~\n").is_empty());
    }

    #[test]
    fn indented_and_inline_code_are_not_links() {
        assert!(dests("para\n\n    [a](x.md)\n").is_empty());
        assert!(dests("see `[a](x.md)` here\n").is_empty());
        assert_eq!(
            dests("[a](<p q.md>) ![i](img.png \"t\")\n"),
            ["p q.md", "img.png"]
        );
    }

    #[test]
    fn code_ranges_cover_all_three_kinds() {
        let src = "a `i` b\n\n```\nf\n```\n\n    ind\n";
        assert_eq!(code(src).len(), 3);
    }

    #[test]
    fn fenced_block_is_not_an_inline_span() {
        assert!(spans("```\n`x`\n```\n").is_empty());
    }
}
