//! Corpus tests for the first NEAT rules: each bug fires, each fix is quiet.

// frob:ticket 01M3Z7151078ZAM6AM1GFWC6QP

use gob_languages::Language;
use grimble_lints::neat::{Options, Report, Rule, Verdict, scan};

fn run(src: &str) -> Report {
    scan(Language::Rust, src, &Options::default()).expect("corpus file parses")
}

fn rules(r: &Report) -> Vec<Rule> {
    r.findings.iter().map(|f| f.rule).collect()
}

// frob:tests crates/grimble-lints/src/neat/mod.rs::scan
#[test]
fn honest_unit_calling_the_clock_is_contradicted() {
    let bug = run(include_str!("corpus/neat/honest_clock_bug.rs"));
    assert_eq!(rules(&bug), vec![Rule::EffectCeilingExceeded], "{bug:?}");
    assert_eq!(bug.claims[0].verdict, Verdict::Contradicted);
    assert!(bug.findings[0].message.contains("clock"));
    let fixed = run(include_str!("corpus/neat/honest_clock_fixed.rs"));
    assert!(fixed.findings.is_empty(), "{fixed:?}");
}

// frob:tests crates/grimble-lints/src/neat/mod.rs::scan
#[test]
fn ruff_shape_dispatcher_fires_neat031_and_fix_is_clean() {
    let bug = run(include_str!("corpus/neat/ruff_dispatcher_bug.rs"));
    assert_eq!(rules(&bug), vec![Rule::DispatchSiteOwnsLogic], "{bug:?}");
    let fixed = run(include_str!("corpus/neat/ruff_dispatcher_fixed.rs"));
    assert!(fixed.findings.is_empty(), "{fixed:?}");
}

// frob:tests crates/grimble-lints/src/neat/mod.rs::scan
#[test]
fn unresolved_callee_leaves_the_claim_unverified() {
    let r = run("// frob:honest\nfn f(x: &T) -> u8 { x.mystery() }\n");
    assert!(r.findings.is_empty());
    assert_eq!(r.claims[0].verdict, Verdict::Unverified);
}

// frob:tests crates/grimble-lints/src/neat/mod.rs::scan
#[test]
fn a_local_callee_contributes_its_effects_transitively() {
    let r = run("// frob:pure\nfn f() { g() }\nfn g() { let _ = std::env::var(\"X\"); }\n");
    assert_eq!(rules(&r), vec![Rule::EffectCeilingExceeded], "{r:?}");
}

// frob:tests crates/grimble-lints/src/neat/mod.rs::scan
#[test]
fn shell_units_and_declared_atoms_are_not_flagged() {
    let r = run("// frob:effects clock\nfn f() { std::time::Instant::now(); }\n");
    assert!(r.findings.is_empty());
    assert_eq!(r.claims[0].verdict, Verdict::Verified);
}
