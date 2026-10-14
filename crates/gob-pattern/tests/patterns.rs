//! Grammar-level patterns, metavariables and fixes (frob:ticket 01M4PPRHCTN3TZ0TJF8NRQ4KHD).

use gob_pattern::grammar::{Pattern, apply};
use gob_pattern::{PatternError, RuleFile};

const RULE: &str = r#"
id = "GPOL010"
language = "python"
severity = "warn"
message = "use the logger, not print"
fix = "logger.info($$$ARGS)"
rule = { pattern = "print($$$ARGS)" }
"#;

const FIXTURE: &str =
    "import sys\n\ndef f(x):\n    print(x, 1)\n    print()\n    log(x)\n    return print\n";

// frob:tests crates/gob-pattern/src/lib.rs::find_source
#[test]
fn print_pattern_fires_and_fix_rewrites_the_call() {
    let rule = RuleFile::parse(RULE).unwrap();
    let found = rule.find_source(FIXTURE).unwrap();
    assert_eq!(found.len(), 2);
    let edits: Vec<_> = found.into_iter().filter_map(|f| f.edit).collect();
    assert_eq!(
        apply(FIXTURE, &edits),
        "import sys\n\ndef f(x):\n    logger.info(x, 1)\n    logger.info()\n    log(x)\n    return print\n"
    );
}

// frob:tests crates/gob-pattern/src/grammar.rs::find
#[test]
fn single_metavariable_binds_one_node_and_repeats_must_agree() {
    let p = Pattern::compile("python", "$A == $A").unwrap();
    let m = p.find("a = (x == x) and (y == z)\n").unwrap();
    assert_eq!(m.len(), 1);
    assert_eq!(m[0].bindings["A"], "x");
    let one = Pattern::compile("python", "f($X)").unwrap();
    assert_eq!(one.find("f(1)\nf(1, 2)\nf()\n").unwrap().len(), 1);
}

// frob:tests crates/gob-pattern/src/grammar.rs::find
#[test]
fn multi_metavariable_in_the_middle_and_in_rust() {
    let p = Pattern::compile("python", "f($A, $$$REST, $Z)").unwrap();
    let m = p.find("f(1, 2, 3, 4)\nf(1)\n").unwrap();
    assert_eq!(m.len(), 1);
    assert_eq!(m[0].bindings["REST"], "2, 3");
    let r = Pattern::compile("rust", "$X.unwrap()").unwrap();
    let m = r.find("fn main() { let v = a.b().unwrap(); }").unwrap();
    assert_eq!(m.len(), 1);
    assert_eq!(m[0].bindings["X"], "a.b()");
}

#[test]
fn rule_errors_are_typed() {
    let unbound = RULE.replace("$$$ARGS)\"\nrule", "$$$ARGS) $NOPE\"\nrule");
    let rule = RuleFile::parse(&unbound).unwrap();
    assert!(matches!(
        rule.find_source(FIXTURE),
        Err(PatternError::Grammar(_))
    ));
    assert_eq!(
        RuleFile::parse(&RULE.replace(
            "rule = { pattern = \"print($$$ARGS)\" }",
            "rule = { kind = \"call\" }"
        )),
        Err(PatternError::FixWithoutPattern)
    );
    assert!(matches!(
        RuleFile::parse(&RULE.replace("python", "cobol")),
        Err(PatternError::Grammar(_))
    ));
}
