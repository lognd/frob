//! `"..."` strings (raw, escape-checked; the parser splits interpolation) and `"""..."""` blocks.

use super::error::{LexError, LexErrorKind};
use super::lexer::Lexer;
use super::token::{Block, TokenKind};

impl Lexer<'_> {
    /// A string or block string; the opening quote is at `start`.
    pub(super) fn string(&mut self, start: usize) -> Result<(), LexError> {
        if self.rest().starts_with("\"\"\"") {
            return self.block(start);
        }
        self.bump();
        let body = self.pos;
        loop {
            let at = self.pos;
            match self.bump() {
                None | Some('\n' | '\r') => {
                    return self.err(LexErrorKind::UnterminatedString, start, at);
                }
                Some('"') => {
                    let raw = self.src[body..at].to_owned();
                    self.push(TokenKind::Str(raw), start);
                    return Ok(());
                }
                Some('\\') => match self.bump() {
                    Some('"' | '\\' | 'n' | '{' | '}') => {}
                    None => return self.err(LexErrorKind::UnterminatedString, start, at),
                    Some(c) => return self.err(LexErrorKind::UnknownEscape(c), at, self.pos),
                },
                Some(_) => {}
            }
        }
    }

    /// A `"""` block; the first quote is at `start`. Content is raw.
    fn block(&mut self, start: usize) -> Result<(), LexError> {
        self.pos += 3;
        let body = self.pos;
        let Some(len) = self.rest().find("\"\"\"") else {
            return self.err(LexErrorKind::UnterminatedBlock, start, start + 3);
        };
        let raw = &self.src[body..body + len];
        let value = dedent(raw);
        let body_span = self.span(body, body + len);
        self.pos = body + len + 3;
        self.push(
            TokenKind::Block(Block {
                value,
                body: body_span,
            }),
            start,
        );
        Ok(())
    }
}

/// Drop a blank first and last line, then remove the common leading indentation.
fn dedent(raw: &str) -> String {
    let mut lines: Vec<&str> = raw
        .split('\n')
        .map(|l| l.strip_suffix('\r').unwrap_or(l))
        .collect();
    let blank = |l: &str| l.trim().is_empty();
    if lines.len() > 1 && lines.first().is_some_and(|l| blank(l)) {
        lines.remove(0);
    }
    if lines.len() > 1 && lines.last().is_some_and(|l| blank(l)) {
        lines.pop();
    }
    let indent = lines
        .iter()
        .filter(|l| !blank(l))
        .map(|l| l.len() - l.trim_start_matches([' ', '\t']).len())
        .min()
        .unwrap_or(0);
    let cut: Vec<&str> = lines
        .iter()
        .map(|l| if blank(l) { "" } else { &l[indent..] })
        .collect();
    cut.join("\n")
}
