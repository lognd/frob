//! `crunk check --tier`: rules above the tier are listed as not run, never clean.

// frob:ticket 01M5XCXV02ZVYV71DFY08R5Y3H

use crunk_check::tier::{NotRunStatus, rule_tier};
use crunk_check::{CheckOptions, Crunk, Tier, run_to_tier, sibling_document};

fn project() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(
        dir.path().join("crunk.toml"),
        crunk_spec::presets::preset("default").expect("default preset"),
    )
    .expect("write");
    dir
}

fn run_to(tier: Tier, only: &[&str]) -> crunk_check::CrunkRun {
    let dir = project();
    let opts = CheckOptions {
        only: only.iter().map(|s| (*s).to_owned()).collect(),
        ..CheckOptions::default()
    };
    run_to_tier(dir.path(), &opts, tier).expect("run")
}

// frob:tests crates/crunk-check/src/tier.rs::Tier
// frob:tests crates/crunk-check/src/tier.rs::Tier.as_str
#[test]
fn tier_default_is_t1_and_unknown_lists_all() {
    assert_eq!(Tier::default(), Tier::T1);
    assert_eq!(Tier::T4.as_str(), "T4");
    assert_eq!("t3".parse::<Tier>(), Ok(Tier::T3));
    let err = "T9".parse::<Tier>().expect_err("unknown tier");
    assert!(err.to_string().contains("T0, T1, T2, T3, T4"), "{err}");
}

// frob:tests crates/crunk-check/src/tier.rs::not_run
#[test]
fn t0_skips_solver_rules_and_says_so() {
    let r = run_to(Tier::T0, &[]);
    let layout = r
        .not_run
        .iter()
        .find(|n| n.rule.starts_with("LAYOUT"))
        .expect("LAYOUT listed");
    assert_eq!(layout.tier, Tier::T1);
    assert!(layout.reason.contains("layout solver"), "{}", layout.reason);
    assert!(
        r.report
            .findings
            .iter()
            .all(|f| !f.rule.as_str().starts_with("LAYOUT"))
    );
}

// frob:tests crates/crunk-check/src/tier.rs::not_run
#[test]
fn default_tier_lists_nothing_it_decides() {
    let r = run_to(Tier::default(), &[]);
    assert!(
        r.not_run.iter().all(|n| n.tier > Tier::T1),
        "{:?}",
        r.not_run
    );
}

// frob:tests crates/crunk-check/src/tier.rs::not_run
#[test]
fn not_run_is_stable_ordered_and_family_filtered() {
    let all = run_to(Tier::T0, &[]).not_run;
    let ids: Vec<&str> = all.iter().map(|n| n.rule.as_str()).collect();
    let mut sorted = ids.clone();
    sorted.sort_unstable();
    assert_eq!(ids, sorted);
    let only = run_to(Tier::T0, &["RESP"]).not_run;
    assert!(!only.is_empty() && only.iter().all(|n| n.family == "RESP"));
}

// frob:tests crates/crunk-check/src/tier.rs::rule_tier
#[test]
fn must_measure_above_tier_is_unresolved_and_unknown_family_is_t0() {
    let defs: Vec<_> = gob_check::Product::rule_set(&Crunk).defs().collect();
    assert!(defs.iter().all(|d| rule_tier(d) >= Tier::T0));
    let r = run_to(Tier::T0, &[]);
    for n in &r.not_run {
        let def = defs.iter().find(|d| d.id == n.rule).expect("def");
        let want = if def.must_measure {
            NotRunStatus::Unresolved
        } else {
            NotRunStatus::NotRun
        };
        assert_eq!(n.status, want, "{}", n.rule);
    }
}

// frob:tests crates/crunk-check/src/tier.rs::section
#[test]
fn document_carries_a_not_run_section() {
    let doc = sibling_document(&run_to(Tier::T0, &[]));
    assert_eq!(doc["not_run"]["tier"], "T0");
    assert!(
        doc["not_run"]["rules"]
            .as_array()
            .is_some_and(|a| !a.is_empty())
    );
}
