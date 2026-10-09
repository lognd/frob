//! The const capability [`MATRIX`] and the const queries `#[rule]` expansions assert against.

use crate::{Capability, Fidelity, Lang, Precision};
use Precision::{
    ByNameInCrate as By, Declared as Dec, Keyword as Kw, Lexical as Lex, LexicalImports as LexI,
    LinkTargets as Lnk, Manifest as Man, None as G, NotApplicable as NA, Syntactic as Syn,
};

/// One row: a language, its overall fidelity and its cell per [`Capability`] in [`Capability::ALL`]
/// order.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Row {
    /// The language this row describes.
    pub lang: Lang,
    /// The fidelity its adapter claims.
    pub fidelity: Fidelity,
    /// One precision per capability, indexed by `Capability as usize`.
    pub cells: [Precision; 12],
}

impl Row {
    /// The cell for `cap`.
    pub const fn cell(&self, cap: Capability) -> Precision {
        self.cells[cap as usize]
    }
}

const fn r(lang: Lang, fidelity: Fidelity, cells: [Precision; 12]) -> Row {
    Row {
        lang,
        fidelity,
        cells,
    }
}

use Fidelity::{F0, F1, F2, F3, F4};

/// The capability matrix, indexed by `Lang as usize`.
///
/// Column order: `resolve_ref`, `apply_targets`, `visibility`, `effects`, `test_items`, `imports`,
/// `expand`, `order`, `project_model`, `comments`, `style`, `markup`. `G` is a gap, `NA` is not applicable by
/// construction.
#[rustfmt::skip]
pub const MATRIX: [Row; 12] = [
    r(Lang::Rust,       F3, [LexI, By,  Kw,  G,  Syn, Syn,  G,  Dec, Man, Syn, NA,  NA ]),
    r(Lang::Python,     F2, [Lex,  By,  Syn, G,  Syn, Syn,  G,  G,   G,   Syn, NA,  NA ]),
    r(Lang::CSharp,     F1, [By,   G,   Kw,  G,  Syn, G,    G,  G,   Man, Syn, NA,  NA ]),
    r(Lang::TypeScript, F2, [Lex,  By,  Kw,  G,  Syn, LexI, G,  G,   Man, Syn, Syn, Syn]),
    r(Lang::Css,        F2, [By,   G,   NA,  NA, NA,  G,    NA, G,   G,   Syn, Syn, NA ]),
    r(Lang::Html,       F2, [NA,   NA,  NA,  NA, NA,  G,    NA, G,   G,   Syn, Syn, Syn]),
    r(Lang::Markdown,   F4, [Lnk,  Lnk, NA,  NA, NA,  Syn,  NA, Dec, G,   Syn, NA,  NA ]),
    r(Lang::Yaml,       F1, [G,    G,   G,   G,  G,   G,    G,  G,   G,   Syn, NA,  NA ]),
    r(Lang::Toml,       F0, [G,    G,   G,   G,  G,   G,    G,  G,   G,   Syn, NA,  NA ]),
    r(Lang::Grmb,       F4, [Lex,  Dec, NA,  NA, NA,  Syn,  NA, Dec, G,   Syn, NA,  NA ]),
    r(Lang::OpaqueText, F0, [G,    G,   G,   G,  G,   G,    G,  G,   G,   Syn, G,   G  ]),
    r(Lang::Binary,     F0, [NA,   NA,  NA,  NA, NA,  NA,   NA, NA,  NA,  NA,  NA,  NA ]),
];

// Rows are indexed by discriminant: a misordered row fails the build here.
const _: () = {
    let mut i = 0;
    while i < MATRIX.len() {
        assert!(MATRIX[i].lang as usize == i, "MATRIX row out of Lang order");
        i += 1;
    }
};

/// The matrix row of `lang`.
pub const fn row(lang: Lang) -> &'static Row {
    &MATRIX[lang as usize]
}

/// The overall fidelity of `lang`.
pub const fn lang_fidelity(lang: Lang) -> Fidelity {
    MATRIX[lang as usize].fidelity
}

/// The cell of (`lang`, `cap`).
pub const fn precision(lang: Lang, cap: Capability) -> Precision {
    MATRIX[lang as usize].cell(cap)
}

/// True when `lang` supplies `cap` (a provided cell, not a gap and not declared not-applicable).
pub const fn provides(lang: Lang, cap: Capability) -> bool {
    precision(lang, cap).is_provided()
}

/// True when at least one language supplies every capability in `needs` at `min` fidelity or better.
pub const fn universal_satisfiable(needs: &[Capability], min: Fidelity) -> bool {
    let mut r = 0;
    while r < MATRIX.len() {
        let lang = MATRIX[r].lang;
        let mut ok = MATRIX[r].fidelity as u8 >= min as u8;
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_lang_has_its_row() {
        for (i, l) in Lang::ALL.into_iter().enumerate() {
            assert_eq!(MATRIX[i].lang, l);
            assert_eq!(row(l).lang, l);
        }
    }

    #[test]
    fn pseudo_rows_exist() {
        assert_eq!(lang_fidelity(Lang::OpaqueText), Fidelity::F0);
        assert!(provides(Lang::OpaqueText, Capability::Comments));
        assert_eq!(lang_fidelity(Lang::Binary), Fidelity::F0);
        for c in Capability::ALL {
            assert_eq!(precision(Lang::Binary, c), Precision::NotApplicable);
        }
    }

    #[test]
    fn spike_expectations_hold() {
        assert!(!provides(Lang::Rust, Capability::Effects));
        assert!(!provides(Lang::Css, Capability::TestItems));
        assert!(universal_satisfiable(&[Capability::Comments], Fidelity::F1));
        assert!(!universal_satisfiable(
            &[Capability::Comments, Capability::Effects],
            Fidelity::F1
        ));
    }

    #[test]
    fn names_round_trip_and_aliases_fold() {
        for l in Lang::ALL {
            assert_eq!(Lang::from_tag(l.name()), Some(l));
        }
        assert_eq!(Lang::from_tag("opaque"), Some(Lang::OpaqueText));
        assert_eq!(Lang::from_tag("tsx"), Some(Lang::TypeScript));
        assert_eq!(Lang::from_tag("cobol"), None);
    }
}
