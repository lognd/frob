//! Files, rules, headers, examples and explain blocks, with item-level recovery.

use gob_text::Span;

use super::clause::CLAUSE_WORDS;
use super::cursor::{PResult, Parser, cover, describe, is_reserved};
use super::error::{ParseErrorKind, ParseWarningKind};
use crate::grl::ast::{
    Clause, Example, ExampleBody, Expect, ExpectKind, Explain, File, Header, HeaderKind, Input,
    InputKind, Knob, LangSet, Polarity, Rollup, Rule, Scope, Severity, Spanned, StrLit, Word,
};
use crate::grl::token::{StrPart, Token, TokenKind};

/// Words that start a header.
const HEADER_WORDS: &[&str] = &[
    "lang",
    "polarity",
    "severity",
    "scope",
    "must_measure",
    "needs",
    "rollup",
    "knob",
];

/// Words that start an example input.
const INPUT_WORDS: &[&str] = &[
    "file", "config", "model", "diff", "lease", "expect", "fixed",
];

/// Where an item sits in a rule: headers, clauses, examples, then explain.
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
enum Stage {
    Header,
    Clause,
    Example,
    Explain,
}

/// The pieces of a rule body as they are read.
#[derive(Default)]
struct Body {
    headers: Vec<Header>,
    clauses: Vec<Clause>,
    examples: Vec<Example>,
    explain: Option<Explain>,
    explain_seen: bool,
    close: Option<Span>,
}

