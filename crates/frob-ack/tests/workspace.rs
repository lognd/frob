//! Smoke: the rules run over a multi-module workspace quickly and find no dangling doc targets.
//!
//! The workspace is a generated fixture, not this repository: dangling-target detection is covered
//! by `ack.rs` (DRIFT002 fires on a bad heading and on a missing file), and this repository's own
//! doc targets are enforced by the `check` step of `cargo dev ci` (`frob check`), so walking the
//! real workspace here only repeated that work at debug-build speed.

use std::time::Instant;

use frob_ack::{Inputs, evaluate};

const MODULES: usize = 40;

/// A workspace of `MODULES` source files, each linking to a heading that exists.
fn write_workspace(root: &std::path::Path) {
    std::fs::create_dir_all(root.join("src")).expect("mkdir src");
    std::fs::create_dir_all(root.join("docs")).expect("mkdir docs");
    let mut guide = String::from("# Guide\n");
    for i in 0..MODULES {
        guide.extend([
            "\n## Topic ",
            &i.to_string(),
            "\n\nText for topic ",
            &i.to_string(),
            ".\n",
        ]);
        let lib = format!(
            "// frob:doc docs/guide.md#topic-{i}\npub fn documented_{i}(x: u32) -> u32 {{\n    helper_{i}(x) + 1\n}}\n\nfn helper_{i}(x: u32) -> u32 {{\n    x * 2\n}}\n\npub fn plain_{i}(x: u32) -> u32 {{\n    x\n}}\n"
        );
        std::fs::write(root.join(format!("src/m{i}.rs")), lib).expect("write module");
    }
    std::fs::write(root.join("docs/guide.md"), guide).expect("write guide");
}

// frob:ticket 01M41ZSW6DZMBE5QWNGB6VY10G
#[test]
fn evaluate_over_a_generated_workspace_has_no_dangling_doc_target() {
    let dir = tempfile::tempdir().expect("tempdir");
    write_workspace(dir.path());
    // Warm the symbol and findings caches.
    let warm = Inputs::collect(dir.path()).expect("collect");
    evaluate(dir.path(), &warm);

    let start = Instant::now();
    let inputs = Inputs::collect(dir.path()).expect("collect");
    let findings = evaluate(dir.path(), &inputs);
    let took = start.elapsed();

    assert!(inputs.graph.node_count() > 100, "walked a real workspace");
    assert!(
        !findings.iter().any(|f| f.rule.as_str() == "DRIFT002"),
        "{findings:?}"
    );
    eprintln!("evaluate took {took:?}");
}
