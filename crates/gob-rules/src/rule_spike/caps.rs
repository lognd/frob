//! STUB of the future `gob-caps` leaf crate (~9R52NCF spike): a four-capability, five-language
//! capability matrix, const so the `#[rule]` expansion can assert against it at compile time.

/// How well an adapter understands a language, lowest to highest.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Fidelity {
    /// Text only.
    F0,
    /// Syntactic.
    F1,
    /// Symbols.
    F2,
    /// Resolved references.
    F3,
}

/// A language the stub matrix knows.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Lang {
    /// Rust.
    Rust,
    /// Python.
    Python,
    /// CSS.
    Css,
    /// Markdown.
    Markdown,
    /// Pseudo-language: bytes that are not text.
    Binary,
}

/// A fact an adapter can supply to rules.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Capability {
    /// Comment nodes and directive binding.
    Comments,
    /// Test functions and modules.
    TestItems,
    /// Public/private visibility of items.
    Visibility,
    /// Side effects of a call (a gap in every language, so no rule can need it yet).
    Effects,
}

/// What one matrix cell says about a (language, capability) pair.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Precision {
    /// Declared not applicable by construction (css has no tests).
    NotApplicable,
    /// A gap: possible, not implemented yet.
    None,
    /// Provided, syntactic precision.
    Syntactic,
    /// Provided, exact.
    Exact,
}

use Precision::{Exact, NotApplicable, Syntactic};

/// One row: language, its overall fidelity, and its cell per `Capability` in declaration order.
pub const MATRIX: [(Lang, Fidelity, [Precision; 4]); 5] = [
    (
        Lang::Rust,
        Fidelity::F3,
        [Exact, Exact, Exact, Precision::None],
    ),
    (
        Lang::Python,
        Fidelity::F2,
        [Syntactic, Syntactic, Precision::None, Precision::None],
    ),
    (
        Lang::Css,
        Fidelity::F1,
        [Syntactic, NotApplicable, NotApplicable, NotApplicable],
    ),
    (
        Lang::Markdown,
        Fidelity::F1,
        [Syntactic, NotApplicable, NotApplicable, NotApplicable],
    ),
    (
        Lang::Binary,
        Fidelity::F0,
        [NotApplicable, NotApplicable, NotApplicable, NotApplicable],
    ),
];

/// The row index of `lang` in [`MATRIX`].
const fn row(lang: Lang) -> usize {
    let mut i = 0;
    while i < MATRIX.len() {
        if MATRIX[i].0 as u8 == lang as u8 {
            return i;
        }
        i += 1;
    }
    panic!("language missing from the stub matrix");
}

/// The overall fidelity of `lang`.
pub const fn lang_fidelity(lang: Lang) -> Fidelity {
    MATRIX[row(lang)].1
}

/// True when `lang` supplies `cap` (a provided cell, not a gap and not declared not-applicable).
pub const fn provides(lang: Lang, cap: Capability) -> bool {
    matches!(MATRIX[row(lang)].2[cap as usize], Syntactic | Exact)
}

/// True when at least one language supplies every capability in `needs` at `min` fidelity or better.
pub const fn universal_satisfiable(needs: &[Capability], min: Fidelity) -> bool {
    let mut r = 0;
    while r < MATRIX.len() {
        let lang = MATRIX[r].0;
        let mut ok = MATRIX[r].1 as u8 >= min as u8;
        let mut i = 0;
        while i < needs.len() {
            ok = ok && provides(lang, needs[i]);
            i += 1;
        }
        if ok {
            return true;
        }
        r += 1;
    }
    false
}
