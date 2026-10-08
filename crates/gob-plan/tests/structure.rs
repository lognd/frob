//! Behaviour of the structural checks beyond the goldens (grl-spec.md sections 7.4, 9 and 10).

use gob_plan::check::{Code, check_file};
use gob_plan::grl::parse;
use gob_text::FileInterner;

const FIRE: &str = "  example fire \"\"\"\n    x\n  \"\"\"\n";
const CLEAN: &str = "  example clean \"\"\"\n    y\n  \"\"\"\n";
const EXPLAIN: &str = "  explain \"\"\"\n    e\n\n    ## Remedy\n    r\n  \"\"\"\n";

fn codes_of(src: &str) -> Vec<Code> {
    let parsed = parse(FileInterner::new().intern("t.grl"), src);
    assert!(parsed.is_ok(), "{:?}\n{src}", parsed.errors);
    check_file(&parsed.file)
        .iter()
        .filter_map(|d| d.code)
        .collect()
}

fn rule(header: &str, body: &str, examples: &str, explain: &str) -> String {
    format!("rule NOPE999 \"t\" {{\n  {header}\n{body}\n{examples}{explain}}}\n")
}

fn ok_rule(header: &str, body: &str) -> Vec<Code> {
    codes_of(&rule(header, body, &format!("{FIRE}{CLEAN}"), EXPLAIN))
}

// frob:ticket 01M3ZX7E2DPA2CXBAQ8ZKM5W7Y
// frob:tests crates/gob-plan/src/check/mod.rs::check_file_with
#[test]
fn defs_may_call_earlier_defs_only() {
    let calls =
        "  find c: call\n  def a(x) = x is call\n  def b(x) = a(x)\n  report c \"m\" when b(c)";
    assert!(ok_rule("lang rust", calls).is_empty());
    let selfcall = "  find c: call\n  def a(x) = a(x)\n  report c \"m\" when a(c)";
    assert_eq!(ok_rule("lang rust", selfcall), [Code::Grl009]);
    let forward =
        "  find c: call\n  def b(x) = a(x)\n  def a(x) = x is call\n  report c \"m\" when b(c)";
    assert_eq!(ok_rule("lang rust", forward), [Code::Grl009]);
}

// frob:ticket 01M3ZX7E2DPA2CXBAQ8ZKM5W7Y
// frob:tests crates/gob-plan/src/check/mod.rs::check_file
#[test]
fn a_closure_needs_within() {
    let open = "  find f: function\n  find g: function\n  where f reaches g via calls\n  report f \"m {g.name}\"";
    assert_eq!(ok_rule("lang rust", open), [Code::Grl010]);
    let bounded = open.replace("via calls", "via calls within 4");
    assert!(ok_rule("lang rust", &bounded).is_empty());
}

// frob:ticket 01M3ZX7E2DPA2CXBAQ8ZKM5W7Y
// frob:tests crates/gob-plan/src/check/mod.rs::compile_report
#[test]
fn examples_and_remedy_are_required_and_universal_rules_need_a_third() {
    let body = "  find c: call\n  report c \"m\"";
    assert_eq!(
        codes_of(&rule("lang rust", body, FIRE, EXPLAIN)),
        [Code::Grl011]
    );
    assert_eq!(
        codes_of(&rule("lang rust", body, "", EXPLAIN)),
        [Code::Grl011, Code::Grl011]
    );
    let no_remedy = "  explain \"\"\"\n    e\n  \"\"\"\n";
    assert_eq!(
        codes_of(&rule(
            "lang rust",
            body,
            &format!("{FIRE}{CLEAN}"),
            no_remedy
        )),
        [Code::Grl012]
    );
    let universal = rule("lang *", body, &format!("{FIRE}{CLEAN}"), EXPLAIN);
    assert_eq!(codes_of(&universal), [Code::Grl011]);
    let third = format!("{FIRE}{CLEAN}  example notapplicable css \"\"\"\n    z\n  \"\"\"\n");
    assert!(codes_of(&rule("lang *", body, &third, EXPLAIN)).is_empty());
}

// frob:ticket 01M3ZX7E2DPA2CXBAQ8ZKM5W7Y
// frob:tests crates/gob-plan/src/check/mod.rs::Code.severity
#[test]
fn a_side_relation_needs_its_root_declared() {
    let body = "  find d: `dbg!($$$ARGS)`\n  where d.file.path in diff.changed\n  report d \"m\"";
    assert_eq!(ok_rule("lang rust", body), [Code::Grl014]);
    assert!(ok_rule("lang rust\n  needs diff", body).is_empty());
    assert_eq!(ok_rule("lang rust\n  needs lease", body), [Code::Grl014]);
    let config = "  find r: config.invariants.forbid_imports\n  report r \"m\"";
    assert!(ok_rule("lang rust", config).is_empty());
}
