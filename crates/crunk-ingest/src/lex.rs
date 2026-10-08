//! A CSS component-value tokenizer: the token granularity the Python crunk read through tinycss2.
//!
//! The CSS adapter splits a declaration value at top-level whitespace and commas, so `1px/2px` is
//! one word there. Colors, lengths and `var()` references are located per token, which needs
//! the CSS Syntax level 3 token classes; this module is that tokenizer for already-delimited
//! text (a declaration value, a selector, an at-rule prelude). It never fails: malformed input
//! degrades to literal tokens.

// frob:ticket 01M43ARY91XZ35DN9SCHRHS033

/// The class of one component-value token.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Kind {
    Whitespace,
    Comment,
    Ident,
    /// `name(` ... `)`; [`Tok::inner`] spans the arguments.
    Function,
    Hash,
    Number,
    Percentage,
    Dimension,
    Str,
    Url,
    /// `(...)`, `[...]` or `{...}`; [`Tok::inner`] spans the contents.
    Block(char),
    AtKeyword,
    UnicodeRange,
    Literal,
}

/// One token: its class and byte range in the tokenized text.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct Tok {
    pub kind: Kind,
    pub start: usize,
    pub end: usize,
    /// Byte range of a function's arguments or a block's contents.
    pub inner: Option<(usize, usize)>,
}

impl Tok {
    /// True for tokens that carry no value (whitespace and comments).
    pub(crate) fn is_trivia(&self) -> bool {
        matches!(self.kind, Kind::Whitespace | Kind::Comment)
    }

    /// The token text.
    pub(crate) fn text<'a>(&self, src: &'a str) -> &'a str {
        &src[self.start..self.end]
    }
}

fn ident_start(c: char) -> bool {
    c.is_ascii_alphabetic() || c == '_' || !c.is_ascii()
}

fn name_char(c: char) -> bool {
    ident_start(c) || c.is_ascii_digit() || c == '-'
}

fn is_newline(c: char) -> bool {
    matches!(c, '\n' | '\r' | '\x0c')
}

struct Lexer<'a> {
    src: &'a str,
}

