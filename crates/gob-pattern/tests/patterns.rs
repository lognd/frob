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
}

// frob:tests crates/gob-pattern/src/grammar.rs::find
#[test]
fn single_metavariable_binds_one_node_and_repeats_must_agree_part_2() {
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
}

// frob:tests crates/gob-pattern/src/grammar.rs::find
#[test]
fn multi_metavariable_in_the_middle_and_in_rust_part_2() {
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

const CONSTRAINED: &str = r#"
id = "GPOL011"
language = "python"
severity = "warn"
message = "private name passed to print"
rule = { pattern = "print($A)", constraints = { A = { kind = "identifier", regex = "^_" } } }
"#;

// frob:tests crates/gob-pattern/src/lib.rs::find_source
#[test]
fn metavariable_constraints_keep_only_matching_captures() {
    let rule = RuleFile::parse(CONSTRAINED).unwrap();
    let src = "print(_x)\nprint(y)\nprint(_a + 1)\nprint('_s')\n";
    let found = rule.find_source(src).unwrap();
    assert_eq!(found.len(), 1);
    assert_eq!(&src[found[0].range.clone()], "print(_x)");
}

const WITH_CASES: &str = r#"
id = "GPOL011"
language = "python"
severity = "warn"
message = "use the logger, not print"
fix = "logger.info($$$ARGS)"
rule = { pattern = "print($$$ARGS)" }

[[test]]
name = "fires"
source = "print(1)\nlog(2)\n"
matches = ["print(1)"]
fixed = "logger.info(1)\nlog(2)\n"

[[test]]
source = "log(2)\n"
"#;

// frob:tests crates/gob-pattern/src/authoring.rs::run_tests
#[test]
fn embedded_cases_pass_and_a_wrong_expectation_fails() {
    let rule = RuleFile::parse(WITH_CASES).unwrap();
    assert_eq!(rule.tests.len(), 2);
    assert!(rule.run_tests().is_empty());
}

// frob:tests crates/gob-pattern/src/authoring.rs::run_tests
#[test]
fn a_wrong_match_expectation_fails_the_case() {
    let bad = WITH_CASES.replace("matches = [\"print(1)\"]", "matches = []");
    let failures = RuleFile::parse(&bad).unwrap().run_tests();
    assert_eq!(failures.len(), 1);
    assert!(failures[0].to_string().contains("fires"));
}

// frob:tests crates/gob-pattern/src/authoring.rs::run_tests
#[test]
fn a_wrong_fixed_output_fails_the_case() {
    let bad_fix = WITH_CASES.replace("fixed = \"logger.info(1)", "fixed = \"nope(1)");
    assert_eq!(RuleFile::parse(&bad_fix).unwrap().run_tests().len(), 1);
}

// frob:tests crates/gob-pattern/src/authoring.rs::next_id
#[test]
fn next_id_is_one_past_the_highest_in_the_rules_dir() {
    let dir = std::env::temp_dir().join(format!("gob-pattern-ids-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    assert_eq!(gob_pattern::authoring::next_id(&dir), "GPOL001");
    std::fs::write(dir.join("a.grl.toml"), RULE).unwrap();
    std::fs::write(dir.join("b.grl.toml"), WITH_CASES).unwrap();
    std::fs::write(dir.join("junk.grl.toml"), "not toml [").unwrap();
    assert_eq!(gob_pattern::authoring::next_id(&dir), "GPOL012");
    std::fs::remove_dir_all(&dir).unwrap();
    assert_eq!(gob_pattern::authoring::next_id(&dir), "GPOL001");
}

// frob:tests crates/gob-pattern/src/authoring.rs::next_id_after
#[test]
fn next_id_after_pads_and_ignores_foreign_ids() {
    use gob_pattern::authoring::next_id_after;
    assert_eq!(next_id_after([]), "GPOL001");
    assert_eq!(next_id_after(["GPOL009", "POL500", "GPOLx"]), "GPOL010");
    assert_eq!(next_id_after(["GPOL999"]), "GPOL1000");
}
