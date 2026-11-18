//! Kernel flow findings: label closure, endorsement and rate (FLOW001-003).

// frob:ticket 01M4FGYG9TXDAMZ2VS2ZHGJKX1

use grimble_model::{ModelFiles, check_model};

/// The (rule, message) of every FLOW finding of `body` wrapped in a module header.
fn flow_findings(body: &str) -> Vec<(String, String)> {
    let text = format!("grimble = \"2\";\nmodule m;\n{body}");
    let model = ModelFiles::new().with_file("design/model.grmb", text.as_bytes());
    check_model(&model)
        .into_iter()
        .filter(|f| f.rule.to_string().starts_with("FLOW"))
        .map(|f| (f.rule.to_string(), f.message))
        .collect()
}

// frob:tests crates/grimble-model/src/kernel.rs::kernel_findings
#[test]
fn secret_flow_into_public_node_is_a_label_closure_finding() {
    let got = flow_findings(
        "node a : trusted {\n}\nnode b : trusted {\n  clearance Public;\n}\n\
         flow f2 : a -> b {\n  label Secret;\n  rate 1 req/s;\n}\n",
    );
    assert!(
        got.iter().any(|(r, m)| r == "FLOW001" && m.contains("f2")),
        "{got:?}"
    );
}

// frob:tests crates/grimble-model/src/kernel.rs::kernel_findings
#[test]
fn foreign_to_trusted_without_boundary_or_rate_is_flagged() {
    let got = flow_findings(
        "node a : foreign {\n}\nnode b : trusted {\n}\nflow f1 : a -> b {\n  label Public;\n}\n",
    );
    assert!(
        got.iter().any(|(r, m)| r == "FLOW002" && m.contains("f1")),
        "{got:?}"
    );
    assert!(
        got.iter().any(|(r, m)| r == "FLOW003" && m.contains("f1")),
        "{got:?}"
    );
}

// frob:tests crates/grimble-model/src/kernel.rs::kernel_findings
#[test]
fn boundary_and_rate_clear_the_findings() {
    let got = flow_findings(
        "node a : foreign {\n}\nnode b : trusted {\n  clearance Public;\n}\n\
         flow f1 : a -> b {\n  label Public;\n  rate 10 req/s;\n}\n\
         boundary b1 endorse f1 : foreign -> trusted;\n",
    );
    assert!(got.is_empty(), "{got:?}");
}

/// The (rule, message) of every VMOD finding of `body` wrapped in a module header.
fn vmod_findings(body: &str) -> Vec<(String, String)> {
    let text = format!("grimble = \"2\";\nmodule m;\n{body}");
    let model = ModelFiles::new().with_file("design/model.grmb", text.as_bytes());
    check_model(&model)
        .into_iter()
        .filter(|f| f.rule.to_string().starts_with("VMOD"))
        .map(|f| (f.rule.to_string(), f.message))
        .collect()
}

const REQ: &str = "vmodel req_a {\n  kind artifact;\n  level requirements;\n}\n";

// frob:tests crates/grimble-model/src/kernel.rs::vmodel_findings
#[test]
fn a_requirement_no_design_satisfies_is_one_orphan_finding() {
    let got = vmod_findings(REQ);
    assert_eq!(got.len(), 1, "{got:?}");
    assert_eq!(got[0].0, "VMOD001");
    assert!(got[0].1.contains("req_a"), "{got:?}");
}

// frob:tests crates/grimble-model/src/kernel.rs::vmodel_findings
#[test]
fn a_design_satisfying_the_requirement_closes_both_rules() {
    let body = format!(
        "{REQ}vmodel des_a {{\n  kind artifact;\n  level component_design;\n  satisfies req_a;\n}}\n"
    );
    let got = vmod_findings(&body);
    assert!(got.is_empty(), "{got:?}");
}

// frob:tests crates/grimble-model/src/kernel.rs::vmodel_findings
#[test]
fn a_design_with_no_satisfies_is_an_unjustified_design() {
    let got = vmod_findings("vmodel des_a {\n  kind artifact;\n  level system_design;\n}\n");
    assert_eq!(got.len(), 1, "{got:?}");
    assert_eq!(got[0].0, "VMOD002");
    assert!(got[0].1.contains("des_a"), "{got:?}");
}
