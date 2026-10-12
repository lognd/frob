//! Behaviour of the fix checks (GRL015; grl-spec.md section 8).

use gob_plan::check::{Code, Tier, check_file_as};
use gob_plan::grl::parse;
use gob_text::FileInterner;

const EXAMPLES: &str = "  example fire \"\"\"\n    x\n  \"\"\"\n  example clean \"\"\"\n    y\n  \"\"\"\n  explain \"\"\"\n    e\n\n    ## Remedy\n    r\n  \"\"\"\n";

fn codes(body: &str, tier: Tier) -> Vec<Code> {
    let src = format!("rule NOPE999 \"t\" {{\n  lang rust\n{body}\n{EXAMPLES}}}\n");
    let parsed = parse(FileInterner::new().intern("t.grl"), &src);
    assert!(parsed.is_ok(), "{:?}\n{src}", parsed.errors);
    check_file_as(&parsed.file, None, tier)
        .iter()
        .filter_map(|d| d.code)
        .collect()
}

// frob:ticket 01M3ZX7ECR0R91Q5R2T16R03NG
// frob:tests crates/gob-plan/src/check/mod.rs::check_file_as
#[test]
fn a_fix_without_applicability_is_grl015() {
    let bare = "  find d: call\n  report d \"m\"\n  fix d -> `x`";
    assert_eq!(codes(bare, Tier::Plugin), [Code::Grl015]);
    assert_eq!(codes(bare, Tier::Std), [Code::Grl015]);
    let ok = "  find d: call\n  report d \"m\"\n  fix d -> `x` [machine]";
    assert!(codes(ok, Tier::Plugin).is_empty());
    let manual = "  find d: call\n  report d \"m\"\n  fix manual \"do it by hand\"";
    assert!(codes(manual, Tier::Plugin).is_empty());
}

// frob:ticket 01M3ZX7ECR0R91Q5R2T16R03NG
// frob:tests crates/gob-plan/src/check/mod.rs::check_file_as
#[test]
fn a_host_fix_is_std_only() {
    let host = "  find d: call\n  report d \"m\"\n  fix host add_grant(d) [has-placeholders]";
    assert_eq!(codes(host, Tier::Plugin), [Code::Grl015]);
    assert!(codes(host, Tier::Std).is_empty());
}

// frob:ticket 01M3ZX7ECR0R91Q5R2T16R03NG
// frob:tests crates/gob-plan/src/check/mod.rs::check_file_as
#[test]
fn a_plugin_fix_outside_the_report_target_is_grl015_but_std_may() {
    let wide = "  find d: call\n  find f: function\n  report d \"m\"\n  fix f -> `x` [machine]";
    assert_eq!(codes(wide, Tier::Plugin), [Code::Grl015]);
    assert!(codes(wide, Tier::Std).is_empty());
    let del = "  find d: call\n  find f: function\n  report d \"m\"\n  fix delete f [machine]";
    assert_eq!(codes(del, Tier::Plugin), [Code::Grl015]);
    let inside = "  find d: call\n  report d \"m\"\n  fix after d -> `x` [machine]";
    assert!(codes(inside, Tier::Plugin).is_empty());
}
