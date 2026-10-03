//! The token cursor: peeking, expecting, error recording and recovery.

use gob_text::{FileId, Span, TextRange, TextSize};

use super::error::{ParseError, ParseErrorKind, ParseWarning, ParseWarningKind};
use crate::grl::ast::Word;
use crate::grl::token::{Token, TokenKind};

/// Deepest nesting of conditions, shapes and terms the parser follows.
pub(super) const MAX_DEPTH: usize = 96;

/// Words that start an item or join conditions, so they never name a variable, kind or verb.
const RESERVED: &[&str] = &[
    "rule",
    "lang",
    "polarity",
    "severity",
    "scope",
    "must_measure",
    "needs",
    "rollup",
    "knob",
    "find",
    "where",
    "some",
    "no",
    "def",
    "report",
    "note",
    "fix",
    "unresolved",
    "example",
    "explain",
    "and",
    "or",
    "not",
    "when",
    "because",
    "via",
    "within",
];

/// Marker for "this construct failed; the error is already recorded".
#[derive(Debug, Clone, Copy)]
pub(super) struct Abort;

/// The result of every parsing function: a node, or an already-recorded error.
pub(super) type PResult<T> = Result<T, Abort>;

/// The parser state: tokens, position, and the diagnostics found so far.
pub(super) struct Parser<'a> {
    pub(super) file: FileId,
    pub(super) text: &'a str,
    toks: &'a [Token],
    pub(super) pos: usize,
    /// Open brackets consumed since the current item began (for recovery).
    pub(super) bal: i32,
    depth: usize,
    errors: Vec<ParseError>,
    warnings: Vec<ParseWarning>,
}

impl<'a> Parser<'a> {
    pub(super) fn new(file: FileId, text: &'a str, toks: &'a [Token]) -> Self {
        Self {
            file,
            text,
            toks,
            pos: 0,
            bal: 0,
            depth: 0,
            errors: Vec::new(),
            warnings: Vec::new(),
        }
    }

    pub(super) fn finish(self) -> (Vec<ParseError>, Vec<ParseWarning>) {
        (self.errors, self.warnings)
    }

    // ---- looking ----

