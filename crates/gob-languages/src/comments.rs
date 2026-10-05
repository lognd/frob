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

// frob:ticket 01M44YQSHSC4N13E98FN2HND27
/// Lexer state for the plain-text C# comment scan.
struct CsLexer<'t> {
    /// The source bytes (delimiters are ASCII, so byte scanning is UTF-8 safe).
    b: &'t [u8],
    /// Current byte offset.
    i: usize,
    /// Comments found so far.
    out: Vec<Range<usize>>,
}

impl CsLexer<'_> {
    /// Byte at `at`, or 0 past the end.
    fn at(&self, at: usize) -> u8 {
        self.b.get(at).copied().unwrap_or(0)
    }

    /// Length of the run of `c` starting at `from`.
    fn run(&self, from: usize, c: u8) -> usize {
        self.b[from.min(self.b.len())..]
            .iter()
            .take_while(|&&x| x == c)
            .count()
    }

    /// Consume a `//` comment to the end of its line (newline excluded).
    fn line_comment(&mut self) {
        let start = self.i;
        while self.i < self.b.len() && !matches!(self.b[self.i], b'\n' | b'\r') {
            self.i += 1;
        }
        self.out.push(start..self.i);
    }

    /// Consume a `/* */` comment (unterminated runs to the end of the file).
    fn block_comment(&mut self) {
        let start = self.i;
        self.i += 2;
        while self.i < self.b.len() && !(self.b[self.i] == b'*' && self.at(self.i + 1) == b'/') {
            self.i += 1;
        }
        self.i = (self.i + 2).min(self.b.len());
        self.out.push(start..self.i);
    }

    /// Consume a character literal (`'x'`, `'\''`, `'"'`) on one line.
    fn char_literal(&mut self) {
        self.i += 1;
        while self.i < self.b.len() {
            match self.b[self.i] {
                b'\\' => self.i += 2,
                b'\'' => {
                    self.i += 1;
                    return;
                }
                b'\n' => return,
                _ => self.i += 1,
            }
        }
    }

    /// If a string literal starts at `self.i` (`"`, `@"`, `$"`, `$@"`, `@$"`, `$$"""`),
    /// return `(dollars, verbatim, offset of the first quote)`.
    fn string_start(&self) -> Option<(usize, bool, usize)> {
        let (mut p, mut dollars, mut verbatim) = (self.i, 0, false);
        loop {
            match self.at(p) {
                b'$' => dollars += 1,
                b'@' => verbatim = true,
                b'"' => return Some((dollars, verbatim, p)),
                _ => return None,
            }
            p += 1;
        }
    }

    /// Consume the string literal described by [`Self::string_start`], holes included.
    fn string(&mut self, dollars: usize, verbatim: bool, quote: usize) {
        let quotes = self.run(quote, b'"');
        if quotes >= 3 && !verbatim {
            self.i = quote + quotes;
            self.raw_string(dollars, quotes);
            return;
        }
        self.i = quote + 1;
        while self.i < self.b.len() {
            match self.b[self.i] {
                b'\\' if !verbatim => self.i += 2,
                b'"' if verbatim && self.at(self.i + 1) == b'"' => self.i += 2,
                b'"' => {
                    self.i += 1;
                    return;
                }
                b'\n' if !verbatim => return,
                b'{' if dollars > 0 => {
                    if self.at(self.i + 1) == b'{' {
                        self.i += 2;
                    } else {
                        self.i += 1;
                        self.code(true);
                    }
                }
                _ => self.i += 1,
            }
        }
    }

    /// Consume a raw string body whose delimiter is `quotes` quotes; `dollars` opens holes.
    fn raw_string(&mut self, dollars: usize, quotes: usize) {
        while self.i < self.b.len() {
            match self.b[self.i] {
                b'"' => {
                    let n = self.run(self.i, b'"');
                    self.i += n;
                    if n >= quotes {
                        return;
                    }
                }
                b'{' if dollars > 0 => {
                    let n = self.run(self.i, b'{');
                    self.i += n;
                    if n >= dollars {
                        self.code(true);
                    }
                }
                _ => self.i += 1,
            }
        }
    }

    /// Lex code; with `hole` set, stop after the `}` that closes an interpolation hole.
    fn code(&mut self, hole: bool) {
        let mut depth = 0usize;
        let mut bol = !hole;
        while self.i < self.b.len() {
            let c = self.b[self.i];
            match c {
                b'/' if self.at(self.i + 1) == b'/' => self.line_comment(),
                b'/' if self.at(self.i + 1) == b'*' => self.block_comment(),
                b'\'' => self.char_literal(),
                b'"' | b'$' | b'@' => {
                    if let Some((dollars, verbatim, quote)) = self.string_start() {
                        self.string(dollars, verbatim, quote);
                    } else {
                        self.i += 1;
                    }
                }
                b'#' if bol => self.preprocessor(),
                b'{' => {
                    depth += 1;
                    self.i += 1;
                }
                b'}' => {
                    self.i += 1;
                    if hole && depth == 0 {
                        return;
                    }
                    depth = depth.saturating_sub(1);
                }
                _ => self.i += 1,
            }
            if self.i > 0 && self.i <= self.b.len() {
                let last = self.b[self.i - 1];
                bol = last == b'\n' || (bol && matches!(last, b' ' | b'\t' | b'\r'));
            }
        }
    }

    /// Skip a preprocessor line (`#if`, `#region it's`): not a comment, quotes are plain text,
    /// but a trailing `//` comment on it is still a comment.
    fn preprocessor(&mut self) {
        while self.i < self.b.len() && !matches!(self.b[self.i], b'\n' | b'\r') {
            if self.b[self.i] == b'/' && self.at(self.i + 1) == b'/' {
                self.line_comment();
                return;
            }
            self.i += 1;
        }
    }
}

