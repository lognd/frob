//! The incompleteness metric: how often an answer is Unknown although the truth is known.
//!
//! `docs/design/cohesion.md` section 2.3: the honesty theorem keeps frob from claiming a
//! false answer but not from saying Unknown too often, so each corpus case carries an
//! oracle column (the true answer, known by construction) next to the answer the
//! analysis gave. This module is the pure comparison: [`parse_corpus`] reads the cases,
//! [`measure`] tallies them per language and capability, and [`gate`] compares the tally
//! with a committed [`Baseline`]. A rise in the false-Unknown rate fails like a
//! regression; a false Must (a decided answer that differs from the oracle) fails always.

use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

use gob_caps::Capability;
use serde::{Deserialize, Serialize};

// frob:ticket 01M4CXSZ5PYK101KSEH6SJ9WYR

/// A three-valued answer to a capability question.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Verdict {
    /// The property holds (a Must answer).
    Yes,
    /// The property does not hold (a Must answer).
    No,
    /// No decided answer: the analysis gave up, or nobody could decide it.
    Unknown,
}

impl Verdict {
    /// True for `Yes` and `No`.
    pub const fn is_decided(self) -> bool {
        !matches!(self, Self::Unknown)
    }
}

/// One corpus case: the oracle (true) answer beside the observed one.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OracleCase {
    /// A unique, stable name for the case.
    pub id: String,
    /// The language of the case (`rust`, `python`, ...).
    pub language: String,
    /// The capability asked, spelled as `Capability::name` (`resolve_ref`, ...).
    pub capability: String,
    /// The true answer, known by construction; `unknown` when genuinely undecidable.
    pub oracle: Verdict,
    /// The answer the analysis gave; the live column that `incompleteness_live` checks.
    pub observed: Verdict,
    /// The file name the probe source is read as; its extension picks the adapter.
    #[serde(default)]
    pub file: Option<String>,
    /// The probe source text the real adapter reads.
    #[serde(default)]
    pub source: Option<String>,
    /// What is asked of the source: a symbol, callee or import target, by capability.
    #[serde(default)]
    pub query: Option<String>,
}

/// What one case shows.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    /// The observed answer equals the oracle.
    Correct,
    /// Observed Unknown while the oracle is decided: incomplete, but honest.
    FalseUnknown,
    /// A decided answer that differs from the oracle (or decides an undecidable
    /// question): a soundness bug.
    FalseMust,
}

impl OracleCase {
    /// Classify this case against its oracle.
    pub fn outcome(&self) -> Outcome {
        match (self.oracle, self.observed) {
            (o, v) if o == v => Outcome::Correct,
            (_, Verdict::Unknown) => Outcome::FalseUnknown,
            _ => Outcome::FalseMust,
        }
    }
}

/// Why a corpus or baseline could not be used.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum IncompletenessError {
    /// The TOML did not parse into the expected shape.
    #[error("E-INCOMPLETE-PARSE: {0}")]
    Parse(String),
    /// A case or cell named a capability that does not exist.
    #[error("E-INCOMPLETE-CAPABILITY: `{0}` is not a capability")]
    UnknownCapability(String),
    /// Two cases share an id.
    #[error("E-INCOMPLETE-DUPLICATE: case id `{0}` appears twice")]
    DuplicateId(String),
    /// A case has an empty id or language.
    #[error("E-INCOMPLETE-EMPTY-FIELD: a case has an empty id or language")]
    EmptyField,
    /// The corpus has no cases, so the metric would pass vacuously.
    #[error("E-INCOMPLETE-VACUOUS: the corpus has no cases")]
    EmptyCorpus,
    /// A baseline cell claims more false Unknowns than decidable cases, or lists a cell twice.
    #[error("E-INCOMPLETE-BASELINE: {0}")]
    Baseline(String),
}

#[derive(Deserialize)]
struct CorpusFile {
    #[serde(default)]
    case: Vec<OracleCase>,
}