impl Parser<'_> {
    /// Parse every rule in the file.
    pub(super) fn file(&mut self) -> File {
        let mut rules = Vec::new();
        while !self.at_end() {
            if self.at_word("rule") {
                if let Some(rule) = self.rule() {
                    rules.push(rule);
                }
                continue;
            }
            let found = describe(self.peek());
            let span = self.here();
            self.error(ParseErrorKind::NotARule { found }, span);
            self.skip_to(|p| p.at_word("rule"));
            if !self.at_end() && !self.at_word("rule") {
                self.bump();
            }
        }
        File { rules }
    }

    fn rule(&mut self) -> Option<Rule> {
        let start = self.here();
        self.bump();
        self.bal = 0;
        let Ok((id, slug, open)) = self.rule_head() else {
            self.skip_to_open_brace();
            if let Some(open) = self.eat(&TokenKind::LBrace) {
                let _ = self.rule_body(open, "?");
            }
            return None;
        };
        let body = self.rule_body(open, &id.text);
        let end = body.close.unwrap_or_else(|| self.prev_span());
        tracing::trace!(rule = %id.text, "parsed rule");
        Some(Rule {
            id,
            slug,
            headers: body.headers,
            clauses: body.clauses,
            examples: body.examples,
            explain: body.explain,
            span: cover(start, end),
        })
    }

    fn rule_head(&mut self) -> PResult<(Word, StrLit, Span)> {
        let Some(Token {
            kind: TokenKind::RuleId(id),
            span,
        }) = self.peek()
        else {
            return self.expected_hint(
                "a rule id such as `TODO001` after `rule`",
                Some("rule ids are capital letters then three digits"),
            );
        };
        self.bump();
        let id = Word {
            text: id.clone(),
            span: *span,
        };
        let slug = self.plain_str("the rule's slug in quotes after its id")?;
        let open = self.expect(&TokenKind::LBrace, "`{` to open the rule body")?;
        Ok((id, slug, open))
    }

    fn skip_to_open_brace(&mut self) {
        while let Some(tok) = self.peek() {
            if tok.kind == TokenKind::LBrace || self.at_word("rule") {
                return;
            }
            self.bump();
        }
    }

    /// Read items until the closing brace.
    fn rule_body(&mut self, open: Span, id: &str) -> Body {
        let mut body = Body::default();
        let mut stage = Stage::Header;
        loop {
            self.bal = 0;
            let before = self.pos;
            let Some(tok) = self.peek() else {
                self.error(ParseErrorKind::UnclosedRule, open);
                break;
            };
            if tok.kind == TokenKind::RBrace {
                body.close = Some(tok.span);
                self.bump();
                break;
            }
            let item_stage = self.word().and_then(|w| self.stage_of(w));
            if let Some(item) = item_stage {
                self.check_order(stage, item, tok.span);
                stage = stage.max(item);
                self.item(item, &mut body);
            } else {
                let _: PResult<()> = self.expected("a header, a clause, an `example` or `explain`");
                self.skip_to(Self::is_item_start);
            }
            if self.pos == before {
                self.bump();
            }
        }
        if !body.explain_seen {
            let at = body.close.unwrap_or_else(|| self.here());
            self.error(ParseErrorKind::MissingExplain(id.to_owned()), at);
        }
        body
    }

    fn stage_of(&self, w: &str) -> Option<Stage> {
        if !(self.is_item_start() || (w == "where" && !self.prev_is_dot())) {
            return None;
        }
        if HEADER_WORDS.contains(&w) {
            Some(Stage::Header)
        } else if CLAUSE_WORDS.contains(&w) {
            Some(Stage::Clause)
        } else if w == "example" {
            Some(Stage::Example)
        } else if w == "explain" {
            Some(Stage::Explain)
        } else {
            None
        }
    }

    /// True when the word at the cursor begins a rule item (and is not a field or condition word).
    fn is_item_start(&self) -> bool {
        let Some(w) = self.word() else { return false };
        let after_dot = self.pos.checked_sub(1).is_some_and(|_| self.prev_is_dot());
        if after_dot {
            return false;
        }
        match w {
            "knob" => !self.is_nth(1, &TokenKind::Dot),
            "some" | "no" => self.at_quant(),
            "where" => self.starts_line(),
            _ => {
                HEADER_WORDS.contains(&w)
                    || CLAUSE_WORDS.contains(&w)
                    || w == "example"
                    || w == "explain"
            }
        }
    }

    /// True when only whitespace including a line break separates the cursor from the previous token.
    fn starts_line(&self) -> bool {
        let Some(tok) = self.peek() else { return false };
        let Some(prev) = self.pos.checked_sub(1).and_then(|i| self.token_at(i)) else {
            return true;
        };
        let gap = prev.span.range.end().to_usize()..tok.span.range.start().to_usize();
        self.text.get(gap).is_some_and(|g| g.contains('\n'))
    }

    fn prev_is_dot(&self) -> bool {
        self.pos
            .checked_sub(1)
            .and_then(|i| self.token_at(i))
            .is_some_and(|t| t.kind == TokenKind::Dot)
    }

    fn check_order(&mut self, current: Stage, item: Stage, at: Span) {
        let word = self.word().unwrap_or_default().to_owned();
        if current == Stage::Explain {
            if item == Stage::Explain {
                self.error(ParseErrorKind::DuplicateExplain, at);
            } else {
                self.error(
                    ParseErrorKind::Misplaced {
                        what: format!("`{word}`"),
                        rule_order: "before `explain`",
                    },
                    at,
                );
            }
        } else if item < current {
            let (what, order) = match item {
                Stage::Header => ("a header", "before the clauses"),
                Stage::Clause => ("a clause", "before the examples"),
                _ => ("an example", "before `explain`"),
            };
            self.error(
                ParseErrorKind::Misplaced {
                    what: format!("{what} (`{word}`)"),
                    rule_order: order,
                },
                at,
            );
        }
    }

    fn item(&mut self, stage: Stage, body: &mut Body) {
        let began = self.here();
        let result = match stage {
            Stage::Header => self.header().map(|h| body.headers.push(h)),
            Stage::Clause => self.clause().map(|c| body.clauses.push(c)),
            Stage::Example => self.example().map(|e| body.examples.push(e)),
            Stage::Explain => {
                body.explain_seen = true;
                self.explain().map(|e| {
                    if body.explain.is_none() {
                        body.explain = Some(e);
                    }
                })
            }
        };
        if result.is_err() {
            tracing::trace!(at = %began.range, "recovering after a bad item");
            self.skip_to(Self::is_item_start);
        }
    }

    // ---- headers ----

    fn header(&mut self) -> PResult<Header> {
        let start = self.here();
        let word = self.word().unwrap_or_default();
        self.bump();
        let node = match word {
            "lang" => HeaderKind::Lang(self.lang_set()?),
            "polarity" => HeaderKind::Polarity(self.polarity()?),
            "severity" => HeaderKind::Severity(self.choice(
                "a severity",
                "`error`, `warn` and `advisory`",
                &[
                    ("error", Severity::Error),
                    ("warn", Severity::Warn),
                    ("advisory", Severity::Advisory),
                ],
            )?),
            "scope" => HeaderKind::Scope(self.choice(
                "a scope",
                "`file` and `repo`",
                &[("file", Scope::File), ("repo", Scope::Repo)],
            )?),
            "rollup" => HeaderKind::Rollup(self.choice(
                "a rollup",
                "`file`, `directory` and `unit`",
                &[
                    ("file", Rollup::File),
                    ("directory", Rollup::Directory),
                    ("unit", Rollup::Unit),
                ],
            )?),
            "must_measure" => HeaderKind::MustMeasure,
            "needs" => {
                let mut names = vec![self.need("a name after `needs`")?];
                while self.eat(&TokenKind::Comma).is_some() {
                    names.push(self.need("a name after `,`")?);
                }
                HeaderKind::Needs(names)
            }
            _ => HeaderKind::Knob(self.knob()?),
        };
        Ok(Spanned {
            node,
            span: cover(start, self.prev_span()),
        })
    }

    /// One `needs` entry: a capability name, or `vocab(NAME)` kept as the single word `vocab(NAME)`.
    fn need(&mut self, what: &str) -> PResult<Word> {
        let mut word = self.name(what)?;
        if word.text == "vocab" && self.eat(&TokenKind::LParen).is_some() {
            let inner = self.name("a vocabulary knob name after `vocab(`")?;
            let close = self.expect(&TokenKind::RParen, "`)` closing `vocab(`")?;
            word.text = format!("vocab({})", inner.text);
            word.span = cover(word.span, close);
        }
        Ok(word)
    }

    fn lang_set(&mut self) -> PResult<LangSet> {
        const WHAT: &str = "a language id such as `rust`, `*`, `-` or `[rust, python]`";
        let Some(tok) = self.peek() else {
            return self.expected(WHAT);
        };
        match &tok.kind {
            TokenKind::Star => {
                self.bump();
                Ok(LangSet::Any { quoted: false })
            }
            TokenKind::Minus => {
                self.bump();
                Ok(LangSet::Nothing)
            }
            TokenKind::Str(parts) if matches!(parts.as_slice(), [StrPart::Text { value, .. }] if value == "*") =>
            {
                self.bump();
                self.warn(ParseWarningKind::QuotedLangStar, tok.span);
                Ok(LangSet::Any { quoted: true })
            }
            TokenKind::Ident(_) => Ok(LangSet::One(self.name(WHAT)?)),
            TokenKind::LBracket => {
                self.bump();
                let mut langs = vec![self.name("a language id")?];
                while self.eat(&TokenKind::Comma).is_some() {
                    langs.push(self.name("a language id after `,`")?);
                }
                self.expect(&TokenKind::RBracket, "`,` or `]` in the language list")?;
                Ok(LangSet::List(langs))
            }
            _ => self.expected_hint(WHAT, Some("language ids are bare words, never quoted")),
        }
    }

    fn polarity(&mut self) -> PResult<Polarity> {
        if let Some(Token {
            kind: TokenKind::Polarity(p),
            ..
        }) = self.peek()
        {
            self.bump();
            return Ok(match p.as_str() {
                "P+" => Polarity::Pplus,
                "P-" => Polarity::Pminus,
                "P0" => Polarity::P0,
                "Pn" => Polarity::Pn,
                _ => Polarity::Pc,
            });
        }
        self.expected("a polarity: `P+`, `P-`, `P0`, `Pn` or `Pc`")
    }

    /// One word out of a closed set; other words are a `BadChoice` error.
    fn choice<T: Copy>(
        &mut self,
        what: &'static str,
        choices: &'static str,
        table: &[(&str, T)],
    ) -> PResult<T> {
        let word = self.ident(&format!("{what}: {choices}"))?;
        match table.iter().find(|(w, _)| *w == word.text) {
            Some((_, v)) => Ok(*v),
            None => self.fail(
                ParseErrorKind::BadChoice {
                    what,
                    found: word.text,
                    choices,
                },
                word.span,
            ),
        }
    }

    fn knob(&mut self) -> PResult<Knob> {
        let name = self.name("a knob name after `knob`")?;
        self.expect(&TokenKind::Colon, "`:` and the knob's type")?;
        let ty = self.type_ref()?;
        self.expect(&TokenKind::Eq, "`=` and the knob's default value")?;
        let default = self.literal()?;
        let doc = self.plain_str("the knob's description in quotes after its value")?;
        Ok(Knob {
            name,
            ty,
            default,
            doc,
        })
    }

    // ---- examples and explain ----

    fn example(&mut self) -> PResult<Example> {
        let start = self.here();
        self.bump();
        let expect = self.expect_kind()?;
        let lang = if self.word().is_some_and(|w| !is_reserved(w)) {
            Some(self.ident("a language id")?)
        } else {
            None
        };
        let name = if matches!(self.peek().map(|t| &t.kind), Some(TokenKind::Str(_))) {
            Some(self.plain_str("the example's name")?)
        } else {
            None
        };
        let body = if matches!(self.peek().map(|t| &t.kind), Some(TokenKind::Block(_))) {
            ExampleBody::Source(self.block("the example source")?)
        } else if self.is(&TokenKind::LBrace) {
            ExampleBody::Inputs(self.inputs())
        } else {
            return self.expected("`{` or a triple-quoted block holding the example's source");
        };
        Ok(Example {
            expect,
            lang,
            name,
            body,
            span: cover(start, self.prev_span()),
        })
    }

    fn expect_kind(&mut self) -> PResult<Expect> {
        const CHOICES: &str = "`fire`, `clean`, `unresolved`, `notapplicable` and `known-gap`";
        let word = self.hyphen_word(&format!(
            "what the example must do after `example`: {CHOICES}"
        ))?;
        let kind = match word.text.as_str() {
            "fire" => ExpectKind::Fire,
            "clean" => ExpectKind::Clean,
            "unresolved" => ExpectKind::Unresolved,
            "notapplicable" => ExpectKind::NotApplicable,
            "known-gap" => ExpectKind::KnownGap,
            _ => {
                return self.fail(
                    ParseErrorKind::BadChoice {
                        what: "an example outcome",
                        found: word.text,
                        choices: CHOICES,
                    },
                    word.span,
                );
            }
        };
        Ok(Expect {
            kind,
            span: word.span,
        })
    }

    /// `{ input ... }`; bad inputs are reported and skipped.
    fn inputs(&mut self) -> Vec<Input> {
        self.bump();
        let mut inputs = Vec::new();
        loop {
            self.bal = 0;
            let before = self.pos;
            if self.is(&TokenKind::RBrace) {
                self.bump();
                break;
            }
            if self.at_end() {
                let _: PResult<()> = self.expected("`}` to close the example");
                break;
            }
            if self.word().is_some_and(|w| INPUT_WORDS.contains(&w)) {
                match self.input() {
                    Ok(input) => inputs.push(input),
                    Err(_) => self.skip_to(Self::is_input_start),
                }
            } else {
                let _: PResult<()> = self.expected(
                    "an input (`file`, `config`, `model`, `diff`, `lease`, `expect` or `fixed`) or `}`",
                );
                self.skip_to(Self::is_input_start);
            }
            if self.pos == before {
                self.bump();
            }
        }
        inputs
    }

    fn is_input_start(&self) -> bool {
        self.word().is_some_and(|w| INPUT_WORDS.contains(&w)) && !self.prev_is_dot()
    }

    fn input(&mut self) -> PResult<Input> {
        let start = self.here();
        let word = self.word().unwrap_or_default();
        self.bump();
        let node = match word {
            "file" => {
                let path = self.plain_str("the file's path in quotes after `file`")?;
                let text = self.block("the file's text as a triple-quoted block")?;
                InputKind::File { path, text }
            }
            "config" => InputKind::Config(self.block("the config text as a triple-quoted block")?),
            "model" => InputKind::Model(self.block("the model text as a triple-quoted block")?),
            "fixed" => {
                InputKind::Fixed(self.block("the expected output as a triple-quoted block")?)
            }
            "expect" => InputKind::Expect(
                self.plain_str("the expectation in quotes, such as \"line 3: warn\"")?,
            ),
            "diff" => InputKind::Diff(self.string_list()?),
            _ => InputKind::Lease(self.string_list()?),
        };
        Ok(Spanned {
            node,
            span: cover(start, self.prev_span()),
        })
    }

    fn string_list(&mut self) -> PResult<Vec<StrLit>> {
        self.expect(&TokenKind::LBracket, "`[` and a list of strings")?;
        let mut items = Vec::new();
        if !self.is(&TokenKind::RBracket) {
            loop {
                items.push(self.plain_str("a string")?);
                if self.eat(&TokenKind::Comma).is_none() {
                    break;
                }
            }
        }
        self.expect(&TokenKind::RBracket, "`,` or `]` in the list")?;
        Ok(items)
    }

    fn explain(&mut self) -> PResult<Explain> {
        let start = self.here();
        self.bump();
        let text = self.block("the rule page as a triple-quoted block after `explain`")?;
        Ok(Explain {
            span: cover(start, text.span),
            text,
        })
    }
}
