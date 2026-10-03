//! The GRL parser: tokens to the syntax tree of [`crate::grl::ast`] (grl-spec.md section 5).
//!
//! [`parse`] lexes and parses a whole file. It is a recursive-descent parser
//! that recovers at item boundaries, so one file yields several syntax errors
//! where possible. Unknown words stay words: kinds, verbs and fields are the
//! generated vocabulary and are checked later (GRL001), never here. The
//! parser never panics, whatever the tokens.
//!
//! Deviations from the written grammar, each needed by an example of the spec
//! (recorded for the spec owner): a shape may carry a string argument
//! (`directive "todo"`); terms include function calls (`resolve(a, b)`);
//! a bare term is a condition (`c.observed`); `reaches` may omit `within`
//! (GRL010 reports it); `certainly` and `possibly` may precede a verb
//! (section 7.2).

mod clause;
mod cond;
mod cursor;
mod error;
mod literal;
mod rule;

#[cfg(test)]
mod tests;

use gob_text::FileId;

use super::ast::File;
use super::lexer::lex;
use super::token::Token;

pub use error::{ParseError, ParseErrorKind, ParseWarning, ParseWarningKind};

use cursor::Parser;

/// The result of parsing: the tree of everything that parsed, plus diagnostics.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Parsed {
    /// The rules that parsed (rules with a broken header are left out).
    pub file: File,
    /// Syntax errors in source order of detection; empty when the text is valid.
    pub errors: Vec<ParseError>,
    /// Accepted-but-discouraged forms, such as `lang "*"`.
    pub warnings: Vec<ParseWarning>,
}

impl Parsed {
    /// True when no syntax error was found.
    pub fn is_ok(&self) -> bool {
        self.errors.is_empty()
    }
}

/// Parse a whole GRL file; lexical errors end the parse with that one error.
pub fn parse(file: FileId, text: &str) -> Parsed {
    match lex(file, text) {
        Ok(lexed) => parse_tokens(file, text, &lexed.tokens),
        Err(e) => {
            tracing::debug!(file = %file, error = %e, "GRL source did not lex");
            Parsed {
                file: File { rules: Vec::new() },
                errors: vec![ParseError {
                    span: e.span,
                    kind: ParseErrorKind::Lexical(e.kind),
                }],
                warnings: Vec::new(),
            }
        }
    }
}

/// Parse an already lexed token stream; `text` is only read for `{expr}` interpolations.
pub fn parse_tokens(file: FileId, text: &str, tokens: &[Token]) -> Parsed {
    let mut parser = Parser::new(file, text, tokens);
    let ast = parser.file();
    let (errors, warnings) = parser.finish();
    tracing::debug!(
        file = %file,
        rules = ast.rules.len(),
        errors = errors.len(),
        warnings = warnings.len(),
        "parsed GRL source"
    );
    Parsed {
        file: ast,
        errors,
        warnings,
    }
}
