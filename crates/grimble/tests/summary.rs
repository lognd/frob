//! `grimble check --summary`: a compact check output for evidence under a size cap.

// frob:ticket 01M4HEMDB8A1X1RQFNVJB1G32M

use std::fmt::Write as _;
use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

/// A repository of `nodes` nodes that each call `subprocess` without a grant (one CAP001 each).
fn large_model(dir: &Path, nodes: usize) {
    write(
        dir,
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    let mut model = String::from("grimble = \"2\";\nmodule m;\n");
    for i in 0..nodes {
        let _ = write!(
            model,
            "node n{i:04} : trusted {{\n  owns \"src/n{i:04}/**\";\n}}\n"
        );
        write(
            dir,
            &format!("src/n{i:04}/x.py"),
            "import subprocess\n\ndef go():\n    subprocess.run([\"ls\"])\n",
        );
    }
    write(dir, "design/m.grmb", &model);
}

fn check(dir: &Path, args: &[&str]) -> Value {
    let (_, out, err) = run_for_test(&grimble::cli(), args, dir);
    serde_json::from_str(&out).unwrap_or_else(|e| panic!("{e}: {out} {err}"))
}

// frob:tests crates/grimble/src/lib.rs::GrimbleProduct.check
// frob:tests crates/grimble-check/src/summary.rs::summary_document
#[test]
fn summary_of_a_large_model_is_compact() {
    let dir = tempfile::tempdir().unwrap();
    large_model(dir.path(), 500);
    let full = check(dir.path(), &["check", "--json"]);
    let full_len = full["data"].to_string().len();
    assert!(full_len > 64 * 1024, "model is not large enough: {full_len}");

    let first = check(dir.path(), &["check", "--summary", "--json"]);
    let data = &first["data"];
    assert!(data.to_string().len() < 64 * 1024, "{}", data.to_string().len());
    assert_eq!(data["schema_version"], "grimble.check-summary/1");
    assert_eq!(data["compute_digest"], full["data"]["compute_digest"]);
    assert!(
        data["document_digest"]
            .as_str()
            .is_some_and(|d| d.starts_with("blake3:")),
        "{data}"
    );
    let rule = data["findings"]["by_rule"]
        .as_array()
        .unwrap()
        .iter()
        .find(|r| r["rule"] == "CAP001")
        .unwrap_or_else(|| panic!("no CAP001 row: {data}"));
    assert_eq!(rule["error"], 500);
    assert_eq!(data["findings"]["by_severity"]["error"], 500);
    let caps = &data["capabilities"];
    assert_eq!(caps["nodes"], 500);
    assert_eq!(caps["cells"]["undeclared"], 500);
    assert_eq!(caps["unattributed_findings"], 0);
    // 500 per-node rows overflow the node budget: folded by aggregation, not cut.
    assert_eq!(caps["nodes_detail"], "per-signature");
    assert_eq!(caps["by_node"][0]["nodes"], 500);

    // Deterministic: a second run yields the same bytes (timing is not digested).
    let second = check(dir.path(), &["check", "--summary", "--json"]);
    assert_eq!(first["data"], second["data"]);
}

#[test]
fn summary_of_an_empty_model_is_all_zero() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "[grimble]\nmodels = []\n");
    let doc = check(dir.path(), &["check", "--summary", "--json"]);
    let data = &doc["data"];
    assert_eq!(data["findings"]["total"], 0);
    assert_eq!(data["capabilities"]["nodes"], 0);
    assert_eq!(data["capabilities"]["nodes_detail"], "per-node");
    assert!(data["compute_digest"].is_string(), "{data}");
}

#[test]
fn small_model_lists_each_node() {
    let dir = tempfile::tempdir().unwrap();
    large_model(dir.path(), 3);
    let doc = check(dir.path(), &["check", "--summary", "--json"]);
    let rows = doc["data"]["capabilities"]["by_node"].as_array().unwrap();
    let names: Vec<_> = rows.iter().map(|r| r["node"].as_str().unwrap()).collect();
    assert_eq!(names.len(), 3, "{doc}");
    let mut sorted = names.clone();
    sorted.sort_unstable();
    assert_eq!(names, sorted);
    assert_eq!(rows[0]["undeclared"], 1);
}

#[test]
fn summary_without_json_still_runs() {
    let dir = tempfile::tempdir().unwrap();
    large_model(dir.path(), 2);
    let (code, out, _) = run_for_test(&grimble::cli(), &["check", "--summary"], dir.path());
    assert_eq!(code, 1, "the gate verdict is unchanged: {out}");
    assert!(out.contains("grimble.check-summary/1"), "{out}");
}
