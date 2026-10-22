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
pub const MATRIX: [Row; 14] = [
    r(Lang::Rust,       F4, [LexI, By,  Kw,  G,  Syn, Syn,  G,  Dec, Man, Syn, NA,  NA ]),
    r(Lang::Python,     F3, [Lex,  By,  Syn, G,  Syn, Syn,  G,  G,   G,   Syn, NA,  NA ]),
    r(Lang::CSharp,     F1, [By,   G,   Kw,  G,  Syn, G,    G,  G,   Man, Syn, NA,  NA ]),
    r(Lang::TypeScript, F3, [Lex,  By,  Kw,  G,  Syn, LexI, G,  G,   Man, Syn, Syn, Syn]),
    r(Lang::Css,        F2, [By,   G,   NA,  NA, NA,  G,    NA, G,   G,   Syn, Syn, NA ]),
    r(Lang::Html,       F1, [NA,   NA,  NA,  NA, NA,  G,    NA, G,   G,   Syn, Syn, Syn]),
    r(Lang::Markdown,   F3, [Lnk,  Lnk, NA,  NA, NA,  Syn,  NA, Dec, G,   Syn, NA,  NA ]),
    r(Lang::Yaml,       F1, [G,    G,   G,   G,  G,   G,    G,  G,   G,   Syn, NA,  NA ]),
    r(Lang::Toml,       F0, [G,    G,   G,   G,  G,   G,    G,  G,   G,   Syn, NA,  NA ]),
    r(Lang::GithubActions, F2, [G,  G,  G,  G,  G,   G,    G,  G,   G,   Syn, NA,  NA ]),
    r(Lang::Dockerfile, F2, [G,  G,   G,   G,  G,   G,    G,  G,   G,   Syn, NA,  NA ]),
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

// frob:ticket 01M4CXV46WX4E0WSVYJPYM7TRG
/// Languages whose declared fidelity the cells do not justify yet; the list may only shrink.
///
/// Both measure F1 from their corpus, so the pin is a known overclaim, not a licence for new ones.
pub const UNJUSTIFIED: [Lang; 2] = [Lang::GithubActions, Lang::Dockerfile];

const fn has(cells: &[Precision; 12], cap: Capability) -> bool {
    cells[cap as usize].is_provided()
}

/// The highest fidelity the capability `cells` justify (universal-model.md 3.3 read off the matrix).
///
/// F1 needs any provided cell; F2 needs `resolve_ref` or `imports` (binders and references);
/// F3 needs `apply_targets` on top; F4 needs `comments` and `order` (attributes, regions, phases).
/// Each rung also needs every rung below it.
pub const fn fidelity_ceiling(cells: &[Precision; 12]) -> Fidelity {
    let mut any = false;
    let mut i = 0;
    while i < cells.len() {
        any = any || cells[i].is_provided();
        i += 1;
    }
    if !any {
        Fidelity::F0
    } else if !(has(cells, Capability::ResolveRef) || has(cells, Capability::Imports)) {
        Fidelity::F1
    } else if !has(cells, Capability::ApplyTargets) {
        Fidelity::F2
    } else if !(has(cells, Capability::Comments) && has(cells, Capability::Order)) {
        Fidelity::F3
    } else {
        Fidelity::F4
    }
}

/// True when the cells of `row` justify the fidelity it declares.
pub const fn is_justified(row: &Row) -> bool {
    row.fidelity as u8 <= fidelity_ceiling(&row.cells) as u8
}

const fn is_unjustified_pin(lang: Lang) -> bool {
    let mut i = 0;
    while i < UNJUSTIFIED.len() {
        if UNJUSTIFIED[i] as usize == lang as usize {
            return true;
        }
        i += 1;
    }
    false
}

// A declared level the cells cannot justify fails the build, unless pinned in UNJUSTIFIED.
const _: () = {
    let mut i = 0;
    while i < MATRIX.len() {
        assert!(
            is_justified(&MATRIX[i]) != is_unjustified_pin(MATRIX[i].lang),
            "MATRIX fidelity is not justified by its cells (or a stale UNJUSTIFIED pin)"
        );
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
    // frob:tests crates/gob-caps/src/matrix.rs::fidelity_ceiling
    fn declared_fidelity_is_justified_by_the_cells() {
        for row in &MATRIX {
            assert_eq!(
                is_justified(row),
                !UNJUSTIFIED.contains(&row.lang),
                "{:?}",
                row.lang
            );
        }
        // Promoting a row past what its cells support is rejected.
        let mut csharp = *super::row(Lang::CSharp);
        assert!(is_justified(&csharp));
        csharp.fidelity = Fidelity::F3;
        assert!(!is_justified(&csharp));
        // Rungs: nothing provided is F0; resolve without apply is F2; full rust is F4.
        assert_eq!(fidelity_ceiling(&[Precision::None; 12]), Fidelity::F0);
        assert_eq!(fidelity_ceiling(&row(Lang::Css).cells), Fidelity::F2);
        assert_eq!(fidelity_ceiling(&row(Lang::Rust).cells), Fidelity::F4);
        assert_eq!(fidelity_ceiling(&row(Lang::Python).cells), Fidelity::F3);
        assert_eq!(fidelity_ceiling(&row(Lang::Binary).cells), Fidelity::F0);
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
