//! Lowering a relation object written as a field path and a snippet taken as roles.

// frob:ticket 01M5ETB7Y10SZTEWWKBR3AHZ1T

use gob_plan::grl::parse;
use gob_plan::lower::{LowerError, lower_rule};
use gob_plan::plan::{Plan, Provenance};
use gob_text::FileInterner;

const EXPLAIN: &str = "  explain \"\"\"\n    Why.\n    ## Remedy\n    Fix.\n  \"\"\"\n";

fn lower(lines: &[&str]) -> Result<Plan, LowerError> {
    let src = format!(
        "rule TST001 \"t\" {{\n  lang *\n  {}\n{EXPLAIN}}}\n",
        lines.join("\n  ")
    );
    let parsed = parse(FileInterner::new().intern("rules/T.grl"), &src);
    assert!(parsed.is_ok(), "{:?}\n{src}", parsed.errors);
    lower_rule(&parsed.file.rules[0], Provenance::Std)
}

fn roles(snippet: &str) -> Result<Plan, LowerError> {
    lower(&[
        "find b: branch",
        &format!("where b is {snippet} as roles"),
        "report b \"x\"",
    ])
}

fn unsupported(r: Result<Plan, LowerError>) -> &'static str {
    match r {
        Err(LowerError::Unsupported { what, .. }) => what,
        other => panic!("expected Unsupported, got {other:?}"),
    }
}

// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn a_field_path_relation_object_lowers() {
    let r = lower(&[
        "find s: call",
        "where some p: function where s resolves to p and p peer of s.unit",
        "report s \"x\"",
    ]);
    assert!(r.is_ok(), "{r:?}");
}

// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn a_field_path_object_on_an_unbound_variable_is_an_unknown_var() {
    let r = lower(&[
        "find s: call",
        "where some p: function where p peer of h.unit",
        "report s \"x\"",
    ]);
    assert!(matches!(r, Err(LowerError::UnknownVar { .. })), "{r:?}");
}

// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn a_roles_snippet_with_one_call_or_no_body_lowers() {
    for s in [
        "rust`if $C { $F($$$A) }`",
        "rust`if $C { $F(); }`",
        "rust`while $C { $F() }`",
        "rust`if $C { }`",
    ] {
        let r = roles(s);
        assert!(r.is_ok(), "{s}: {r:?}");
    }
}

// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn a_roles_snippet_outside_the_lift_is_refused_by_name() {
    assert_eq!(
        unsupported(roles("rust`$X.f()`")),
        "a roles snippet whose root is not a branch or loop"
    );
    assert_eq!(
        unsupported(roles("rust`if $C { a() } else { b() }`")),
        "a roles snippet with an else branch"
    );
    for s in [
        "rust`if $C { a(); b() }`",
        "rust`if $C { x = 1 }`",
        "rust`if $C { if $D { f() } }`",
    ] {
        assert_eq!(
            unsupported(roles(s)),
            "a roles snippet body that is not exactly one call",
            "{s}"
        );
    }
}
