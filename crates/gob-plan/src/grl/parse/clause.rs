//! Clauses: find, where, some, no, def, report, note, fix and unresolved.

use super::cursor::{PResult, Parser, cover};
use super::error::ParseErrorKind;
use crate::grl::ast::{
    Applicability, ApplicabilityKind, Clause, ClauseKind, Def, Fix, FixKind, Note, Placement,
    Report, Spanned, Unresolved,
};
use crate::grl::token::{Token, TokenKind};

/// Words that start a clause.
pub(super) const CLAUSE_WORDS: &[&str] = &[
    "find",
    "where",
    "some",
    "no",
    "def",
    "report",
    "note",
    "fix",
    "unresolved",
];

impl Parser<'_> {
    /// Parse the clause starting at the cursor (its keyword is a clause word).
    pub(super) fn clause(&mut self) -> PResult<Clause> {
        let start = self.here();
        let word = self.word().unwrap_or_default();
        let node = match word {
            "find" => {
                self.bump();
                ClauseKind::Find(self.binding("find")?)
            }
            "where" => {
                self.bump();
                ClauseKind::Where(self.cond()?)
            }
            "some" | "no" => {
                let (quant, _) = self.quant_word()?;
                let name = if word == "some" { "some" } else { "no" };
                ClauseKind::Quant {
                    quant,
                    binding: self.binding(name)?,
                }
            }
            "def" => {
                self.bump();
                ClauseKind::Def(self.def()?)
            }
            "report" => {
                self.bump();
                ClauseKind::Report(self.report()?)
            }
            "note" => {
                self.bump();
                let target = self.name("the variable to attach the note to, after `note`")?;
                let message = self.message("the note text in quotes")?;
                ClauseKind::Note(Note { target, message })
            }
            "fix" => {
                self.bump();
                ClauseKind::Fix(self.fix()?)
            }
            _ => {
                self.bump();
                let when = {
                    self.expect_word("when", "`when` after `unresolved`")?;
                    self.cond()?
                };
                self.expect_word("because", "`because \"reason\"` after the condition")?;
                let because = self.message("the reason in quotes")?;
                ClauseKind::Unresolved(Unresolved { when, because })
            }
        };
        Ok(Spanned {
            node,
            span: cover(start, self.prev_span()),
        })
    }

    fn def(&mut self) -> PResult<Def> {
        let name = self.name("a def name after `def`")?;
        self.expect(
            &TokenKind::LParen,
            "`(` and the parameters after the def name",
        )?;
        let mut params = Vec::new();
        if !self.is(&TokenKind::RParen) {
            loop {
                params.push(self.name("a parameter name")?);
                if self.eat(&TokenKind::Comma).is_none() {
                    break;
                }
            }
        }
        self.expect(&TokenKind::RParen, "`,` or `)` after the parameter")?;
        self.expect(&TokenKind::Eq, "`=` and the body after the parameters")?;
        let body = self.cond()?;
        Ok(Def { name, params, body })
    }

    fn report(&mut self) -> PResult<Report> {
        let target = self.name("the variable to report, after `report`")?;
        let message = self.message("the message in quotes after the variable")?;
        let when = if self.eat_word("when").is_some() {
            Some(self.cond()?)
        } else {
            None
        };
        Ok(Report {
            target,
            message,
            when,
        })
    }

    fn fix(&mut self) -> PResult<Fix> {
        match self.word() {
            Some("delete") => {
                self.bump();
                let target = self.name("the variable to delete, after `fix delete`")?;
                let applicability = self.applicability()?;
                Ok(Fix {
                    kind: FixKind::Delete { target },
                    applicability,
                })
            }
            Some("host") => {
                self.bump();
                let name = self.name("the host fix name after `fix host`")?;
                let (args, _) = self.call_args()?;
                let applicability = self.applicability()?;
                Ok(Fix {
                    kind: FixKind::Host { name, args },
                    applicability,
                })
            }
            Some("manual") => {
                self.bump();
                let message = self.message("the steps in quotes after `fix manual`")?;
                Ok(Fix {
                    kind: FixKind::Manual { message },
                    applicability: None,
                })
            }
            _ => self.fix_replace(),
        }
    }

    fn fix_replace(&mut self) -> PResult<Fix> {
        let placement = match (self.word(), self.word_nth(1)) {
            (Some("before"), Some(_)) => Some(Placement::Before),
            (Some("after"), Some(_)) => Some(Placement::After),
            _ => None,
        };
        if placement.is_some() {
            self.bump();
        }
        let target = self.name("the variable to fix, after `fix`")?;
        self.expect(&TokenKind::Arrow, "`->` and the replacement snippet")?;
        let Some(Token {
            kind: TokenKind::Snippet(with),
            span,
        }) = self.peek()
        else {
            return self.expected("the replacement snippet in backticks after `->`");
        };
        self.bump();
        let applicability = self.applicability()?;
        Ok(Fix {
            kind: FixKind::Replace {
                placement,
                target,
                with: with.clone(),
                with_span: *span,
            },
            applicability,
        })
    }

    /// `[machine]`, `[maybe-incorrect]` or `[has-placeholders]`; absent is `None` (GRL015 later).
    fn applicability(&mut self) -> PResult<Option<Applicability>> {
        if self.eat(&TokenKind::LBracket).is_none() {
            return Ok(None);
        }
        let word = self.hyphen_word("`machine`, `maybe-incorrect` or `has-placeholders`")?;
        let kind = match word.text.as_str() {
            "machine" => ApplicabilityKind::Machine,
            "maybe-incorrect" => ApplicabilityKind::MaybeIncorrect,
            "has-placeholders" => ApplicabilityKind::HasPlaceholders,
            _ => {
                return self.fail(
                    ParseErrorKind::BadChoice {
                        what: "a fix applicability",
                        found: word.text,
                        choices: "`machine`, `maybe-incorrect` and `has-placeholders`",
                    },
                    word.span,
                );
            }
        };
        self.expect(&TokenKind::RBracket, "`]` after the applicability")?;
        Ok(Some(Applicability {
            kind,
            span: word.span,
        }))
    }
}
