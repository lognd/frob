//! The workspace's own crates must satisfy PROC001.

use std::path::Path;

#[test]
fn workspace_has_no_forbidden_process_references() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let hits = gob_exec::proc001::scan(&root);
    assert!(hits.is_empty(), "PROC001 hits: {hits:#?}");
}