fn check_capability(name: &str) -> Result<(), IncompletenessError> {
    if Capability::ALL.iter().any(|c| c.name() == name) {
        Ok(())
    } else {
        Err(IncompletenessError::UnknownCapability(name.to_owned()))
    }
}

/// Parse and validate a TOML corpus of `[[case]]` tables.
///
/// # Errors
/// `Parse`, `EmptyCorpus`, `EmptyField`, `UnknownCapability` or `DuplicateId`.
pub fn parse_corpus(text: &str) -> Result<Vec<OracleCase>, IncompletenessError> {
    let file: CorpusFile =
        toml::from_str(text).map_err(|e| IncompletenessError::Parse(e.to_string()))?;
    if file.case.is_empty() {
        return Err(IncompletenessError::EmptyCorpus);
    }
    let mut seen = BTreeSet::new();
    for c in &file.case {
        if c.id.trim().is_empty() || c.language.trim().is_empty() {
            return Err(IncompletenessError::EmptyField);
        }
        check_capability(&c.capability)?;
        if !seen.insert(c.id.as_str()) {
            return Err(IncompletenessError::DuplicateId(c.id.clone()));
        }
    }
    tracing::debug!(cases = file.case.len(), "parsed the oracle corpus");
    Ok(file.case)
}

/// A (language, capability) pair, the unit the metric is reported in.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub struct CellKey {
    /// The language.
    pub language: String,
    /// The capability name.
    pub capability: String,
}

impl fmt::Display for CellKey {
    /// `language/capability`.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}/{}", self.language, self.capability)
    }
}

/// The tally for one cell.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
pub struct Tally {
    /// Cases whose oracle is decided: the denominator of the false-Unknown rate.
    pub decidable: u64,
    /// Decidable cases answered Unknown.
    pub false_unknown: u64,
    /// Cases answered with a decided answer that disagrees with the oracle.
    pub false_must: u64,
}

impl Tally {
    /// The false-Unknown rate, or `None` when no case is decidable.
    #[allow(clippy::cast_precision_loss)]
    pub fn rate(&self) -> Option<f64> {
        (self.decidable > 0).then(|| self.false_unknown as f64 / self.decidable as f64)
    }
}

/// The per-cell tallies of a corpus.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct Report {
    /// Tallies keyed by cell, sorted.
    pub cells: BTreeMap<CellKey, Tally>,
}

/// Tally `cases` per language and capability.
pub fn measure(cases: &[OracleCase]) -> Report {
    let mut cells: BTreeMap<CellKey, Tally> = BTreeMap::new();
    for c in cases {
        let t = cells
            .entry(CellKey {
                language: c.language.clone(),
                capability: c.capability.clone(),
            })
            .or_default();
        if c.oracle.is_decided() {
            t.decidable += 1;
        }
        match c.outcome() {
            Outcome::Correct => {}
            Outcome::FalseUnknown => t.false_unknown += 1,
            Outcome::FalseMust => {
                tracing::error!(case = %c.id, "false Must: a decided answer disagrees with the oracle");
                t.false_must += 1;
            }
        }
    }
    Report { cells }
}

impl Report {
    /// One line per cell: counts and the rate, for the CI log.
    pub fn render_text(&self) -> String {
        let lines = self.cells.iter().map(|(k, t)| {
            let rate = t
                .rate()
                .map_or_else(|| "n/a".to_owned(), |r| format!("{:.1}%", r * 100.0));
            format!(
                "{k}: {}/{} false Unknown ({rate}), {} false Must\n",
                t.false_unknown, t.decidable, t.false_must
            )
        });
        std::iter::once("false-Unknown rate per language and capability\n".to_owned())
            .chain(lines)
            .collect()
    }

