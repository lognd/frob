//! The language matrix for Universal rules (`docs/design/testing.md` section 4, D106).
//!
//! A Universal rule is tested once per matrix cell (a language at its fidelity, plus opaque text,
//! binary and an embedded island). A block names its cell with `cell=NAME`. The expected outcome
//! class of each cell is not hand-written truth: a pluggable [`Deriver`] computes it from the rule's
//! declared needs and the capability matrix, and a block whose `expect=` contradicts it fails.
//! `gob-mdtest` cannot depend on `gob-check` (which owns the resolver), so the caller injects the
//! deriver; `crates/frob-check/tests/rule_matrix.rs` wires the real one.
//!
//! Completeness mirrors [`crate::coverage`]: every Universal rule has a block in every cell, or an
//! allowlisted `[[matrix_gap]]` with a ticket. The allowlist may only shrink.
//!
//! `parity=NAME` groups blocks of one rule that state the same logical case in several languages:
//! every block in a group whose cell derives `Examine` must agree on fire versus clean.

// frob:ticket 01M48Q4DMNMQEYQNWPK42DZ0RZ

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;

use serde::Deserialize;

use crate::coverage::{Allowlist, is_handle};
use crate::parse::{Block, Expect};

/// The matrix cells, in report order: languages at their fidelity, then the pseudo-cells.
pub const CELLS: [&str; 8] = [
    "rust",
    "python",
    "typescript",
    "csharp",
    "markdown",
    "text",
    "binary",
    "island",
];

/// What a cell does to a rule, derived from needs and capabilities (not hand-written).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Derived {
    /// The rule examines the file: `expect=fire` or `expect=clean`.
    Examine,
    /// The rule applies but cannot decide: `expect=unresolved`.
    Unresolved,
    /// The rule cannot apply by construction: `expect=notapplicable`.
    NotApplicable,
}

impl Derived {
    /// True when a block expecting `expect` agrees with this derived class.
    #[must_use]
    pub fn admits(self, expect: Expect) -> bool {
        match self {
            Self::Examine => matches!(expect, Expect::Fire | Expect::Clean),
            Self::Unresolved => expect == Expect::Unresolved,
            Self::NotApplicable => expect == Expect::NotApplicable,
        }
    }
}

impl std::fmt::Display for Derived {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            Self::Examine => "fire or clean",
            Self::Unresolved => "unresolved",
            Self::NotApplicable => "notapplicable",
        })
    }
}

/// The injected derivation: `(rule id, cell)` to the derived class, or `None` when the rule is unknown.
pub type Deriver<'a> = &'a dyn Fn(&str, &str) -> Option<Derived>;

/// One allowlisted matrix gap: a rule's cell (or `*` for every uncovered cell) with no block yet.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MatrixGap {
    /// Product namespace of the rule.
    pub product: String,
    /// Rule id.
    pub rule: String,
    /// A cell name from [`CELLS`], or `*` for all of the rule's uncovered cells.
    pub cell: String,
    /// Ticket handle (`~XXXXXXX`) that will fill the cell.
    pub ticket: String,
}

/// The outcome of one product's matrix check.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct MatrixReport {
    /// `(rule, cell)` pairs checked.
    pub checked: usize,
    /// Blocks whose `expect=` contradicts the derived class.
    pub contradictions: Vec<String>,
    /// Parity groups whose Examine cells disagree on fire versus clean.
    pub parity: Vec<String>,
    /// `(rule, cell)` with no block and no allowlist entry.
    pub missing: Vec<(String, String)>,
    /// Allowlist entries whose cells are all filled (delete them).
    pub stale: Vec<String>,
    /// Allowlist entries naming a rule that is not a Universal rule of the product, or an unknown cell.
    pub unknown: Vec<String>,
    /// Allowlist entries without a valid ticket handle.
    pub bad_ticket: Vec<String>,
}

impl MatrixReport {
    /// True when nothing is wrong.
    #[must_use]
    pub fn passed(&self) -> bool {
        self.contradictions.is_empty()
            && self.parity.is_empty()
            && self.missing.is_empty()
            && self.stale.is_empty()
            && self.unknown.is_empty()
            && self.bad_ticket.is_empty()
    }

    /// A multi-line failure text naming every offence.
    #[must_use]
    pub fn render(&self) -> String {
        let mut out = format!("language matrix ({} rule cells)\n", self.checked);
        for c in &self.contradictions {
            let _ = writeln!(out, "  contradiction: {c}");
        }
        for p in &self.parity {
            let _ = writeln!(out, "  parity: {p}");
        }
        for (rule, cell) in &self.missing {
            let _ = writeln!(
                out,
                "  {rule}: no `cell={cell}` block; add one or allowlist it as a [[matrix_gap]] with a ticket"
            );
        }
        for s in &self.stale {
            let _ = writeln!(out, "  {s}: allowlisted but now covered; delete the entry");
        }
        for u in &self.unknown {
            let _ = writeln!(
                out,
                "  {u}: allowlisted but not a Universal rule or known cell; delete the entry"
            );
        }
        for b in &self.bad_ticket {
            let _ = writeln!(
                out,
                "  {b}: allowlist entry needs a ticket handle like ~ABCDEFG"
            );
        }
        out
    }
}

