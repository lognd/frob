//! `stmt` and adapter control nodes, `directly inside` through body groups, and statement
//! wrappers looking through to their call, end to end over real python.

// frob:ticket 01M5GE4YWPW8XRWCP5N1A69KMM

use gob_plan::examples::{install_model_reader, run_example};
use gob_plan::grl::parse;
use gob_text::FileInterner;

/// A one-clause rule `find x: KIND where COND` reporting `x`, with one python example.
fn passes(kind: &str, cond: &str, example: &str) -> bool {
    install_model_reader(grimble_check::example_model::read_example_model);
    let outcome = if example.contains("#~") {
        "fire"
    } else {
        "clean"
    };
    let cond = if cond.is_empty() {
        String::new()
    } else {
        format!("  where {cond}\n")
    };
    let src = format!(
        "rule STM001 \"stmt\" {{\n  lang python\n  severity warn\n\n  find x: {kind}\n{cond}  report x \"hit\"\n\n  example {outcome} python \"\"\"\n{example}  \"\"\"\n  explain \"\"\"\n    Test rule.\n    ## Remedy\n    None.\n  \"\"\"\n}}\n"
    );
    let parsed = parse(FileInterner::new().intern("rules/S.grl"), &src);
    assert!(parsed.is_ok(), "{:?}", parsed.errors);
    let rule = &parsed.file.rules[0];
    let r = run_example(rule, &rule.examples[0]).expect("example runs");
    assert!(r.passed, "{}", r.diff);
    true
}

// frob:tests KindTest.member
#[test]
fn stmt_matches_statements_and_not_expressions() {
    assert!(passes(
        "stmt",
        "",
        "    x = 1   #~ warn\n    return x   #~ warn\n"
    ));
}

// frob:tests KindTest.member
#[test]
fn adapter_if_and_for_are_branch_and_loop() {
    assert!(passes(
        "branch",
        "",
        "    if a:   #~ warn\n        pass\n    for i in a:\n        pass\n"
    ));
    assert!(passes(
        "loop",
        "",
        "    if a:\n        pass\n    for i in a:   #~ warn\n        pass\n"
    ));
}

// frob:tests Eval.inside
#[test]
fn directly_inside_passes_through_the_body_group_only() {
    let body = "    def f():\n        a = 1\n        if a:\n            b = 2\n";
    assert!(passes(
        "function",
        "count(s: stmt directly inside x) >= 2",
        "    def f():   #~ warn\n        a = 1\n        if a:\n            b = 2\n"
    ));
    assert!(passes(
        "function",
        "count(s: stmt directly inside x) >= 3",
        body
    ));
}

// frob:tests unwrap_statement
#[test]
fn a_call_statement_is_a_call_and_is_counted_once() {
    assert!(passes(
        "function",
        "count(c: call inside x) == 1",
        "    def f():   #~ warn\n        g()\n"
    ));
    assert!(passes(
        "function",
        "count(s: stmt directly inside x where s is call) == 1",
        "    def f():   #~ warn\n        g()\n        y = 1\n"
    ));
}
