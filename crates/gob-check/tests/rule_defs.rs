//! A toy product that runs declared rules (`RuleDef`s) with no group or file-check wiring (~GBBKJ6V).
//!
//! `product_rules/{alpha,beta,gamma}` are generated rule crates in miniature: ALP001 is a file
//! rule, BET001 a repo rule, GMM001 a `must_measure` repo rule with a product-fact `inapplicable()`.
//! The product lists them once and the pipeline runs exactly that list.

use std::sync::Arc;

use gob_check::{
    CheckError, CollectCx, Collected, FileCheck, NoScope, Product, RepoGroup, RuleSet, RunOptions,
    Snapshot, run,
};
use gob_diagnostics::ExitCode;
use gob_rules::{
    ExceptionCtx, Finding, RequiredReason, Resolved, Severity, apply_exceptions, indexgen,
};
use gob_symbols::{Fidelity, FileInfo, ParseStatus};
use gob_text::FileInterner;

/// The host trait the fixture rules evaluate against; the toy product is its own host.
pub trait Host {
    /// True when the repository is bad.
    fn bad_repo(&self) -> bool;
    /// How many items the product holds.
    fn items(&self) -> usize;
    /// True when the product has no item store at all.
    fn disabled(&self) -> bool;
}

#[path = "product_rules/alpha/src/rules/mod.rs"]
pub mod alpha_rules;
#[path = "product_rules/beta/src/rules/mod.rs"]
pub mod beta_rules;
#[path = "product_rules/gamma/src/rules/mod.rs"]
pub mod gamma_rules;

/// Stand-in rule crate, see `product_rules.rs`.
mod alpha {
    pub use super::alpha_rules as rules;
}
/// Stand-in rule crate.
mod beta {
    pub use super::beta_rules as rules;
}
/// Stand-in rule crate.
mod gamma {
    pub use super::gamma_rules as rules;
}

mod listed {
    use super::{Host, alpha, beta, gamma};

    gob_check::product_rules! {
        product = Toy;
        host = dyn Host;
        crates = [alpha, beta, gamma];
    }
}

/// A product with no file checks and no repo groups: its rules are exactly the list above.
struct Toy {
    bad: bool,
    items: usize,
    disabled: bool,
}

impl Host for Toy {
    fn bad_repo(&self) -> bool {
        self.bad
    }
    fn items(&self) -> usize {
        self.items
    }
    fn disabled(&self) -> bool {
        self.disabled
    }
}

fn host<'a>(toy: &'a Toy, _snap: &'a Snapshot<Toy>) -> &'a (dyn Host + 'static) {
    toy
}

impl Product for Toy {
    type Shared = ();
    type Inputs = ();
    type Scope = NoScope;

    fn name(&self) -> &'static str {
        "toy"
    }

    fn collect(&self, _cx: &mut CollectCx<'_>) -> Result<Collected<Self>, CheckError> {
        Ok(Collected {
            shared: (),
            inputs: (),
            findings: Vec::new(),
        })
    }

    fn rule_set(&self) -> RuleSet<Self> {
        RuleSet::new().bind(listed::rules(), host)
    }

    fn file_checks(&self) -> Vec<Arc<dyn FileCheck<Self>>> {
        Vec::new()
    }

    fn repo_groups(&self) -> Vec<RepoGroup<Self>> {
        Vec::new()
    }

    fn repo_digest(&self, _snap: &Snapshot<Self>) -> Vec<u8> {
        Vec::new()
    }

    fn resolve_exceptions(
        &self,
        _snap: &Snapshot<Self>,
        files: &FileInterner,
        raw: Vec<Finding>,
    ) -> Resolved {
        apply_exceptions(raw, &[], &ExceptionCtx { files })
    }

    /// `.log` and `.png` files are adapter-less (opaque F0); every other file has no facts.
    fn file_info(&self, _shared: &(), path: &str) -> Option<FileInfo> {
        matches!(
            std::path::Path::new(path)
                .extension()
                .and_then(|e| e.to_str()),
            Some("log" | "png")
        )
        .then(|| FileInfo {
            language: String::new(),
            fidelity: Fidelity::F0,
            parse_status: ParseStatus::NotParsed,
            degraded: false,
        })
    }
}

fn toy(bad: bool, items: usize, disabled: bool) -> Toy {
    Toy {
        bad,
        items,
        disabled,
    }
}

fn tree() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("a.txt"), "a bad word\n").expect("write");
    std::fs::write(dir.path().join("b.txt"), "all fine\n").expect("write");
    dir
}

fn quiet() -> RunOptions {
    RunOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..RunOptions::default()
    }
}

fn ids(findings: &[Finding]) -> Vec<String> {
    findings.iter().map(|f| f.rule.to_string()).collect()
}

// frob:tests crates/gob-check/src/defs.rs::run_file_rules
// frob:tests crates/gob-check/src/defs.rs::run_repo_rules
#[test]
fn a_toy_product_runs_its_listed_file_and_repo_rules_with_no_group_wiring() {
    let dir = tree();
    let first = run(&toy(true, 3, false), dir.path(), &quiet()).expect("first run");
    assert_eq!(ids(&first.findings), ["ALP001", "BET001"]);
    assert_eq!(first.subjects_examined.get("ALP001"), Some(&2));
    assert_eq!(first.subjects_examined.get("GMM001"), Some(&3));
    assert!(first.stats.file_misses > 0);
    let second = run(&toy(true, 3, false), dir.path(), &quiet()).expect("second run");
    assert_eq!(second.stats.file_misses, 0, "file results are cached");
    assert_eq!(second.stats.repo_misses, 0, "repo results are cached");
    assert_eq!(second.findings, first.findings);
    assert_eq!(second.subjects_examined, first.subjects_examined);
}

