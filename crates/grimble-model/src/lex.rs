//! The hand-written lexer (grmb-spec 2): tokens, comments and lexical diagnostics.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

use crate::span::{Diagnostic, Span};

/// Punctuation tokens (grmb-spec 2.2).
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Punct {
    /// `{`
    LBrace,
    /// `}`
    RBrace,
    /// `(`
    LParen,
    /// `)`
    RParen,
    /// `[`
    LBracket,
    /// `]`
    RBracket,
    /// `;`
    Semi,
    /// `,`
    Comma,
    /// `:`
    Colon,
    /// `::`
    ColonColon,
    /// `.`
    Dot,
    /// `=`
    Eq,
    /// `->`
    Arrow,
    /// `<=`
    Le,
    /// `&`
    Amp,
    /// `|`
    Pipe,
    /// `!`
    Bang,
    /// `~`
    Tilde,
    /// `!=`
    Ne,
}

impl Punct {
    /// The spelling of the token.
    pub const fn text(self) -> &'static str {
        match self {
            Self::LBrace => "{",
            Self::RBrace => "}",
            Self::LParen => "(",
            Self::RParen => ")",
            Self::LBracket => "[",
            Self::RBracket => "]",
            Self::Semi => ";",
            Self::Comma => ",",
            Self::Colon => ":",
            Self::ColonColon => "::",
            Self::Dot => ".",
            Self::Eq => "=",
            Self::Arrow => "->",
            Self::Le => "<=",
            Self::Amp => "&",
            Self::Pipe => "|",
            Self::Bang => "!",
            Self::Tilde => "~",
            Self::Ne => "!=",
        }
    }
}

/// A token kind.
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum Tok {
    /// An identifier or keyword.
    Ident(String),
    /// A number, as written.
    Number(String),
    /// A number with its (unchecked) unit lexeme.
    Quantity {
        /// The number, as written.
        number: String,
        /// The unit lexeme, as written.
        unit: String,
    },
    /// A date lexeme `YYYY-MM-DD` (calendar validity is checked later).
    Date(String),
    /// A string with escapes resolved.
    Str(String),
    /// Punctuation.
    P(Punct),
    /// End of input.
    Eof,
    /// A lexical error already reported; skipped by the parser.
    Bad,
}

impl Tok {
    /// A short description for messages.
    pub fn describe(&self) -> String {
        match self {
            Self::Ident(s) => format!("`{s}`"),
            Self::Number(s) => format!("number `{s}`"),
            Self::Quantity { number, unit } => format!("quantity `{number} {unit}`"),
            Self::Date(s) => format!("date `{s}`"),
            Self::Str(_) => "a string".to_owned(),
            Self::P(p) => format!("`{}`", p.text()),
            Self::Eof => "end of file".to_owned(),
            Self::Bad => "an invalid token".to_owned(),
        }
    }
}

/// A token with its span.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Token {
    /// The kind.
    pub tok: Tok,
    /// Where it is.
    pub span: Span,
}

/// The three comment forms (grmb-spec 2.3).
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum CommentKind {
    /// `// text`
    Line,
    /// `/// text`
    Doc,
    /// `/* text */`
    Block,
}

/// A comment, kept verbatim for trivia.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Comment {
    /// Which form.
    pub kind: CommentKind,
    /// The full lexeme including delimiters, without a trailing newline.
    pub text: String,
    /// Where it is.
    pub span: Span,
}

impl Comment {
    /// The prose of a doc comment: after `///`, one leading space removed.
    pub fn doc_text(&self) -> &str {
        let t = self.text.strip_prefix("///").unwrap_or(&self.text);
        t.strip_prefix(' ').unwrap_or(t)
    }
}

/// The output of [`lex`].
#[derive(Clone, Debug, Default)]
pub struct Lexed {
    /// Tokens, ending with [`Tok::Eof`].
    pub tokens: Vec<Token>,
    /// Comments in source order (never in the token stream).
    pub comments: Vec<Comment>,
    /// Lexical diagnostics (all MDL000).
    pub diags: Vec<Diagnostic>,
}

struct Lexer<'a> {
    src: &'a str,
    bytes: &'a [u8],
    pos: usize,
    out: Lexed,
}

/// Lexes `src`, which must already be known to be valid UTF-8 without BOM, NUL or bare CR.
pub fn lex(src: &str) -> Lexed {
    let mut lx = Lexer {
        src,
        bytes: src.as_bytes(),
        pos: 0,
        out: Lexed::default(),
    };
    lx.run();
    tracing::trace!(
        tokens = lx.out.tokens.len(),
        comments = lx.out.comments.len(),
        diags = lx.out.diags.len(),
        "lexed"
    );
    lx.out
}

fn is_ident_start(b: u8) -> bool {
    b.is_ascii_alphabetic() || b == b'_'
}

fn is_ident_cont(b: u8) -> bool {
    b.is_ascii_alphanumeric() || b == b'_'
}

