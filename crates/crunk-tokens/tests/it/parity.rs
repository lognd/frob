//! Export parity read from disk: `check_parity` against a spec whose generated files are absent.

// frob:ticket 01M51N0ZN8BWH8C6RYGJBJQ73T

use crunk_tokens::export::check_parity;

// frob:tests crates/crunk-tokens/src/export/parity.rs::check_parity
#[test]
fn a_project_without_generated_files_has_no_divergence() {
    let dir = tempfile::tempdir().expect("tempdir");
    let spec = crunk_spec::parse_spec(
        crunk_spec::presets::DEFAULT,
        std::path::Path::new("crunk.toml"),
        dir.path(),
    )
    .expect("default preset parses");
    let found = check_parity(&spec).expect("parity decides");
    assert!(found.is_empty(), "{found:?}");
}