// frob:tests crates/gob-check/src/defs.rs::run_repo_rules
#[test]
fn a_clean_toy_fires_nothing() {
    let dir = tree();
    std::fs::write(dir.path().join("a.txt"), "fine\n").expect("write");
    let report = run(&toy(false, 1, false), dir.path(), &quiet()).expect("run");
    assert!(report.findings.is_empty(), "{:?}", report.findings);
    assert!(
        report.subjects_examined["ALP001"] > 0,
        "a clean pass examined something"
    );
}

// frob:tests crates/gob-check/src/defs.rs::Live.select
#[test]
fn an_inapplicable_rule_is_skipped_and_its_reason_reported_once_in_json_and_text() {
    let dir = tree();
    let report = run(&toy(false, 0, true), dir.path(), &quiet()).expect("run");
    assert_eq!(
        ids(&report.findings),
        ["ALP001"],
        "inapplicable GMM001 is no finding, not even its zero-subject Unresolved"
    );
    assert!(!report.subjects_examined.contains_key("GMM001"));
    let why = "the product has no item store configured";
    assert_eq!(report.fidelity.inapplicable["GMM001"], why);
    let json = serde_json::to_value(&report.fidelity).expect("json");
    assert_eq!(json["inapplicable"]["GMM001"], why);
    let text = report.fidelity.lines();
    let mentions = text.iter().filter(|l| l.contains("GMM001")).count();
    assert_eq!(mentions, 1, "{text:?}");
    assert!(text.iter().any(|l| l.contains(why)));
}

// frob:tests crates/gob-check/src/defs.rs::zero_subjects
#[test]
fn zero_subjects_for_a_must_measure_rule_is_the_required_unresolved() {
    let dir = tree();
    let report = run(&toy(false, 0, false), dir.path(), &quiet()).expect("run");
    let zero: Vec<&Finding> = report
        .findings
        .iter()
        .filter(|f| f.severity == Severity::Unresolved)
        .collect();
    assert_eq!(zero.len(), 1, "{:?}", report.findings);
    assert_eq!(zero[0].rule.as_str(), "GMM001");
    assert_eq!(
        zero[0].required,
        Some(RequiredReason::ZeroSubjects {
            rule: "GMM001".into()
        })
    );
    assert_eq!(report.exit_code(), ExitCode::Negative);
}

// frob:tests crates/gob-check/src/report.rs::CheckReport.rule_reports
#[test]
fn the_zero_subject_unresolved_is_typed_vacuous_and_the_counters_convert_to_a_rule_report() {
    let dir = tree();
    let report = run(&toy(false, 0, false), dir.path(), &quiet()).expect("run");
    let f = report
        .findings
        .iter()
        .find(|f| f.rule.as_str() == "GMM001")
        .expect("GMM001 finding");
    assert_eq!(f.reason, Some(gob_rules::UnresolvedReason::Vacuous));
    let rr = report
        .rule_reports()
        .into_iter()
        .find(|r| r.rule.as_str() == "GMM001")
        .expect("GMM001 report");
    assert_eq!(rr.subjects_examined, 0);
    assert_eq!(rr.unresolved().count(), 1);
    assert!(!rr.is_certified_clean());
}

// frob:tests crates/gob-check/src/defs.rs::zero_subjects
#[test]
fn only_selects_declared_rules_by_id_and_family_and_skips_the_rest() {
    let dir = tree();
    let only = |name: &str| RunOptions {
        only: vec![name.to_owned()],
        ..quiet()
    };
    let report = run(&toy(true, 0, false), dir.path(), &only("ALP001")).expect("run");
    assert_eq!(
        ids(&report.findings),
        ["ALP001"],
        "BET001 and GMM001 dropped"
    );
    let report = run(&toy(true, 0, false), dir.path(), &only("BET")).expect("run");
    assert_eq!(ids(&report.findings), ["BET001"]);
    assert!(matches!(
        run(&toy(true, 0, false), dir.path(), &only("NOPE")),
        Err(CheckError::UnknownFamily(_))
    ));
}

// frob:tests crates/gob-check/src/filecheck.rs::run_file_checks
#[test]
fn the_resolver_decides_per_file_for_declared_rules() {
    let dir = tree();
    std::fs::write(dir.path().join("x.log"), "a bad log\n").expect("write");
    std::fs::write(dir.path().join("y.log"), "another\n").expect("write");
    std::fs::write(dir.path().join("p.png"), [0u8, 1, 2]).expect("write");
    let report = run(&toy(false, 1, false), dir.path(), &quiet()).expect("run");
    // ALP001 fires only on the file it examined; the opaque logs are one rolled-up Unresolved
    // per run naming both rules that read comments (ALP001 and BET001); the binary is declared
    // not applicable.
    // frob:ticket 01M4FG5RCDA668CK81QT54E67N
    let unresolved: Vec<String> = report
        .findings
        .iter()
        .filter(|f| f.severity == Severity::Unresolved)
        .map(|f| f.message.clone())
        .collect();
    assert_eq!(unresolved.len(), 1, "{unresolved:?}");
    assert!(unresolved[0].contains("ALP001, BET001"), "{unresolved:?}");
    assert!(
        unresolved[0].contains("2 opaque text file(s)"),
        "{unresolved:?}"
    );
    assert_eq!(
        report.subjects_examined.get("ALP001"),
        Some(&2),
        "the two txt files"
    );
    assert_eq!(
        report.fidelity.languages["opaque"].not_applicable_reasons["ALP001"],
        "binary artifact holds no text"
    );
}

#[test]
fn fixture_indexes_are_fresh() {
    for name in ["alpha", "beta", "gamma"] {
        let dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("tests/product_rules")
            .join(name);
        indexgen::assert_fresh(dir).expect("fixture index is fresh");
    }
}
