//! The live workspace's generated schema files match what the registered generator renders.
// frob:ticket 01M5H16QQT8R5N9162DMQE4F44

use gob_dev::{Kind, Mode, apply, generate, workspace_root};

#[test]
fn real_workspace_schemas_are_current() {
    frob_docgen::register();
    let root = workspace_root().expect("workspace root");
    let files = generate(Kind::Schemas, &root.join("crates")).expect("generate");
    let applied = apply(&root, &files, Mode::Check).expect("apply");
    assert_eq!(
        applied.differing, 0,
        "generated files differ or are missing"
    );
}
