//! Comment discovery: comment texts split into candidate directive lines.

use gob_languages::{Language, ParsedTree, comment_spans};

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

/// Split one `#` comment (text includes the hashes) into its segment.
fn hash_comment<'t>(out: &mut Vec<Segment<'t>>, text: &'t str, offset: usize) {
    let body = text.trim_start_matches('#');
    push(
        out,
        offset + text.len() - body.len(),
        body.trim_end_matches(['\n', '\r']),
        false,
    );
}

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
// frob:ticket 01M43PEZ2CNVTHKJGPR02G4F97
/// All comment segments of `text`, split from the spans `gob_languages::comment_spans` finds.
pub(crate) fn segments<'t>(
    language: Language,
    text: &'t str,
    tree: Option<&'t ParsedTree>,
) -> Vec<Segment<'t>> {
    let mut out = Vec::new();
    for span in comment_spans(language, text, tree) {
        let raw = &text[span.clone()];
        if raw.starts_with("//") {
            line_comment(&mut out, raw, span.start);
        } else if raw.starts_with("/*") {
            block_comment(&mut out, raw, span.start);
        } else if raw.starts_with("<!--") {
            html_comment(&mut out, raw, span.start);
        } else {
            hash_comment(&mut out, raw, span.start);
        }
    }
    tracing::trace!(
        language = language.name(),
        count = out.len(),
        "comment segments"
    );
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use gob_languages::parse_comment_spans;

    fn texts(v: &[Segment<'_>]) -> Vec<String> {
        v.iter().map(|s| s.text.to_owned()).collect()
    }

    fn segs(language: Language, src: &str) -> Vec<Segment<'_>> {
        segments(language, src, None)
    }

    #[test]
    fn line_and_doc_prefixes() {
        let src = "// a\n/// b\n//! c\n";
        let s = segs(Language::Rust, src);
        assert_eq!(texts(&s), ["a", "b", "c"]);
        assert!(s[2].inner_doc && !s[1].inner_doc);
        assert_eq!(&src[s[1].offset..=s[1].offset], "b");
    }

    #[test]
    fn block_lines() {
        let src = "/* x\n * y\n */\n";
        let s = segs(Language::Rust, src);
        assert_eq!(texts(&s), ["x", "y"]);
        assert_eq!(&src[s[1].offset..=s[1].offset], "y");
    }

    #[test]
    // frob:tests crates/gob-directives/src/comments.rs::segments
    fn html_and_hash() {
        let src = "<!-- a -->\n<!--\n b\n-->\n";
        let s = segs(Language::Markdown, src);
        assert_eq!(texts(&s), ["a", "b"]);
        assert_eq!(&src[s[1].offset..=s[1].offset], "b");
        let t = "k = \"#no\" # yes\n# all\n";
        let h = segs(Language::Toml, t);
        assert_eq!(texts(&h), ["yes", "all"]);
        assert_eq!(&t[h[0].offset..h[0].offset + 3], "yes");
    }

    /// Every segment lies inside a shared span and every non-empty span yields a segment.
    // frob:tests crates/gob-directives/src/comments.rs::segments
    #[test]
    fn segments_cover_exactly_the_shared_corpus_spans() {
        for (language, text) in [
            (
                Language::Toml,
                include_str!("../../gob-languages/tests/corpus/strings.toml"),
            ),
            (
                Language::Yaml,
                include_str!("../../gob-languages/tests/corpus/strings.yaml"),
            ),
            (
                Language::Python,
                include_str!("../../gob-languages/tests/corpus/strings.py"),
            ),
            (
                Language::Markdown,
                include_str!("../../gob-languages/tests/corpus/doc.md"),
            ),
        ] {
            let spans = parse_comment_spans(language, text);
            let tree = match gob_languages::parse(
                language,
                text,
                &gob_languages::ParseLimits::default(),
            ) {
                gob_languages::ParseResult::Parsed(t) => Some(t),
                gob_languages::ParseResult::Unresolved(_) => None,
            };
            let segs = segments(language, text, tree.as_ref());
            for s in &segs {
                assert!(
                    spans
                        .iter()
                        .any(|r| r.start <= s.offset && s.offset + s.text.len() <= r.end),
                    "{language:?}: segment {:?} outside every span",
                    s.text
                );
            }
            for r in &spans {
                assert!(
                    segs.iter().any(|s| r.start <= s.offset && s.offset < r.end),
                    "{language:?}: span {:?} has no segment",
                    &text[r.clone()]
                );
            }
        }
    }
}
