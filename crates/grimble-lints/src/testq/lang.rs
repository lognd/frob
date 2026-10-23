//! The languages TESTQ has a test vocabulary for.

// frob:ticket 01M5HJNEBY5YBCJB06D5ZSH4H5

use gob_languages::Language;

use crate::syntax;

/// A language family whose tests TESTQ001 can read.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Lang {
    /// Rust.
    Rust,
    /// Python.
    Python,
    /// TypeScript, TSX, JavaScript and JSX: one test vocabulary (jest, vitest, mocha, node:test).
    Script,
    /// `C#` (`xUnit`, `NUnit`, `MSTest`).
    CSharp,
}

impl Lang {
    /// The test-vocabulary family of `language`, or `None` when TESTQ has none for it.
    pub(crate) fn of(language: Language) -> Option<Self> {
        match language {
            Language::Rust => Some(Self::Rust),
            Language::Python => Some(Self::Python),
            Language::TypeScript | Language::Tsx | Language::JavaScript | Language::Jsx => {
                Some(Self::Script)
            }
            Language::CSharp => Some(Self::CSharp),
            _ => None,
        }
    }

    /// The flow-scanner tag, for the languages that also have nondeterminism vocabulary.
    pub(crate) fn flow(self) -> Option<syntax::Lang> {
        match self {
            Self::Rust => Some(syntax::Lang::Rust),
            Self::Python => Some(syntax::Lang::Python),
            Self::Script | Self::CSharp => None,
        }
    }
}
