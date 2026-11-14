//! A GRL rule lists with the same row shape as a Rust std rule and a pack rule, and accepts the
//! `reads`, `since` and `fidelity` headers (docs/design/shared/grl-spec.md section 4).

// frob:ticket 01M48R07AYMKWPKZDXW4BKKSMH

use gob_plan::grl::ast::{HeaderKind, Rule};
use gob_plan::grl::parse;
use gob_plan::lower::{grl_row, lower_rule, read_names};
use gob_plan::plan::Provenance;
use gob_rules::{Provenance as RuleProvenance, RuleMeta, RuleRow};
use gob_text::FileInterner;

fn source(extra: &str) -> String {
    format!(
        r#"rule ROW900 "row shape" {{
  lang *
  polarity P-  severity error  scope file  rollup file
  {extra}

  find f: function
  report f "function {{f.name}}"
  example fire rust {{
    file "src/a.rs" """
      fn a() {{}}   //~ error
    """
  }}
  example clean rust {{
    file "src/a.rs" """
      struct S;
    """
  }}
  explain """
    A row test rule.
    ## Remedy
    None.
  """
}}
"#
    )
}

fn rule(extra: &str) -> Rule {
    let src = source(extra);
    let parsed = parse(FileInterner::new().intern("rules/ROW900.grl"), &src);
    assert!(parsed.is_ok(), "{:?}\n{src}", parsed.errors);
    parsed.file.rules[0].clone()
}

fn keys(row: &RuleRow) -> Vec<String> {
    serde_json::to_value(row)
        .unwrap()
        .as_object()
        .unwrap()
        .keys()
        .cloned()
        .collect()
}

static STD: RuleMeta = RuleMeta {
    id: "AAA001",
    slug: "std-rule",
    family: "AAA",
    product: "frob",
    severity: gob_rules::Severity::Error,
    summary: "s",
    explanation: "s",
    tier: gob_rules::Tier::Universal,
    scope: gob_rules::Scope::File,
    fix: gob_rules::FixKind::Manual,
    polarity: gob_rules::Polarity::Pplus,
    must_measure: false,
    needs: gob_rules::Needs::Structural,
    version: 1,
    since: "0.1.0",
    module: "std_mod",
};

// frob:tests grl_row
#[test]
fn grl_row_has_the_same_keys_as_a_std_row() {
    let grl = grl_row(&rule(""), "frob", &RuleProvenance::Std);
    assert_eq!(
        keys(&grl),
        keys(&RuleRow::from_meta(&STD, &RuleProvenance::Std))
    );
}

// frob:tests grl_row
#[test]
fn grl_row_has_the_same_keys_as_a_pack_row() {
    let grl = grl_row(&rule(""), "frob", &RuleProvenance::Std);
    let pack = RuleRow::from_meta(&STD, &RuleProvenance::Pack("acme".into()));
    assert_eq!(keys(&grl), keys(&pack));
}

// frob:tests grl_row
#[test]
fn since_header_reaches_the_row() {
    let row = grl_row(&rule("since \"0.5.0\""), "frob", &RuleProvenance::Std);
    assert_eq!(row.since, "0.5.0");
}

// frob:tests grl_row
#[test]
fn fidelity_header_reaches_the_row() {
    let row = grl_row(&rule("fidelity f3"), "frob", &RuleProvenance::Std);
    assert_eq!(row.fidelity.as_deref(), Some("F3"));
}

// frob:tests read_names
#[test]
fn reads_header_names_side_relations() {
    assert_eq!(read_names(&rule("reads diff, lease")), ["diff", "lease"]);
}

// frob:tests read_names
#[test]
fn needs_of_a_side_relation_is_a_deprecated_alias_of_reads() {
    assert_eq!(read_names(&rule("needs diff")), ["diff"]);
}

// frob:tests lower_rule
#[test]
fn needs_alias_lowers_like_reads() {
    let plan = lower_rule(&rule("needs diff"), Provenance::Std).unwrap();
    let reads = lower_rule(&rule("reads diff"), Provenance::Std).unwrap();
    assert_eq!(plan.parts().reads, reads.parts().reads);
}

// frob:tests lower_rule
#[test]
fn since_and_fidelity_do_not_change_the_plan() {
    let plain = lower_rule(&rule(""), Provenance::Std).unwrap();
    let headed = lower_rule(&rule("since \"0.5.0\"\n  fidelity f2"), Provenance::Std).unwrap();
    assert_eq!(plain.parts().ops, headed.parts().ops);
}

#[test]
fn since_and_fidelity_parse_as_headers() {
    let r = rule("since \"0.5.0\"\n  fidelity f2");
    let n = r
        .headers
        .iter()
        .filter(|h| matches!(h.node, HeaderKind::Since(_) | HeaderKind::Fidelity(_)))
        .count();
    assert_eq!(n, 2);
}
