//! Comment discovery: comment texts split into candidate directive lines.

use gob_languages::{Language, ParsedTree};

/// One logical comment line: its content (prefix stripped, trimmed) and file offset.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Segment<'t> {
    /// Byte offset of `text` in the file.
    pub(crate) offset: usize,
    /// Trimmed content after the comment markers.
    pub(crate) text: &'t str,
    /// True for inner doc comments (`//!`, `/*!`) that document the container.
    pub(crate) inner_doc: bool,
}

/// Trim `s` and report the byte offset of the trimmed start within `s`.
fn trim_at(s: &str) -> (usize, &str) {
    let lead = s.len() - s.trim_start().len();
    (lead, s.trim())
}

fn push<'t>(out: &mut Vec<Segment<'t>>, offset: usize, s: &'t str, inner_doc: bool) {
    let (lead, text) = trim_at(s);
    if !text.is_empty() {
        out.push(Segment {
            offset: offset + lead,
            text,
            inner_doc,
        });
    }
}

/// Split one `//` comment node (text starts at `offset`).
fn line_comment<'t>(out: &mut Vec<Segment<'t>>, text: &'t str, offset: usize) {
    let body = &text[2..];
    let (skip, inner) = match body.chars().next() {
        Some('/') => (1, false),
        Some('!') => (1, true),
        _ => (0, false),
    };
    push(out, offset + 2 + skip, &body[skip..], inner);
}

/// Split one `/* */` comment node into per-line segments.
fn block_comment<'t>(out: &mut Vec<Segment<'t>>, text: &'t str, offset: usize) {
    let mut pos = 0;
    for (n, line) in text.split_inclusive('\n').enumerate() {
        let line_off = pos;
        pos += line.len();
        let mut s = line.trim_end_matches(['\n', '\r']);
        let mut start = 0;
        let mut inner = false;
        if n == 0 {
            s = &s[2..];
            start = 2;
            match s.chars().next() {
                Some('!') => {
                    inner = true;
                    s = &s[1..];
                    start += 1;
                }
                Some('*') if !s.starts_with("*/") => {
                    s = &s[1..];
                    start += 1;
                }
                _ => {}
            }
        } else {
            let (lead, t) = trim_at(s);
            if t.starts_with('*') && !t.starts_with("*/") {
                s = &s[lead + 1..];
                start = lead + 1;
            }
        }
        if let Some(stripped) = s.trim_end().strip_suffix("*/") {
            s = stripped;
        }
        push(out, offset + line_off + start, s, inner);
    }
}

/// Split one `<!-- -->` comment (text includes the markers) into per-line segments.
fn html_comment<'t>(out: &mut Vec<Segment<'t>>, text: &'t str, offset: usize) {
    let inner = text.strip_prefix("<!--").unwrap_or(text);
    let inner = inner.strip_suffix("-->").unwrap_or(inner);
    let mut pos = text.len() - text.strip_prefix("<!--").unwrap_or(text).len();
    for line in inner.split_inclusive('\n') {
        let l = line.trim_end_matches(['\n', '\r']);
        push(out, offset + pos, l, false);
        pos += line.len();
    }
}

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

/// Comment segments of a Rust file from its syntax tree.
fn rust_tree(tree: &ParsedTree) -> Vec<Segment<'_>> {
    let mut out = Vec::new();
    let text: &str = &tree.text;
    walk(tree.root(), &mut |n| match n.kind() {
        "line_comment" => line_comment(&mut out, &text[n.byte_range()], n.start_byte()),
        "block_comment" => block_comment(&mut out, &text[n.byte_range()], n.start_byte()),
        _ => {}
    });
    out
}

/// Byte ranges of code blocks in a markdown tree.
fn markdown_code_ranges(tree: &ParsedTree) -> Vec<std::ops::Range<usize>> {
    let mut out = Vec::new();
    walk(tree.root(), &mut |n| {
        if matches!(n.kind(), "fenced_code_block" | "indented_code_block") {
            out.push(n.byte_range());
        }
    });
    out
}

