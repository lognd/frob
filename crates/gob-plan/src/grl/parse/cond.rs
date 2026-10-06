//! Conditions, relations, objects, shapes and terms.

use super::cursor::{PResult, Parser, cover, is_reserved};
use super::error::ParseErrorKind;
use crate::grl::ast::{
    ArithOp, Binding, Call, Cast, CastKind, Certainty, CmpOp, Cond, CondKind, Containment, FieldEq,
    LiteralKind, Object, Path, Position, Quant, Rel, RelKind, Shape, ShapeKind, Source, Spanned,
    Term, TermKind, Word,
};
use crate::grl::token::{Token, TokenKind};

/// Words that begin a relation after a subject (besides verbs).
const REL_WORDS: &[&str] = &[
    "directly",
    "inside",
    "has",
    "under",
    "before",
    "after",
    "adjoins",
    "reaches",
    "certainly",
    "possibly",
];

/// Two-word verbs: the first word and the word that completes it.
const MULTI_WORD_VERBS: &[(&str, &str)] = &[("resolves", "to"), ("owned", "by"), ("peer", "of")];

impl Parser<'_> {
    // ---- bindings and sources ----

    /// `NAME ":" source { rel } [ "where" cond ]`, shared by find, some, no and count.
    pub(super) fn binding(&mut self, after: &str) -> PResult<Binding> {
        let name = self.name(&format!("a variable name after `{after}`"))?;
        self.expect(&TokenKind::Colon, "`:` after the variable name")?;
        let source = self.source()?;
        let mut end = source.span();
        let mut rels = Vec::new();
        while self.at_rel_start() {
            let rel = self.rel()?;
            end = rel.span;
            rels.push(rel);
        }
        let filter = if self.eat_word("where").is_some() {
            let cond = self.cond()?;
            end = cond.span;
            Some(cond)
        } else {
            None
        };
        Ok(Binding {
            span: cover(name.span, end),
            name,
            source,
            rels,
            filter,
        })
    }

    fn source(&mut self) -> PResult<Source> {
        let is_side =
            self.word().is_some_and(|w| !is_reserved(w)) && self.is_nth(1, &TokenKind::Dot);
        if is_side {
            let path = self.path("a side relation such as `diff.changed`")?;
            return Ok(Source::Side(path));
        }
        Ok(Source::Shape(self.shape()?))
    }

    /// A shape: kind, snippet or parenthesised alternatives.
    pub(super) fn shape(&mut self) -> PResult<Shape> {
        self.nest(Self::shape_inner)
    }

    fn shape_inner(&mut self) -> PResult<Shape> {
        let Some(tok) = self.peek() else {
            return self.expected("a kind, a snippet or `(` shapes `)`");
        };
        match &tok.kind {
            TokenKind::Snippet(snippet) => {
                self.bump();
                let cast = self.cast()?;
                let end = cast.as_ref().map_or(tok.span, |c| c.span);
                Ok(Spanned {
                    node: ShapeKind::Snippet {
                        snippet: snippet.clone(),
                        cast,
                    },
                    span: cover(tok.span, end),
                })
            }
            TokenKind::LParen => {
                self.bump();
                let mut alts = vec![self.shape()?];
                while self.eat(&TokenKind::Pipe).is_some() {
                    alts.push(self.shape()?);
                }
                let close = self.expect(&TokenKind::RParen, "`|` or `)` after the shape")?;
                Ok(Spanned {
                    node: ShapeKind::Alt(alts),
                    span: cover(tok.span, close),
                })
            }
            TokenKind::Ident(_) => {
                let kind = self.name("a kind such as `function`, a snippet, or `(` shapes `)`")?;
                let mut span = kind.span;
                let mut fields = Vec::new();
                let mut arg = None;
                if self.eat(&TokenKind::LParen).is_some() {
                    loop {
                        fields.push(self.field_eq()?);
                        if self.eat(&TokenKind::Comma).is_none() {
                            break;
                        }
                    }
                    span = cover(
                        span,
                        self.expect(&TokenKind::RParen, "`,` or `)` after the field")?,
                    );
                } else if matches!(self.peek().map(|t| &t.kind), Some(TokenKind::Str(_))) {
                    let lit = self.plain_str("a string")?;
                    span = cover(span, lit.span);
                    arg = Some(lit);
                }
                Ok(Spanned {
                    node: ShapeKind::Kind { kind, fields, arg },
                    span,
                })
            }
            _ => self.expected("a kind such as `function`, a snippet, or `(` shapes `)`"),
        }
    }

    fn cast(&mut self) -> PResult<Option<Cast>> {
        let Some(as_span) = self.eat_word("as") else {
            return Ok(None);
        };
        let word = self.ident("`roles` or a kind after `as`")?;
        let span = cover(as_span, word.span);
        let node = if word.text == "roles" {
            CastKind::Roles
        } else {
            CastKind::Kind(word)
        };
        Ok(Some(Spanned { node, span }))
    }

    /// One `name = literal` pair of a kind pattern; the leading-dot form `.name = literal` is
    /// accepted too (grl-spec.md section 6) and means the same, the bare form being canonical.
    fn field_eq(&mut self) -> PResult<FieldEq> {
        let dot = self.eat(&TokenKind::Dot);
        let name = self.ident("a field name")?;
        self.expect(&TokenKind::Eq, "`=` after the field name")?;
        let value = self.literal()?;
        Ok(FieldEq {
            span: cover(dot.unwrap_or(name.span), value.span),
            name,
            value,
        })
    }

    // ---- conditions ----

    /// A condition: `or` of `and` of unary conditions.
    pub(super) fn cond(&mut self) -> PResult<Cond> {
        self.nest(Self::disj)
    }

    fn disj(&mut self) -> PResult<Cond> {
        let first = self.conj()?;
        if !self.at_word("or") {
            return Ok(first);
        }
        let mut parts = vec![first];
        while self.eat_word("or").is_some() {
            parts.push(self.conj()?);
        }
        Ok(join(CondKind::Or, parts))
    }

    fn conj(&mut self) -> PResult<Cond> {
        let first = self.unary()?;
        if !self.at_word("and") {
            return Ok(first);
        }
        let mut parts = vec![first];
        while self.eat_word("and").is_some() {
            parts.push(self.unary()?);
        }
        Ok(join(CondKind::And, parts))
    }

    fn unary(&mut self) -> PResult<Cond> {
        self.nest(Self::unary_inner)
    }

    fn unary_inner(&mut self) -> PResult<Cond> {
        if let Some(not) = self.eat_word("not") {
            let inner = self.unary()?;
            return Ok(Spanned {
                span: cover(not, inner.span),
                node: CondKind::Not(Box::new(inner)),
            });
        }
        if self.at_word("any") && self.is_nth(1, &TokenKind::LBrace) {
            return self.any();
        }
        if self.is(&TokenKind::LParen) {
            let open = self.here();
            self.bump();
            let inner = self.cond()?;
            let close = self.expect(&TokenKind::RParen, "`)` to close the condition")?;
            return Ok(Spanned {
                node: inner.node,
                span: cover(open, close),
            });
        }
        if self.at_quant() {
            return self.quant_cond();
        }
        self.atom()
    }

    fn any(&mut self) -> PResult<Cond> {
        let start = self.here();
        self.bump();
        self.bump();
        let mut parts = Vec::new();
        if self.is(&TokenKind::RBrace) {
            let close = self.here();
            self.error(ParseErrorKind::EmptyAny, cover(start, close));
        } else {
            loop {
                parts.push(self.cond()?);
                if self.eat(&TokenKind::Comma).is_none() {
                    break;
                }
            }
        }
        let close = self.expect(&TokenKind::RBrace, "`,` or `}` in `any { ... }`")?;
        Ok(Spanned {
            node: CondKind::Any(parts),
            span: cover(start, close),
        })
    }

    /// True at `some NAME :` or `no NAME :`.
    pub(super) fn at_quant(&self) -> bool {
        matches!(self.word(), Some("some" | "no"))
            && self.word_nth(1).is_some()
            && self.is_nth(2, &TokenKind::Colon)
    }

    /// Read the `some`/`no` word at the cursor.
    pub(super) fn quant_word(&mut self) -> PResult<(Quant, gob_text::Span)> {
        let quant = if self.at_word("some") {
            Quant::Some
        } else {
            Quant::No
        };
        let word = if quant == Quant::Some { "some" } else { "no" };
        let span = self.expect_word(word, "`some` or `no`")?;
        Ok((quant, span))
    }

    fn quant_cond(&mut self) -> PResult<Cond> {
        let (quant, start) = self.quant_word()?;
        let word = if quant == Quant::Some { "some" } else { "no" };
        let binding = self.binding(word)?;
        Ok(Spanned {
            span: cover(start, binding.span),
            node: CondKind::Quant {
                quant,
                binding: Box::new(binding),
            },
        })
    }

    fn atom(&mut self) -> PResult<Cond> {
        if let Some(kw) = self.eat_word("exists") {
            let term = self.term()?;
            return Ok(Spanned {
                span: cover(kw, term.span),
                node: CondKind::Exists(term),
            });
        }
        let lhs = self.term()?;
        let start = lhs.span;
        let Some(tok) = self.peek() else {
            return Ok(bare(lhs));
        };
        match &tok.kind {
            TokenKind::Tilde => {
                self.bump();
                let rhs = self.term()?;
                Ok(binary(start, rhs.span, CondKind::RegexMatch { lhs, rhs }))
            }
            TokenKind::EqEq
            | TokenKind::Ne
            | TokenKind::Lt
            | TokenKind::Le
            | TokenKind::Gt
            | TokenKind::Ge => {
                let op = cmp_op(&tok.kind);
                self.bump();
                let rhs = self.term()?;
                Ok(binary(start, rhs.span, CondKind::Cmp { op, lhs, rhs }))
            }
            TokenKind::Ident(w) => self.atom_word(lhs, w),
            _ => Ok(bare(lhs)),
        }
    }

    /// The atom forms that continue with a word after the left term.
    fn atom_word(&mut self, lhs: Term, word: &str) -> PResult<Cond> {
        let start = lhs.span;
        match word {
            "matches" => {
                self.bump();
                let rhs = self.term()?;
                Ok(binary(start, rhs.span, CondKind::GlobMatch { lhs, rhs }))
            }
            "in" if !self.at_in_unit() => {
                self.bump();
                let rhs = self.range_term()?;
                Ok(binary(start, rhs.span, CondKind::In { lhs, rhs }))
            }
            "is" => self.is_atom(lhs),
            "has" if self.word_nth(1) == Some("attr") && self.is_str_nth(2) => {
                self.bump();
                self.bump();
                let attr = self.plain_str("an attribute name string")?;
                Ok(binary(
                    start,
                    attr.span,
                    CondKind::HasAttr { subject: lhs, attr },
                ))
            }
            w if self.starts_rel_word(w) => {
                let rel = self.rel()?;
                Ok(binary(
                    start,
                    rel.span,
                    CondKind::Rel {
                        subject: lhs,
                        rel: Box::new(rel),
                    },
                ))
            }
            _ => Ok(bare(lhs)),
        }
    }

    fn is_atom(&mut self, subject: Term) -> PResult<Cond> {
        let start = subject.span;
        self.bump();
        let Some(tok) = self.peek() else {
            return self.expected("a kind, a boolean field or a snippet after `is`");
        };
        match &tok.kind {
            TokenKind::Snippet(snippet) => {
                self.bump();
                let mut end = tok.span;
                let mut roles = false;
                if self.at_word("as") {
                    self.bump();
                    end = self.expect_word(
                        "roles",
                        "`roles` after `as` (only `as roles` follows `is`)",
                    )?;
                    roles = true;
                }
                Ok(binary(
                    start,
                    end,
                    CondKind::IsSnippet {
                        subject,
                        snippet: snippet.clone(),
                        roles,
                    },
                ))
            }
            TokenKind::Ident(_) => {
                let test = self.name("a kind or boolean field after `is`")?;
                Ok(binary(start, test.span, CondKind::Is { subject, test }))
            }
            _ => self.expected("a kind, a boolean field or a snippet after `is`"),
        }
    }

    fn is_str_nth(&self, n: usize) -> bool {
        matches!(self.nth(n).map(|t| &t.kind), Some(TokenKind::Str(_)))
    }

    /// True at `in unit` that is a relation rather than membership.
    fn at_in_unit(&self) -> bool {
        self.at_word("in") && self.word_nth(1) == Some("unit") && !self.is_nth(2, &TokenKind::Dot)
    }

    // ---- relations ----

    /// True when the cursor starts a relation after a source.
    pub(super) fn at_rel_start(&self) -> bool {
        match self.word() {
            Some("in") => self.at_in_unit(),
            Some(w) => self.starts_rel_word(w),
            None => false,
        }
    }

    /// A relation word or a verb (any non-reserved word that is not an operator word).
    fn starts_rel_word(&self, w: &str) -> bool {
        if matches!(w, "in" | "is" | "matches") {
            return w == "in" && self.at_in_unit();
        }
        if w == "has" && self.word_nth(1) == Some("attr") && self.is_str_nth(2) {
            return false;
        }
        REL_WORDS.contains(&w) || !is_reserved(w)
    }

    /// A relation and its object.
    pub(super) fn rel(&mut self) -> PResult<Rel> {
        let start = self.here();
        let Some(word) = self.word() else {
            return self.expected("a relation such as `inside` or a verb such as `calls`");
        };
        match word {
            "directly" => {
                self.bump();
                let dir = match self.word() {
                    Some("inside") => Containment::Inside,
                    Some("has") => Containment::Has,
                    _ => return self.expected("`inside` or `has` after `directly`"),
                };
                self.bump();
                let object = self.object()?;
                Ok(rel_node(
                    start,
                    object.span(),
                    RelKind::Containment {
                        directly: true,
                        dir,
                        object,
                    },
                ))
            }
            "inside" | "has" => {
                let dir = if word == "inside" {
                    Containment::Inside
                } else {
                    Containment::Has
                };
                self.bump();
                let object = self.object()?;
                Ok(rel_node(
                    start,
                    object.span(),
                    RelKind::Containment {
                        directly: false,
                        dir,
                        object,
                    },
                ))
            }
            "in" => {
                self.bump();
                self.expect_word("unit", "`unit` after `in`")?;
                let object = self.object()?;
                Ok(rel_node(start, object.span(), RelKind::InUnit { object }))
            }
            "under" => {
                self.bump();
                let term = self.term()?;
                Ok(Spanned {
                    span: cover(start, term.span),
                    node: RelKind::Under { term },
                })
            }
            "before" | "after" | "adjoins" => {
                let position = match word {
                    "before" => Position::Before,
                    "after" => Position::After,
                    _ => Position::Adjoins,
                };
                self.bump();
                let object = self.object()?;
                Ok(rel_node(
                    start,
                    object.span(),
                    RelKind::Position { position, object },
                ))
            }
            "reaches" => self.reaches(),
            "certainly" | "possibly" => {
                let certainty = if word == "certainly" {
                    Certainty::Certainly
                } else {
                    Certainty::Possibly
                };
                self.bump();
                self.verb_rel(start, Some(certainty))
            }
            _ => self.verb_rel(start, None),
        }
    }

    fn verb_rel(&mut self, start: gob_text::Span, certainty: Option<Certainty>) -> PResult<Rel> {
        let verb = self.verb("a verb such as `calls`")?;
        let object = self.object()?;
        Ok(rel_node(
            start,
            object.span(),
            RelKind::Verb {
                certainty,
                verb,
                object,
            },
        ))
    }

    /// A verb: one word, or one of the two-word verbs joined with a single space.
    fn verb(&mut self, what: &str) -> PResult<Word> {
        let mut verb = self.name(what)?;
        if let Some((_, second)) = MULTI_WORD_VERBS
            .iter()
            .find(|(first, _)| *first == verb.text)
            && self.at_word(second)
        {
            let tail = self.here();
            self.bump();
            verb.text.push(' ');
            verb.text.push_str(second);
            verb.span = cover(verb.span, tail);
        }
        Ok(verb)
    }

    fn reaches(&mut self) -> PResult<Rel> {
        let start = self.here();
        self.bump();
        let target = self.object()?;
        self.expect_word(
            "via",
            "`via` and the verbs to follow, as in `reaches f via calls within 6`",
        )?;
        let mut via = vec![self.verb("a verb after `via`")?];
        while self.eat(&TokenKind::Comma).is_some() {
            via.push(self.verb("a verb after `,`")?);
        }
        let mut end = via[via.len() - 1].span;
        let within = if self.eat_word("within").is_some() {
            let term = self.term()?;
            end = term.span;
            Some(term)
        } else {
            None
        };
        Ok(Spanned {
            span: cover(start, end),
            node: RelKind::Reaches {
                target,
                via,
                within,
            },
        })
    }

    /// The object of a relation: an anonymous shape or a term.
    pub(super) fn object(&mut self) -> PResult<Object> {
        let shape_start = match self.peek().map(|t| &t.kind) {
            Some(TokenKind::Snippet(_) | TokenKind::LParen) => true,
            Some(TokenKind::Ident(w)) if !is_reserved(w) && w != "count" => {
                self.is_nth(1, &TokenKind::LParen) || self.is_str_nth(1)
            }
            _ => false,
        };
        if shape_start {
            Ok(Object::Shape(self.shape()?))
        } else {
            Ok(Object::Term(self.term()?))
        }
    }

    // ---- terms ----

    /// A term with `+ - *` (multiplication binds tighter).
    pub(super) fn term(&mut self) -> PResult<Term> {
        self.nest(Self::additive)
    }

    fn additive(&mut self) -> PResult<Term> {
        let mut lhs = self.multiplicative()?;
        loop {
            let op = match self.peek().map(|t| &t.kind) {
                Some(TokenKind::Plus) => ArithOp::Add,
                Some(TokenKind::Minus) => ArithOp::Sub,
                _ => return Ok(lhs),
            };
            self.bump();
            let rhs = self.multiplicative()?;
            lhs = arith(op, lhs, rhs);
        }
    }

    fn multiplicative(&mut self) -> PResult<Term> {
        let mut lhs = self.primary()?;
        while self.eat(&TokenKind::Star).is_some() {
            let rhs = self.primary()?;
            lhs = arith(ArithOp::Mul, lhs, rhs);
        }
        Ok(lhs)
    }

    /// A term that may be a range `a..b` (right of `in`).
    fn range_term(&mut self) -> PResult<Term> {
        let lo = self.term()?;
        if self.eat(&TokenKind::DotDot).is_none() {
            return Ok(lo);
        }
        let hi = self.term()?;
        Ok(Spanned {
            span: cover(lo.span, hi.span),
            node: TermKind::Range {
                lo: Box::new(lo),
                hi: Box::new(hi),
            },
        })
    }

    fn primary(&mut self) -> PResult<Term> {
        const WHAT: &str =
            "a value: a name such as `f.name`, a number, a string, `knob.NAME` or `count(...)`";
        let Some(tok) = self.peek() else {
            return self.expected(WHAT);
        };
        match &tok.kind {
            TokenKind::Int(_)
            | TokenKind::Decimal(_)
            | TokenKind::Str(_)
            | TokenKind::Regex(_)
            | TokenKind::Minus
            | TokenKind::LBracket => {
                let lit = self.literal()?;
                Ok(Spanned {
                    span: lit.span,
                    node: TermKind::Literal(lit),
                })
            }
            TokenKind::Ident(w) => self.word_term(tok, w),
            _ => self.expected(WHAT),
        }
    }

    fn word_term(&mut self, tok: &Token, w: &str) -> PResult<Term> {
        if w == "true" || w == "false" {
            self.bump();
            let lit = Spanned {
                node: LiteralKind::Bool(w == "true"),
                span: tok.span,
            };
            return Ok(Spanned {
                span: tok.span,
                node: TermKind::Literal(lit),
            });
        }
        if w == "knob" && self.is_nth(1, &TokenKind::Dot) {
            self.bump();
            self.bump();
            let name = self.ident("a knob name after `knob.`")?;
            return Ok(Spanned {
                span: cover(tok.span, name.span),
                node: TermKind::Knob(name),
            });
        }
        if w == "count" && self.is_nth(1, &TokenKind::LParen) {
            self.bump();
            self.bump();
            let binding = self.binding("count(")?;
            let close = self.expect(&TokenKind::RParen, "`)` to close `count(...)`")?;
            return Ok(Spanned {
                span: cover(tok.span, close),
                node: TermKind::Count(Box::new(binding)),
            });
        }
        if is_reserved(w) {
            return self.expected(
                "a value: a name such as `f.name`, a number, a string, `knob.NAME` or `count(...)`",
            );
        }
        if self.is_nth(1, &TokenKind::LParen) {
            let call = self.call()?;
            return Ok(Spanned {
                span: call.span,
                node: TermKind::Call(call),
            });
        }
        let first = self.ident("a name")?;
        let path: Path = self.path_from(first)?;
        Ok(Spanned {
            span: path.span,
            node: TermKind::Path(path),
        })
    }

    fn call(&mut self) -> PResult<Call> {
        let name = self.ident("a function name")?;
        self.bump();
        let mut args = Vec::new();
        if !self.is(&TokenKind::RParen) {
            loop {
                args.push(self.term()?);
                if self.eat(&TokenKind::Comma).is_none() {
                    break;
                }
            }
        }
        let close = self.expect(&TokenKind::RParen, "`,` or `)` after the argument")?;
        Ok(Call {
            span: cover(name.span, close),
            name,
            args,
        })
    }

    /// Parse `NAME(args)` where terms are allowed as arguments (used by `fix host`).
    pub(super) fn call_args(&mut self) -> PResult<(Vec<Term>, gob_text::Span)> {
        self.expect(&TokenKind::LParen, "`(` after the host fix name")?;
        let mut args = Vec::new();
        if !self.is(&TokenKind::RParen) {
            loop {
                args.push(self.term()?);
                if self.eat(&TokenKind::Comma).is_none() {
                    break;
                }
            }
        }
        let close = self.expect(&TokenKind::RParen, "`,` or `)` after the argument")?;
        Ok((args, close))
    }
}

