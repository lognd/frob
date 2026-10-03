//! The workspace's own crates must satisfy PROC001 under this repository's `frob.toml` policy.

use std::path::Path;

// frob:tests crates/gob-exec/src/proc001.rs::scan
#[test]
fn workspace_has_no_forbidden_process_references() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let spawners: Vec<String> = ["gob-exec", "gob-git"].map(str::to_owned).to_vec();
    let hits = gob_exec::proc001::scan(&root, &spawners);
    assert!(hits.is_empty(), "PROC001 hits: {hits:#?}");
}
