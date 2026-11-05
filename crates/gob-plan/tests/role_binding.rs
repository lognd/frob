//! Metavariables of an `as roles` snippet bind as role nodes usable by the rest of the rule.

// frob:ticket 01M4XJ9HA1C3KVG78XF5YAFTXP

use gob_plan::examples::run_example;
use gob_plan::grl::parse;
use gob_plan::lower::{LowerError, lower_rule};
use gob_plan::plan::{Plan, Provenance};
use gob_text::FileInterner;

const EXPLAIN: &str = "  explain \"\"\"\n    Why.\n    ## Remedy\n    Fix.\n  \"\"\"\n";
const SNIP: &str = "find b: rust`if $C { $F($$$A) }` as roles";

fn lower(lines: &[&str]) -> Result<Plan, LowerError> {
    let src = format!(
        "rule TST001 \"t\" {{\n  lang *\n  {}\n{EXPLAIN}}}\n",
        lines.join("\n  ")
    );
    let parsed = parse(FileInterner::new().intern("rules/T.grl"), &src);
    assert!(parsed.is_ok(), "{:?}\n{src}", parsed.errors);
    lower_rule(&parsed.file.rules[0], Provenance::Std)
}

// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn each_named_metavariable_is_usable_in_later_clauses() {
    let r = lower(&[SNIP, "report f \"m\""]);
    assert!(r.is_ok(), "{r:?}");
}

// frob:tests crates/gob-plan/src/plan/codec.rs::encode
#[test]
fn a_plan_with_role_ops_survives_the_codec() {
    let p = lower(&[SNIP, "report f \"m\""]).expect("lowers");
    let bytes = p.to_bytes();
    let back = Plan::load(&bytes).expect("loads");
    assert_eq!(back.to_bytes(), bytes);
}

// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn a_metavariable_clashing_with_a_binder_is_refused() {
    let r = lower(&[SNIP, "find c: call", "report c \"m\""]);
    assert!(r.is_err(), "{r:?}");
}

// frob:tests crates/gob-plan/src/exec/core/eval/predicate.rs::role_op
#[test]
fn the_callee_role_node_is_reported_by_the_rule() {
    let src = format!(
        "rule TST001 \"t\" {{\n  lang rust\n  {SNIP}\n  report f \"callee\"\n  example fire rust \"\"\"\n    fn a() {{\n        if true {{\n            go() //~ error\n        }}\n    }}\n  \"\"\"\n{EXPLAIN}}}\n"
    );
    let parsed = parse(FileInterner::new().intern("rules/T.grl"), &src);
    assert!(parsed.is_ok(), "{:?}\n{src}", parsed.errors);
    let rule = &parsed.file.rules[0];
    let r = run_example(rule, &rule.examples[0]).expect("runs");
    assert!(r.passed, "{}", r.diff);
}

// frob:tests crates/gob-plan/src/exec/core/eval/predicate.rs::role_op
#[test]
fn the_condition_role_node_is_reported_on_its_own_line() {
    let src = format!(
        "rule TST001 \"t\" {{\n  lang rust\n  {SNIP}\n  report c \"condition\"\n  example fire rust \"\"\"\n    fn a() {{\n        if true {{ //~ error\n            go()\n        }}\n    }}\n  \"\"\"\n{EXPLAIN}}}\n"
    );
    let parsed = parse(FileInterner::new().intern("rules/T.grl"), &src);
    assert!(parsed.is_ok(), "{:?}\n{src}", parsed.errors);
    let rule = &parsed.file.rules[0];
    let r = run_example(rule, &rule.examples[0]).expect("runs");
    assert!(r.passed, "{}", r.diff);
}