/// Plain-text C# fallback: string-aware scan for `//`, `///` and `/* */` comments.
///
/// Regular, verbatim (`@"..."`), interpolated (`$"..."`, holes included) and raw (`"""..."""`)
/// strings and character literals never yield comments; preprocessor lines are skipped.
fn csharp_plain(text: &str) -> Vec<Range<usize>> {
    let mut lexer = CsLexer {
        b: text.as_bytes(),
        i: 0,
        out: Vec::new(),
    };
    lexer.code(false);
    lexer.out
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
        (Language::Python | Language::CSharp, Some(t)) => node_spans(t, &["comment"]),
        (Language::CSharp, None) => csharp_plain(text),
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
            Language::CSharp,
            include_str!("../tests/corpus/strings.cs"),
            &[
                "/// <summary>TODO real xml doc</summary>",
                "// real one",
                "// real two",
                "// real three",
                "/* real four */",
            ],
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
    // frob:tests crates/gob-languages/src/comments.rs::csharp_plain
    fn csharp_block_and_doc_forms_and_unterminated_strings() {
        let src = "/** doc\n * x */\nclass A { string s = \"open // no\n; } // yes\n";
        let want = ["/** doc\n * x */", "// yes"];
        for tree in [true, false] {
            let got: Vec<&str> = if tree {
                parse_comment_spans(Language::CSharp, src)
            } else {
                comment_spans(Language::CSharp, src, None)
            }
            .into_iter()
            .map(|r| &src[r])
            .collect();
            assert_eq!(got, want, "tree={tree}");
        }
    }

    #[test]
    // frob:tests crates/gob-languages/src/parse.rs::parse
    fn csharp_syntax_error_is_a_partial_tree_with_errors() {
        let src = "class A { void M( { // c\n";
        let ParseResult::Parsed(t) = parse(Language::CSharp, src, &ParseLimits::default()) else {
            panic!("expected a partial tree");
        };
        assert!(t.has_errors());
        let got = comment_spans(Language::CSharp, src, Some(&t));
        assert_eq!(got.len(), 1);
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
