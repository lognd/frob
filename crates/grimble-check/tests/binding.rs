//! `grimble check` registers the binding rules and fills the document's `bindings`.

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC

use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn the_document_carries_bindings_and_sys_findings() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(
        dir.path(),
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\n\nnode a : trusted { owns \"src/**\"; owns \"src/gone.rs::x\"; }\nnode d : trusted { owns \"design/**\"; }\n",
    );
    write(dir.path(), "src/lib.rs", "pub fn run() {}\n");
    write(dir.path(), "docs/loose.txt", "x\n");
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    let findings: Vec<String> = doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .map(|f| f["rule"].as_str().unwrap().to_owned())
        .collect();
    assert!(findings.contains(&"SYS001".to_owned()), "{findings:?}");
    let bindings = doc["bindings"].as_array().unwrap();
    assert!(bindings.iter().any(|b| b["entity"] == "node/a"
        && b["identity"] == "src/lib.rs::run"
        && b["status"] == "must"
        && b["rank"] == 2));
    let rules = doc["rules"].as_array().unwrap();
    assert!(rules.iter().any(|r| r["rule"] == "SYS001"));
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn no_model_means_no_binding_rows() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(dir.path(), "src/lib.rs", "pub fn run() {}\n");
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    assert!(doc["bindings"].as_array().unwrap().is_empty());
    assert!(
        doc["findings"]
            .as_array()
            .unwrap()
            .iter()
            .all(|f| !f["rule"].as_str().unwrap().starts_with("SYS"))
    );
}

// frob:ticket 01M403Q1W4PMWRM8GXPRS10WX7
// frob:tests crates/grimble-check/src/bind_cache.rs::BindSummary
#[test]
fn a_warm_run_reuses_the_binding_and_an_edit_rebuilds_it() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(
        dir.path(),
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\n\nnode a : trusted { owns \"src/**\"; }\n",
    );
    write(dir.path(), "src/lib.rs", "pub fn run() {}\n");
    let cold = run(dir.path(), &CheckOptions::default()).unwrap();
    assert!(!cold.bind_cached, "the first run builds the binding");
    let warm = run(dir.path(), &CheckOptions::default()).unwrap();
    assert!(
        warm.bind_cached,
        "an unchanged repository reuses the binding"
    );
    let strip = |r: &grimble_check::GrimbleRun| {
        let mut d = sibling_document(r);
        d.as_object_mut().unwrap().remove("timing");
        d
    };
    assert_eq!(strip(&cold), strip(&warm), "warm output equals cold output");
    write(
        dir.path(),
        "src/lib.rs",
        "pub fn run() {}\npub fn more() {}\n",
    );
    let edited = run(dir.path(), &CheckOptions::default()).unwrap();
    assert!(!edited.bind_cached, "an edit rebuilds the binding");
}

// frob:tests crates/grimble-check/src/bind_cache.rs::BindSummary
#[test]
fn a_summary_survives_its_encoding() {
    use grimble_bind::BindFinding;
    use grimble_check::bind_cache::BindSummary;
    let mut s = BindSummary::default();
    s.bindings.push(serde_json::json!({"entity": "node/a"}));
    s.findings.push(BindFinding {
        rule: "SYS001",
        severity: gob_rules::Severity::Warn,
        file: Some("src/a.rs".to_owned()),
        range: Some((1, 4)),
        message: "m".to_owned(),
        anchor: "a".to_owned(),
    });
    s.subjects.insert("SYS003", 7);
    assert_eq!(BindSummary::decode(&s.encode()), Some(s));
    assert_eq!(BindSummary::decode(b"{}"), None);
}
