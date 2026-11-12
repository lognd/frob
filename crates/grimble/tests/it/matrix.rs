//! `grimble matrix` end to end: the CAP findings of a repository as matrix cells with a census.

// frob:ticket 01M5A75BY0FCJY0YXHRN8ZASNE

use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

const MODEL: &str = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/**\";\n  may fs.write at \"src/**\" because=\"reserved\";\n}\n";

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

fn matrix(dir: &Path) -> Value {
    let (code, out, err) = run_for_test(&grimble::cli(), &["matrix", "--json"], dir);
    assert_eq!(code, 0, "{out} {err}");
    serde_json::from_str(&out).unwrap_or_else(|e| panic!("{e}: {out} {err}"))
}

// frob:tests crates/grimble/src/matrix_cmd.rs::matrix_of
#[test]
fn a_grant_with_no_use_is_a_declared_unused_cell_in_the_census() {
    let dir = tempfile::tempdir().unwrap();
    let p = dir.path();
    write(
        p,
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(p, "design/m.grmb", MODEL);
    write(p, "src/a.py", "x = 1\n");
    let doc = matrix(p);
    let data = &doc["data"];
    let cells = data["cells"].as_array().unwrap();
    assert!(
        cells
            .iter()
            .any(|c| c["cell"] == "declared-unused" && c["atom"] == "fs.write"),
        "{data}"
    );
    assert_eq!(data["census"]["declared-unused"], 1, "{data}");
}

#[test]
fn a_repository_with_no_model_prints_an_empty_matrix() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "src/a.py", "x = 1\n");
    let data = matrix(dir.path())["data"].clone();
    assert_eq!(data["cells"].as_array().unwrap().len(), 0, "{data}");
}
