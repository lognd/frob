//! Proves the workspace print/dbg clippy ban (~J1PTXPF) is configured and stays configured.
// frob:ticket 01M5XMR625ABZ4HX19EJ1PTXPF

use std::path::Path;

/// Read a file at the workspace root.
fn root_file(name: &str) -> String {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    std::fs::read_to_string(root.join(name)).expect("workspace root file readable")
}

#[test]
fn workspace_denies_print_and_dbg_lints() {
    let cargo = root_file("Cargo.toml");
    for lint in ["print_stdout", "print_stderr", "dbg_macro"] {
        let line = cargo
            .lines()
            .find(|l| l.trim_start().starts_with(lint))
            .unwrap_or_else(|| panic!("{lint} missing from [workspace.lints.clippy]"));
        assert!(line.contains("\"deny\""), "{lint} must be deny: {line}");
    }
}

#[test]
fn clippy_toml_only_exempts_tests() {
    let clippy = root_file("clippy.toml");
    assert!(clippy.contains("allow-print-in-tests = true"));
    assert!(clippy.contains("allow-dbg-in-tests = true"));
}
