//! A language-agnostic token stream for the clone rule DUP001: comments, whitespace and import
//! statements are dropped, so two copies of a block compare equal across files and languages.

// frob:ticket 01M4D958QKMX7VHFJMRMAWDT22

/// What a token is, as far as clone detection cares.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Kind {
    /// A name that is not a keyword; alpha-renaming (R2) and shape (R3) abstract it.
    Ident,
    /// A reserved word shared by the supported languages; never abstracted.
    Keyword,
    /// A numeric literal; the shape rung (R3) abstracts it.
    Number,
    /// A string or character literal; the shape rung (R3) abstracts it.
    Str,
    /// One punctuation character.
    Punct,
}

/// One token with its place in the file.
#[derive(Debug, Clone, Copy)]
pub(crate) struct Tok<'a> {
    /// What the token is.
    pub kind: Kind,
    /// The token text.
    pub text: &'a str,
    /// Byte offset of the first byte.
    pub start: usize,
    /// Byte offset one past the last byte.
    pub end: usize,
    /// 1-based line of the first byte.
    pub line: u32,
}

/// Reserved words common to the supported languages; kept verbatim by the abstracting rungs.
const KEYWORDS: &[&str] = &[
    "if",
    "else",
    "elif",
    "for",
    "while",
    "loop",
    "match",
    "switch",
    "case",
    "default",
    "break",
    "continue",
    "return",
    "yield",
    "await",
    "async",
    "fn",
    "def",
    "function",
    "class",
    "struct",
    "enum",
    "trait",
    "impl",
    "interface",
    "let",
    "const",
    "var",
    "mut",
    "static",
    "pub",
    "public",
    "private",
    "protected",
    "try",
    "catch",
    "except",
    "finally",
    "throw",
    "raise",
    "new",
    "in",
    "is",
    "not",
    "and",
    "or",
    "as",
    "with",
    "lambda",
    "self",
    "this",
    "true",
    "false",
    "null",
    "none",
    "None",
    "True",
    "False",
    "void",
    "type",
    "where",
    "do",
    "unsafe",
    "extern",
    "mod",
    "pass",
    "del",
];

/// Words that open an import statement, which is skipped whole (a block of imports is not a clone).
const IMPORT_WORDS: &[&str] = &["use", "import", "from", "using"];

/// Words that may precede an import word on its line (`pub use`, `export import`).
const IMPORT_PREFIX: &[&str] = &["pub", "export"];

/// True for a byte that can start a name.
fn ident_start(c: char) -> bool {
    c == '_' || c == '$' || c.is_alphabetic()
}

/// True for a character that can continue a name.
fn ident_part(c: char) -> bool {
    c == '_' || c == '$' || c.is_alphanumeric()
}

/// Count the newlines in `s`.
fn newlines(s: &str) -> u32 {
    u32::try_from(s.bytes().filter(|&b| b == b'\n').count()).unwrap_or(u32::MAX)
}

/// The end offset of the quoted literal that opens at `at` (`text[at]` is the quote).
fn string_end(text: &str, at: usize, hash_style: bool) -> usize {
    let rest = &text[at..];
    let quote = rest.as_bytes()[0];
    let triple =
        hash_style && rest.len() >= 3 && rest.as_bytes()[1] == quote && rest.as_bytes()[2] == quote;
    let mut escaped = false;
    for (i, c) in rest.char_indices().skip(if triple { 3 } else { 1 }) {
        if escaped {
            escaped = false;
        } else if c == '\\' {
            escaped = true;
        } else if triple {
            if rest[i..].starts_with(&rest[..3]) {
                return at + i + 3;
            }
        } else if c as u32 == u32::from(quote) {
            return at + i + 1;
        } else if c == '\n' && (hash_style || quote == b'\'') {
            return at + i;
        }
    }
    text.len()
}

/// True when the `'` at `at` opens a lifetime or label (`'a`), not a character literal.
fn is_lifetime(text: &str, at: usize) -> bool {
    let mut chars = text[at + 1..].chars();
    let Some(first) = chars.next() else {
        return false;
    };
    if !ident_start(first) {
        return false;
    }
    let after = text[at + 1..]
        .char_indices()
        .find(|&(_, c)| !ident_part(c))
        .map(|(i, _)| at + 1 + i);
    after.is_none_or(|i| !text[i..].starts_with('\''))
}

