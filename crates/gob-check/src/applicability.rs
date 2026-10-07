//! The one applicability resolver (D107, `rule-authoring.md` section 3).
//!
//! [`resolve`] is pure: a rule's declared [`Applies`] plus the facts of one file give
//! `Examine`, `NotApplicable(reason)` or `Unresolved(reason)`. The reasons are data, so
//! the pipeline can count and print them.
//!
//! Until the `#[rule]` attribute lands (`~N88H9SY`) a rule carries no `applies`, so
//! [`temporary_applies`] is the single table that expresses each existing rule's
//! `applies` as data, keyed by its `RuleMeta`. It is temporary: the migration tickets
//! delete one row per rule as they move it onto the attribute.

use gob_caps::{Capability, Fidelity, Lang, Precision};
use gob_rules::{RuleDef, RuleMeta};
use gob_symbols::{FileInfo, ParseStatus};

use crate::status::SubjectStatus;

/// What a rule declares about the files it can examine (the declaration's own type).
pub use gob_rules::Applies;

/// One rule as the resolver and the fidelity accounting see it: id, family and declared `applies`.
///
/// Legacy rules get theirs from [`temporary_applies`]; a `RuleDef` carries its own.
#[derive(Debug, Clone, Copy)]
pub struct RuleRef {
    /// Rule id.
    pub id: &'static str,
    /// Family prefix.
    pub family: &'static str,
    /// What the rule declares about the files it can examine.
    pub applies: Applies,
}

impl RuleRef {
    /// A legacy rule, through the temporary `applies` table.
    pub fn of_meta(meta: &RuleMeta) -> Self {
        Self {
            id: meta.id,
            family: meta.family,
            applies: temporary_applies(meta),
        }
    }

    /// A declared rule, through its own `applies`.
    pub fn of_def(def: &RuleDef) -> Self {
        Self {
            id: def.id,
            family: def.family,
            applies: def.applies,
        }
    }
}

/// The facts of one file that applicability reads.
#[derive(Debug, Clone, Copy)]
pub struct FileFacts<'a> {
    /// The built-in language, or `None` for a tag outside the closed list.
    pub lang: Option<Lang>,
    /// True for an adapter-less file (one opaque F0 unit).
    pub opaque: bool,
    /// For an opaque file: true when its comments are scanned anyway (TOML).
    pub scanned: bool,
    /// The fidelity the file was folded at.
    pub fidelity: Fidelity,
    /// How the parse went.
    pub parse: &'a ParseStatus,
}

impl<'a> FileFacts<'a> {
    /// The facts of `info`; `binary` marks non-text bytes and `scanned` an opaque file whose comments are read.
    pub fn of(info: &'a FileInfo, binary: bool, scanned: bool) -> Self {
        let opaque = info.is_opaque();
        let lang = if opaque {
            Some(match (binary, scanned) {
                (true, _) => Lang::Binary,
                (false, true) => Lang::Toml,
                (false, false) => Lang::OpaqueText,
            })
        } else {
            Lang::from_tag(&info.language)
        };
        Self {
            lang,
            opaque,
            scanned,
            fidelity: info.fidelity,
            parse: &info.parse_status,
        }
    }

    /// The facts of an unscanned, non-binary opaque text file.
    pub fn opaque_text(parse: &'a ParseStatus) -> Self {
        Self {
            lang: Some(Lang::OpaqueText),
            opaque: true,
            scanned: false,
            fidelity: Fidelity::F0,
            parse,
        }
    }
}

/// The precision of (`facts`, `cap`) for the pseudo-language rows.
///
/// The matrix rows for `opaque-text` and scanned TOML hold the D106 target values; today's
/// answers are the older ones (a capability rule is not applicable to adapter-less text, a
/// comment rule is unresolved unless the scanner reads the file). This override keeps them
/// until `~59MXB7Z` flips the opaque-text row and deletes it. Binary reads the matrix.
fn opaque_precision(facts: &FileFacts<'_>, cap: Capability) -> Precision {
    match (facts.lang, cap) {
        (Some(Lang::Binary), _) => gob_caps::precision(Lang::Binary, cap),
        (_, Capability::Comments) if facts.scanned => Precision::Syntactic,
        (_, Capability::Comments) => Precision::None,
        _ => Precision::NotApplicable,
    }
}

/// Why a declared not-applicable cell is not applicable (today's wording).
fn not_applicable_reason(facts: &FileFacts<'_>, cap: Capability) -> String {
    if facts.lang == Some(Lang::Binary) && cap == Capability::Comments {
        "binary artifact holds no text".to_owned()
    } else {
        "no adapter: the file has no parsed items".to_owned()
    }
}