/// HTML comments in `text`, skipping those inside `skip` ranges.
fn html_regions<'t>(text: &'t str, skip: &[std::ops::Range<usize>]) -> Vec<Segment<'t>> {
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
        html_comment(&mut out, &text[start..end], start);
    }
    out
}

/// `#` comments of a TOML-like file, ignoring `#` inside quotes (naive).
fn hash_comments(text: &str) -> Vec<Segment<'_>> {
    let mut out = Vec::new();
    let mut offset = 0;
    for line in text.split_inclusive('\n') {
        let mut quote: Option<char> = None;
        for (i, c) in line.char_indices() {
            match (quote, c) {
                (None, '"' | '\'') => quote = Some(c),
                (Some(q), c) if c == q => quote = None,
                (None, '#') => {
                    let body = line[i..].trim_start_matches('#');
                    let skip = line.len() - i - body.len();
                    push(
                        &mut out,
                        offset + i + skip,
                        body.trim_end_matches(['\n', '\r']),
                        false,
                    );
                    break;
                }
                _ => {}
            }
        }
        offset += line.len();
    }
    out
}

/// Plain-text Rust fallback: whole-line `//` comments and `/* */` regions.
fn rust_plain(text: &str) -> Vec<Segment<'_>> {
    let mut out = Vec::new();
    let mut offset = 0;
    for line in text.split_inclusive('\n') {
        let lead = line.len() - line.trim_start().len();
        if line[lead..].starts_with("//") {
            let l = line[lead..].trim_end_matches(['\n', '\r']);
            line_comment(&mut out, l, offset + lead);
        }
        offset += line.len();
    }
    let mut from = 0;
    while let Some(p) = text[from..].find("/*") {
        let start = from + p;
        let end = text[start..]
            .find("*/")
            .map_or(text.len(), |e| start + e + 2);
        block_comment(&mut out, &text[start..end], start);
        from = end;
    }
    out.sort_by_key(|s| s.offset);
    out
}

/// All comment segments of `text`, using `tree` when one was produced.
pub(crate) fn segments<'t>(
    language: Language,
    text: &'t str,
    tree: Option<&'t ParsedTree>,
) -> Vec<Segment<'t>> {
    let found = match (language, tree) {
        (Language::Rust, Some(t)) => rust_tree(t),
        (Language::Rust, None) => rust_plain(text),
        (Language::Markdown, Some(t)) => html_regions(text, &markdown_code_ranges(t)),
        (Language::Markdown, None) => html_regions(text, &[]),
        (Language::Toml, _) => hash_comments(text),
    };
    tracing::trace!(
        language = language.name(),
        count = found.len(),
        "comment segments"
    );
    found
}

#[cfg(test)]
mod tests {
    use super::*;

    fn texts(v: &[Segment<'_>]) -> Vec<String> {
        v.iter().map(|s| s.text.to_owned()).collect()
    }

    #[test]
    fn line_and_doc_prefixes() {
        let src = "// a\n/// b\n//! c\n";
        let s = rust_plain(src);
        assert_eq!(texts(&s), ["a", "b", "c"]);
        assert!(s[2].inner_doc && !s[1].inner_doc);
        assert_eq!(&src[s[1].offset..=s[1].offset], "b");
    }

    #[test]
    fn block_lines() {
        let src = "/* x\n * y\n */\n";
        let s = rust_plain(src);
        assert_eq!(texts(&s), ["x", "y"]);
        assert_eq!(&src[s[1].offset..=s[1].offset], "y");
    }

    #[test]
    fn html_and_hash() {
        let src = "<!-- a -->\n<!--\n b\n-->\n";
        let s = html_regions(src, &[]);
        assert_eq!(texts(&s), ["a", "b"]);
        assert_eq!(&src[s[1].offset..=s[1].offset], "b");
        let t = "k = \"#no\" # yes\n# all\n";
        let h = hash_comments(t);
        assert_eq!(texts(&h), ["yes", "all"]);
        assert_eq!(&t[h[0].offset..h[0].offset + 3], "yes");
    }
}
