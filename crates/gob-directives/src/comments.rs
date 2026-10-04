//! Comment discovery: comment texts split into candidate directive lines.

use gob_languages::{Language, ParsedTree};
#[cfg(test)]
use gob_languages::{ParseLimits, ParseResult, parse};

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

// frob:ticket 01M43A5DJT8XBQYEK36F0KSGKF
/// Comment segments of a Python file from its syntax tree (`#` inside strings is not a comment).
fn python_tree(tree: &ParsedTree) -> Vec<Segment<'_>> {
    let mut out = Vec::new();
    let text: &str = &tree.text;
    walk(tree.root(), &mut |n| {
        if n.kind() == "comment" {
            let raw = &text[n.byte_range()];
            let body = raw.trim_start_matches('#');
            let skip = raw.len() - body.len();
            push(
                &mut out,
                n.start_byte() + skip,
                body.trim_end_matches(['\n', '\r']),
                false,
            );
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

/// Push the `#` comment starting at byte `at` of `line` (file offset of the line is `offset`).
fn push_hash<'t>(out: &mut Vec<Segment<'t>>, line: &'t str, at: usize, offset: usize) {
    let body = line[at..].trim_start_matches('#');
    let skip = line.len() - at - body.len();
    push(
        out,
        offset + at + skip,
        body.trim_end_matches(['\n', '\r']),
        false,
    );
}

/// Lexer state carried across lines by [`hash_comments`].
#[derive(Clone, Copy, PartialEq, Eq)]
enum Str {
    /// Outside any string.
    None,
    /// Inside a quoted string (`"` or `'`); `multi` strings span lines.
    Quoted { quote: u8, multi: bool },
    /// Inside a YAML block scalar whose content is indented deeper than `parent`.
    Block { parent: usize },
}

/// True when `rest` (text after a block-scalar indicator) is only header modifiers and a comment.
fn block_header_tail(rest: &str) -> bool {
    let t = rest.trim_start_matches(|c: char| c == '+' || c == '-' || c.is_ascii_digit());
    let t = t.trim_start();
    t.is_empty() || t.starts_with('#')
}

// frob:ticket 01M43HGBQ9YS0Z8YPKQ41MBK6Q
/// `#` comments of a TOML, YAML or fallback-Python file, lexing strings so quoted `#` is text.
///
/// TOML: basic, literal, multi-line basic and multi-line literal strings (escapes honoured).
/// YAML: quoted scalars (also multi-line), block scalars (`|`, `>`), and `#` only after whitespace.
fn hash_comments(text: &str, yaml: bool) -> Vec<Segment<'_>> {
    let mut out = Vec::new();
    let mut offset = 0;
    let mut state = Str::None;
    for line in text.split_inclusive('\n') {
        let b = line.as_bytes();
        let indent = line.len() - line.trim_start().len();
        if let Str::Block { parent } = state {
            if line.trim().is_empty() || indent > parent {
                offset += line.len();
                continue;
            }
            state = Str::None;
        }
        let mut i = 0;
        while i < b.len() {
            match state {
                Str::Block { .. } => {
                    // Rest of the header line: only modifiers and an optional comment.
                    if let Some(h) = line[i..].find('#') {
                        let at = i + h;
                        push_hash(&mut out, line, at, offset);
                    }
                    break;
                }
                Str::None => match b[i] {
                    q @ (b'"' | b'\'') => {
                        let value_start = !yaml
                            || i == 0
                            || matches!(b[i - 1], b' ' | b'\t' | b'[' | b'{' | b',' | b':');
                        if value_start {
                            let triple = !yaml && b[i..].starts_with(&[q, q, q]);
                            state = Str::Quoted {
                                quote: q,
                                multi: triple,
                            };
                            i += if triple { 3 } else { 1 };
                            continue;
                        }
                    }
                    b'|' | b'>'
                        if yaml
                            && (i == 0 || matches!(b[i - 1], b' ' | b'\t'))
                            && block_header_tail(&line[i + 1..]) =>
                    {
                        state = Str::Block { parent: indent };
                    }
                    b'#' if !yaml || i == 0 || matches!(b[i - 1], b' ' | b'\t') => {
                        push_hash(&mut out, line, i, offset);
                        break;
                    }
                    _ => {}
                },
                Str::Quoted { quote, multi } => {
                    let escapes = quote == b'"';
                    if b[i] == b'\\' && escapes {
                        i += 2;
                        continue;
                    }
                    if b[i] == quote {
                        if multi {
                            if b[i..].starts_with(&[quote, quote, quote]) {
                                // A run of 3..=5 quotes closes; extras are content.
                                let run = b[i..].iter().take_while(|&&c| c == quote).count();
                                state = Str::None;
                                i += run;
                                continue;
                            }
                        } else if yaml && quote == b'\'' && b.get(i + 1) == Some(&quote) {
                            // YAML `''` is an escaped quote, not a close.
                            i += 2;
                            continue;
                        } else {
                            state = Str::None;
                        }
                    }
                }
            }
            i += 1;
        }
        // Single-line TOML strings end at the newline; YAML quoted scalars may continue.
        if let Str::Quoted { multi: false, .. } = state {
            if !yaml {
                state = Str::None;
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

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
/// All comment segments of `text`, using `tree` when one was produced.
pub(crate) fn segments<'t>(
    language: Language,
    text: &'t str,
    tree: Option<&'t ParsedTree>,
) -> Vec<Segment<'t>> {
    let found = match (language, tree) {
        (Language::Rust, Some(t)) => rust_tree(t),
        (Language::Rust, None) => rust_plain(text),
        (Language::Markdown, Some(t)) => {
            html_regions(text, &gob_languages::markdown_code_ranges(t))
        }
        (Language::Markdown, None) => html_regions(text, &[]),
        (Language::Toml, _) | (Language::Python, None) => hash_comments(text, false),
        (Language::Yaml, _) => hash_comments(text, true),
        (Language::Python, Some(t)) => python_tree(t),
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
    // frob:tests crates/gob-directives/src/comments.rs::python_tree
    fn python_comments_skip_strings_and_docstrings() {
        let src = "# a\nx = \"# no\"  # yes\n\"\"\"# doc\"\"\"\n#!shebang\n";
        let ParseResult::Parsed(tree) = parse(Language::Python, src, &ParseLimits::default())
        else {
            panic!("python parses");
        };
        let s = python_tree(&tree);
        assert_eq!(texts(&s), ["a", "yes", "!shebang"]);
        assert_eq!(&src[s[1].offset..s[1].offset + 3], "yes");
    }

    #[test]
    fn html_and_hash() {
        let src = "<!-- a -->\n<!--\n b\n-->\n";
        let s = html_regions(src, &[]);
        assert_eq!(texts(&s), ["a", "b"]);
        assert_eq!(&src[s[1].offset..=s[1].offset], "b");
        let t = "k = \"#no\" # yes\n# all\n";
        let h = hash_comments(t, false);
        assert_eq!(texts(&h), ["yes", "all"]);
        assert_eq!(&t[h[0].offset..h[0].offset + 3], "yes");
    }

    #[test]
    // frob:tests crates/gob-directives/src/comments.rs::hash_comments
    fn toml_strings_hide_hash_in_every_form() {
        let cases: &[(&str, &[&str])] = &[
            ("a = \"# no\" # yes\n", &["yes"]),
            ("a = '# no' # yes\n", &["yes"]),
            ("a = \"x \\\" # no\" # yes\n", &["yes"]),
            (
                "a = \"\"\"\n# frob:doc no\n  # frob:doc no\n\"\"\" # yes\n# after\n",
                &["yes", "after"],
            ),
            ("a = '''\n# frob:doc no\n''' # yes\n", &["yes"]),
            ("a = \"\"\"\nesc \\\"\"\" # no\n\"\"\"\n# real\n", &["real"]),
            ("a = \"\"\"\nx\"\"\"\"\n# real\n", &["real"]),
            ("a = '''\nx''''\n# real\n", &["real"]),
            ("a = \"\"\"\nline \\\n# no\n\"\"\"\n# real\n", &["real"]),
            ("a = ''\n# real\n", &["real"]),
            ("a = \"\"\n# real\n", &["real"]),
            ("a = \"unterminated\n# real\n", &["real"]),
        ];
        for (src, want) in cases {
            assert_eq!(texts(&hash_comments(src, false)), *want, "{src:?}");
        }
    }

    #[test]
    // frob:tests crates/gob-directives/src/comments.rs::hash_comments
    fn yaml_strings_and_block_scalars_hide_hash() {
        let cases: &[(&str, &[&str])] = &[
            ("a: \"# no\" # yes\n", &["yes"]),
            ("a: 'it''s # no' # yes\n", &["yes"]),
            ("a: x#no # yes\n", &["yes"]),
            ("a: |\n  # no\n  # no\n# real\n", &["real"]),
            ("a: >-  # yes\n  # no\nb: 1\n", &["yes"]),
            ("a: \"two\n  # no\n  lines\" # yes\n", &["yes"]),
            ("- it's fine # yes\n", &["yes"]),
        ];
        for (src, want) in cases {
            assert_eq!(texts(&hash_comments(src, true)), *want, "{src:?}");
        }
    }
}
