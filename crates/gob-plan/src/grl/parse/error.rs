//! Syntax errors and warnings, worded for the rule author (grl-spec.md section 10).
//!
//! Syntax errors carry no GRL code yet: the compile-error table of the spec
//! starts at GRL001 (unknown word) and has no row for "the text is not a
//! rule". The goldens ticket (~YTQ622S) assigns the code for the whole
//! syntax family (this type and the lexer's `LexError`); until then callers
//! print the message, the span and the help line only.

use gob_text::Span;

use crate::grl::LexErrorKind;

/// A syntax error: what is wrong and where.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("{kind}")]
pub struct ParseError {
    /// What went wrong.
    pub kind: ParseErrorKind,
    /// The offending range (empty at end of input when something is missing there).
    pub span: Span,
}

impl ParseError {
    /// A one-line suggestion for the fix, when there is an obvious one.
    pub fn help(&self) -> Option<String> {
        self.kind.help()
    }
}

/// The ways GRL text can fail to parse.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum ParseErrorKind {
    /// The text could not even be split into tokens.
    #[error("{0}")]
    Lexical(LexErrorKind),
    /// A required piece is missing or something else stands in its place.
    #[error("expected {what}, found {found}")]
    Expected {
        /// What the grammar needs here, for example "a variable name after `find`".
        what: String,
        /// What is there instead, for example "`:`" or "the end of the file".
        found: String,
        /// An optional one-line suggestion for this particular spot.
        hint: Option<&'static str>,
    },
    /// Something other than `rule` at the top of the file.
    #[error("expected `rule` to start a rule, found {found}")]
    NotARule {
        /// What is there instead.
        found: String,
    },
    /// A rule whose `{` is never matched.
    #[error("this rule is never closed")]
    UnclosedRule,
    /// A keyword that belongs earlier in the rule.
    #[error("{what} must come {rule_order} in a rule")]
    Misplaced {
        /// The item, for example "a header (`lang`)".
        what: String,
        /// Where it belongs, for example "before the clauses".
        rule_order: &'static str,
    },
    /// A rule without its `explain` block.
    #[error("rule `{0}` has no `explain` block")]
    MissingExplain(String),
    /// A second `explain` in one rule.
    #[error("a rule has exactly one `explain` block")]
    DuplicateExplain,
    /// A word outside a closed grammar set (severity, scope, polarity, ...).
    #[error("`{found}` is not {what}; the choices are {choices}")]
    BadChoice {
        /// What is being chosen, for example "a severity".
        what: &'static str,
        /// The word written.
        found: String,
        /// The allowed words, ready to print.
        choices: &'static str,
    },
    /// An interpolation holding more than a field, knob or witness.
    #[error("an interpolation holds a field, knob or witness such as `{{x.name}}`, not this")]
    BadInterpolation,
    /// An `any { }` with nothing inside.
    #[error("`any` needs at least one condition inside its braces")]
    EmptyAny,
    /// Constructs nested too deeply to read safely.
    #[error("this is nested too deeply to read (more than {0} levels)")]
    TooDeep(usize),
    /// A number too large for a knob value.
    #[error("the number `{0}` is too large")]
    NumberTooLarge(String),
}

impl ParseErrorKind {
    /// A one-line suggestion for the fix, when there is an obvious one.
    pub fn help(&self) -> Option<String> {
        match self {
            Self::Lexical(k) => k.help(),
            Self::NotARule { .. } => Some("a file holds rules: `rule ID \"slug\" { ... }`".into()),
            Self::UnclosedRule => Some("add the closing `}` after the `explain` block".into()),
            Self::Misplaced { .. } => Some(
                "a rule reads: headers, then clauses, then examples, then `explain`; move it"
                    .into(),
            ),
            Self::MissingExplain(_) => Some(
                "end the rule with `explain \"\"\"` ... `\"\"\"` holding a `## Remedy` section"
                    .into(),
            ),
            Self::DuplicateExplain => Some("merge the two blocks into one".into()),
            Self::BadChoice { choices, .. } => Some(format!("write one of {choices}")),
            Self::BadInterpolation => Some(
                "name a variable or knob field, for example `{f.name}` or `{knob.depth}`".into(),
            ),
            Self::EmptyAny => Some("write `any { a, b }`, or drop the `any`".into()),
            Self::TooDeep(_) => Some("split the condition into named `def`s".into()),
            Self::Expected { hint, .. } => hint.map(Into::into),
            Self::NumberTooLarge(_) => None,
        }
    }
}

/// A parse warning: the text is accepted but should be changed.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("{kind}")]
pub struct ParseWarning {
    /// What to change.
    pub kind: ParseWarningKind,
    /// The range to change.
    pub span: Span,
}

impl ParseWarning {
    /// A one-line suggestion for the change.
    pub fn help(&self) -> Option<String> {
        self.kind.help()
    }
}

/// The accepted-but-discouraged forms.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum ParseWarningKind {
    /// `lang "*"`.
    #[error("language ids are bare words, so `\"*\"` should not be quoted")]
    QuotedLangStar,
}

impl ParseWarningKind {
    /// A one-line suggestion for the change.
    pub fn help(&self) -> Option<String> {
        match self {
            Self::QuotedLangStar => Some("drop the quotes: `lang *`".into()),
        }
    }
}