    /// The report as a baseline file, for committing when the rate falls.
    ///
    /// # Errors
    /// `Parse` when the baseline cannot be serialized.
    pub fn to_baseline_toml(&self) -> Result<String, IncompletenessError> {
        let file = BaselineFile {
            cell: self
                .cells
                .iter()
                .map(|(k, t)| BaselineCell {
                    language: k.language.clone(),
                    capability: k.capability.clone(),
                    decidable: t.decidable,
                    false_unknown: t.false_unknown,
                })
                .collect(),
        };
        toml::to_string(&file).map_err(|e| IncompletenessError::Parse(e.to_string()))
    }
}

#[derive(Serialize, Deserialize)]
struct BaselineFile {
    #[serde(default)]
    cell: Vec<BaselineCell>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct BaselineCell {
    language: String,
    capability: String,
    decidable: u64,
    false_unknown: u64,
}

/// The accepted false-Unknown counts per cell; the rate may fall but not rise.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct Baseline {
    cells: BTreeMap<CellKey, Tally>,
}

/// Parse and validate a baseline TOML (`[[cell]]` tables).
///
/// # Errors
/// `Parse`, `UnknownCapability` or `Baseline` for malformed, misnamed or inconsistent cells.
pub fn parse_baseline(text: &str) -> Result<Baseline, IncompletenessError> {
    let file: BaselineFile =
        toml::from_str(text).map_err(|e| IncompletenessError::Parse(e.to_string()))?;
    let mut cells = BTreeMap::new();
    for c in file.cell {
        check_capability(&c.capability)?;
        if c.false_unknown > c.decidable {
            return Err(IncompletenessError::Baseline(format!(
                "{}/{} has more false Unknowns than decidable cases",
                c.language, c.capability
            )));
        }
        let key = CellKey {
            language: c.language,
            capability: c.capability,
        };
        let tally = Tally {
            decidable: c.decidable,
            false_unknown: c.false_unknown,
            false_must: 0,
        };
        if cells.insert(key.clone(), tally).is_some() {
            return Err(IncompletenessError::Baseline(format!("{key} listed twice")));
        }
    }
    Ok(Baseline { cells })
}

/// One reason the gate fails.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum Violation {
    /// A decided answer disagreed with the oracle; never baselined.
    FalseMust {
        /// The cell.
        cell: CellKey,
        /// How many cases.
        count: u64,
    },
    /// The false-Unknown rate rose above the baseline's.
    Rise {
        /// The cell.
        cell: CellKey,
        /// Baseline `(false_unknown, decidable)`; `(0, 0)` for a cell with no baseline.
        was: (u64, u64),
        /// Current `(false_unknown, decidable)`.
        now: (u64, u64),
    },
    /// A baselined cell has no decidable case now, so its rate can no longer be measured.
    Vanished {
        /// The cell.
        cell: CellKey,
        /// The baseline decidable count that was lost.
        was_decidable: u64,
    },
}

impl fmt::Display for Violation {
    /// A one-line actionable description.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::FalseMust { cell, count } => write!(
                f,
                "{cell}: {count} false Must (a decided answer disagrees with the oracle); a soundness bug"
            ),
            Self::Rise { cell, was, now } => write!(
                f,
                "{cell}: false-Unknown rate rose from {}/{} to {}/{}",
                was.0, was.1, now.0, now.1
            ),
            Self::Vanished {
                cell,
                was_decidable,
            } => write!(
                f,
                "{cell}: no decidable case remains (baseline had {was_decidable}); the rate is unmeasured"
            ),
        }
    }
}

