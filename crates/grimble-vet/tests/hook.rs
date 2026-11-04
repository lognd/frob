//! `vet --hook`: install-shaped command parsing and vetting.

use grimble_vet::{Advisory, Allowlist, Rule, Snapshot, parse_install, vet_command};

const ADVISORY: &str = r#"
[advisory]
id = "RUSTSEC-2099-0001"
package = "badcrate"
title = "memory corruption"
[versions]
patched = [">=1.2.3"]
"#;

const UNFIXED: &str = r#"
[advisory]
id = "RUSTSEC-2099-0002"
package = "deadcrate"
title = "unsound"
[versions]
patched = []
"#;

fn snapshot() -> Snapshot {
    Snapshot::new(vec![
        Advisory::parse("t", ADVISORY).expect("advisory"),
        Advisory::parse("t", UNFIXED).expect("advisory"),
    ])
}

fn allow(entries: &[&str]) -> Allowlist {
    Allowlist {
        allow: entries.iter().map(|s| (*s).to_owned()).collect(),
    }
}

#[test]
fn parses_cargo_add_with_flags_and_pins() {
    let r = parse_install("cargo add serde@1.0.0 tokio --features full -F rt");
    let got: Vec<_> = r
        .iter()
        .map(|i| (i.name.as_str(), i.version.as_deref()))
        .collect();
    assert_eq!(got, [("serde", Some("1.0.0")), ("tokio", None)]);
}

#[test]
fn parses_install_after_a_chain() {
    let r =
        parse_install("cd x && cargo +nightly install --locked ripgrep --version 14.0.0 | tee log");
    assert_eq!(r.len(), 1);
    assert_eq!(r[0].name, "ripgrep");
    assert_eq!(r[0].version.as_deref(), Some("14.0.0"));
}

#[test]
fn ignores_other_commands() {
    assert!(parse_install("cargo build --release && ls").is_empty());
}

#[test]
fn skips_git_installs() {
    assert!(parse_install("cargo install --git https://example.com/x").is_empty());
}

#[test]
fn skips_path_installs() {
    assert!(parse_install("cargo add foo --path ../foo").is_empty());
}

#[test]
fn blocks_an_unvetted_crate() {
    let rep = vet_command("cargo add evil", &allow(&["serde"]), &snapshot());
    assert_eq!(rep.errors(), 1);
    assert_eq!(rep.findings[0].rule, Rule::UnvettedDirect);
}

#[test]
fn allows_a_vetted_crate() {
    let rep = vet_command("cargo add serde", &allow(&["serde"]), &snapshot());
    assert_eq!(rep.errors(), 0);
    assert_eq!(rep.examined, 1);
}

#[test]
fn blocks_a_pinned_advisory_version() {
    let rep = vet_command(
        "cargo add badcrate@1.0.0",
        &allow(&["badcrate"]),
        &snapshot(),
    );
    assert_eq!(rep.findings.len(), 1);
    assert_eq!(rep.findings[0].rule, Rule::Advisory);
}

#[test]
fn allows_a_pinned_patched_version() {
    let rep = vet_command(
        "cargo add badcrate@1.2.3",
        &allow(&["badcrate"]),
        &snapshot(),
    );
    assert_eq!(rep.errors(), 0);
}

#[test]
fn unpinned_allows_a_fixed_advisory() {
    let ok = vet_command("cargo add badcrate", &allow(&["badcrate"]), &snapshot());
    assert_eq!(ok.errors(), 0);
}

#[test]
fn unpinned_blocks_an_unfixed_advisory() {
    let bad = vet_command("cargo add deadcrate", &allow(&["deadcrate"]), &snapshot());
    assert_eq!(bad.errors(), 1);
}