/// Check `blocks` against the derived matrix of the Universal `rules` of `product`.
///
/// Every cell block is compared with `derive`; every `(rule, cell)` must be filled or allowlisted;
/// parity groups must agree.
#[must_use]
pub fn analyze_matrix(
    product: &str,
    rules: &[String],
    blocks: &[Block],
    derive: Deriver<'_>,
    allowlist: &Allowlist,
) -> MatrixReport {
    let mut report = MatrixReport::default();
    let universal: BTreeSet<&str> = rules.iter().map(String::as_str).collect();
    let mut filled: BTreeSet<(&str, &str)> = BTreeSet::new();
    let mut groups: BTreeMap<(&str, &str), Vec<(&Block, &str)>> = BTreeMap::new();
    for b in blocks {
        let Some(cell) = b.cell.as_deref() else {
            continue;
        };
        let rule = b.rule.as_str();
        if !universal.contains(rule) {
            continue;
        }
        filled.insert((rule, cell));
        match derive(rule, cell) {
            Some(d) if !d.admits(b.expect) => report.contradictions.push(format!(
                "{rule} cell={cell} expects {} but the capability matrix derives {d} ({})",
                b.expect, b.name
            )),
            Some(Derived::Examine) => {
                if let Some(p) = b.parity.as_deref() {
                    groups.entry((rule, p)).or_default().push((b, cell));
                }
            }
            _ => {}
        }
    }
    for ((rule, name), members) in &groups {
        let fires: BTreeSet<bool> = members
            .iter()
            .map(|(b, _)| b.expect == Expect::Fire)
            .collect();
        if fires.len() > 1 {
            let cells: Vec<String> = members
                .iter()
                .map(|(b, c)| format!("{c}={}", b.expect))
                .collect();
            report.parity.push(format!(
                "{rule} parity={name} disagrees across cells: {}",
                cells.join(", ")
            ));
        }
    }
    let allowed: Vec<&MatrixGap> = allowlist
        .matrix_gap
        .iter()
        .filter(|g| g.product == product)
        .collect();
    for rule in rules {
        for cell in CELLS {
            report.checked += 1;
            let listed = allowed
                .iter()
                .any(|g| g.rule == *rule && (g.cell == cell || g.cell == "*"));
            match (filled.contains(&(rule.as_str(), cell)), listed) {
                (false, false) => report.missing.push((rule.clone(), cell.to_owned())),
                (true, true) if allowed.iter().any(|g| g.rule == *rule && g.cell == cell) => {
                    report.stale.push(format!("{rule} cell={cell}"));
                }
                _ => {}
            }
        }
    }
    for g in &allowed {
        let key = format!("{} cell={}", g.rule, g.cell);
        if !universal.contains(g.rule.as_str())
            || (g.cell != "*" && !CELLS.contains(&g.cell.as_str()))
        {
            report.unknown.push(key.clone());
        }
        if !is_handle(&g.ticket) {
            report.bad_ticket.push(key.clone());
        }
        if g.cell == "*"
            && CELLS
                .iter()
                .all(|c| filled.contains(&(g.rule.as_str(), *c)))
        {
            report.stale.push(key);
        }
    }
    tracing::info!(
        product,
        checked = report.checked,
        contradictions = report.contradictions.len(),
        missing = report.missing.len(),
        passed = report.passed(),
        "language matrix analysed"
    );
    report
}

/// Test entry point: panic naming every matrix offence of `product`'s Universal `rules`.
///
/// `compile_time_manifest` is the caller's `env!("CARGO_MANIFEST_DIR")`; the workspace root is two
/// levels above it.
///
/// # Panics
///
/// Panics when the matrix check fails or the allowlist is unreadable.
pub fn assert_matrix(
    compile_time_manifest: &str,
    product: &str,
    rules: &[String],
    derive: Deriver<'_>,
) {
    let root = crate::manifest_dir(compile_time_manifest)
        .ancestors()
        .nth(2)
        .expect("crate lives two levels below the workspace root")
        .to_owned();
    let allowlist = Allowlist::load(&root.join(crate::coverage::ALLOWLIST_PATH))
        .unwrap_or_else(|e| panic!("{e}"));
    let blocks = crate::coverage::scan_blocks(&root);
    let report = analyze_matrix(product, rules, &blocks, derive, &allowlist);
    assert!(report.passed(), "{}", report.render());
}