impl Lexer<'_> {
    fn at(&self, i: usize) -> Option<char> {
        self.src.get(i..).and_then(|s| s.chars().next())
    }

    fn valid_escape(&self, i: usize) -> bool {
        self.at(i) == Some('\\') && self.at(i + 1).is_some_and(|c| !is_newline(c))
    }

    /// Whether an identifier starts at `i`.
    fn would_start_ident(&self, i: usize) -> bool {
        match self.at(i) {
            Some('-') => {
                let n = self.at(i + 1);
                n.is_some_and(|c| ident_start(c) || c == '-') || self.valid_escape(i + 1)
            }
            Some(c) if ident_start(c) => true,
            Some('\\') => self.valid_escape(i),
            _ => false,
        }
    }

    /// Whether a number starts at `i`.
    fn would_start_number(&self, i: usize) -> bool {
        match self.at(i) {
            Some(c) if c.is_ascii_digit() => true,
            Some('+' | '-') => match self.at(i + 1) {
                Some(c) if c.is_ascii_digit() => true,
                Some('.') => self.at(i + 2).is_some_and(|c| c.is_ascii_digit()),
                _ => false,
            },
            Some('.') => self.at(i + 1).is_some_and(|c| c.is_ascii_digit()),
            _ => false,
        }
    }

    fn name_end(&self, mut i: usize) -> usize {
        while let Some(c) = self.at(i) {
            if name_char(c) {
                i += c.len_utf8();
            } else if self.valid_escape(i) {
                i = self.escape_end(i);
            } else {
                break;
            }
        }
        i
    }

    /// The end of the escape starting at the backslash at `i`: 1-6 hex digits and one optional
    /// trailing whitespace, or any single character.
    fn escape_end(&self, i: usize) -> usize {
        let mut j = i + 1;
        let mut hex = 0;
        while hex < 6 && self.at(j).is_some_and(|c| c.is_ascii_hexdigit()) {
            j += 1;
            hex += 1;
        }
        if hex == 0 {
            return j + self.at(j).map_or(0, char::len_utf8);
        }
        match self.at(j) {
            Some('\r') if self.at(j + 1) == Some('\n') => j + 2,
            Some(c) if c.is_whitespace() => j + c.len_utf8(),
            _ => j,
        }
    }

    fn digits_end(&self, mut i: usize) -> usize {
        while self.at(i).is_some_and(|c| c.is_ascii_digit()) {
            i += 1;
        }
        i
    }

    fn number_end(&self, mut i: usize) -> usize {
        if matches!(self.at(i), Some('+' | '-')) {
            i += 1;
        }
        i = self.digits_end(i);
        if self.at(i) == Some('.') && self.at(i + 1).is_some_and(|c| c.is_ascii_digit()) {
            i = self.digits_end(i + 1);
        }
        if matches!(self.at(i), Some('e' | 'E')) {
            let mut j = i + 1;
            if matches!(self.at(j), Some('+' | '-')) {
                j += 1;
            }
            if self.at(j).is_some_and(|c| c.is_ascii_digit()) {
                i = self.digits_end(j);
            }
        }
        i
    }

    fn string_end(&self, start: usize) -> usize {
        let quote = self.at(start).unwrap_or('"');
        let mut i = start + 1;
        while let Some(c) = self.at(i) {
            if c == '\\' {
                i += 1 + self.at(i + 1).map_or(0, char::len_utf8);
            } else if c == quote {
                return i + 1;
            } else if is_newline(c) {
                return i;
            } else {
                i += c.len_utf8();
            }
        }
        self.src.len()
    }

    fn comment_end(&self, start: usize) -> usize {
        self.src[start + 2..]
            .find("*/")
            .map_or(self.src.len(), |k| start + 2 + k + 2)
    }

    /// The index of the close that matches the open at `open_at`, or the end of input.
    fn block_end(&self, open_at: usize) -> (usize, usize) {
        let mut stack: Vec<char> = Vec::new();
        let mut i = open_at;
        while let Some(c) = self.at(i) {
            match c {
                '(' => stack.push(')'),
                '[' => stack.push(']'),
                '{' => stack.push('}'),
                ')' | ']' | '}' => {
                    if stack.last() == Some(&c) {
                        stack.pop();
                        if stack.is_empty() {
                            return (i, i + 1);
                        }
                    }
                }
                '"' | '\'' => {
                    i = self.string_end(i);
                    continue;
                }
                '/' if self.at(i + 1) == Some('*') => {
                    i = self.comment_end(i);
                    continue;
                }
                '\\' => {
                    i += 1 + self.at(i + 1).map_or(0, char::len_utf8);
                    continue;
                }
                _ => {}
            }
            i += c.len_utf8();
        }
        (self.src.len(), self.src.len())
    }

    fn next(&self, i: usize) -> Tok {
        let c = self.at(i).unwrap_or(' ');
        let simple = |kind, end| Tok {
            kind,
            start: i,
            end,
            inner: None,
        };
        if c.is_whitespace() {
            let mut j = i;
            while self.at(j).is_some_and(char::is_whitespace) {
                j += self.at(j).map_or(1, char::len_utf8);
            }
            return simple(Kind::Whitespace, j);
        }
        if c == '/' && self.at(i + 1) == Some('*') {
            return simple(Kind::Comment, self.comment_end(i));
        }
        if c == '"' || c == '\'' {
            return simple(Kind::Str, self.string_end(i));
        }
        if c == '#' && self.at(i + 1).is_some_and(name_char) {
            return simple(Kind::Hash, self.name_end(i + 1));
        }
        if self.would_start_number(i) {
            let end = self.number_end(i);
            if self.would_start_ident(end) {
                return simple(Kind::Dimension, self.name_end(end));
            }
            if self.at(end) == Some('%') {
                return simple(Kind::Percentage, end + 1);
            }
            return simple(Kind::Number, end);
        }
        if matches!(c, 'u' | 'U')
            && self.at(i + 1) == Some('+')
            && self
                .at(i + 2)
                .is_some_and(|n| n.is_ascii_hexdigit() || n == '?')
        {
            let mut j = i + 2;
            while self
                .at(j)
                .is_some_and(|n| n.is_ascii_hexdigit() || n == '?' || n == '-')
            {
                j += 1;
            }
            return simple(Kind::UnicodeRange, j);
        }
        if self.would_start_ident(i) {
            let end = self.name_end(i);
            if self.at(end) == Some('(') {
                let (close, after) = self.block_end(end);
                let kind = if self.src[i..end].eq_ignore_ascii_case("url") {
                    Kind::Url
                } else {
                    Kind::Function
                };
                return Tok {
                    kind,
                    start: i,
                    end: after,
                    inner: Some((end + 1, close.max(end + 1))),
                };
            }
            return simple(Kind::Ident, end);
        }
        if c == '@' && self.would_start_ident(i + 1) {
            return simple(Kind::AtKeyword, self.name_end(i + 1));
        }
        if matches!(c, '(' | '[' | '{') {
            let (close, after) = self.block_end(i);
            return Tok {
                kind: Kind::Block(c),
                start: i,
                end: after,
                inner: Some((i + 1, close.max(i + 1))),
            };
        }
        simple(Kind::Literal, i + c.len_utf8())
    }
}

