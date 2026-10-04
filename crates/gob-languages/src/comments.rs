//! The single owner of per-language comment discovery: raw comment byte spans.
//!
//! Every consumer (directive scanning in `gob-directives`, TODO001 in `frob-obligations`)
//! asks this module where the comments are and derives its own view (stripped segments,
//! whole lines) from the spans, so a lexing fix is made once.

use std::ops::Range;

use crate::{Language, ParseLimits, ParseResult, ParsedTree, hash_comment_starts, parse};

/// Visit every descendant of `root` in document order.
fn walk<'a>(root: tree_sitter::Node<'a>, f: &mut impl FnMut(tree_sitter::Node<'a>)) {
    let mut cursor = root.walk();
    loop {
        f(cursor.node());
        if cursor.goto_first_child() || cursor.goto_next_sibling() {
            continue;
        }
        loop {
            if !cursor.goto_parent() {
                return;
            }
            if cursor.goto_next_sibling() {
                break;
            }
        }
    }
}

/// Spans of the nodes of `tree` whose kind is one of `kinds`.
fn node_spans(tree: &ParsedTree, kinds: &[&str]) -> Vec<Range<usize>> {
    let mut out = Vec::new();
    walk(tree.root(), &mut |n| {
        if kinds.contains(&n.kind()) {
            out.push(n.byte_range());
        }
    });
    out
}

/// Plain-text Rust fallback: whole-line `//` comments and `/* */` regions.
fn rust_plain(text: &str) -> Vec<Range<usize>> {
    let mut out = Vec::new();
    let mut offset = 0;
    for line in text.split_inclusive('\n') {
        let lead = line.len() - line.trim_start().len();
        if line[lead..].starts_with("//") {
            let body = line[lead..].trim_end_matches(['\n', '\r']);
            out.push(offset + lead..offset + lead + body.len());
        }
        offset += line.len();
    }
    let mut from = 0;
    while let Some(p) = text[from..].find("/*") {
        let start = from + p;
        let end = text[start..]
            .find("*/")
            .map_or(text.len(), |e| start + e + 2);
        out.push(start..end);
        from = end;
    }
    out.sort_by_key(|r| r.start);
    out
}

// frob:ticket 01M43KP0RXKB1DJA8KGJTV288R
/// Byte range of a leading `---` (YAML) or `+++` (TOML) front matter block, fences included.
///
/// Front matter is data in another language, never markdown: an HTML comment inside it is a
/// string or a comment of that language, not a comment of the document. An unclosed fence is not
/// front matter.
fn front_matter(text: &str) -> Option<Range<usize>> {
    let fence = ["---", "+++"].into_iter().find(|f| {
        text.strip_prefix(f)
            .is_some_and(|r| r.trim_end_matches([' ', '\t']).starts_with(['\n', '\r']))
    })?;
    let mut pos = 0;
    for (n, line) in text.split_inclusive('\n').enumerate() {
        pos += line.len();
        if n > 0 && line.trim_end() == fence {
            return Some(0..pos);
        }
    }
    None
}

/// Code ranges of a markdown tree (empty without a tree or without the markdown grammar).
fn code_ranges(tree: Option<&ParsedTree>) -> Vec<Range<usize>> {
    #[cfg(feature = "markdown")]
    if let Some(t) = tree {
        return crate::markdown_code_ranges(t);
    }
    let _ = tree;
    Vec::new()
}

/// HTML comments of markdown `text` outside code and outside front matter, markers included.
fn markdown_spans(text: &str, tree: Option<&ParsedTree>) -> Vec<Range<usize>> {
    let mut skip = code_ranges(tree);
    skip.extend(front_matter(text));
    let mut out = Vec::new();
    let mut from = 0;
    while let Some(p) = text[from..].find("<!--") {
        let start = from + p;
        let end = text[start..]
            .find("-->")
            .map_or(text.len(), |e| start + e + 3);
        from = end;
        if skip.iter().any(|r| r.contains(&start)) {
            continue;
        }
        out.push(start..end);
    }
    out
}

/// `#` comments of a TOML, YAML or fallback-Python file, each to the end of its line.
fn hash_spans(text: &str, yaml: bool) -> Vec<Range<usize>> {
    hash_comment_starts(text, yaml)
        .into_iter()
        .map(|at| {
            let end = text[at..].find('\n').map_or(text.len(), |e| at + e);
            let line = text[at..end].trim_end_matches('\r');
            at..at + line.len()
        })
        .collect()
}

