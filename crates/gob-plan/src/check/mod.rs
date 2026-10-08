//! The GRL checker: typed diagnostics over a parsed rule (grl-spec.md sections 7.1 and 10).
//!
//! [`check_file`] walks the syntax tree and returns [`Diagnostic`]s; [`render`] prints them in
//! the rustc-style shape the goldens under `tests/grl_errors` fix byte for byte;
//! [`compile_report`] is the whole pipeline from source text to that text.
//!
//! # Codes
//!
//! | Code | Meaning |
//! |---|---|
//! | GRL001 | unknown word: kind, field, verb, side relation, knob, function, variable |
//! | GRL003 | a variable used only inside `not`, `no` or `unresolved when`, bound nowhere |
//! | GRL004 | a variable bound twice |
//! | GRL005 | a type mismatch |
//! | GRL009 | a def that calls itself or a def written after it |
//! | GRL010 | a `reaches` closure without `within` |
//! | GRL011 | a missing `fire`, `clean` or (universal rules) `notapplicable` example |
//! | GRL012 | an `explain` text without a `## Remedy` section |
//! | GRL013 | (warning) a `find` variable never used |
//! | GRL014 | a side relation read but not listed in `needs` |
//! | GRL017 | `certainly` or `possibly` in a negative position |
//! | GRL018 | a word no language of the rule's `lang` answers |
//!
//! GRL017 and GRL018 are not in the spec table yet: the formal review (2026-10-08, sections 2.3
//! and 3) shows `certainly`/`possibly` are not monotone, so they are only sound in positive
//! positions, and that `NotApplicable` is a static property of a (rule, language) pair, so a rule
//! naming a word none of its languages answers is a compile error, not a runtime value.

mod names;
mod render;
mod structure;
mod vocab;

use gob_text::{FileInterner, Span};

use crate::catalog::ConfigSchema;
use crate::grl::{self, ParseError};

pub use render::render;

/// How serious a diagnostic is.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Severity {
    /// The rule does not compile.
    Error,
    /// The rule compiles; the author should look.
    Warning,
}

/// The compile-time diagnostic codes of the checker.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Code {
    /// Unknown word.
    Grl001,
    /// Variable used only inside a non-binding construct and bound nowhere.
    Grl003,
    /// Variable bound twice.
    Grl004,
    /// Type mismatch.
    Grl005,
    /// Def recursion or forward reference.
    Grl009,
    /// Closure without `within`.
    Grl010,
    /// Missing fire, clean or universal third example.
    Grl011,
    /// Explain without `## Remedy`.
    Grl012,
    /// Variable bound and never used (warning).
    Grl013,
    /// Side relation used but not in `needs`.
    Grl014,
    /// `certainly` or `possibly` in a negative position.
    Grl017,
    /// A word no language of the rule answers.
    Grl018,
}

impl Code {
    /// The code as printed, such as `GRL001`.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Grl001 => "GRL001",
            Self::Grl003 => "GRL003",
            Self::Grl004 => "GRL004",
            Self::Grl005 => "GRL005",
            Self::Grl009 => "GRL009",
            Self::Grl010 => "GRL010",
            Self::Grl011 => "GRL011",
            Self::Grl012 => "GRL012",
            Self::Grl013 => "GRL013",
            Self::Grl014 => "GRL014",
            Self::Grl017 => "GRL017",
            Self::Grl018 => "GRL018",
        }
    }

    /// Whether the code is an error or a warning.
    pub const fn severity(self) -> Severity {
        match self {
            Self::Grl013 => Severity::Warning,
            _ => Severity::Error,
        }
    }
}

/// A source range with the words printed under it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Label {
    /// The range.
    pub span: Span,
    /// The text printed after the markers; may be empty.
    pub text: String,
}

/// One located message: what is wrong, where, and how to fix it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Diagnostic {
    /// The code; `None` for a syntax error, which has no GRL code.
    pub code: Option<Code>,
    /// Error or warning.
    pub severity: Severity,
    /// The headline, in the author's words.
    pub message: String,
    /// The span the diagnostic is about (printed with `^`).
    pub primary: Label,
    /// Related spans (printed with `-`).
    pub secondary: Vec<Label>,
    /// `= note:` lines.
    pub notes: Vec<String>,
    /// `= help:` lines.
    pub helps: Vec<String>,
}

impl Diagnostic {
    /// A diagnostic with a code; the severity follows the code.
    pub fn new(
        code: Code,
        message: impl Into<String>,
        span: Span,
        label: impl Into<String>,
    ) -> Self {
        Self {
            code: Some(code),
            severity: code.severity(),
            message: message.into(),
            primary: Label {
                span,
                text: label.into(),
            },
            secondary: Vec::new(),
            notes: Vec::new(),
            helps: Vec::new(),
        }
    }

    /// Add a related span.
    #[must_use]
    pub fn with_secondary(mut self, span: Span, label: impl Into<String>) -> Self {
        self.secondary.push(Label {
            span,
            text: label.into(),
        });
        self
    }

    /// Add a `= note:` line.
    #[must_use]
    pub fn with_note(mut self, note: impl Into<String>) -> Self {
        self.notes.push(note.into());
        self
    }

    /// Add a `= help:` line.
    #[must_use]
    pub fn with_help(mut self, help: impl Into<String>) -> Self {
        self.helps.push(help.into());
        self
    }

    /// The diagnostic for a syntax error (no GRL code).
    pub fn syntax(err: &ParseError) -> Self {
        let mut d = Self {
            code: None,
            severity: Severity::Error,
            message: err.to_string(),
            primary: Label {
                span: err.span,
                text: String::new(),
            },
            secondary: Vec::new(),
            notes: Vec::new(),
            helps: Vec::new(),
        };
        if let Some(h) = err.help() {
            d.helps.push(h);
        }
        d
    }
}

// frob:ticket 01M3ZX7DYR7PR1PBCZ7E8Q56WW
/// Check every rule of a parsed file; diagnostics come in source order.
pub fn check_file(file: &grl::ast::File) -> Vec<Diagnostic> {
    check_file_with(file, None)
}

// frob:ticket 01M3ZX7DMYNTWB3AP04CDMAECH
/// Check every rule of a parsed file, typing `config.<table>` paths and rows from `config`.
pub fn check_file_with(file: &grl::ast::File, config: Option<&ConfigSchema>) -> Vec<Diagnostic> {
    let mut out: Vec<Diagnostic> = file
        .rules
        .iter()
        .flat_map(|r| {
            let mut d = names::check_rule(r, config);
            d.extend(structure::check_rule(r));
            d
        })
        .collect();
    out.sort_by_key(|d| d.primary.span.range.start());
    tracing::debug!(
        rules = file.rules.len(),
        diagnostics = out.len(),
        "checked GRL file"
    );
    out
}

// frob:ticket 01M3ZX7DYR7PR1PBCZ7E8Q56WW
/// Parse, check and render one rule file: the exact text the compiler prints for it.
pub fn compile_report(path: &str, source: &str) -> String {
    let parsed = grl::parse(FileInterner::new().intern(path), source);
    let diagnostics: Vec<Diagnostic> = if parsed.is_ok() {
        check_file(&parsed.file)
    } else {
        parsed.errors.iter().map(Diagnostic::syntax).collect()
    };
    render(path, source, &diagnostics)
}