impl Lexer<'_> {
    fn peek(&self, off: usize) -> Option<u8> {
        self.bytes.get(self.pos + off).copied()
    }

    fn push(&mut self, tok: Tok, start: usize) {
        self.out.tokens.push(Token {
            tok,
            span: Span::new(start, self.pos),
        });
    }

    fn error(&mut self, span: Span, msg: impl Into<String>) {
        self.out.diags.push(Diagnostic::new("MDL000", span, msg));
        self.out.tokens.push(Token {
            tok: Tok::Bad,
            span,
        });
    }

    fn run(&mut self) {
        while let Some(b) = self.peek(0) {
            match b {
                b' ' | b'\t' | b'\n' | b'\r' => self.pos += 1,
                b'/' if self.peek(1) == Some(b'/') => self.line_comment(),
                b'/' if self.peek(1) == Some(b'*') => self.block_comment(),
                b'"' => self.string(),
                b if b.is_ascii_digit() => self.number(),
                b if is_ident_start(b) => self.ident(),
                _ => self.punct(),
            }
        }
        let end = self.src.len();
        self.out.tokens.push(Token {
            tok: Tok::Eof,
            span: Span::new(end, end),
        });
    }

    fn line_comment(&mut self) {
        let start = self.pos;
        while let Some(b) = self.peek(0) {
            if b == b'\n' {
                break;
            }
            self.pos += 1;
        }
        let text = self.src[start..self.pos].trim_end_matches('\r').to_owned();
        let kind = if text.starts_with("///") && !text.starts_with("////") {
            CommentKind::Doc
        } else {
            CommentKind::Line
        };
        self.out.comments.push(Comment {
            kind,
            text,
            span: Span::new(start, self.pos),
        });
    }

    fn block_comment(&mut self) {
        let start = self.pos;
        let mut depth = 0usize;
        let mut closed = false;
        while self.pos < self.bytes.len() {
            if self.bytes[self.pos] == b'/' && self.peek(1) == Some(b'*') {
                depth += 1;
                self.pos += 2;
            } else if self.bytes[self.pos] == b'*' && self.peek(1) == Some(b'/') {
                depth -= 1;
                self.pos += 2;
                if depth == 0 {
                    closed = true;
                    break;
                }
            } else {
                self.pos += 1;
            }
        }
        let span = Span::new(start, self.pos);
        if !closed {
            self.out.diags.push(Diagnostic::new(
                "MDL000",
                span,
                "unterminated block comment",
            ));
        }
        self.out.comments.push(Comment {
            kind: CommentKind::Block,
            text: self.src[start..self.pos].replace("\r\n", "\n"),
            span,
        });
    }

    fn ident(&mut self) {
        let start = self.pos;
        while self.peek(0).is_some_and(is_ident_cont) {
            self.pos += 1;
        }
        let text = self.src[start..self.pos].to_owned();
        self.push(Tok::Ident(text), start);
    }

    fn digits(&mut self) -> usize {
        let from = self.pos;
        while self.peek(0).is_some_and(|b| b.is_ascii_digit()) {
            self.pos += 1;
        }
        self.pos - from
    }

    fn number(&mut self) {
        let start = self.pos;
        let first = self.digits();
        if first == 4
            && self.peek(0) == Some(b'-')
            && self.peek(1).is_some_and(|b| b.is_ascii_digit())
        {
            let save = self.pos;
            self.pos += 1;
            let m = self.digits();
            if m == 2 && self.peek(0) == Some(b'-') {
                self.pos += 1;
                let d = self.digits();
                if d == 2 {
                    let text = self.src[start..self.pos].to_owned();
                    self.push(Tok::Date(text), start);
                    return;
                }
            }
            self.pos = save;
        }
        if self.peek(0) == Some(b'.') && self.peek(1).is_some_and(|b| b.is_ascii_digit()) {
            self.pos += 1;
            self.digits();
        }
        let number = self.src[start..self.pos].to_owned();
        let mut look = self.pos;
        while matches!(self.bytes.get(look), Some(b' ' | b'\t')) {
            look += 1;
        }
        let unit_start = look;
        let ustart = self.bytes.get(look).copied();
        if ustart == Some(b'%') {
            look += 1;
        } else if ustart.is_some_and(|b| b.is_ascii_alphabetic()) {
            while self.bytes.get(look).is_some_and(u8::is_ascii_alphabetic) {
                look += 1;
            }
        } else {
            self.push(Tok::Number(number), start);
            return;
        }
        if self.bytes.get(look) == Some(&b'/')
            && self
                .bytes
                .get(look + 1)
                .is_some_and(u8::is_ascii_alphabetic)
        {
            look += 1;
            while self.bytes.get(look).is_some_and(u8::is_ascii_alphabetic) {
                look += 1;
            }
        }
        let unit = self.src[unit_start..look].to_owned();
        self.pos = look;
        self.push(Tok::Quantity { number, unit }, start);
    }

    fn string(&mut self) {
        let start = self.pos;
        self.pos += 1;
        let mut value = String::new();
        while let Some(rest) = self.src.get(self.pos..) {
            let Some(c) = rest.chars().next() else {
                let span = Span::new(start, self.pos);
                self.error(span, "unterminated string");
                return;
            };
            self.pos += c.len_utf8();
            match c {
                '"' => {
                    self.push(Tok::Str(value), start);
                    return;
                }
                '\n' | '\r' => {
                    let span = Span::new(start, self.pos - 1);
                    self.pos -= 1;
                    self.error(span, "a string contains no raw newline");
                    return;
                }
                '\\' => {
                    if let Some(ch) = self.escape() {
                        value.push(ch);
                    }
                }
                c => value.push(c),
            }
        }
        let span = Span::new(start, self.pos);
        self.error(span, "unterminated string");
    }

    fn escape(&mut self) -> Option<char> {
        let esc_start = self.pos - 1;
        let c = self.src.get(self.pos..)?.chars().next()?;
        self.pos += c.len_utf8();
        match c {
            '"' => Some('"'),
            '\\' => Some('\\'),
            'n' => Some('\n'),
            't' => Some('\t'),
            'r' => Some('\r'),
            'u' if self.peek(0) == Some(b'{') => {
                let hex_start = self.pos + 1;
                let mut look = hex_start;
                while self.bytes.get(look).is_some_and(u8::is_ascii_hexdigit) {
                    look += 1;
                }
                let ok = look > hex_start && self.bytes.get(look) == Some(&b'}');
                let ch = ok
                    .then(|| u32::from_str_radix(&self.src[hex_start..look], 16).ok())
                    .flatten()
                    .and_then(char::from_u32);
                if ok {
                    self.pos = look + 1;
                }
                if ch.is_none() {
                    self.out.diags.push(Diagnostic::new(
                        "MDL000",
                        Span::new(esc_start, self.pos),
                        "invalid unicode escape",
                    ));
                }
                ch
            }
            _ => {
                self.out.diags.push(Diagnostic::new(
                    "MDL000",
                    Span::new(esc_start, self.pos),
                    format!("unknown escape `\\{c}`"),
                ));
                None
            }
        }
    }

    fn punct(&mut self) {
        let start = self.pos;
        let b = self.bytes[self.pos];
        let two = (b, self.peek(1));
        let (p, len) = match two {
            (b':', Some(b':')) => (Punct::ColonColon, 2),
            (b'-', Some(b'>')) => (Punct::Arrow, 2),
            (b'<', Some(b'=')) => (Punct::Le, 2),
            (b'!', Some(b'=')) => (Punct::Ne, 2),
            (b'{', _) => (Punct::LBrace, 1),
            (b'}', _) => (Punct::RBrace, 1),
            (b'(', _) => (Punct::LParen, 1),
            (b')', _) => (Punct::RParen, 1),
            (b'[', _) => (Punct::LBracket, 1),
            (b']', _) => (Punct::RBracket, 1),
            (b';', _) => (Punct::Semi, 1),
            (b',', _) => (Punct::Comma, 1),
            (b':', _) => (Punct::Colon, 1),
            (b'.', _) => (Punct::Dot, 1),
            (b'=', _) => (Punct::Eq, 1),
            (b'&', _) => (Punct::Amp, 1),
            (b'|', _) => (Punct::Pipe, 1),
            (b'!', _) => (Punct::Bang, 1),
            (b'~', _) => (Punct::Tilde, 1),
            _ => {
                let c = self.src[self.pos..].chars().next().unwrap_or('?');
                self.pos += c.len_utf8();
                let msg = if c.is_ascii() {
                    format!("unexpected character `{c}`")
                } else {
                    "identifiers and punctuation are ASCII; non-ASCII text belongs in strings and comments"
                        .to_owned()
                };
                self.error(Span::new(start, self.pos), msg);
                return;
            }
        };
        self.pos += len;
        self.push(Tok::P(p), start);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn toks(s: &str) -> Vec<Tok> {
        lex(s).tokens.into_iter().map(|t| t.tok).collect()
    }

    #[test]
    fn quantities_dates_and_strings() {
        assert_eq!(
            toks("30 s 5req/s 15 %/d 2026-12-01 \"a\\n\\u{41}\""),
            vec![
                Tok::Quantity {
                    number: "30".into(),
                    unit: "s".into()
                },
                Tok::Quantity {
                    number: "5".into(),
                    unit: "req/s".into()
                },
                Tok::Quantity {
                    number: "15".into(),
                    unit: "%/d".into()
                },
                Tok::Date("2026-12-01".into()),
                Tok::Str("a\nA".into()),
                Tok::Eof
            ]
        );
    }

    #[test]
    fn comments_nest_and_leave_the_token_stream() {
        let l = lex("a /* x /* y */ z */ b // c\n/// d\n");
        assert_eq!(l.tokens.len(), 3);
        assert_eq!(l.comments.len(), 3);
        assert_eq!(l.comments[2].kind, CommentKind::Doc);
        assert_eq!(l.comments[2].doc_text(), "d");
        assert!(l.diags.is_empty());
    }

    #[test]
    fn raw_newline_in_string_is_reported() {
        let l = lex("\"a\nb\"");
        assert!(l.diags.iter().any(|d| d.rule == "MDL000"));
    }
}
