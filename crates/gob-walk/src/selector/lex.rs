//! Selector tokens with spans and a source map for string escapes.

use super::parse::{Span, SyntaxError};

/// A string literal's unescaped value and where each content byte came from.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct StrLit {
    pub value: String,
    /// `map[i]` is the absolute source offset of the character that produced byte `i`.
    pub map: Vec<usize>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) enum Tok {
    LParen,
    RParen,
    Comma,
    Pipe,
    Amp,
    Bang,
    Eq,
    Ne,
    Tilde,
    Le,
    Percent,
    Slash,
    Str(StrLit),
    Ident(String),
    Number(String),
    Eof,
}

impl Tok {
    pub fn describe(&self) -> String {
        match self {
            Self::LParen => "`(`".into(),
            Self::RParen => "`)`".into(),
            Self::Comma => "`,`".into(),
            Self::Pipe => "`|`".into(),
            Self::Amp => "`&`".into(),
            Self::Bang => "`!`".into(),
            Self::Eq => "`=`".into(),
            Self::Ne => "`!=`".into(),
            Self::Tilde => "`~`".into(),
            Self::Le => "`<=`".into(),
            Self::Percent => "`%`".into(),
            Self::Slash => "`/`".into(),
            Self::Str(_) => "a string".into(),
            Self::Ident(i) => format!("`{i}`"),
            Self::Number(n) => format!("`{n}`"),
            Self::Eof => "end of selector".into(),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct Token {
    pub tok: Tok,
    pub span: Span,
}

fn fail<T>(start: usize, end: usize, message: &str) -> Result<T, SyntaxError> {
    Err(SyntaxError {
        span: Span { start, end },
        message: message.to_owned(),
    })
}

fn punct(c: char) -> Option<Tok> {
    Some(match c {
        '(' => Tok::LParen,
        ')' => Tok::RParen,
        ',' => Tok::Comma,
        '|' => Tok::Pipe,
        '&' => Tok::Amp,
        '=' => Tok::Eq,
        '~' => Tok::Tilde,
        '%' => Tok::Percent,
        '/' => Tok::Slash,
        _ => return None,
    })
}

/// Lexes `text`; every span is shifted by `base`.
pub(super) fn lex(text: &str, base: usize) -> Result<Vec<Token>, SyntaxError> {
    let chars: Vec<(usize, char)> = text.char_indices().collect();
    let at = |i: usize| chars.get(i).map(|&(_, c)| c);
    let off = |i: usize| base + chars.get(i).map_or(text.len(), |&(o, _)| o);
    let mut out = Vec::new();
    let mut i = 0;
    while i < chars.len() {
        let c = chars[i].1;
        let start = off(i);
        let simple = |tok: Tok, len: usize| Token {
            tok,
            span: Span {
                start,
                end: start + len,
            },
        };
        match c {
            c if c.is_whitespace() => i += 1,
            c if punct(c).is_some() => {
                if let Some(tok) = punct(c) {
                    out.push(simple(tok, 1));
                }
                i += 1;
            }
            '!' if at(i + 1) == Some('=') => {
                out.push(simple(Tok::Ne, 2));
                i += 2;
            }
            '!' => {
                out.push(simple(Tok::Bang, 1));
                i += 1;
            }
            '<' if at(i + 1) == Some('=') => {
                out.push(simple(Tok::Le, 2));
                i += 2;
            }
            '<' => return fail(start, start + 1, "`<` must be written `<=`"),
            '"' => {
                let (lit, next) = lex_string(&chars, i, base, text.len())?;
                out.push(Token {
                    tok: Tok::Str(lit),
                    span: Span {
                        start,
                        end: off(next),
                    },
                });
                i = next;
            }
            c if c.is_ascii_digit() => {
                let mut j = i;
                while at(j).is_some_and(|d| d.is_ascii_digit()) {
                    j += 1;
                }
                if at(j) == Some('.') && at(j + 1).is_some_and(|d| d.is_ascii_digit()) {
                    j += 1;
                    while at(j).is_some_and(|d| d.is_ascii_digit()) {
                        j += 1;
                    }
                }
                out.push(Token {
                    tok: Tok::Number(chars[i..j].iter().map(|&(_, c)| c).collect()),
                    span: Span { start, end: off(j) },
                });
                i = j;
            }
            c if c.is_ascii_alphabetic() || c == '_' => {
                let mut j = i;
                while at(j).is_some_and(|d| d.is_ascii_alphanumeric() || d == '_') {
                    j += 1;
                }
                out.push(Token {
                    tok: Tok::Ident(chars[i..j].iter().map(|&(_, c)| c).collect()),
                    span: Span { start, end: off(j) },
                });
                i = j;
            }
            other => {
                return fail(
                    start,
                    start + other.len_utf8(),
                    &format!("unexpected character `{other}`"),
                );
            }
        }
    }
    let end = base + text.len();
    out.push(Token {
        tok: Tok::Eof,
        span: Span { start: end, end },
    });
    Ok(out)
}

fn lex_string(
    chars: &[(usize, char)],
    open: usize,
    base: usize,
    len: usize,
) -> Result<(StrLit, usize), SyntaxError> {
    let off = |i: usize| base + chars.get(i).map_or(len, |&(o, _)| o);
    let mut value = String::new();
    let mut map = Vec::new();
    let mut push = |c: char, src: usize, value: &mut String| {
        value.push(c);
        map.extend(std::iter::repeat_n(src, c.len_utf8()));
    };
    let mut i = open + 1;
    loop {
        let Some(&(_, c)) = chars.get(i) else {
            return fail(off(open), off(i), "unterminated string");
        };
        match c {
            '"' => return Ok((StrLit { value, map }, i + 1)),
            '\n' | '\r' => return fail(off(i), off(i) + 1, "raw newline in string"),
            '\\' => {
                let Some(&(_, e)) = chars.get(i + 1) else {
                    return fail(off(i), off(i + 1), "unterminated escape");
                };
                let src = off(i);
                match e {
                    '"' | '\\' => {
                        push(e, src, &mut value);
                        i += 2;
                    }
                    'n' => {
                        push('\n', src, &mut value);
                        i += 2;
                    }
                    't' => {
                        push('\t', src, &mut value);
                        i += 2;
                    }
                    'r' => {
                        push('\r', src, &mut value);
                        i += 2;
                    }
                    'u' => {
                        let (ch, next) = lex_unicode(chars, i, base, len)?;
                        push(ch, src, &mut value);
                        i = next;
                    }
                    _ => return fail(src, off(i + 2), "unknown escape"),
                }
            }
            c => {
                push(c, off(i), &mut value);
                i += 1;
            }
        }
    }
}

fn lex_unicode(
    chars: &[(usize, char)],
    backslash: usize,
    base: usize,
    len: usize,
) -> Result<(char, usize), SyntaxError> {
    let off = |i: usize| base + chars.get(i).map_or(len, |&(o, _)| o);
    let mut j = backslash + 2;
    if chars.get(j).map(|&(_, c)| c) != Some('{') {
        return fail(off(backslash), off(j), "expected `{` after `\\u`");
    }
    j += 1;
    let mut hex = String::new();
    while let Some(&(_, c)) = chars.get(j) {
        if c == '}' {
            break;
        }
        hex.push(c);
        j += 1;
    }
    if chars.get(j).is_none() {
        return fail(off(backslash), off(j), "unterminated `\\u{...}` escape");
    }
    let ch = u32::from_str_radix(&hex, 16)
        .ok()
        .filter(|_| !hex.is_empty())
        .and_then(char::from_u32);
    match ch {
        Some(c) => Ok((c, j + 1)),
        None => fail(off(backslash), off(j + 1), "invalid unicode escape"),
    }
}
