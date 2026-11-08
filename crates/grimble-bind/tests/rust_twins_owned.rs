//! Byte-identical Rust files in different crates are each owned, cold or warm.

// frob:ticket 01M6W7DN4VK9M7A08FENK65NZG

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

const MODEL: &str = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"crates/frob-*/**\";\n  owns \"crates/frob/**\";\n}\nnode d : trusted {\n  owns \"design/**\";\n}\n";
const TWIN: &str = "use std::ffi::OsStr;\nuse std::path::Path;\n\n/// text\npub(crate) fn text(path: &Path) -> String {\n    path.display().to_string()\n}\n\n/// name\npub(crate) fn name_text(name: &OsStr) -> String {\n    text(Path::new(name))\n}\n";
const CRATES: [&str; 4] = ["frob-evidence", "frob-release", "frob-worktree", "frob"];

fn bind_all(dir: &std::path::Path) -> Binding {
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

fn repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    for c in CRATES {
        std::fs::create_dir_all(dir.path().join("crates").join(c).join("src")).unwrap();
        // frob:accept LOG001 because="test fixture writes a temp source file, not log output"
        std::fs::write(
            dir.path().join("crates").join(c).join("src/pathtext.rs"),
            TWIN,
        )
        .unwrap();
    }
    // frob:accept LOG001 because="test fixture writes a temp model file, not log output"
    std::fs::write(dir.path().join("design/model.grmb"), MODEL).unwrap();
    dir
}

// frob:tests crates/grimble-bind/src/eval.rs::sys001
#[test]
fn identical_rust_files_in_different_crates_are_all_owned() {
    let dir = repo();
    for round in 0..3 {
        let b = bind_all(dir.path());
        let unowned: Vec<_> = b.findings.iter().filter(|f| f.rule == "SYS001").collect();
        assert!(unowned.is_empty(), "round {round}: {unowned:?}");
    }
}
