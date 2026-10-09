//! Comment discovery: comment texts split into candidate directive lines.

use std::borrow::Cow;

use gob_languages::{Language, ParsedTree, comment_spans};

/// Placeholder byte for source text elided by a line continuation.
///
/// A joined segment keeps the byte length of its source extent so offsets stay
/// valid; the lexer drops these bytes and maps token ranges back.
pub(crate) const ELIDED: char = '\0';

/// One logical comment line: its content (prefix stripped, trimmed) and file offset.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Segment<'t> {
    /// Byte offset of `text` in the file.
    pub(crate) offset: usize,
    /// Trimmed content after the comment markers.
    pub(crate) text: Cow<'t, str>,
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
            text: Cow::Borrowed(text),
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

/// True when `text` opens like a directive: `<word>:<verb>` then space or end.
fn looks_like_directive(text: &str) -> bool {
    let Some((ns, rest)) = text.split_once(':') else {
        return false;
    };
    let verb = rest.split(char::is_whitespace).next().unwrap_or("");
    crate::lex::is_word(ns, false) && crate::lex::is_word(verb, true)
}

/// The gap between two segments when `next` continues `prev` across a line break.
///
/// `prev` must end in a backslash; the gap must hold only the rest of its line
/// (blank), one newline and the next line's comment marker (`#`, `//`, `///`,
/// `//!`, a block-comment `*`).
fn continuation_gap<'s>(src: &'s str, prev: &Segment<'_>, next: &Segment<'_>) -> Option<&'s str> {
    if !prev.text.ends_with('\\') || !looks_like_directive(&prev.text) {
        return None;
    }
    let gap = src.get(prev.offset + prev.text.len()..next.offset)?;
    let (before, after) = gap.split_once('\n')?;
    let marker_only = after
        .chars()
        .all(|c| c.is_whitespace() && c != '\n' || "#/!*".contains(c));
    (before.trim().is_empty() && marker_only).then_some(gap)
}

/// Join directive lines ended by `\` with the comment line that follows (v1 wrapping).
///
/// The backslash, newline and next marker become [`ELIDED`] bytes, so the text
/// joins directly (a break may fall mid-token) and every offset still maps.
fn join_continuations<'t>(src: &'t str, segs: Vec<Segment<'t>>) -> Vec<Segment<'t>> {
    let mut out: Vec<Segment<'t>> = Vec::with_capacity(segs.len());
    for seg in segs {
        let gap = out
            .last()
            .and_then(|prev| continuation_gap(src, prev, &seg));
        if let (Some(gap), Some(prev)) = (gap, out.last_mut()) {
            let mut joined = String::with_capacity(prev.text.len() + gap.len() + seg.text.len());
            joined.push_str(&prev.text[..prev.text.len() - 1]);
            joined.extend(std::iter::repeat_n(ELIDED, 1 + gap.len()));
            joined.push_str(&seg.text);
            tracing::debug!(offset = prev.offset, "directive continuation joined");
            prev.text = Cow::Owned(joined);
        } else {
            out.push(seg);
        }
    }
    out
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
    let out = join_continuations(text, out);
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
        v.iter().map(|s| s.text.to_string()).collect()
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
    fn continuation_joins_hash_slash_and_block_lines() {
        let hash = "# frob:tests a::te\\\n# st kind=\"unit\"\n";
        let s = segs(Language::Python, hash);
        assert_eq!(s.len(), 1);
        assert_eq!(
            s[0].text.replace(ELIDED, ""),
            "frob:tests a::test kind=\"unit\""
        );
        assert_eq!(s[0].text.len(), hash.trim_end().len() - 2);
        let slash = "// frob:tests a::t \\\n// kind=\"unit\"\n";
        assert_eq!(segs(Language::Rust, slash).len(), 1);
        let block = "/* frob:tests a::t \\\n * kind=\"unit\" */\n";
        assert_eq!(segs(Language::Rust, block).len(), 1);
        let prose = "# note \\\n# frob:ticket X\n";
        assert_eq!(segs(Language::Python, prose).len(), 2);
        let closed = "/* frob:tests a \\ */\n// next\n";
        assert_eq!(segs(Language::Rust, closed).len(), 2);
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
                Language::CSharp,
                include_str!("../../gob-languages/tests/corpus/strings.cs"),
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