fn cmp_op(kind: &TokenKind) -> CmpOp {
    match kind {
        TokenKind::Ne => CmpOp::Ne,
        TokenKind::Lt => CmpOp::Lt,
        TokenKind::Le => CmpOp::Le,
        TokenKind::Gt => CmpOp::Gt,
        TokenKind::Ge => CmpOp::Ge,
        _ => CmpOp::Eq,
    }
}

fn arith(op: ArithOp, lhs: Term, rhs: Term) -> Term {
    Spanned {
        span: cover(lhs.span, rhs.span),
        node: TermKind::Binary {
            op,
            lhs: Box::new(lhs),
            rhs: Box::new(rhs),
        },
    }
}

fn binary(start: gob_text::Span, end: gob_text::Span, node: CondKind) -> Cond {
    Spanned {
        node,
        span: cover(start, end),
    }
}

/// A term standing alone as a condition: a def call, or a boolean field.
fn bare(term: Term) -> Cond {
    match term {
        Spanned {
            node: TermKind::Call(call),
            span,
        } => Spanned {
            node: CondKind::DefCall(call),
            span,
        },
        other => Spanned {
            span: other.span,
            node: CondKind::Flag(other),
        },
    }
}

fn rel_node(start: gob_text::Span, end: gob_text::Span, node: RelKind) -> Rel {
    Spanned {
        span: cover(start, end),
        node,
    }
}

fn join(make: fn(Vec<Cond>) -> CondKind, parts: Vec<Cond>) -> Cond {
    let span = cover(parts[0].span, parts[parts.len() - 1].span);
    Spanned {
        node: make(parts),
        span,
    }
}
