//! Opaque-region cases: a lexical rule fires inside an island, a structural rule over it is Unresolved.
//!
//! `docs/design/shared/universal-model.md` section 2.2 item 4 lets text, literals and prose queries
//! read an opaque payload (a shell `run:` body in YAML, a `#if 0` block, a template literal) while
//! every structural query over it is Unknown. A block names its island with `region=NAME`; blocks
//! of one section sharing a name read the same island. A region that holds a lexical `expect=fire`
//! case must also hold a structural rule's `expect=unresolved` case, and no structural rule may
//! claim to fire or be clean over it (that would be a silent pass). Which rules are lexical is
//! injected (`needs = Lexical` in the registry; see [`crate::coverage::CoverageRule`]).

// frob:ticket 01M48Q4FV1V0ZRM8C4J1YMJ2G9

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;

use crate::coverage::OPAQUE_CELL;
use crate::parse::{Block, Expect};

/// The outcome of one opaque-region check.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct OpaqueReport {
    /// Regions examined.
    pub regions: usize,
    /// Lexical `cell=island` fire blocks that name no `region=`.
    pub unnamed: Vec<String>,
    /// Regions with a lexical fire but no structural `expect=unresolved` block.
    pub no_structural: Vec<String>,
    /// Structural blocks over a region that expect something other than Unresolved.
    pub not_unresolved: Vec<String>,
}

impl OpaqueReport {
    /// True when nothing is wrong.
    #[must_use]
    pub fn passed(&self) -> bool {
        self.unnamed.is_empty() && self.no_structural.is_empty() && self.not_unresolved.is_empty()
    }

    /// A multi-line failure text naming every offence.
    #[must_use]
    pub fn render(&self) -> String {
        let mut out = format!("opaque regions ({} examined)\n", self.regions);
        for u in &self.unnamed {
            writeln!(out, "  {u}: lexical island fire needs a `region=NAME`").ok();
        }
        for n in &self.no_structural {
            writeln!(
                out,
                "  {n}: no structural rule is shown Unresolved over this region; add an `expect=unresolved region=...` block"
            )
            .ok();
        }
        for n in &self.not_unresolved {
            writeln!(
                out,
                "  {n}: a structural rule over an opaque region must be Unresolved, never fire or clean"
            )
            .ok();
        }
        out
    }
}

/// Check the `region=` blocks of `blocks` against the `lexical` rule ids.
#[must_use]
pub fn analyze_opaque(lexical: &[String], blocks: &[Block]) -> OpaqueReport {
    let lex: BTreeSet<&str> = lexical.iter().map(String::as_str).collect();
    let mut report = OpaqueReport::default();
    let mut regions: BTreeMap<(&str, &str), Vec<&Block>> = BTreeMap::new();
    for b in blocks {
        match b.region.as_deref() {
            Some(r) => regions.entry((b.section.as_str(), r)).or_default().push(b),
            None if lex.contains(b.rule.as_str())
                && b.expect == Expect::Fire
                && b.matrix_cells().contains(&OPAQUE_CELL) =>
            {
                report.unnamed.push(b.name.clone());
            }
            None => {}
        }
    }
    for ((section, name), members) in &regions {
        report.regions += 1;
        let label = format!("{section} region={name}");
        let fires = members
            .iter()
            .any(|b| lex.contains(b.rule.as_str()) && b.expect == Expect::Fire);
        let mut unresolved = false;
        for b in members.iter().filter(|b| !lex.contains(b.rule.as_str())) {
            if b.expect == Expect::Unresolved {
                unresolved = true;
            } else {
                report.not_unresolved.push(format!("{label}: {}", b.name));
            }
        }
        if fires && !unresolved {
            report.no_structural.push(label);
        }
    }
    tracing::info!(
        regions = report.regions,
        passed = report.passed(),
        "opaque regions analysed"
    );
    report
}

/// Test entry point: panic naming every opaque-region offence among the suites under the workspace.
///
/// `compile_time_manifest` is the caller's `env!("CARGO_MANIFEST_DIR")`.
///
/// # Panics
///
/// Panics when the check fails.
pub fn assert_opaque(compile_time_manifest: &str, lexical: &[String]) {
    let root = crate::manifest_dir(compile_time_manifest)
        .ancestors()
        .nth(2)
        .expect("crate lives two levels below the workspace root")
        .to_owned();
    let blocks = crate::coverage::scan_blocks(&root);
    let report = analyze_opaque(lexical, &blocks);
    assert!(report.passed(), "{}", report.render());
}

// frob:ticket 01M6ME35JTR9149M74ZPPGV4YY
/// Test entry point: run [`assert_opaque`] for one registered `product`, deriving its lexical rules from the registry.
///
/// Only blocks whose rule belongs to `product` are judged, so one product's lexical rules are never
/// mistaken for another's structural ones. `compile_time_manifest` is the caller's `env!("CARGO_MANIFEST_DIR")`.
///
/// # Panics
///
/// Panics when the check fails.
pub fn assert_product_opaque(compile_time_manifest: &str, product: &str) {
    let root = crate::manifest_dir(compile_time_manifest)
        .ancestors()
        .nth(2)
        .expect("crate lives two levels below the workspace root")
        .to_owned();
    let rules = crate::coverage::rules_of(gob_rules::Registry::global(), product);
    let lexical: Vec<String> = rules
        .iter()
        .filter(|r| r.needs == gob_rules::Needs::Lexical)
        .map(|r| r.id.clone())
        .collect();
    let ids: BTreeSet<&str> = rules.iter().map(|r| r.id.as_str()).collect();
    let blocks: Vec<Block> = crate::coverage::scan_blocks(&root)
        .into_iter()
        .filter(|b| ids.contains(b.rule.as_str()))
        .collect();
    tracing::debug!(
        product,
        lexical = lexical.len(),
        blocks = blocks.len(),
        "product opaque check"
    );
    let report = analyze_opaque(&lexical, &blocks);
    assert!(report.passed(), "{}", report.render());
}
