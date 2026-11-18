//! Claim verdicts: `noflow`, `reach` and `bound` are decided or Unresolved, never silently ok.

// frob:ticket 01M4FGYHSXQXJD0JXFV2AZCED5

use grimble_model::{ModelFiles, check_model};

const NODES: &str = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n}\nnode b : trusted {\n}\nnode c : trusted {\n}\n";
const FLOWS: &str =
    "flow f1 : a -> b {\n  label Public;\n}\nflow f2 : b -> c {\n  label Public;\n}\n";

/// The (rule, severity-name, message) of every CLAIM finding of a model built from `claims`.
fn claim_findings(flows: &str, claims: &str) -> Vec<(String, String, String)> {
    let text = format!("{NODES}{flows}{claims}");
    let model = ModelFiles::new().with_file("design/model.grmb", text.as_bytes());
    check_model(&model)
        .into_iter()
        .filter(|f| f.rule.to_string().starts_with("CLAIM"))
        .map(|f| (f.rule.to_string(), format!("{:?}", f.severity), f.message))
        .collect()
}

// frob:tests crates/grimble-model/src/claim.rs::flow_verdict
#[test]
fn noflow_over_a_declared_path_is_refuted_with_the_path() {
    let got = claim_findings(FLOWS, "claim k {\n  noflow a -> c;\n}\n");
    assert_eq!(got.len(), 1, "{got:?}");
    assert_eq!(got[0].0, "CLAIM001");
    assert_eq!(got[0].1, "Error");
    assert!(got[0].2.contains("f1 -> f2"), "{}", got[0].2);
}

// frob:tests crates/grimble-model/src/claim.rs::flow_verdict
#[test]
fn noflow_without_a_path_is_satisfied() {
    assert!(claim_findings(FLOWS, "claim k {\n  noflow c -> a;\n}\n").is_empty());
}

// frob:tests crates/grimble-model/src/claim.rs::flow_verdict
#[test]
fn reach_over_a_declared_path_is_satisfied() {
    assert!(claim_findings(FLOWS, "claim k {\n  reach a -> c;\n}\n").is_empty());
}

// frob:tests crates/grimble-model/src/claim.rs::flow_verdict
#[test]
fn reach_without_a_path_is_refuted() {
    let got = claim_findings(FLOWS, "claim k {\n  reach c -> a;\n}\n");
    assert_eq!(got.len(), 1, "{got:?}");
    assert_eq!(got[0].0, "CLAIM001");
}

// frob:tests crates/grimble-model/src/claim.rs::bound_verdict
#[test]
fn bound_on_an_uncomputable_quantity_is_unresolved_with_the_reason() {
    let got = claim_findings(FLOWS, "claim k {\n  bound latency f1 <= 5 ms;\n}\n");
    assert_eq!(got.len(), 1, "{got:?}");
    assert_eq!(got[0].0, "CLAIM003");
    assert_eq!(got[0].1, "Unresolved");
    assert!(got[0].2.contains("cannot be computed"), "{}", got[0].2);
}

// frob:tests crates/grimble-model/src/claim.rs::evidence_verdict
#[test]
fn claim_above_l1_without_evidence_is_unresolved_never_satisfied() {
    let got = claim_findings(FLOWS, "claim k {\n  noflow c -> a;\n  proof L2;\n}\n");
    assert_eq!(got.len(), 1, "{got:?}");
    assert_eq!(got[0].0, "CLAIM003");
    assert_eq!(got[0].1, "Unresolved");
    assert!(got[0].2.contains("no evidence"), "{}", got[0].2);
}

// frob:tests crates/grimble-model/src/claim.rs::evidence_verdict
#[test]
fn claim_above_l1_with_evidence_or_assumed_is_decided_on_its_flows() {
    let ev =
        "claim k {\n  noflow c -> a;\n  proof L2;\n  evidence tests \"crates/x/tests/t.rs\";\n}\n";
    assert!(claim_findings(FLOWS, ev).is_empty());
}

// frob:tests crates/grimble-model/src/claim.rs::flow_verdict
#[test]
fn noflow_with_an_operand_that_is_no_node_is_unresolved() {
    let got = claim_findings(FLOWS, "claim k {\n  noflow nowhere -> a;\n}\n");
    assert!(
        got.iter().any(|g| g.0 == "CLAIM003" && g.1 == "Unresolved"),
        "{got:?}"
    );
}

/// The CLAIM findings of `claims` under a `default_proof` of `rung`.
fn findings_with_default(rung: &str, claims: &str) -> Vec<String> {
    let text = format!("{NODES}{FLOWS}{claims}");
    let model = ModelFiles::new()
        .with_file("design/model.grmb", text.as_bytes())
        .with_default_proof(rung);
    check_model(&model)
        .into_iter()
        .filter(|f| f.rule.to_string().starts_with("CLAIM"))
        .map(|f| f.message)
        .collect()
}

// frob:tests crates/grimble-model/src/claim.rs::evidence_verdict
#[test]
fn claim_without_proof_clause_is_held_to_the_default_proof() {
    let got = findings_with_default("L2", "claim k {\n  noflow c -> a;\n}\n");
    assert_eq!(got.len(), 1, "{got:?}");
    assert!(got[0].contains("requires proof L2"), "{}", got[0]);
}

// frob:tests crates/grimble-model/src/claim.rs::evidence_verdict
#[test]
fn explicit_l1_proof_overrides_a_higher_default_proof() {
    let got = findings_with_default("L2", "claim k {\n  noflow c -> a;\n  proof L1;\n}\n");
    assert!(got.is_empty(), "{got:?}");
}

