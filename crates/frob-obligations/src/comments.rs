//! Comment discovery for TODO001: every line of comment text with its file offset.

use gob_languages::{Language, ParseLimits, ParseResult, parse};

/// One line of comment text and where it starts in the file.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct CommentLine<'t> {
    /// Byte offset of `text` in the file.
    pub(crate) offset: usize,
    /// The line, markers included (`// x`, `<!-- x`), without its newline.
    pub(crate) text: &'t str,
}

/// Push each line of `text[start..end]` as a comment line.
fn push_lines<'t>(out: &mut Vec<CommentLine<'t>>, text: &'t str, start: usize, end: usize) {
    let mut pos = start;
    for line in text[start..end].split_inclusive('\n') {
        out.push(CommentLine {
            offset: pos,
            text: line.trim_end_matches(['\n', '\r']),
        });
        pos += line.len();
    }
}

/// Byte ranges of the comment nodes of a parsed Rust file.
fn rust_ranges(text: &str) -> Option<Vec<(usize, usize)>> {
    let ParseResult::Parsed(tree) = parse(Language::Rust, text, &ParseLimits::default()) else {
        return None;
    };
    let mut out = Vec::new();
    let mut cursor = tree.root().walk();
    loop {
        let n = cursor.node();
        if matches!(n.kind(), "line_comment" | "block_comment") {
            out.push((n.start_byte(), n.end_byte()));
        }
        if cursor.goto_first_child() || cursor.goto_next_sibling() {
            continue;
        }
        loop {
            if !cursor.goto_parent() {
                return Some(out);
            }
            if cursor.goto_next_sibling() {
                break;
            }
        }
    }
}

/// Comment lines of a Rust file; whole-line `//` comments when no tree exists.
fn rust_lines(text: &str) -> Vec<CommentLine<'_>> {
    let mut out = Vec::new();
    if let Some(ranges) = rust_ranges(text) {
        for (s, e) in ranges {
            push_lines(&mut out, text, s, e);
        }
        return out;
    }
    tracing::warn!("no syntax tree; scanning whole-line comments only");
    let mut offset = 0;
    for line in text.split_inclusive('\n') {
        let lead = line.len() - line.trim_start().len();
        if line[lead..].starts_with("//") {
            push_lines(&mut out, text, offset + lead, offset + line.len());
        }
        offset += line.len();
    }
    out
}

/// True when `line` opens or closes a fenced code block; updates `fence`.
fn toggles_fence(line: &str, fence: &mut Option<char>) -> bool {
    let t = line.trim_start();
    let Some(c) = t.chars().next().filter(|c| matches!(c, '`' | '~')) else {
        return false;
    };
    if !t.starts_with(&c.to_string().repeat(3)) {
        return false;
    }
    match *fence {
        None => *fence = Some(c),
        Some(open) if open == c => *fence = None,
        Some(_) => return false,
    }
    true
}

/// HTML comment lines of a markdown file, outside fenced code.
fn markdown_lines(text: &str) -> Vec<CommentLine<'_>> {
    let mut out = Vec::new();
    let mut fence: Option<char> = None;
    let mut in_comment = false;
    let mut offset = 0;
    for line in text.split_inclusive('\n') {
        let start = offset;
        offset += line.len();
        if !in_comment && (toggles_fence(line, &mut fence) || fence.is_some()) {
            continue;
        }
        let mut pos = 0;
        loop {
            if in_comment {
                if let Some(e) = line[pos..].find("-->") {
                    push_lines(&mut out, text, start + pos, start + pos + e);
                    in_comment = false;
                    pos += e + 3;
                } else {
                    push_lines(&mut out, text, start + pos, start + line.len());
                    break;
                }
            } else if let Some(s) = line[pos..].find("<!--") {
                in_comment = true;
                pos += s + 4;
            } else {
                break;
            }
        }
    }
    out
}

/// `#` comments of a TOML file, ignoring `#` inside quotes (naive).
fn toml_lines(text: &str) -> Vec<CommentLine<'_>> {
    let mut out = Vec::new();
    let mut offset = 0;
    for line in text.split_inclusive('\n') {
        let mut quote: Option<char> = None;
        for (i, c) in line.char_indices() {
            match (quote, c) {
                (None, '"' | '\'') => quote = Some(c),
                (Some(q), c) if c == q => quote = None,
                (None, '#') => {
                    push_lines(&mut out, text, offset + i, offset + line.len());
                    break;
                }
                _ => {}
            }
        }
        offset += line.len();
    }
    out
}

/// All comment lines of `text`.
pub(crate) fn comment_lines(language: Language, text: &str) -> Vec<CommentLine<'_>> {
    let found = match language {
        Language::Rust => rust_lines(text),
        Language::Markdown => markdown_lines(text),
        Language::Toml => toml_lines(text),
    };
    tracing::trace!(
        language = language.name(),
        lines = found.len(),
        "comment lines"
    );
    found
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
    fn markdown_comments_skip_fences() {
        let src = "<!-- a -->\n```\n<!-- no -->\n```\n<!--\nb\n-->\n";
        let got = comment_lines(Language::Markdown, src);
        assert_eq!(texts(&got), [" a ", "", "b"]);
        assert_eq!(&src[got[2].offset..=got[2].offset], "b");
    }

    #[test]
    fn toml_comments_skip_quotes() {
        let src = "k = \"#no\" # yes\n# all\n";
        assert_eq!(
            texts(&comment_lines(Language::Toml, src)),
            ["# yes", "# all"]
        );
    }
}
