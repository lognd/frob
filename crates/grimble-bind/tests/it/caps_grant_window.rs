//! Grants with expiry, profile scope and policy composition (ticket 01M5XNNJTK08K3CB98MCT14W34):
//! an expired `may` fails naming the date, a `profile=test` grant does not cover non-test code,
//! and a `policy` applied by `use` puts its grants on each node.

// frob:ticket 01M5XNNJTK08K3CB98MCT14W34

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

const WRITE: &str = "pub fn go(p: &str) {\n    let _ = std::fs::write(p, \"x\");\n}\n";

fn bind_with(model_text: &str, files: &[(&str, &str)]) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    for (rel, text) in files {
        let p = dir.path().join(rel);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, text).unwrap();
    }
    std::fs::write(dir.path().join("design/model.grmb"), model_text).unwrap();
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let model = ModelFiles::new().with_file("design/model.grmb", model_text.as_bytes().to_vec());
    grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &model,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

fn model(grant: &str) -> String {
    format!(
        "grimble = \"2\";\nmodule m;\nnode a : trusted {{\n  owns \"src/**\";\n  owns \"tests/**\";\n  {grant}\n}}\n"
    )
}

fn fired(b: &Binding, rule: &str) -> Vec<String> {
    b.findings
        .iter()
        .filter(|f| f.rule == rule)
        .map(|f| f.message.clone())
        .collect()
}

// frob:tests crates/grimble-bind/src/caps.rs::cap007
#[test]
fn an_expired_grant_fails_naming_the_date_and_stops_covering() {
    let b = bind_with(
        &model("may fs.write at \"src/**\" until=2020-01-01;"),
        &[("src/w.rs", WRITE)],
    );
    let msgs = fired(&b, "CAP007");
    assert_eq!(msgs.len(), 1, "{:?}", b.findings);
    assert!(msgs[0].contains("2020-01-01"), "{}", msgs[0]);
    assert!(
        !fired(&b, "CAP001").is_empty(),
        "expired grant must not cover"
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::cap007
#[test]
fn a_future_dated_grant_is_clean_and_covers() {
    let b = bind_with(
        &model("may fs.write at \"src/**\" until=2999-01-01;"),
        &[("src/w.rs", WRITE)],
    );
    assert!(fired(&b, "CAP007").is_empty(), "{:?}", b.findings);
    assert!(fired(&b, "CAP001").is_empty(), "{:?}", b.findings);
}

// frob:tests crates/grimble-bind/src/caps.rs::live
#[test]
fn a_test_profile_grant_does_not_cover_non_test_code() {
    let g = "may fs.write profile=test;";
    let prod = bind_with(&model(g), &[("src/w.rs", WRITE)]);
    assert!(!fired(&prod, "CAP001").is_empty(), "{:?}", prod.findings);
    let test = bind_with(&model(g), &[("tests/w.rs", WRITE)]);
    assert!(fired(&test, "CAP001").is_empty(), "{:?}", test.findings);
}

// frob:tests crates/grimble-bind/src/model.rs::apply_policies
#[test]
fn a_policy_puts_its_grants_on_every_node_that_uses_it() {
    let text = "grimble = \"2\";\nmodule m;\npolicy io {\n  may fs.read until=2999-01-01;\n}\n\
node a : trusted {\n  owns \"src/a/**\";\n  use io;\n}\nnode b : trusted {\n  owns \"src/b/**\";\n  use io;\n}\n";
    let files = ModelFiles::new().with_file("design/model.grmb", text.as_bytes().to_vec());
    let model = grimble_bind::model::load(&files);
    let nodes: Vec<_> = model
        .entities
        .values()
        .filter(|e| e.kind == grimble_model::ast::EntityKind::Node)
        .collect();
    assert_eq!(nodes.len(), 2);
    for n in nodes {
        assert_eq!(n.grants.len(), 1, "{}", n.anchor);
        assert_eq!(n.grants[0].via_policy.as_deref(), Some("io"));
        assert_eq!(n.grants[0].until.as_deref(), Some("2999-01-01"));
    }
}
