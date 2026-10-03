//! Lexical errors, worded for the rule author (grl-spec.md section 10).

use gob_text::Span;

/// A lexical error: what is wrong and where.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("{kind}")]
pub struct LexError {
    /// What went wrong.
    pub kind: LexErrorKind,
    /// The offending range (empty at end of input for unterminated items).
    pub span: Span,
}

impl LexError {
    /// A one-line suggestion for the fix, when there is an obvious one.
    pub fn help(&self) -> Option<String> {
        self.kind.help()
    }
}

/// The ways GRL text can fail to lex.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum LexErrorKind {
    /// A non-ASCII character in rule syntax (outside strings, snippets, comments).
    #[error("`{}` contains `{ch}`, which is not plain ASCII; names and keywords use a-z, 0-9 and _", word.as_deref().unwrap_or(&ch.to_string()))]
    NonAscii {
        /// The first non-ASCII character.
        ch: char,
        /// The whole word it sits in, when it is part of one.
        word: Option<String>,
    },
    /// An ASCII character that starts no token.
    #[error("`{}` is not part of the rule language", .0.escape_debug())]
    BadCharacter(char),
    /// A word with capitals that is neither a rule id nor a polarity.
    #[error("`{0}` is not a valid name or rule id")]
    BadWord(String),
    /// A number glued to letters, such as `12ab`.
    #[error("`{0}` is not a valid number")]
    BadNumber(String),
    /// A number that does not fit in 64 bits.
    #[error("the number `{0}` is too large")]
    NumberTooLarge(String),
    /// A `"` string with no closing quote on its line.
    #[error("this string is never closed")]
    UnterminatedString,
    /// A backslash followed by something that is not an escape.
    #[error("`\\{}` is not an escape; strings understand \\\" \\\\ \\n \\{{ and \\}}", .0.escape_debug())]
    UnknownEscape(char),
    /// A `{` interpolation with no matching `}`.
    #[error("this `{{` starts an interpolation that is never closed")]
    UnterminatedInterpolation,
    /// A `{}` with nothing inside.
    #[error("an interpolation `{{}}` needs an expression inside")]
    EmptyInterpolation,
    /// A `"""` block with no closing `"""`.
    #[error("this block string is never closed")]
    UnterminatedBlock,
    /// A backtick snippet with no closing backticks.
    #[error("this snippet is never closed (it needs {ticks} closing backtick{})", if *ticks == 1 { "" } else { "s" })]
    UnterminatedSnippet {
        /// Backticks in the opening delimiter.
        ticks: u8,
    },
    /// A `$` in a snippet that starts no metavariable.
    #[error(
        "a lone `$` in a snippet; write `$$` for a literal dollar or `$NAME` for a metavariable"
    )]
    LoneDollar,
    /// A metavariable name that is not uppercase.
    #[error("the metavariable `{0}` is not uppercase; names look like `$X` or `$$$ARGS`")]
    LowercaseMetavar(String),
    /// A `/` regex with no closing `/` on its line.
    #[error("this regular expression is never closed")]
    UnterminatedRegex,
    /// `//`.
    #[error("this regular expression is empty")]
    EmptyRegex,
    /// A non-ASCII character in a regex literal.
    #[error("`{0}` is not plain ASCII; write it in the regex as \\u{{XXXX}}")]
    NonAsciiRegex(char),
    /// A regex flag other than `i` or `m`.
    #[error("`{0}` is not a regex flag; the flags are `i` and `m`")]
    UnknownRegexFlag(char),
    /// The same regex flag twice.
    #[error("the regex flag `{0}` is given twice")]
    DuplicateRegexFlag(char),
    /// Source larger than the 4 GiB span limit.
    #[error("the file is too large to read (over 4 GiB)")]
    TooLarge,
    /// A sub-range that is outside the text or splits a character.
    #[error("the range to read is not inside the text")]
    BadRange,
}

impl LexErrorKind {
    /// A one-line suggestion for the fix, when there is an obvious one.
    pub fn help(&self) -> Option<String> {
        match self {
            Self::NonAscii { .. } => {
                Some("rename it with plain ASCII, or move the text into a string or snippet".into())
            }
            Self::BadWord(w) => Some(format!(
                "names are lowercase (`{}`); rule ids look like `TODO001`",
                w.to_ascii_lowercase()
            )),
            Self::UnterminatedBlock => Some("close it with a line holding `\"\"\"`".into()),
            Self::UnterminatedString => {
                Some("strings end on the line they start; use `\"\"\"` for several lines".into())
            }
            Self::UnterminatedSnippet { ticks: 1 } => {
                Some("a snippet with a backtick inside is written with double backticks".into())
            }
            Self::LoneDollar => Some("a literal dollar is `$$`".into()),
            Self::LowercaseMetavar(n) => Some(format!(
                "write `{}`, or `$$` to keep a literal dollar before `{}`",
                n.to_ascii_uppercase(),
                n.trim_start_matches('$')
            )),
            _ => None,
        }
    }
}
