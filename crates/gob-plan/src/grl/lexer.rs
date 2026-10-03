//! The lexer driver: whitespace, comments, words, numbers, regexes and punctuation.

use gob_text::{FileId, Span, TextRange, TextSize};

use super::error::{LexError, LexErrorKind};
use super::token::{Comment, Lexed, Regex, Token, TokenKind};

/// Lex a whole GRL file.
///
/// # Errors
///
/// Returns the first [`LexError`] (non-ASCII syntax, an unterminated string,
/// snippet or regex, a stray character, ...) with its span.
pub fn lex(file: FileId, text: &str) -> Result<Lexed, LexError> {
    lex_range(file, text, whole(text))
}

/// Lex `range` of `text`; spans stay relative to the whole text.
///
/// The parser uses this for `{expr}` interpolations.
///
/// # Errors
///
/// As [`lex`]; also [`LexErrorKind::BadRange`] when `range` is outside the
/// text or splits a character.
pub fn lex_range(file: FileId, text: &str, range: TextRange) -> Result<Lexed, LexError> {
    let (start, end) = (range.start().to_usize(), range.end().to_usize());
    let ok = end <= text.len() && text.is_char_boundary(start) && text.is_char_boundary(end);
    if !ok {
        return Err(LexError {
            kind: LexErrorKind::BadRange,
            span: Span::new(file, TextRange::empty(TextSize::new(0))),
        });
    }
    if u32::try_from(text.len()).is_err() {
        return Err(LexError {
            kind: LexErrorKind::TooLarge,
            span: Span::new(file, TextRange::empty(TextSize::new(0))),
        });
    }
    let mut lx = Lexer::new(file, text, start, end);
    let result = lx.run();
    match &result {
        Ok(()) => tracing::debug!(
            file = %file,
            tokens = lx.out.tokens.len(),
            comments = lx.out.comments.len(),
            "lexed GRL source"
        ),
        Err(e) => tracing::debug!(file = %file, error = %e, "GRL lexical error"),
    }
    result.map(|()| lx.out)
}

fn whole(text: &str) -> TextRange {
    let end = u32::try_from(text.len()).unwrap_or(u32::MAX);
    TextRange::new(TextSize::new(0), TextSize::new(end))
}

/// Cursor over `src[pos..end]` that accumulates tokens.
pub(super) struct Lexer<'a> {
    pub(super) file: FileId,
    pub(super) src: &'a str,
    pub(super) pos: usize,
    pub(super) end: usize,
    pub(super) out: Lexed,
}

impl<'a> Lexer<'a> {
    fn new(file: FileId, src: &'a str, pos: usize, end: usize) -> Self {
        Self {
            file,
            src,
            pos,
            end,
            out: Lexed::default(),
        }
    }