/// The raw tokens of `text` (comments and whitespace dropped); `hash_style` selects `#` comments
/// and triple-quoted strings (Python) over `//` and `/* */` comments.
fn raw_tokens(text: &str, hash_style: bool) -> Vec<Tok<'_>> {
    let mut out = Vec::new();
    let mut line = 1_u32;
    let mut i = 0;
    while i < text.len() {
        let rest = &text[i..];
        let Some(c) = rest.chars().next() else {
            break;
        };
        let step = |len: usize| (i + len, newlines(&text[i..i + len]));
        if c.is_whitespace() {
            let (next, nl) = step(c.len_utf8());
            line += nl;
            i = next;
        } else if (hash_style && c == '#') || (!hash_style && rest.starts_with("//")) {
            i += rest.find('\n').unwrap_or(rest.len());
        } else if !hash_style && rest.starts_with("/*") {
            let len = rest.find("*/").map_or(rest.len(), |e| e + 2);
            let (next, nl) = step(len);
            line += nl;
            i = next;
        } else if c == '"' || c == '`' || (c == '\'' && (hash_style || !is_lifetime(text, i))) {
            let end = string_end(text, i, hash_style);
            out.push(Tok {
                kind: Kind::Str,
                text: &text[i..end],
                start: i,
                end,
                line,
            });
            line += newlines(&text[i..end]);
            i = end;
        } else if ident_start(c) {
            let len = rest.find(|ch: char| !ident_part(ch)).unwrap_or(rest.len());
            let word = &rest[..len];
            let kind = if KEYWORDS.contains(&word) {
                Kind::Keyword
            } else {
                Kind::Ident
            };
            out.push(Tok {
                kind,
                text: word,
                start: i,
                end: i + len,
                line,
            });
            i += len;
        } else if c.is_ascii_digit() {
            let mut len = 0;
            let bytes = rest.as_bytes();
            while len < bytes.len() {
                let b = bytes[len];
                let dot_digit = b == b'.' && bytes.get(len + 1).is_some_and(u8::is_ascii_digit);
                if b.is_ascii_alphanumeric() || b == b'_' || dot_digit {
                    len += 1;
                } else {
                    break;
                }
            }
            out.push(Tok {
                kind: Kind::Number,
                text: &rest[..len],
                start: i,
                end: i + len,
                line,
            });
            i += len;
        } else {
            let len = c.len_utf8();
            out.push(Tok {
                kind: Kind::Punct,
                text: &rest[..len],
                start: i,
                end: i + len,
                line,
            });
            i += len;
        }
    }
    out
}

/// True when token `i` is the first on its line.
fn at_line_start(toks: &[Tok<'_>], i: usize) -> bool {
    i == 0 || toks[i - 1].line != toks[i].line
}

/// The index of the first import word of the statement starting at token `i`, if it starts one.
fn import_start(toks: &[Tok<'_>], i: usize) -> bool {
    if !at_line_start(toks, i) {
        return false;
    }
    let mut j = i;
    while IMPORT_PREFIX.contains(&toks[j].text)
        && toks.get(j + 1).is_some_and(|t| t.line == toks[i].line)
    {
        j += 1;
    }
    IMPORT_WORDS.contains(&toks[j].text)
}

/// The token index one past the import statement that starts at `i`.
fn import_end(toks: &[Tok<'_>], i: usize) -> usize {
    let mut depth = 0_i32;
    let mut j = i;
    while j < toks.len() {
        let t = &toks[j];
        if j > i && depth <= 0 && t.line != toks[j - 1].line {
            return j;
        }
        match t.text {
            "(" | "[" | "{" if t.kind == Kind::Punct => depth += 1,
            ")" | "]" | "}" if t.kind == Kind::Punct => depth -= 1,
            ";" if depth <= 0 => return j + 1,
            _ => {}
        }
        j += 1;
    }
    j
}

/// The clone-detection tokens of `text`: comments, whitespace and import statements are dropped.
pub(crate) fn tokens(text: &str, hash_style: bool) -> Vec<Tok<'_>> {
    let raw = raw_tokens(text, hash_style);
    let mut out = Vec::with_capacity(raw.len());
    let mut i = 0;
    while i < raw.len() {
        if import_start(&raw, i) {
            let end = import_end(&raw, i);
            tracing::trace!(line = raw[i].line, "DUP001 skipped an import statement");
            i = end.max(i + 1);
        } else {
            out.push(raw[i]);
            i += 1;
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn texts(src: &str, hash: bool) -> Vec<String> {
        tokens(src, hash)
            .iter()
            .map(|t| t.text.to_owned())
            .collect()
    }

    // frob:tests crates/grimble-arch/src/dup_lex.rs::tokens
    #[test]
    fn comments_whitespace_and_imports_are_dropped() {
        let src = "use a::b;\n// note\nlet x = 1; /* gone */\nfrom m import (a,\n  b)\nx # tail\n";
        assert_eq!(texts(src, false)[..5], ["let", "x", "=", "1", ";"]);
        assert_eq!(texts("from m import (a,\n b)\nx # t\n", true), ["x"]);
    }

    // frob:tests crates/grimble-arch/src/dup_lex.rs::tokens
    #[test]
    fn lifetimes_and_strings_lex_as_expected() {
        let t = tokens("fn f<'a>(x: &'a str) -> char { 'c' }", false);
        assert!(t.iter().any(|t| t.kind == Kind::Str && t.text == "'c'"));
        assert!(t.iter().all(|t| t.text != "'a'"));
        let p = tokens("s = '''a\nb''' + \"q\\\"r\"\n", true);
        assert_eq!(p.iter().filter(|t| t.kind == Kind::Str).count(), 2);
        assert_eq!(p.last().map(|t| t.line), Some(2));
    }
}
