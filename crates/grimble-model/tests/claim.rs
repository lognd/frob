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
