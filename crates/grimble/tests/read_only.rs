//! Read-only grimble views (`exceptions`, `matrix`, `graph`) leave the repository untouched.

// frob:ticket 01M6C6NBJSSAVBR59RBMPWW9VP

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

use gob_cli::run_for_test;

/// Every file under `dir`, relative, so a run's new writes show as a set difference.
fn files(dir: &Path) -> BTreeSet<PathBuf> {
    fn walk(base: &Path, dir: &Path, out: &mut BTreeSet<PathBuf>) {
        for entry in std::fs::read_dir(dir).unwrap() {
            let path = entry.unwrap().path();
            if path.is_dir() {
                walk(base, &path, out);
            } else {
                out.insert(path.strip_prefix(base).unwrap().to_path_buf());
            }
        }
    }
    let mut out = BTreeSet::new();
    walk(dir, dir, &mut out);
    out
}

// frob:tests crates/grimble/src/exceptions.rs::ExceptionsList
// frob:tests crates/grimble/src/matrix_cmd.rs::MatrixVerb
// frob:tests crates/grimble/src/graph_cmd.rs::Graph
#[test]
fn read_only_views_leave_no_new_files_in_the_repository() {
    let dir = tempfile::tempdir().unwrap();
    let model = dir.path().join("m.grmb");
    std::fs::write(
        &model,
        "grimble = \"2\";\nmodule m;\nsystem s {\n  actor customer : human;\n}\n",
    )
    .unwrap();
    let before = files(dir.path());
    for args in [
        &["exceptions", "list", "--json"][..],
        &["matrix", "--json"][..],
        &["graph", "--json"][..],
    ] {
        let (code, out, err) = run_for_test(&grimble::cli(), args, dir.path());
        assert_eq!(code, 0, "{args:?}: {out} {err}");
        assert_eq!(files(dir.path()), before, "{args:?} wrote into the repo");
    }
}