    pub(super) fn peek(&self) -> Option<&'a Token> {
        self.toks.get(self.pos)
    }

    pub(super) fn nth(&self, n: usize) -> Option<&'a Token> {
        self.toks.get(self.pos + n)
    }

    pub(super) fn is(&self, kind: &TokenKind) -> bool {
        self.peek().is_some_and(|t| &t.kind == kind)
    }

    pub(super) fn is_nth(&self, n: usize, kind: &TokenKind) -> bool {
        self.nth(n).is_some_and(|t| &t.kind == kind)
    }

    /// The identifier text at offset `n`, if that token is an identifier.
    pub(super) fn word_nth(&self, n: usize) -> Option<&'a str> {
        match &self.nth(n)?.kind {
            TokenKind::Ident(w) => Some(w.as_str()),
            _ => None,
        }
    }

    pub(super) fn word(&self) -> Option<&'a str> {
        self.word_nth(0)
    }

    pub(super) fn at_word(&self, w: &str) -> bool {
        self.word() == Some(w)
    }

    pub(super) fn at_end(&self) -> bool {
        self.pos >= self.toks.len()
    }

    /// Span of the current token, or an empty span at the end of the input.
    pub(super) fn here(&self) -> Span {
        self.peek().map_or_else(|| self.eof(), |t| t.span)
    }

    /// Span of the token before the cursor (or the start of the file).
    pub(super) fn prev_span(&self) -> Span {
        self.pos
            .checked_sub(1)
            .and_then(|i| self.toks.get(i))
            .map_or_else(|| self.eof_at(0), |t| t.span)
    }

    fn eof(&self) -> Span {
        let end = self
            .toks
            .last()
            .map_or(0, |t| u32::from(t.span.range.end()));
        self.eof_at(end)
    }

    fn eof_at(&self, at: u32) -> Span {
        Span::new(self.file, TextRange::empty(TextSize::new(at)))
    }

    // ---- consuming ----

    pub(super) fn bump(&mut self) -> Option<&'a Token> {
        let tok = self.toks.get(self.pos)?;
        self.pos += 1;
        match tok.kind {
            TokenKind::LBrace | TokenKind::LParen | TokenKind::LBracket => self.bal += 1,
            TokenKind::RBrace | TokenKind::RParen | TokenKind::RBracket => self.bal -= 1,
            _ => {}
        }
        Some(tok)
    }

    pub(super) fn eat(&mut self, kind: &TokenKind) -> Option<Span> {
        if self.is(kind) {
            self.bump().map(|t| t.span)
        } else {
            None
        }
    }

    pub(super) fn eat_word(&mut self, w: &str) -> Option<Span> {
        if self.at_word(w) {
            self.bump().map(|t| t.span)
        } else {
            None
        }
    }

    pub(super) fn expect(&mut self, kind: &TokenKind, what: &str) -> PResult<Span> {
        match self.eat(kind) {
            Some(span) => Ok(span),
            None => self.expected(what),
        }
    }

    pub(super) fn expect_word(&mut self, w: &str, what: &str) -> PResult<Span> {
        match self.eat_word(w) {
            Some(span) => Ok(span),
            None => self.expected(what),
        }
    }

    /// Any identifier, keywords included (field names after a dot).
    pub(super) fn ident(&mut self, what: &str) -> PResult<Word> {
        if let Some(Token {
            kind: TokenKind::Ident(text),
            span,
        }) = self.peek()
        {
            self.bump();
            return Ok(Word {
                text: text.clone(),
                span: *span,
            });
        }
        self.expected(what)
    }

    /// An identifier that is not a reserved word: a variable, def, kind or verb name.
    pub(super) fn name(&mut self, what: &str) -> PResult<Word> {
        if self.word().is_some_and(is_reserved) {
            return self.expected(what);
        }
        self.ident(what)
    }

    /// A word that may be hyphenated (`known-gap`): `ident (- ident)*` with adjacent spans.
    pub(super) fn hyphen_word(&mut self, what: &str) -> PResult<Word> {
        let mut word = self.ident(what)?;
        loop {
            let joins = self.is(&TokenKind::Minus)
                && self.word_nth(1).is_some()
                && self.adjacent(word.span, self.here())
                && self
                    .nth(1)
                    .is_some_and(|t| self.adjacent(self.here(), t.span));
            if !joins {
                return Ok(word);
            }
            self.bump();
            let Some(next) = self.bump() else {
                return Ok(word);
            };
            if let TokenKind::Ident(piece) = &next.kind {
                word.text.push('-');
                word.text.push_str(piece);
                word.span = cover(word.span, next.span);
            }
        }
    }

    fn adjacent(&self, left: Span, right: Span) -> bool {
        left.range.end() == right.range.start()
    }

    // ---- diagnostics ----

    pub(super) fn error(&mut self, kind: ParseErrorKind, span: Span) {
        tracing::debug!(%kind, span = %span.range, "GRL syntax error");
        self.errors.push(ParseError { kind, span });
    }

    pub(super) fn fail<T>(&mut self, kind: ParseErrorKind, span: Span) -> PResult<T> {
        self.error(kind, span);
        Err(Abort)
    }

    pub(super) fn warn(&mut self, kind: ParseWarningKind, span: Span) {
        tracing::debug!(%kind, span = %span.range, "GRL parse warning");
        self.warnings.push(ParseWarning { kind, span });
    }

    /// Fail with "expected `what`, found <current token>".
    pub(super) fn expected<T>(&mut self, what: &str) -> PResult<T> {
        self.expected_hint(what, None)
    }

    pub(super) fn expected_hint<T>(
        &mut self,
        what: &str,
        hint: Option<&'static str>,
    ) -> PResult<T> {
        let found = describe(self.peek());
        let span = self.here();
        self.fail(
            ParseErrorKind::Expected {
                what: what.to_owned(),
                found,
                hint,
            },
            span,
        )
    }

    /// Run `f` one nesting level deeper; too deep is an error, not a stack overflow.
    pub(super) fn nest<T>(&mut self, f: impl FnOnce(&mut Self) -> PResult<T>) -> PResult<T> {
        if self.depth >= MAX_DEPTH {
            let span = self.here();
            return self.fail(ParseErrorKind::TooDeep(MAX_DEPTH), span);
        }
        self.depth += 1;
        let out = f(self);
        self.depth -= 1;
        out
    }

    // ---- recovery ----

    /// Skip to the next token that starts an item (or the `}` closing the enclosing block).
    ///
    /// Does not consume the token it stops at, so callers that may not have
    /// consumed anything guard against standing still. `starts` says whether
    /// the identifier at the cursor begins an item; the
    /// bracket balance of the failed item (`self.bal`) is respected so that a
    /// brace inside a clause is not mistaken for the end of the rule.
    pub(super) fn skip_to(&mut self, starts: impl Fn(&Self) -> bool) {
        loop {
            let Some(tok) = self.peek() else { return };
            match &tok.kind {
                TokenKind::RBrace if self.bal <= 0 => return,
                TokenKind::Ident(_) if self.bal <= 0 && starts(self) => {
                    return;
                }
                _ => {}
            }
            self.bump();
        }
    }
}

