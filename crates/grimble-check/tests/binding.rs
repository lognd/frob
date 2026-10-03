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
    write(dir.path(), "grimble.toml", "");
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
    write(dir.path(), "grimble.toml", "");
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