/// Decide what a rule declaring `applies` may do with the file described by `facts`.
///
/// Pure. Order: project rules examine; a language outside the rule's set is not applicable;
/// each need's cell (declared not-applicable, then gap) for opaque files; a failed parse and a
/// fidelity below the minimum are unresolved; otherwise examine.
pub fn resolve(applies: &Applies, facts: &FileFacts<'_>) -> SubjectStatus {
    let (needs, min_fidelity) = match applies {
        Applies::Project => return SubjectStatus::Examine,
        Applies::Universal {
            needs,
            min_fidelity,
        } => (*needs, *min_fidelity),
        Applies::Languages {
            langs,
            needs,
            min_fidelity,
        } => {
            if !facts.lang.is_some_and(|l| langs.contains(&l)) {
                let wanted: Vec<&str> = langs.iter().map(|l| l.name()).collect();
                return SubjectStatus::NotApplicable(format!(
                    "rule is for {}; file is {}",
                    wanted.join(","),
                    facts.lang.map_or("another language", Lang::name)
                ));
            }
            (*needs, *min_fidelity)
        }
    };
    if facts.opaque {
        let cells: Vec<(Capability, Precision)> = needs
            .iter()
            .map(|&c| (c, opaque_precision(facts, c)))
            .collect();
        if let Some((cap, _)) = cells.iter().find(|(_, p)| *p == Precision::NotApplicable) {
            return SubjectStatus::NotApplicable(not_applicable_reason(facts, *cap));
        }
        if cells.iter().any(|(_, p)| *p == Precision::None) {
            return SubjectStatus::Unresolved(
                "no adapter for this file (opaque F0): its comments and directives were not read"
                    .to_owned(),
            );
        }
        return SubjectStatus::Examine;
    }
    if let ParseStatus::Failed { reason } = facts.parse {
        return SubjectStatus::Unresolved(format!("the file failed to parse ({reason})"));
    }
    if facts.fidelity < min_fidelity {
        return SubjectStatus::Unresolved(format!(
            "file fidelity {} is below the {} the rule needs",
            facts.fidelity, min_fidelity
        ));
    }
    SubjectStatus::Examine
}

/// Text rules: read comments and directives of every text artifact.
const TEXT: Applies = Applies::Universal {
    needs: &[Capability::Comments],
    min_fidelity: Fidelity::F1,
};

/// Rules over documented or invariant-bearing symbols.
const SYMBOLS: Applies = Applies::Universal {
    needs: &[Capability::Visibility],
    min_fidelity: Fidelity::F1,
};

/// Rules over documents' markup (links), not symbols.
const MARKUP: Applies = Applies::Universal {
    needs: &[Capability::Markup],
    min_fidelity: Fidelity::F1,
};

/// Rules over test items and call targets, which need resolved references (F2).
const REACH: Applies = Applies::Universal {
    needs: &[Capability::TestItems],
    min_fidelity: Fidelity::F2,
};

// TEMPORARY (~60SBHYV): one table of existing rules' `applies`, keyed by `RuleMeta`, until the
// `#[rule]` attribute (~N88H9SY) carries it; the migration tickets delete rows. A rule outside
// the table is a project rule and is always examined.
/// The declared applicability of `meta` (TEMPORARY table, see the module docs).
pub fn temporary_applies(meta: &RuleMeta) -> Applies {
    match meta.id {
        "TODO001" | "REF001" | "TEST001" | "INV001" | "DRIFT001" | "DRIFT002" | "DRIFT003"
        | "DRIFT004" => TEXT,
        "DOC001" | "INV002" => SYMBOLS,
        "DOC002" => MARKUP,
        "COV001" | "AFFECT001" => REACH,
        _ => Applies::Project,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-check/src/applicability.rs::resolve
    #[test]
    fn languages_outside_the_set_are_not_applicable_with_a_reason() {
        let applies = Applies::Languages {
            langs: &[Lang::Rust, Lang::Python],
            needs: &[],
            min_fidelity: Fidelity::F1,
        };
        let parse = ParseStatus::Complete;
        let facts = FileFacts {
            lang: Some(Lang::Css),
            opaque: false,
            scanned: false,
            fidelity: Fidelity::F2,
            parse: &parse,
        };
        assert_eq!(
            resolve(&applies, &facts),
            SubjectStatus::NotApplicable("rule is for rust,python; file is css".to_owned())
        );
    }

    #[test]
    fn opaque_rows_keep_todays_answers_and_reasons() {
        let parse = ParseStatus::NotParsed;
        let text = FileFacts::opaque_text(&parse);
        assert!(matches!(
            resolve(&TEXT, &text),
            SubjectStatus::Unresolved(w) if w.contains("opaque F0")
        ));
        assert!(matches!(
            resolve(&SYMBOLS, &text),
            SubjectStatus::NotApplicable(w) if w.contains("no adapter")
        ));
        let binary = FileFacts {
            lang: Some(Lang::Binary),
            ..text
        };
        assert_eq!(
            resolve(&TEXT, &binary),
            SubjectStatus::NotApplicable("binary artifact holds no text".to_owned())
        );
        let scanned = FileFacts {
            scanned: true,
            ..text
        };
        assert_eq!(resolve(&TEXT, &scanned), SubjectStatus::Examine);
    }

    #[test]
    fn project_rules_always_examine() {
        let parse = ParseStatus::NotParsed;
        assert_eq!(
            resolve(&Applies::Project, &FileFacts::opaque_text(&parse)),
            SubjectStatus::Examine
        );
    }

    #[test]
    fn symbol_subjects_derive_from_needs() {
        assert!(REACH.symbol_subjects());
        assert!(SYMBOLS.symbol_subjects());
        assert!(!TEXT.symbol_subjects());
        assert!(!MARKUP.symbol_subjects());
    }
}