// frob:ticket 01M5XNNJQN463MG3PT8NBEC70D
// frob:tests crates/grimble-model/src/check.rs::check_model
#[test]
fn never_claim_parses_and_leaves_the_verdict_to_binding() {
    assert!(claim_findings(FLOWS, "claim k {\n  never a uses net.connect;\n}\n").is_empty());
}

// frob:ticket 01M6QA50DV05MDS2GRDYHEHVFH
// frob:tests crates/grimble-model/src/check.rs::check_model
#[test]
fn never_claim_with_arguments_parses() {
    let text = "claim k {\n  never a uses net.connect(\"h:1\", \"g:2\");\n}\n";
    assert!(claim_findings(FLOWS, text).is_empty());
}

// frob:ticket 01M5XNNJQN463MG3PT8NBEC70D
// frob:tests crates/grimble-model/src/check.rs::check_model
#[test]
fn never_claim_over_an_unknown_node_is_unresolved_reference() {
    let text = format!("{NODES}claim k {{\n  never ghost uses net.connect;\n}}\n");
    let model = ModelFiles::new().with_file("design/model.grmb", text.as_bytes());
    let got: Vec<String> = check_model(&model)
        .into_iter()
        .map(|f| f.rule.to_string())
        .collect();
    assert!(got.iter().any(|r| r == "MDL006"), "{got:?}");
}

// frob:ticket 01M6D5C4JDEMNSMNKBK62N4Y9Y
// frob:tests crates/grimble-model/src/parse.rs::parse_file
#[test]
fn attests_with_and_without_on_parses_and_resolves() {
    let text = format!(
        "{NODES}claim k {{\n  attests \"s\" on a;\n  assumed because=\"b\" until=2026-10-15 owner=l;\n}}\nclaim w {{\n  attests \"t\";\n  assumed because=\"b\" until=2026-10-15 owner=l;\n}}\n"
    );
    let model = ModelFiles::new().with_file("design/model.grmb", text.as_bytes());
    let got: Vec<String> = check_model(&model)
        .into_iter()
        .map(|f| f.rule.to_string())
        .collect();
    assert!(
        !got.iter().any(|r| r == "MDL006" || r == "MDL008"),
        "{got:?}"
    );
}

// frob:ticket 01M6D5C4JDEMNSMNKBK62N4Y9Y
// frob:tests crates/grimble-model/src/check.rs::check_model
#[test]
fn attests_over_an_unknown_node_or_empty_statement_is_reported() {
    let text = format!(
        "{NODES}claim k {{\n  attests \"s\" on ghost;\n}}\nclaim e {{\n  attests \"\";\n}}\n"
    );
    let model = ModelFiles::new().with_file("design/model.grmb", text.as_bytes());
    let got: Vec<String> = check_model(&model)
        .into_iter()
        .map(|f| f.rule.to_string())
        .collect();
    assert!(got.iter().any(|r| r == "MDL006"), "{got:?}");
    assert!(got.iter().any(|r| r == "MDL008"), "{got:?}");
}

/// Every (rule, message) finding of `claims` after the shared nodes.
fn all_findings(claims: &str) -> Vec<(String, String)> {
    let text = format!("{NODES}{claims}");
    let model = ModelFiles::new().with_file("design/model.grmb", text.as_bytes());
    check_model(&model)
        .into_iter()
        .map(|f| (f.rule.to_string(), f.message))
        .collect()
}

// frob:ticket 01M6D5C4JDEMNSMNKBK62N4Y9Y
// frob:tests crates/grimble-model/src/claim.rs::attests_verdict
#[test]
fn attests_without_evidence_is_unresolved_naming_the_owner_at_any_proof() {
    let text = "claim k {
  attests \"s\" on a;
  proof L1;
  assumed because=\"b\" until=2026-10-15 owner=logan;
}
";
    let got: Vec<_> = all_findings(text)
        .into_iter()
        .filter(|f| f.0 == "CLAIM003")
        .collect();
    assert_eq!(got.len(), 1, "{got:?}");
    assert_eq!(got[0].1, "attested by logan, no evidence");
}

// frob:ticket 01M6D5C4JDEMNSMNKBK62N4Y9Y
// frob:tests crates/grimble-model/src/claim.rs::attests_verdict
#[test]
fn attests_with_evidence_raises_no_claim_finding() {
    let text = "claim k {
  attests \"s\";
  assumed because=\"b\" until=2026-10-15 owner=logan;
  verified_by \"docs/t.md\";
}
";
    let got = all_findings(text);
    assert!(!got.iter().any(|f| f.0.starts_with("CLAIM")), "{got:?}");
}

// frob:ticket 01M6D5C4JDEMNSMNKBK62N4Y9Y
// frob:tests crates/grimble-model/src/check.rs::check_model
#[test]
fn attests_without_assumed_is_mdl008() {
    let got = all_findings(
        "claim k {
  attests \"s\";
  verified_by \"docs/t.md\";
}
",
    );
    assert!(got.iter().any(|f| f.0 == "MDL008"), "{got:?}");
}

// frob:ticket 01M6D5C4JDEMNSMNKBK62N4Y9Y
// frob:tests crates/grimble-model/src/check.rs::check_model
#[test]
fn extend_may_not_set_attests() {
    let got = all_findings(
        "claim k {
  noflow a -> b;
}
extend claim k {
  attests \"s\";
}
",
    );
    assert!(
        got.iter()
            .any(|f| f.0 == "MDL008" && f.1.contains("scalar")),
        "{got:?}"
    );
}
