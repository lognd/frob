//! Expectation markers: `//~ error`, `#~ error`, `--~ error`, `<!--~ error -->`, `expect "line 3: error"`.

// frob:ticket 01M3ZX7F8WQQ8JKW7GVVB2EYG6
use std::fmt;

use crate::grl::ast::Severity;

/// A finding's severity as a marker spells it.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Level {
    /// `error`
    Error,
}

impl From<Severity> for Level {
    fn from(s: Severity) -> Self {
        match s {
            Severity::Error => Self::Error,
        }
    }
}

/// What a marker or a reported finding says happens on a line.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Mark {
    /// A finding of this severity.
    Finding(Level),
    /// An Unresolved.
    Unresolved,
}

impl fmt::Display for Mark {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Self::Finding(Level::Error) => "error",
            Self::Unresolved => "unresolved",
        })
    }
}

/// An expected finding: a 1-based line and what is reported there.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct Expected {
    /// The 1-based line the reported node starts on.
    pub line: u32,
    /// What is expected there.
    pub mark: Mark,
}

/// A finding a run reported, in the same terms as [`Expected`].
pub type Actual = Expected;

impl fmt::Display for Expected {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "line {}: {}", self.line, self.mark)
    }
}

fn mark_word(word: &str) -> Option<Mark> {
    Some(match word {
        "error" => Mark::Finding(Level::Error),
        "unresolved" => Mark::Unresolved,
        _ => return None,
    })
}

/// The comment introducer of a language, or `None` for one without comments (JSON).
fn introducer(lang: &str) -> Option<&'static str> {
    match lang {
        "rust" | "c" | "cpp" | "javascript" | "typescript" | "java" | "go" => Some("//~"),
        "python" | "yaml" | "toml" | "shell" | "bash" => Some("#~"),
        "lua" | "sql" => Some("--~"),
        "markdown" | "html" => Some("<!--~"),
        _ => None,
    }
}

/// Every marker of `text` for language `lang`; a line may carry one marker.
pub fn parse_markers(lang: &str, text: &str) -> Vec<Expected> {
    let Some(intro) = introducer(lang) else {
        return Vec::new();
    };
    let mut out: Vec<Expected> = text
        .lines()
        .enumerate()
        .filter_map(|(i, line)| {
            let rest = &line[line.find(intro)? + intro.len()..];
            let word = rest.split_whitespace().next()?;
            let mark = mark_word(word)?;
            Some(Expected {
                line: u32::try_from(i + 1).ok()?,
                mark,
            })
        })
        .collect();
    out.sort();
    out
}

/// Parse an `expect "line 3: error"` string; `None` when it is not of that shape.
pub fn expect_line(text: &str) -> Option<Expected> {
    let (head, word) = text.trim().split_once(':')?;
    let line = head.trim().strip_prefix("line ")?.trim().parse().ok()?;
    Some(Expected {
        line,
        mark: mark_word(word.trim())?,
    })
}
