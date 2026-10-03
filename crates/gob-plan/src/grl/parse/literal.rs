//! Literals, strings, messages, paths and knob types.

use gob_text::{Span, TextRange, TextSize};

use super::cursor::{PResult, Parser, cover};
use super::error::ParseErrorKind;
use crate::grl::ast::{
    BlockLit, Literal, LiteralKind, Message, MessagePart, Path, Spanned, StrLit, TypeKind, TypeRef,
    Word,
};
use crate::grl::lexer::lex_range;
use crate::grl::token::{StrPart, Token, TokenKind};

impl Parser<'_> {
    /// A non-message string: braces are literal, so the value is read back from the source.
    pub(super) fn plain_str(&mut self, what: &str) -> PResult<StrLit> {
        let Some(Token {
            kind: TokenKind::Str(_),
            span,
        }) = self.peek()
        else {
            return self.expected(what);
        };
        self.bump();
        Ok(self.plain_from(*span))
    }

    /// Rejoin a string token into one literal value (see [`decode_plain`]).
    fn plain_from(&self, span: Span) -> StrLit {
        let range = span.range.to_usize_range();
        let inner = self
            .text
            .get(range.start + 1..range.end.saturating_sub(1))
            .unwrap_or_default();
        StrLit {
            value: decode_plain(inner),
            span,
        }
    }

    /// The range of an interpolation including its braces.
    fn braces(expr: Span) -> Span {
        let start = u32::from(expr.range.start()).saturating_sub(1);
        let end = u32::from(expr.range.end()).saturating_add(1);
        Span::new(
            expr.file,
            TextRange::new(TextSize::new(start), TextSize::new(end)),
        )
    }

    /// A message string: text with `{path}` interpolations.
    pub(super) fn message(&mut self, what: &str) -> PResult<Message> {
        let Some(Token {
            kind: TokenKind::Str(parts),
            span,
        }) = self.peek()
        else {
            return self.expected(what);
        };
        self.bump();
        let mut out = Vec::new();
        for part in parts {
            match part {
                StrPart::Text { value, span } => out.push(MessagePart::Text {
                    value: value.clone(),
                    span: *span,
                }),
                StrPart::Interp { expr } => {
                    if let Some(path) = self.interp_path(*expr) {
                        out.push(MessagePart::Interp {
                            path,
                            span: Self::braces(*expr),
                        });
                    }
                }
            }
        }
        Ok(Message {
            parts: out,
            span: *span,
        })
    }

    /// Lex and read the text of `{...}`: it must be a dotted path; errors are recorded.
    fn interp_path(&mut self, expr: Span) -> Option<Path> {
        let lexed = match lex_range(self.file, self.text, expr.range) {
            Ok(l) => l,
            Err(e) => {
                self.error(ParseErrorKind::Lexical(e.kind), e.span);
                return None;
            }
        };
        let mut segments = Vec::new();
        let mut want_ident = true;
        for tok in &lexed.tokens {
            match (&tok.kind, want_ident) {
                (TokenKind::Ident(text), true) => {
                    segments.push(Word {
                        text: text.clone(),
                        span: tok.span,
                    });
                    want_ident = false;
                }
                (TokenKind::Dot, false) => want_ident = true,
                _ => {
                    self.error(ParseErrorKind::BadInterpolation, expr);
                    return None;
                }
            }
        }
        if want_ident {
            self.error(ParseErrorKind::BadInterpolation, expr);
            return None;
        }
        let span = cover(segments[0].span, segments[segments.len() - 1].span);
        Some(Path { segments, span })
    }

    /// A triple-quoted block.
    pub(super) fn block(&mut self, what: &str) -> PResult<BlockLit> {
        if let Some(Token {
            kind: TokenKind::Block(b),
            span,
        }) = self.peek()
        {
            self.bump();
            return Ok(BlockLit {
                value: b.value.clone(),
                body: b.body,
                span: *span,
            });
        }
        let hint = matches!(self.peek().map(|t| &t.kind), Some(TokenKind::Str(_)))
            .then_some("a block is written with three quotes on each side: \"\"\" ... \"\"\"");
        self.expected_hint(what, hint)
    }

    /// A dotted path `a.b.c` of identifiers.
    pub(super) fn path(&mut self, what: &str) -> PResult<Path> {
        let first = self.name(what)?;
        self.path_from(first)
    }

    /// Continue a path after its first word.
    pub(super) fn path_from(&mut self, first: Word) -> PResult<Path> {
        let mut span = first.span;
        let mut segments = vec![first];
        while self.eat(&TokenKind::Dot).is_some() {
            let seg = self.ident("a field name after `.`")?;
            span = cover(span, seg.span);
            segments.push(seg);
        }
        Ok(Path { segments, span })
    }

    /// A knob or field literal; its strings are plain, so braces are literal.
    pub(super) fn literal(&mut self) -> PResult<Literal> {
        self.nest(Self::literal_inner)
    }

    fn literal_inner(&mut self) -> PResult<Literal> {
        let Some(tok) = self.peek() else {
            return self.expected("a value (a number, string, regex, list or `true`/`false`)");
        };
        let span = tok.span;
        let kind = match &tok.kind {
            TokenKind::Int(n) => {
                self.bump();
                LiteralKind::Int(i128::from(*n))
            }
            TokenKind::Decimal(d) => {
                self.bump();
                LiteralKind::Decimal(d.clone())
            }
            TokenKind::Minus => return self.negative(),
            TokenKind::Str(_) => {
                self.bump();
                LiteralKind::Str(self.plain_from(span).value)
            }
            TokenKind::Regex(r) => {
                self.bump();
                LiteralKind::Regex(r.clone())
            }
            TokenKind::LBracket => return self.list(),
            TokenKind::Ident(w) if w == "true" || w == "false" => {
                self.bump();
                LiteralKind::Bool(w == "true")
            }
            TokenKind::Ident(_) if self.is_nth(1, &TokenKind::LParen) => {
                return self.literal_call();
            }
            _ => {
                return self.expected("a value (a number, string, regex, list or `true`/`false`)");
            }
        };
        Ok(Spanned { node: kind, span })
    }

    fn negative(&mut self) -> PResult<Literal> {
        let minus = self.here();
        self.bump();
        let Some(tok) = self.peek() else {
            return self.expected("a number after `-`");
        };
        let node = match &tok.kind {
            TokenKind::Int(n) => LiteralKind::Int(-i128::from(*n)),
            TokenKind::Decimal(d) => LiteralKind::Decimal(format!("-{d}")),
            _ => return self.expected("a number after `-`"),
        };
        self.bump();
        Ok(Spanned {
            node,
            span: cover(minus, tok.span),
        })
    }

    fn list(&mut self) -> PResult<Literal> {
        let open = self.here();
        self.bump();
        let mut items = Vec::new();
        if !self.is(&TokenKind::RBracket) {
            loop {
                items.push(self.literal()?);
                if self.eat(&TokenKind::Comma).is_none() {
                    break;
                }
            }
        }
        let close = self.expect(&TokenKind::RBracket, "`,` or `]` in the list")?;
        Ok(Spanned {
            node: LiteralKind::List(items),
            span: cover(open, close),
        })
    }

    fn literal_call(&mut self) -> PResult<Literal> {
        let name = self.ident("a constructor name")?;
        self.bump();
        let mut args = Vec::new();
        if !self.is(&TokenKind::RParen) {
            loop {
                args.push(self.literal()?);
                if self.eat(&TokenKind::Comma).is_none() {
                    break;
                }
            }
        }
        let close = self.expect(&TokenKind::RParen, "`,` or `)` after the argument")?;
        let span = cover(name.span, close);
        Ok(Spanned {
            node: LiteralKind::Call { name, args },
            span,
        })
    }

    /// A knob type: `int`, `float`, `string`, `bool`, `glob`, `regex`, `vocab` or `list<T>`.
    pub(super) fn type_ref(&mut self) -> PResult<TypeRef> {
        self.nest(Self::type_inner)
    }

    fn type_inner(&mut self) -> PResult<TypeRef> {
        let word = self.ident(
            "a type (`int`, `float`, `string`, `bool`, `glob`, `regex`, `vocab` or `list<T>`)",
        )?;
        let node = match word.text.as_str() {
            "int" => TypeKind::Int,
            "float" => TypeKind::Float,
            "string" => TypeKind::String,
            "bool" => TypeKind::Bool,
            "glob" => TypeKind::Glob,
            "regex" => TypeKind::Regex,
            "vocab" => TypeKind::Vocab,
            "list" => {
                self.expect(&TokenKind::Lt, "`<` after `list`")?;
                let inner = self.type_ref()?;
                let close = if self.is(&TokenKind::Ge) {
                    return self.expected_hint(
                        "`>` to close `list<...>`",
                        Some("write a space between `>` and `=`: `list<int> = ...`"),
                    );
                } else {
                    self.expect(&TokenKind::Gt, "`>` to close `list<...>`")?
                };
                return Ok(Spanned {
                    node: TypeKind::List(Box::new(inner)),
                    span: cover(word.span, close),
                });
            }
            _ => {
                return self.fail(
                    ParseErrorKind::BadChoice {
                        what: "a knob type",
                        found: word.text,
                        choices: "`int`, `float`, `string`, `bool`, `glob`, `regex`, `vocab` and `list<T>`",
                    },
                    word.span,
                );
            }
        };
        Ok(Spanned {
            node,
            span: word.span,
        })
    }
}

/// Decode the source text between a plain string's quotes.
///
/// Braces are literal and need no escaping. The escapes `\"`, `\\` and `\n`
/// decode as in every string; a backslash before a brace is kept as written
/// (`\{` stays two characters), so globs and regexes see their own escape.
fn decode_plain(inner: &str) -> String {
    let mut out = String::with_capacity(inner.len());
    let mut chars = inner.chars();
    while let Some(c) = chars.next() {
        if c != '\\' {
            out.push(c);
            continue;
        }
        match chars.next() {
            Some('"') => out.push('"'),
            Some('\\') | None => out.push('\\'),
            Some('n') => out.push('\n'),
            Some(other) => {
                out.push('\\');
                out.push(other);
            }
        }
    }
    out
}
