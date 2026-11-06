//! The architecture rules CYCLE001, LARGE001, DEAD001, VIS001 and DUP001 over the symbol graph (design:
//! `rules.md` repo-scope family, ticket G10).
//!
//! [`analyze`] reads one [`gob_symbols::SymbolGraph`] and returns every verdict as an
//! [`Verdict`]; the product converts them to its own findings. The five rules never run one
//! by one: they are declared with `#[rule]` ([`rules`]) and staged, like the SYS rules.
//!
//! | Rule | Polarity | Fires | Unresolved |
//! |---|---|---|---|
//! | `CYCLE001` | Pc | a cycle of Must dependency edges (import, call, reference) between crates (files outside any crate) | a cycle that needs a May edge |
//! | `LARGE001` | Pn | a function, method or type longer than `large_lines` | never (a size is exact) |
//! | `DEAD001` | P- | a private function or method no edge reaches | only May edges reach it, or an Unknown edge spells its name |
//! | `VIS001` | P- | a `pub` Rust free function outside the public API that no other package reaches | only a May edge reaches it from outside, or an Unknown edge from another package spells its name |
//! | `DUP001` | Pn | a block of 50 or more tokens copied 3 or more times (exact, renamed or same shape) | never (a token match is exact) |
//! | `DUP004` | Pn | a function in a changed file whose statement shapes match another function's, in any order | never (a shape match is exact) |
//!
//! # Known limits
//!
//! - `CYCLE001` ignores Unknown edges (they name no target to close a cycle through).
//! - `DEAD001` judges functions and methods only: the graph has no edge for a use in a type
//!   position, so a private type could look dead while it is not. A dynamic call that spells no
//!   name (`getattr(x, name)()`) is not matched to any unit.
//! - `VIS001` judges `pub` free functions in Rust files only (a type used in a type position has
//!   no edge), and the public API is the graph's `pub` chain plus `pub use` re-exports.
//! - `DUP001` compares 128-bit window hashes without verifying the tokens, so a collision could
//!   report a false clone (astronomically unlikely); it lexes Rust, Python, TypeScript and C#
//!   files outside tests, ignores comments and imports, and its thresholds are constants.
//! - The pass reads one graph. `DUP001` window hashes are cached in a content-addressed index under
//!   the git common dir, shared by all worktrees; a damaged index fails closed as `DUP003`.

// frob:ticket 01M3Z7141TW2H3HXJRK1QBHP7T

mod cycle;
mod dead;
mod dup;
mod dup_index;
mod dup_lex;
mod dup_struct;
pub mod host;
mod large;
pub mod rules;
mod vis;

use std::collections::{BTreeMap, BTreeSet};

use gob_symbols::SymbolGraph;

pub use grimble_verdict::Verdict;

/// Rule id of the import cycle rule.
pub const CYCLE: &str = "CYCLE001";
/// Rule id of the oversized unit rule.
pub const LARGE: &str = "LARGE001";
/// Rule id of the dead unit rule.
pub const DEAD: &str = "DEAD001";

/// Rule id of the visibility wider than its uses rule.
pub const VIS: &str = "VIS001";

/// Rule id of the exact duplicated code rule (rung R1).
pub const DUP: &str = "DUP001";

/// Rule id of the renamed or same-shape duplicated code rule (rungs R2 and R3).
pub const DUP_RENAMED: &str = "DUP002";

/// Rule id of the unusable clone index rule.
pub const DUP_INDEX: &str = "DUP003";

/// Rule id of the structural (statement-shape) clone rule, scoped to changed files.
pub const DUP_STRUCT: &str = "DUP004";

/// Default tokens a window needs to count as a clone; shorter repeats are idiom, not copy and paste.
pub const DUP_MIN_TOKENS: u64 = 50;

/// Default disjoint sites a block needs before it is reported; two copies are tolerated (the threshold is contested).
pub const DUP_MIN_OCCURRENCES: u64 = 3;