// frob:ticket 01M43A5DJT8XBQYEK36F0KSGKF
// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
/// Byte spans of every comment of `text`, markers included, in document order.
///
/// `tree` is the syntax tree of `text` when one was produced; without it each language falls
/// back to a text scan. Strings, markdown code and markdown front matter never hold comments.
pub fn comment_spans(
    language: Language,
    text: &str,
    tree: Option<&ParsedTree>,
) -> Vec<Range<usize>> {
    let found = match (language, tree) {
        (Language::Rust, Some(t)) => node_spans(t, &["line_comment", "block_comment"]),
        (Language::Rust, None) => rust_plain(text),
        (Language::Markdown, t) => markdown_spans(text, t),
        (Language::Toml, _) | (Language::Python, None) => hash_spans(text, false),
        (Language::Yaml, _) => hash_spans(text, true),
        (Language::Python, Some(t)) => node_spans(t, &["comment"]),
    };
    tracing::trace!(
        language = language.name(),
        count = found.len(),
        "comment spans"
    );
    found
}

/// Parse `text` with the default limits and return its comment spans.
///
/// TOML and YAML are text-scanned and never parsed; an unparsable file uses the text fallback.
pub fn parse_comment_spans(language: Language, text: &str) -> Vec<Range<usize>> {
    let tree = match language {
        Language::Toml | Language::Yaml => None,
        _ => match parse(language, text, &ParseLimits::default()) {
            ParseResult::Parsed(t) => Some(t),
            ParseResult::Unresolved(u) => {
                tracing::warn!(
                    language = language.name(),
                    reason = %u.reason,
                    "no syntax tree; scanning comments as plain text"
                );
                None
            }
        },
    };
    comment_spans(language, text, tree.as_ref())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The shared corpus: strings in every TOML/YAML/Python form, front matter, fenced code,
    /// HTML comments. Consumers include this to prove they see the same spans.
    pub(crate) const CORPUS: &[(Language, &str, &[&str])] = &[
        (
            Language::Toml,
            include_str!("../tests/corpus/strings.toml"),
            &["# real one", "# real two", "# real three"],
        ),
        (
            Language::Yaml,
            include_str!("../tests/corpus/strings.yaml"),
            &["# real one", "# real two"],
        ),
        (
            Language::Python,
            include_str!("../tests/corpus/strings.py"),
            &["# real one", "# real two", "# real three"],
        ),
        (
            Language::Markdown,
            include_str!("../tests/corpus/doc.md"),
            &["<!-- real one -->", "<!--\nreal two\n-->"],
        ),
    ];

    #[test]
    fn corpus_spans_are_exact() {
        for (language, text, want) in CORPUS {
            let got: Vec<&str> = parse_comment_spans(*language, text)
                .into_iter()
                .map(|r| &text[r])
                .collect();
            assert_eq!(&got, want, "{language:?}");
        }
    }

    #[test]
    fn text_fallback_agrees_on_the_corpus() {
        for (language, text, want) in CORPUS {
            let got: Vec<&str> = comment_spans(*language, text, None)
                .into_iter()
                .map(|r| &text[r])
                .collect();
            if *language == Language::Python {
                // The fallback is text-only: it cannot tell docstrings from code.
                assert!(got.len() >= want.len());
            } else if *language != Language::Markdown {
                assert_eq!(&got, want, "{language:?}");
            }
        }
    }

    #[test]
    fn rust_spans_skip_strings() {
        let src = "// a\nfn f() { let _ = \"// no\"; } /* b\n c */\n";
        let got: Vec<&str> = parse_comment_spans(Language::Rust, src)
            .into_iter()
            .map(|r| &src[r])
            .collect();
        assert_eq!(got, ["// a", "/* b\n c */"]);
    }

    #[test]
    // frob:tests crates/gob-languages/src/comments.rs::front_matter
    fn front_matter_is_not_markdown_but_a_later_html_comment_is() {
        for fence in ["---", "+++"] {
            let src = format!("{fence}\nk = \"<!-- in -->\"\n{fence}\n<!-- out -->\n");
            let got = parse_comment_spans(Language::Markdown, &src);
            assert_eq!(got.len(), 1, "fence {fence}");
            assert_eq!(&src[got[0].clone()], "<!-- out -->");
        }
        let unclosed = "---\n<!-- kept -->\n";
        assert_eq!(parse_comment_spans(Language::Markdown, unclosed).len(), 1);
        let not_first = "text\n---\n<!-- kept -->\n---\n";
        assert_eq!(parse_comment_spans(Language::Markdown, not_first).len(), 1);
    }
}
