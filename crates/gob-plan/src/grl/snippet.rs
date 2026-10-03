//! Backtick snippets: raw text, `$` metavariables, double-backtick form.

use super::error::{LexError, LexErrorKind};
use super::lexer::Lexer;
use super::token::{MetaKind, MetaVar, Snippet, SnippetLang, TokenKind};

fn is_name_start(c: char) -> bool {
    c.is_ascii_uppercase() || c == '_'
}

fn is_name_char(c: char) -> bool {
    c.is_ascii_uppercase() || c.is_ascii_digit() || c == '_'
}

impl Lexer<'_> {
    /// A snippet starting at `start`; `tick` is the opening backtick when a language tag precedes it.
    pub(super) fn snippet(&mut self, start: usize, tick: Option<usize>) -> Result<(), LexError> {
        let open = tick.unwrap_or(start);
        let lang = tick.map(|t| SnippetLang {
            name: self.src[start..t].to_owned(),
            span: self.span(start, t),
        });
        self.pos = open;
        let ticks: u8 = if self.rest().starts_with("``") { 2 } else { 1 };
        self.pos += usize::from(ticks);
        let close = if ticks == 2 { "``" } else { "`" };
        let body = self.pos;
        let mut metavars = Vec::new();
        let mut dollars = Vec::new();
        loop {
            if self.rest().starts_with(close) {
                break;
            }
            let at = self.pos;
            match self.bump() {
                None => {
                    return self.err(
                        LexErrorKind::UnterminatedSnippet { ticks },
                        open,
                        open + usize::from(ticks),
                    );
                }
                Some('$') => {
                    self.pos = at;
                    self.dollars(&mut metavars, &mut dollars)?;
                }
                Some(_) => {}
            }
        }
        let text = self.src[body..self.pos].to_owned();
        let body_span = self.span(body, self.pos);
        self.pos += usize::from(ticks);
        self.push(
            TokenKind::Snippet(Snippet {
                lang,
                ticks,
                text,
                body: body_span,
                metavars,
                dollars,
            }),
            start,
        );
        Ok(())
    }

    /// Consume a run of dollars (and a following name) at the cursor.
    fn dollars(
        &mut self,
        metavars: &mut Vec<MetaVar>,
        literals: &mut Vec<gob_text::Span>,
    ) -> Result<(), LexError> {
        let run_start = self.pos;
        while self.eat('$') {}
        let mut n = self.pos - run_start;
        let mut at = run_start;
        while n > 3 || n == 2 {
            literals.push(self.span(at, at + 2));
            at += 2;
            n -= 2;
        }
        if n == 0 {
            return Ok(());
        }
        let name_start = self.pos;
        if self.peek().is_some_and(is_name_start) {
            while self.peek().is_some_and(is_name_char) {
                self.bump();
            }
        } else if self.peek().is_some_and(|c| c.is_ascii_lowercase()) {
            while self
                .peek()
                .is_some_and(|c| c.is_ascii_alphanumeric() || c == '_')
            {
                self.bump();
            }
            let written = self.src[at..self.pos].to_owned();
            return self.err(LexErrorKind::LowercaseMetavar(written), at, self.pos);
        } else if n == 1 {
            return self.err(LexErrorKind::LoneDollar, at, self.pos);
        }
        let name = &self.src[name_start..self.pos];
        let name = (!name.is_empty() && name != "_").then(|| name.to_owned());
        let kind = if n == 1 { MetaKind::One } else { MetaKind::Seq };
        metavars.push(MetaVar {
            kind,
            name,
            span: self.span(at, self.pos),
        });
        Ok(())
    }
}