/// The value of identifier text: CSS escapes resolved (`\\31 0` is `10`).
pub(crate) fn unescape(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut chars = text.chars().peekable();
    while let Some(c) = chars.next() {
        if c != '\\' {
            out.push(c);
            continue;
        }
        let mut hex = String::new();
        while hex.len() < 6 && chars.peek().is_some_and(char::is_ascii_hexdigit) {
            hex.extend(chars.next());
        }
        if hex.is_empty() {
            out.extend(chars.next());
            continue;
        }
        if chars.peek().is_some_and(|c| c.is_whitespace())
            && chars.next() == Some('\r')
            && chars.peek() == Some(&'\n')
        {
            chars.next();
        }
        let code = u32::from_str_radix(&hex, 16).unwrap_or(0xFFFD);
        out.push(
            char::from_u32(code)
                .filter(|&c| c != '\0')
                .unwrap_or('\u{FFFD}'),
        );
    }
    out
}

/// Split dimension text (`10px`, `-1.5e2rem`) into its number and unit.
pub(crate) fn split_dimension(text: &str) -> (&str, &str) {
    let end = Lexer { src: text }.number_end(0);
    text.split_at(end)
}

/// Tokenize `src` into its top-level component-value tokens.
pub(crate) fn tokenize(src: &str) -> Vec<Tok> {
    let lexer = Lexer { src };
    let mut out = Vec::new();
    let mut i = 0;
    while i < src.len() {
        let tok = lexer.next(i);
        debug_assert!(tok.end > i, "the lexer must advance");
        i = tok.end.max(i + 1);
        out.push(tok);
    }
    out
}

/// The tokens inside `tok` (a function's arguments or a block's contents), offsets absolute in `src`.
pub(crate) fn inner_tokens(src: &str, tok: &Tok) -> Vec<Tok> {
    let Some((lo, hi)) = tok.inner else {
        return Vec::new();
    };
    tokenize(&src[lo..hi])
        .into_iter()
        .map(|t| Tok {
            start: t.start + lo,
            end: t.end + lo,
            inner: t.inner.map(|(a, b)| (a + lo, b + lo)),
            ..t
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn kinds(src: &str) -> Vec<(Kind, &str)> {
        tokenize(src)
            .iter()
            .filter(|t| !t.is_trivia())
            .map(|t| (t.kind, t.text(src)))
            .collect()
    }

    // frob:tests crates/crunk-ingest/src/lex.rs::tokenize
    #[test]
    fn token_classes() {
        assert_eq!(
            kinds("1px/2px"),
            [
                (Kind::Dimension, "1px"),
                (Kind::Literal, "/"),
                (Kind::Dimension, "2px")
            ]
        );
        assert_eq!(
            kinds("-1.5e2rem 50% #fff red 0 .5"),
            [
                (Kind::Dimension, "-1.5e2rem"),
                (Kind::Percentage, "50%"),
                (Kind::Hash, "#fff"),
                (Kind::Ident, "red"),
                (Kind::Number, "0"),
                (Kind::Number, ".5")
            ]
        );
        assert_eq!(
            kinds("--x var(--a, 1px) rgb(0 0 0 / 50%)"),
            [
                (Kind::Ident, "--x"),
                (Kind::Function, "var(--a, 1px)"),
                (Kind::Function, "rgb(0 0 0 / 50%)")
            ]
        );
        assert_eq!(
            kinds("url(a.png) \"s;\" (a:b) U+0025-00FF"),
            [
                (Kind::Url, "url(a.png)"),
                (Kind::Str, "\"s;\""),
                (Kind::Block('('), "(a:b)"),
                (Kind::UnicodeRange, "U+0025-00FF")
            ]
        );
    }

    // frob:tests crates/crunk-ingest/src/lex.rs::split_dimension
    #[test]
    fn dimensions_split_into_number_and_unit() {
        assert_eq!(split_dimension("10px"), ("10", "px"));
        assert_eq!(split_dimension("-1.5e2rem"), ("-1.5e2", "rem"));
        assert_eq!(split_dimension("1em"), ("1", "em"));
    }

    // frob:tests crates/crunk-ingest/src/lex.rs::unescape
    #[test]
    fn escapes_resolve() {
        assert_eq!(unescape("\\31 0"), "10");
        assert_eq!(unescape("a\\:b"), "a:b");
        assert_eq!(unescape("plain"), "plain");
        assert_eq!(unescape("\\e9x"), "\u{e9}x");
    }

    // frob:tests crates/crunk-ingest/src/lex.rs::inner_tokens
    #[test]
    fn inner_tokens_are_absolute() {
        let src = "x var(--a)";
        let f = tokenize(src)
            .into_iter()
            .find(|t| t.kind == Kind::Function)
            .unwrap();
        let inner = inner_tokens(src, &f);
        assert_eq!(inner[0].text(src), "--a");
    }
}
