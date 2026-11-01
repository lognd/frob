//! CAP002 selects the walk once per scoped grant, not once per owned file (the quadratic regression).
//! One test per binary: the counter is process-global.

// frob:ticket 01M6ABTR2AWBBW7M9T7EJ8Y6Y1

use std::sync::atomic::Ordering;

use grimble_bind::caps::CAP002_SELECT_FILES_CALLS;
use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

fn bind_many(n: usize, body: &str) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("src")).unwrap();
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    for i in 0..n {
        // frob:accept LOG001 because="test fixture writes a temp source file, not log output"
        std::fs::write(
            dir.path().join(format!("src/f{i}.py")),
            "def go():\n    return 1\n",
        )
        .unwrap();
    }
    let text =
        format!("grimble = \"2\";\nmodule m;\nnode a : trusted {{\n  owns \"src/**\";\n{body}}}\n");
    // frob:accept LOG001 because="test fixture writes a temp source file, not log output"
    std::fs::write(dir.path().join("design/model.grmb"), &text).unwrap();
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let files = ModelFiles::new().with_file("design/model.grmb", text.into_bytes());
    grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &files,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

// frob:tests crates/grimble-bind/src/caps.rs::cap002
#[test]
fn cap002_runs_select_files_once_per_scoped_grant_regardless_of_owned_files() {
    let body =
        "  may fs.read at \"src/f0.py\";\n  may fs.write at \"src/f1.py\";\n  may net.connect;\n";
    CAP002_SELECT_FILES_CALLS.store(0, Ordering::Relaxed);
    let _ = bind_many(12, body);
    // Two grants carry `at`; the unscoped one selects nothing. Twelve owned files must not multiply it.
    assert_eq!(CAP002_SELECT_FILES_CALLS.load(Ordering::Relaxed), 2);
}