/// True for words that cannot name a variable, kind or verb.
pub(super) fn is_reserved(word: &str) -> bool {
    RESERVED.contains(&word)
}

/// The span covering both.
pub(super) fn cover(a: Span, b: Span) -> Span {
    Span::new(a.file, a.range.cover(b.range))
}

/// A user-facing description of a token (or the end of the file).
pub(super) fn describe(tok: Option<&Token>) -> String {
    let Some(tok) = tok else {
        return "the end of the file".to_owned();
    };
    match &tok.kind {
        TokenKind::Ident(w) | TokenKind::RuleId(w) | TokenKind::Polarity(w) => format!("`{w}`"),
        TokenKind::Int(n) => format!("the number `{n}`"),
        TokenKind::Decimal(n) => format!("the number `{n}`"),
        TokenKind::Str(_) => "a string".to_owned(),
        TokenKind::Block(_) => "a triple-quoted block".to_owned(),
        TokenKind::Snippet(_) => "a snippet".to_owned(),
        TokenKind::Regex(_) => "a regular expression".to_owned(),
        TokenKind::LBrace => "`{`".to_owned(),
        TokenKind::RBrace => "`}`".to_owned(),
        TokenKind::LParen => "`(`".to_owned(),
        TokenKind::RParen => "`)`".to_owned(),
        TokenKind::LBracket => "`[`".to_owned(),
        TokenKind::RBracket => "`]`".to_owned(),
        TokenKind::Comma => "`,`".to_owned(),
        TokenKind::Colon => "`:`".to_owned(),
        TokenKind::Dot => "`.`".to_owned(),
        TokenKind::DotDot => "`..`".to_owned(),
        TokenKind::Eq => "`=`".to_owned(),
        TokenKind::EqEq => "`==`".to_owned(),
        TokenKind::Ne => "`!=`".to_owned(),
        TokenKind::Lt => "`<`".to_owned(),
        TokenKind::Le => "`<=`".to_owned(),
        TokenKind::Gt => "`>`".to_owned(),
        TokenKind::Ge => "`>=`".to_owned(),
        TokenKind::Tilde => "`~`".to_owned(),
        TokenKind::Pipe => "`|`".to_owned(),
        TokenKind::Plus => "`+`".to_owned(),
        TokenKind::Minus => "`-`".to_owned(),
        TokenKind::Star => "`*`".to_owned(),
        TokenKind::Arrow => "`->`".to_owned(),
    }
}

impl Parser<'_> {
    /// The token at absolute index `i`.
    pub(super) fn token_at(&self, i: usize) -> Option<&Token> {
        self.toks.get(i)
    }
}
