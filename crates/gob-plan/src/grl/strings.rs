//! `"..."` strings with escapes and interpolation, and `"""..."""` blocks.

use super::error::{LexError, LexErrorKind};
use super::lexer::Lexer;
use super::token::{Block, StrPart, TokenKind};

impl Lexer<'_> {
    /// A string or block string; the opening quote is at `start`.
    pub(super) fn string(&mut self, start: usize) -> Result<(), LexError> {
        if self.rest().starts_with("\"\"\"") {
            return self.block(start);
        }
        self.bump();
        let mut parts = Vec::new();
        let mut text = String::new();
        let mut text_start = self.pos;
        loop {
            let at = self.pos;
            match self.bump() {
                None | Some('\n' | '\r') => {
                    return self.err(LexErrorKind::UnterminatedString, start, at);
                }
                Some('"') => {
                    self.flush_text(&mut parts, &mut text, text_start, at);
                    break;
                }
                Some('\\') => match self.bump() {
                    Some('"') => text.push('"'),
                    Some('\\') => text.push('\\'),
                    Some('n') => text.push('\n'),
                    Some('{') => text.push('{'),
                    Some('}') => text.push('}'),
                    None => return self.err(LexErrorKind::UnterminatedString, start, at),
                    Some(c) => return self.err(LexErrorKind::UnknownEscape(c), at, self.pos),
                },
                Some('{') => {
                    self.flush_text(&mut parts, &mut text, text_start, at);
                    let expr = self.interpolation(at)?;
                    parts.push(StrPart::Interp { expr });
                    text_start = self.pos;
                }
                Some(c) => text.push(c),
            }
        }
        self.push(TokenKind::Str(parts), start);
        Ok(())
    }

    fn flush_text(&self, parts: &mut Vec<StrPart>, text: &mut String, from: usize, to: usize) {
        if !text.is_empty() {
            parts.push(StrPart::Text {
                value: std::mem::take(text),
                span: self.span(from, to),
            });
        }
    }

    /// Scan to the `}` matching the `{` at `open`; returns the expression span.
    fn interpolation(&mut self, open: usize) -> Result<gob_text::Span, LexError> {
        let body = self.pos;
        let mut depth = 1usize;
        loop {
            let at = self.pos;
            match self.bump() {
                None | Some('\n' | '\r') => {
                    return self.err(LexErrorKind::UnterminatedInterpolation, open, open + 1);
                }
                Some('{') => depth += 1,
                Some('}') => {
                    depth -= 1;
                    if depth == 0 {
                        if at == body {
                            return self.err(LexErrorKind::EmptyInterpolation, open, self.pos);
                        }
                        return Ok(self.span(body, at));
                    }
                }
                Some('"') => self.skip_nested_string(open)?,
                Some(_) => {}
            }
        }
    }

    /// Skip a string literal inside an interpolation (its opening quote is consumed).
    fn skip_nested_string(&mut self, open: usize) -> Result<(), LexError> {
        loop {
            match self.bump() {
                None | Some('\n' | '\r') => {
                    return self.err(LexErrorKind::UnterminatedInterpolation, open, open + 1);
                }
                Some('\\') => {
                    self.bump();
                }
                Some('"') => return Ok(()),
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