    pub(super) fn rest(&self) -> &'a str {
        &self.src[self.pos..self.end]
    }

    pub(super) fn peek(&self) -> Option<char> {
        self.rest().chars().next()
    }

    pub(super) fn peek2(&self) -> Option<char> {
        self.rest().chars().nth(1)
    }

    pub(super) fn bump(&mut self) -> Option<char> {
        let c = self.peek()?;
        self.pos += c.len_utf8();
        Some(c)
    }

    pub(super) fn eat(&mut self, c: char) -> bool {
        if self.peek() == Some(c) {
            self.pos += c.len_utf8();
            true
        } else {
            false
        }
    }

    pub(super) fn span(&self, start: usize, end: usize) -> Span {
        let off = |n: usize| TextSize::new(u32::try_from(n).unwrap_or(u32::MAX));
        Span::new(self.file, TextRange::new(off(start), off(end)))
    }

    pub(super) fn err<T>(
        &self,
        kind: LexErrorKind,
        start: usize,
        end: usize,
    ) -> Result<T, LexError> {
        Err(LexError {
            kind,
            span: self.span(start, end),
        })
    }

    pub(super) fn push(&mut self, kind: TokenKind, start: usize) {
        let span = self.span(start, self.pos);
        tracing::trace!(?kind, %span.range, "token");
        self.out.tokens.push(Token { kind, span });
    }

    fn run(&mut self) -> Result<(), LexError> {
        while let Some(c) = self.peek() {
            let start = self.pos;
            match c {
                ' ' | '\t' | '\n' | '\r' => {
                    self.bump();
                }
                '#' => self.comment(),
                '"' => self.string(start)?,
                '`' => self.snippet(start, None)?,
                '/' => self.regex(start)?,
                '0'..='9' => self.number(start)?,
                c if !c.is_ascii() && !c.is_alphanumeric() => {
                    self.bump();
                    return self.err(
                        LexErrorKind::NonAscii { ch: c, word: None },
                        start,
                        self.pos,
                    );
                }
                c if c.is_ascii_alphabetic() || c == '_' || !c.is_ascii() => self.word(start)?,
                _ => self.punct(start, c)?,
            }
        }
        Ok(())
    }

    fn comment(&mut self) {
        let start = self.pos;
        while let Some(c) = self.peek() {
            if c == '\n' || c == '\r' {
                break;
            }
            self.bump();
        }
        let span = self.span(start, self.pos);
        self.out.comments.push(Comment { span });
    }

    /// Identifier, rule id, polarity, or the language tag of a snippet.
    fn word(&mut self, start: usize) -> Result<(), LexError> {
        let mut non_ascii = None;
        while let Some(c) = self.peek() {
            if c.is_ascii_alphanumeric() || c == '_' {
                self.bump();
            } else if !c.is_ascii() && c.is_alphanumeric() {
                non_ascii.get_or_insert((c, self.pos));
                self.bump();
            } else {
                break;
            }
        }
        let word = &self.src[start..self.pos];
        if let Some((ch, at)) = non_ascii {
            return self.err(
                LexErrorKind::NonAscii {
                    ch,
                    word: Some(word.to_owned()),
                },
                at,
                at + ch.len_utf8(),
            );
        }
        let first = word.as_bytes()[0];
        if first.is_ascii_lowercase() || first == b'_' {
            if word.bytes().any(|b| b.is_ascii_uppercase()) {
                return self.err(LexErrorKind::BadWord(word.to_owned()), start, self.pos);
            }
            if self.peek() == Some('`') {
                return self.snippet(start, Some(self.pos));
            }
            self.push(TokenKind::Ident(word.to_owned()), start);
            return Ok(());
        }
        if is_rule_id(word) {
            self.push(TokenKind::RuleId(word.to_owned()), start);
        } else if matches!(word, "P0" | "Pn" | "Pc") {
            self.push(TokenKind::Polarity(word.to_owned()), start);
        } else if word == "P" && matches!(self.peek(), Some('+' | '-')) {
            self.bump();
            let text = self.src[start..self.pos].to_owned();
            self.push(TokenKind::Polarity(text), start);
        } else {
            return self.err(LexErrorKind::BadWord(word.to_owned()), start, self.pos);
        }
        Ok(())
    }

    fn number(&mut self, start: usize) -> Result<(), LexError> {
        self.digits();
        let mut decimal = false;
        if self.peek() == Some('.') && self.peek2().is_some_and(|c| c.is_ascii_digit()) {
            self.bump();
            self.digits();
            decimal = true;
        }
        if self
            .peek()
            .is_some_and(|c| c.is_ascii_alphanumeric() || c == '_')
        {
            while self
                .peek()
                .is_some_and(|c| c.is_ascii_alphanumeric() || c == '_')
            {
                self.bump();
            }
            let text = self.src[start..self.pos].to_owned();
            return self.err(LexErrorKind::BadNumber(text), start, self.pos);
        }
        let text = &self.src[start..self.pos];
        if decimal {
            self.push(TokenKind::Decimal(text.to_owned()), start);
        } else if let Ok(n) = text.parse::<u64>() {
            self.push(TokenKind::Int(n), start);
        } else {
            return self.err(
                LexErrorKind::NumberTooLarge(text.to_owned()),
                start,
                self.pos,
            );
        }
        Ok(())
    }

    fn digits(&mut self) {
        while self.peek().is_some_and(|c| c.is_ascii_digit()) {
            self.bump();
        }
    }

    /// A `/.../flags` literal; the opening slash is at `start`.
    fn regex(&mut self, start: usize) -> Result<(), LexError> {
        self.bump();
        let body = self.pos;
        let mut in_class = false;
        loop {
            let at = self.pos;
            match self.bump() {
                None | Some('\n' | '\r') => {
                    return self.err(LexErrorKind::UnterminatedRegex, start, at);
                }
                Some('\\') => match self.bump() {
                    None | Some('\n' | '\r') => {
                        return self.err(LexErrorKind::UnterminatedRegex, start, at);
                    }
                    Some(c) if !c.is_ascii() => {
                        return self.err(LexErrorKind::NonAsciiRegex(c), at + 1, self.pos);
                    }
                    Some(_) => {}
                },
                Some('[') => in_class = true,
                Some(']') => in_class = false,
                Some('/') if !in_class => break,
                Some(c) if !c.is_ascii() => {
                    return self.err(LexErrorKind::NonAsciiRegex(c), at, self.pos);
                }
                Some(_) => {}
            }
        }
        let pattern = self.src[body..self.pos - 1].to_owned();
        if pattern.is_empty() {
            return self.err(LexErrorKind::EmptyRegex, start, self.pos);
        }
        let (mut ignore_case, mut multi_line) = (false, false);
        while let Some(c) = self.peek().filter(char::is_ascii_alphabetic) {
            let at = self.pos;
            self.bump();
            let flag = match c {
                'i' => &mut ignore_case,
                'm' => &mut multi_line,
                other => return self.err(LexErrorKind::UnknownRegexFlag(other), at, self.pos),
            };
            if *flag {
                return self.err(LexErrorKind::DuplicateRegexFlag(c), at, self.pos);
            }
            *flag = true;
        }
        self.push(
            TokenKind::Regex(Regex {
                pattern,
                ignore_case,
                multi_line,
            }),
            start,
        );
        Ok(())
    }

    fn punct(&mut self, start: usize, c: char) -> Result<(), LexError> {
        self.bump();
        let two = |lx: &mut Self, next: char, yes: TokenKind, no: TokenKind| {
            if lx.eat(next) { yes } else { no }
        };
        let kind = match c {
            '{' => TokenKind::LBrace,
            '}' => TokenKind::RBrace,
            '(' => TokenKind::LParen,
            ')' => TokenKind::RParen,
            '[' => TokenKind::LBracket,
            ']' => TokenKind::RBracket,
            ',' => TokenKind::Comma,
            ':' => TokenKind::Colon,
            '.' => two(self, '.', TokenKind::DotDot, TokenKind::Dot),
            '=' => two(self, '=', TokenKind::EqEq, TokenKind::Eq),
            '<' => two(self, '=', TokenKind::Le, TokenKind::Lt),
            '>' => two(self, '=', TokenKind::Ge, TokenKind::Gt),
            '-' => two(self, '>', TokenKind::Arrow, TokenKind::Minus),
            '~' => TokenKind::Tilde,
            '|' => TokenKind::Pipe,
            '+' => TokenKind::Plus,
            '*' => TokenKind::Star,
            '!' if self.eat('=') => TokenKind::Ne,
            other => return self.err(LexErrorKind::BadCharacter(other), start, self.pos),
        };
        self.push(kind, start);
        Ok(())
    }
}

/// True for `[A-Z]+[0-9]{3}`.
fn is_rule_id(word: &str) -> bool {
    let letters = word.bytes().take_while(u8::is_ascii_uppercase).count();
    let digits = &word[letters..];
    letters > 0 && digits.len() == 3 && digits.bytes().all(|b| b.is_ascii_digit())
}
