//! Byte-identical files in different crates are each owned, cold or warm, never SYS001.

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

const MODEL: &str = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"crates/a/**\";\n}\nnode b : trusted {\n  owns \"crates/b/**\";\n}\nnode d : trusted {\n  owns \"design/**\";\n}\n";

fn bind_twins(dir: &std::path::Path) -> Binding {
    let walked = gob_walk::walk(dir, &gob_walk::WalkConfig::default()).unwrap();
    let files = ModelFiles::new().with_file("design/model.grmb", MODEL.as_bytes().to_vec());
    grimble_bind::bind(&BindInput {
        root: dir,
        entries: &walked.files,
        model: &files,
        modeled: &["design/**".to_owned()],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

fn twin_repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().unwrap();
    for d in ["crates/a", "crates/b", "design"] {
        std::fs::create_dir_all(dir.path().join(d)).unwrap();
    }
    for d in ["crates/a", "crates/b"] {
        // frob:accept LOG001 because="test fixture writes a temp source file, not log output"
        std::fs::write(
            dir.path().join(d).join("same.py"),
            "def go():\n    return 1\n",
        )
        .unwrap();
    }
    // frob:accept LOG001 because="test fixture writes a temp model file, not log output"
    std::fs::write(dir.path().join("design/model.grmb"), MODEL).unwrap();
    dir
}

// frob:tests crates/grimble-bind/src/eval.rs::sys001
#[test]
fn identical_files_in_different_crates_are_both_owned() {
    let dir = twin_repo();
    for _ in 0..2 {
        let b = bind_twins(dir.path());
        let unowned: Vec<_> = b.findings.iter().filter(|f| f.rule == "SYS001").collect();
        assert!(unowned.is_empty(), "{unowned:?}");
    }
}
