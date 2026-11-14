//! `has_config`: the one file that marks a crunk project.

// frob:ticket 01M51N0ZN8BWH8C6RYGJBJQ73T

// frob:tests crates/crunk-check/src/lib.rs::has_config
#[test]
fn only_a_crunk_toml_marks_a_project() {
    let dir = tempfile::tempdir().expect("tempdir");
    assert!(!crunk_check::has_config(dir.path()));
    std::fs::write(dir.path().join("crunk.toml"), "").expect("write");
    assert!(crunk_check::has_config(dir.path()));
}