/// Everything the architecture pass reads.
pub struct ArchInput<'a> {
    /// The symbol graph of the walk.
    pub graph: &'a SymbolGraph,
    /// Repo-relative file path to the crate (package) that owns it; a file absent here is its own node.
    pub crates: &'a BTreeMap<String, String>,
    /// A unit longer than this many lines fires `LARGE001`; 0 turns the rule off.
    pub large_lines: usize,
    /// Tokens a window needs to count as a `DUP001` clone; 0 turns the rule off ([`DUP_MIN_TOKENS`] by default).
    pub dup_min_tokens: usize,
    /// Disjoint copies a block needs for `DUP001` to fire; below 2 turns the rule off ([`DUP_MIN_OCCURRENCES`] by default).
    pub dup_min_occurrences: usize,
    /// The text of a repo-relative file, `None` when unreadable (only called when `LARGE001` or `DUP001` is on).
    pub read: &'a dyn Fn(&str) -> Option<String>,
    /// Directory of the shared `DUP001` clone index ([`dup_index_dir`]); `None` computes every run without one.
    pub dup_index: Option<&'a std::path::Path>,
    /// Repo-relative files changed against the base; `DUP004` runs only for these (empty turns it off).
    pub changed: &'a BTreeSet<String>,
}

/// The shared clone index directory for the checkout at `root` (under the git common dir), `None` outside git.
pub fn dup_index_dir(root: &std::path::Path) -> Option<std::path::PathBuf> {
    dup_index::dir_for(root)
}

/// What the architecture pass found and examined.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct ArchReport {
    /// Findings of the five rules, sorted by file, rule and anchor.
    pub findings: Vec<Verdict>,
    /// Subjects examined per rule (nodes, sized units, private functions, `pub` functions, lexed files); a rule that is off has none.
    pub subjects: BTreeMap<&'static str, usize>,
    /// Rules whose whole scope is absent here (rule id to the reason), so zero subjects is not a gap.
    pub not_applicable: BTreeMap<&'static str, String>,
}

/// Run `CYCLE001`, `LARGE001`, `DEAD001`, `VIS001` and `DUP001` over `input`.
pub fn analyze(input: &ArchInput<'_>) -> ArchReport {
    let mut report = ArchReport::default();
    let (findings, nodes) = cycle::check(input.graph, input.crates);
    report.subjects.insert(CYCLE, nodes);
    report.findings.extend(findings);
    if nodes == 0 {
        tracing::debug!("no source units in the walk; architecture rules do not apply");
        for id in [
            CYCLE,
            LARGE,
            DEAD,
            VIS,
            DUP,
            DUP_RENAMED,
            DUP_INDEX,
            DUP_STRUCT,
        ] {
            report
                .not_applicable
                .insert(id, "no source files in the walk".to_owned());
        }
    }
    if input.large_lines > 0 {
        let (findings, sized) = large::check(input.graph, input.large_lines, input.read);
        report.subjects.insert(LARGE, sized);
        report.findings.extend(findings);
    } else {
        tracing::debug!("LARGE001 is off (large_lines = 0)");
    }
    let (findings, candidates) = dead::check(input.graph);
    report.subjects.insert(DEAD, candidates);
    report.findings.extend(findings);
    let (findings, candidates) = vis::check(input.graph, input.crates);
    report.subjects.insert(VIS, candidates);
    if !vis::has_rust(input.graph) {
        tracing::debug!("no Rust units in the walk; VIS001 does not apply");
        report
            .not_applicable
            .insert(VIS, "no Rust source files in the walk".to_owned());
    }
    report.findings.extend(findings);
    let (findings, lexed) = dup::check(
        input.graph,
        input.read,
        input.dup_min_tokens,
        input.dup_min_occurrences,
        input.dup_index,
    );
    report.subjects.insert(DUP, lexed);
    report.subjects.insert(DUP_RENAMED, lexed);
    report.subjects.insert(DUP_INDEX, lexed);
    report.findings.extend(findings);
    if input.changed.is_empty() {
        tracing::debug!("no changed files against a base; DUP004 does not apply");
        report.not_applicable.insert(
            DUP_STRUCT,
            "no changed files to scope the structural clone check to".to_owned(),
        );
    } else {
        let (findings, lexed) = dup_struct::check(
            input.graph,
            input.read,
            input.dup_min_tokens,
            input.dup_min_occurrences,
            input.changed,
        );
        report.subjects.insert(DUP_STRUCT, lexed);
        report.findings.extend(findings);
    }
    report
        .findings
        .sort_by(|a, b| (&a.file, a.rule, &a.anchor).cmp(&(&b.file, b.rule, &b.anchor)));
    tracing::info!(
        findings = report.findings.len(),
        subjects = ?report.subjects,
        "architecture pass done"
    );
    report
}