/// Compare `report` with `baseline`; empty means the gate passes.
///
/// A cell absent from the baseline is held to a zero rate. A lower rate passes, however
/// the counts moved. Violations are sorted by cell.
pub fn gate(report: &Report, baseline: &Baseline) -> Vec<Violation> {
    let mut out = Vec::new();
    for (cell, now) in &report.cells {
        if now.false_must > 0 {
            out.push(Violation::FalseMust {
                cell: cell.clone(),
                count: now.false_must,
            });
        }
        let was = baseline.cells.get(cell).copied().unwrap_or_default();
        if now.decidable == 0 {
            if was.decidable > 0 {
                out.push(Violation::Vanished {
                    cell: cell.clone(),
                    was_decidable: was.decidable,
                });
            }
            continue;
        }
        // now.fu / now.dec > was.fu / was.dec, cross-multiplied; was.dec == 0 means rate 0.
        let rose = if was.decidable == 0 {
            now.false_unknown > 0
        } else {
            u128::from(now.false_unknown) * u128::from(was.decidable)
                > u128::from(was.false_unknown) * u128::from(now.decidable)
        };
        if rose {
            out.push(Violation::Rise {
                cell: cell.clone(),
                was: (was.false_unknown, was.decidable),
                now: (now.false_unknown, now.decidable),
            });
        }
    }
    for (cell, was) in &baseline.cells {
        if was.decidable > 0 && !report.cells.contains_key(cell) {
            out.push(Violation::Vanished {
                cell: cell.clone(),
                was_decidable: was.decidable,
            });
        }
    }
    out.sort();
    for v in &out {
        tracing::warn!(violation = %v, "incompleteness gate");
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn case(id: &str, lang: &str, oracle: Verdict, observed: Verdict) -> OracleCase {
        OracleCase {
            id: id.to_owned(),
            language: lang.to_owned(),
            capability: "resolve_ref".to_owned(),
            oracle,
            observed,
            file: None,
            source: None,
            query: None,
        }
    }

    fn base(fu: u64, dec: u64) -> Baseline {
        let text = format!(
            "[[cell]]\nlanguage = \"rust\"\ncapability = \"resolve_ref\"\ndecidable = {dec}\nfalse_unknown = {fu}\n"
        );
        parse_baseline(&text).unwrap()
    }

    // frob:tests crates/gob-check/src/incompleteness.rs::OracleCase.outcome
    #[test]
    fn outcomes_classify_against_the_oracle() {
        use Verdict::{No, Unknown, Yes};
        assert_eq!(case("a", "rust", Yes, Yes).outcome(), Outcome::Correct);
        assert_eq!(
            case("a", "rust", Unknown, Unknown).outcome(),
            Outcome::Correct
        );
        assert_eq!(
            case("a", "rust", Yes, Unknown).outcome(),
            Outcome::FalseUnknown
        );
        assert_eq!(case("a", "rust", Yes, No).outcome(), Outcome::FalseMust);
        assert_eq!(
            case("a", "rust", Unknown, Yes).outcome(),
            Outcome::FalseMust
        );
    }

    // frob:tests crates/gob-check/src/incompleteness.rs::measure
    #[test]
    fn undecidable_oracles_stay_out_of_the_denominator() {
        use Verdict::{Unknown, Yes};
        let r = measure(&[
            case("a", "rust", Yes, Unknown),
            case("b", "rust", Yes, Yes),
            case("c", "rust", Unknown, Unknown),
        ]);
        let t = r.cells.values().next().unwrap();
        assert_eq!((t.decidable, t.false_unknown, t.false_must), (2, 1, 0));
        assert_eq!(t.rate(), Some(0.5));
    }

    // frob:tests crates/gob-check/src/incompleteness.rs::gate
    #[test]
    fn a_rise_fails_and_a_fall_or_equal_passes() {
        use Verdict::{Unknown, Yes};
        let one_of_two = measure(&[case("a", "rust", Yes, Unknown), case("b", "rust", Yes, Yes)]);
        assert!(gate(&one_of_two, &base(1, 2)).is_empty());
        assert!(gate(&one_of_two, &base(2, 2)).is_empty());
        // 1/1 down to 1/2: the rate fell. 1/4 up to 1/2: same count, smaller denominator, a rise.
        assert!(gate(&one_of_two, &base(1, 1)).is_empty());
        assert_eq!(gate(&one_of_two, &base(1, 4)).len(), 1);
        let rose = gate(&one_of_two, &base(0, 2));
        assert!(matches!(rose[..], [Violation::Rise { .. }]));
        assert!(rose[0].to_string().contains("rust/resolve_ref"));
    }

    // frob:tests crates/gob-check/src/incompleteness.rs::gate
    #[test]
    fn a_false_must_always_fails_even_when_baselined() {
        use Verdict::{No, Yes};
        let r = measure(&[case("a", "rust", Yes, No)]);
        let v = gate(&r, &base(0, 1));
        assert!(matches!(v[..], [Violation::FalseMust { count: 1, .. }]));
    }

    // frob:tests crates/gob-check/src/incompleteness.rs::gate
    #[test]
    fn an_unbaselined_cell_is_held_to_zero_and_a_lost_cell_is_flagged() {
        use Verdict::{Unknown, Yes};
        let r = measure(&[case("a", "python", Yes, Unknown)]);
        let v = gate(&r, &base(0, 3));
        assert_eq!(v.len(), 2, "{v:?}");
        assert!(
            v.iter()
                .any(|x| matches!(x, Violation::Rise { was: (0, 0), .. }))
        );
        assert!(v.iter().any(|x| matches!(
            x,
            Violation::Vanished {
                was_decidable: 3,
                ..
            }
        )));
        // A cell whose oracles are all undecidable has no rate to hold.
        let only_undecidable = measure(&[case("u", "rust", Unknown, Unknown)]);
        assert!(gate(&only_undecidable, &Baseline::default()).is_empty());
        assert_eq!(gate(&only_undecidable, &base(0, 2)).len(), 1);
    }

    // frob:tests crates/gob-check/src/incompleteness.rs::parse_corpus
    #[test]
    fn a_bad_corpus_is_rejected() {
        let case_toml = |id: &str, cap: &str| {
            format!(
                "[[case]]\nid = \"{id}\"\nlanguage = \"rust\"\ncapability = \"{cap}\"\noracle = \"yes\"\nobserved = \"yes\"\n"
            )
        };
        assert_eq!(parse_corpus(""), Err(IncompletenessError::EmptyCorpus));
        assert_eq!(
            parse_corpus(&case_toml("a", "nope")),
            Err(IncompletenessError::UnknownCapability("nope".to_owned()))
        );
        let dup = case_toml("a", "imports") + &case_toml("a", "imports");
        assert_eq!(
            parse_corpus(&dup),
            Err(IncompletenessError::DuplicateId("a".to_owned()))
        );
        assert_eq!(
            parse_corpus(&case_toml(" ", "imports")),
            Err(IncompletenessError::EmptyField)
        );
        assert!(matches!(
            parse_corpus("[[case]]\nid = 1"),
            Err(IncompletenessError::Parse(_))
        ));
        assert_eq!(parse_corpus(&case_toml("a", "imports")).unwrap().len(), 1);
    }

    // frob:tests crates/gob-check/src/incompleteness.rs::parse_baseline
    #[test]
    fn a_bad_baseline_is_rejected() {
        let cell = "[[cell]]\nlanguage = \"rust\"\ncapability = \"imports\"\ndecidable = 1\nfalse_unknown = 2\n";
        assert!(matches!(
            parse_baseline(cell),
            Err(IncompletenessError::Baseline(_))
        ));
        let twice = cell
            .replace("false_unknown = 2", "false_unknown = 0")
            .repeat(2);
        assert!(matches!(
            parse_baseline(&twice),
            Err(IncompletenessError::Baseline(_))
        ));
        assert!(parse_baseline(&cell.replace("imports", "bogus")).is_err());
    }

    // frob:tests crates/gob-check/src/incompleteness.rs::Report.to_baseline_toml
    #[test]
    fn a_report_round_trips_through_a_baseline() {
        use Verdict::{Unknown, Yes};
        let r = measure(&[case("a", "rust", Yes, Unknown), case("b", "rust", Yes, Yes)]);
        let b = parse_baseline(&r.to_baseline_toml().unwrap()).unwrap();
        assert!(gate(&r, &b).is_empty());
        assert!(
            r.render_text()
                .contains("rust/resolve_ref: 1/2 false Unknown (50.0%)")
        );
    }
}
