//! Comment discovery for TODO001: every line of comment text with its file offset.
//!
//! The comments themselves come from `gob_languages::parse_comment_spans`, the one owner of
//! per-language comment discovery; this module only cuts the spans into lines.

use gob_languages::{Language, parse_comment_spans};

/// One line of comment text and where it starts in the file.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct CommentLine<'t> {
    /// Byte offset of `text` in the file.
    pub(crate) offset: usize,
    /// The line, markers included (`// x`, `<!-- x`), without its newline.
    pub(crate) text: &'t str,
}

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
// frob:ticket 01M43PEZ2CNVTHKJGPR02G4F97
/// All comment lines of `text`.
pub(crate) fn comment_lines(language: Language, text: &str) -> Vec<CommentLine<'_>> {
    let mut out = Vec::new();
    for span in parse_comment_spans(language, text) {
        let mut pos = span.start;
        for line in text[span].split_inclusive('\n') {
            out.push(CommentLine {
                offset: pos,
                text: line.trim_end_matches(['\n', '\r']),
            });
            pos += line.len();
        }
    }
    tracing::trace!(
        language = language.name(),
        lines = out.len(),
        "comment lines"
    );
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn texts(v: &[CommentLine<'_>]) -> Vec<String> {
        v.iter().map(|l| l.text.to_owned()).collect()
    }

    #[test]
    fn rust_comments_skip_strings() {
        let src = "// a\nfn f() { let _ = \"// no\"; } /* b\n c */\n";
        assert_eq!(
            texts(&comment_lines(Language::Rust, src)),
            ["// a", "/* b", " c */"]
        );
    }

    #[test]
    fn markdown_lines_keep_markers_and_offsets() {
        let src = "<!-- a -->\n```\n<!-- no -->\n```\n<!--\nb\n-->\n";
        let got = comment_lines(Language::Markdown, src);
        assert_eq!(texts(&got), ["<!-- a -->", "<!--", "b", "-->"]);
        assert_eq!(&src[got[2].offset..=got[2].offset], "b");
    }

    /// The lines are exactly the shared corpus spans cut at newlines.
    // frob:tests crates/frob-obligations/src/comments.rs::comment_lines
    #[test]
    fn lines_cover_exactly_the_shared_corpus_spans() {
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
            let want: Vec<&str> = parse_comment_spans(language, text)
                .into_iter()
                .flat_map(|r| text[r].lines().collect::<Vec<_>>())
                .collect();
            let got = comment_lines(language, text);
            assert_eq!(texts(&got), want, "{language:?}");
            for l in &got {
                assert_eq!(&text[l.offset..l.offset + l.text.len()], l.text);
            }
        }
    }

    /// A C# `///` doc line carries its marker text and offset, string contents never appear.
    // frob:tests crates/frob-obligations/src/comments.rs::comment_lines
    #[test]
    fn csharp_doc_lines_and_strings() {
        let src = "var s = \"// TODO no\";\n/// TODO yes\nvoid M() {}\n";
        let got = comment_lines(Language::CSharp, src);
        assert_eq!(texts(&got), ["/// TODO yes"]);
        assert_eq!(&src[got[0].offset..got[0].offset + 3], "///");
    }
}
