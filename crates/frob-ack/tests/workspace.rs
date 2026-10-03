//! Smoke: the rules run over this workspace quickly and find no dangling doc targets.

use std::path::PathBuf;
use std::time::Instant;

use frob_ack::{Inputs, evaluate};

fn workspace_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("workspace root")
}

#[test]
fn evaluate_over_this_workspace_has_no_dangling_doc_target() {
    let root = workspace_root();
    // Warm the symbol and findings caches.
    let warm = Inputs::collect(&root).expect("collect");
    evaluate(&root, &warm);

    let start = Instant::now();
    let inputs = Inputs::collect(&root).expect("collect");
    let findings = evaluate(&root, &inputs);
    let took = start.elapsed();

    assert!(inputs.graph.node_count() > 100, "walked a real workspace");
    assert!(
        !findings.iter().any(|f| f.rule.as_str() == "DRIFT002"),
        "{findings:?}"
    );
    eprintln!("evaluate took {took:?}");
}
