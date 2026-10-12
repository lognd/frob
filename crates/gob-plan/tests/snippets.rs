//! Behaviour of the snippet checks (GRL006 and GRL008; grl-spec.md sections 7.3 and 10).

use gob_plan::check::{Code, Tier, check_file_as};
use gob_plan::grl::parse;
use gob_text::FileInterner;

const EXAMPLES: &str = "  example fire \"\"\"\n    x\n  \"\"\"\n  example clean \"\"\"\n    y\n  \"\"\"\n  example notapplicable python \"\"\"\n    z\n  \"\"\"\n  explain \"\"\"\n    e\n\n    ## Remedy\n    r\n  \"\"\"\n";

fn codes(lang: &str, body: &str) -> Vec<Code> {
    let src = format!("rule NOPE999 \"t\" {{\n  lang {lang}\n{body}\n{EXAMPLES}}}\n");
    let parsed = parse(FileInterner::new().intern("t.grl"), &src);
    assert!(parsed.is_ok(), "{:?}\n{src}", parsed.errors);
    check_file_as(&parsed.file, None, Tier::Plugin)
        .iter()
        .filter_map(|d| d.code)
        .collect()
}

// frob:ticket 01M3ZX7E5VPTH8J16D5APQDEAP
// frob:tests crates/gob-plan/src/check/snippets.rs::check_rule
#[test]
fn a_plain_snippet_is_grl006_only_in_a_universal_rule() {
    let plain = "  find d: `f($X)`\n  report d \"m\"";
    assert_eq!(codes("*", plain), [Code::Grl006]);
    assert!(codes("rust", plain).is_empty());
    let tagged = "  find d: rust`f($X)`\n  report d \"m\"";
    assert_eq!(codes("*", tagged), [Code::Grl006]);
    let roles = "  find d: rust`f($X)` as roles\n  report d \"m\"";
    assert!(codes("*", roles).is_empty());
}

// frob:ticket 01M3ZX7E5VPTH8J16D5APQDEAP
// frob:tests crates/gob-plan/src/check/snippets.rs::check_rule
#[test]
fn a_snippet_test_in_a_where_is_checked_too() {
    let cond = "  find d: call\n  where d is `f($X)`\n  report d \"m\"";
    assert_eq!(codes("*", cond), [Code::Grl006]);
    let ok = "  find d: call\n  where d is rust`f($X)` as roles\n  report d \"m\"";
    assert!(codes("*", ok).is_empty());
}

// frob:ticket 01M3ZX7E5VPTH8J16D5APQDEAP
// frob:tests crates/gob-plan/src/check/snippets.rs::check_rule
#[test]
fn a_fix_metavariable_must_be_bound_by_a_snippet() {
    let bound =
        "  find d: `f($X, $$$REST)`\n  report d \"m\"\n  fix d -> `g($X, $$$REST)` [machine]";
    assert!(codes("rust", bound).is_empty());
    let unbound = "  find d: `f($X, $$$REST)`\n  report d \"m\"\n  fix d -> `g($Y)` [machine]";
    assert_eq!(codes("rust", unbound), [Code::Grl008]);
    let anonymous = "  find d: `f($_)`\n  report d \"m\"\n  fix d -> `g($_)` [machine]";
    assert!(codes("rust", anonymous).is_empty());
}
