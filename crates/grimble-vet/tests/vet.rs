//! Vetting over lockfile text, advisory files and the allowlist.

use grimble_vet::{Advisory, Allowlist, Rule, Snapshot, parse_lockfile, vet};

use std::fmt::Write as _;

const REG: &str = "registry+https://github.com/rust-lang/crates.io-index";

fn lock(pkgs: &[(&str, &str)]) -> String {
    let mut s = String::from(
        "version = 4\n[[package]]\nname = \"app\"\nversion = \"0.1.0\"\ndependencies = [\n",
    );
    for (n, _) in pkgs {
        writeln!(s, " \"{n}\",").unwrap();
    }
    s.push_str("]\n");
    for (n, v) in pkgs {
        write!(
            s,
            "[[package]]\nname = \"{n}\"\nversion = \"{v}\"\nsource = \"{REG}\"\n"
        )
        .unwrap();
    }
    s
}

const ADVISORY: &str = r#"
[advisory]
id = "RUSTSEC-2099-0001"
package = "badcrate"
title = "memory corruption"
[versions]
patched = [">=1.2.3"]
unaffected = ["<1.0.0"]
"#;

fn snapshot() -> Snapshot {
    Snapshot::new(vec![Advisory::parse("t", ADVISORY).expect("advisory")])
}

#[test]
fn advisory_is_reported_with_id_and_fixed_versions() {
    let head = parse_lockfile(&lock(&[("badcrate", "1.1.0")])).expect("lock");
    let base = parse_lockfile(&lock(&[])).expect("lock");
    let allow = Allowlist::parse("allow = [\"badcrate\"]").expect("allow");
    let r = vet(&head, Some(&base), &snapshot(), &allow);
    let f = r
        .findings
        .iter()
        .find(|f| f.rule == Rule::Advisory)
        .expect("advisory finding");
    assert_eq!(f.advisory.as_deref(), Some("RUSTSEC-2099-0001"));
    assert_eq!(f.fixed, vec![">=1.2.3".to_owned()]);
    assert_eq!(r.errors(), 1);
}

#[test]
fn patched_and_unaffected_versions_are_clean() {
    for v in ["1.2.3", "0.9.0"] {
        let head = parse_lockfile(&lock(&[("badcrate", v)])).expect("lock");
        let r = vet(&head, None, &snapshot(), &Allowlist::default());
        assert!(r.findings.is_empty(), "{v}: {:?}", r.findings);
    }
}

#[test]
fn new_direct_dependency_is_reported_unless_vetted() {
    let base = parse_lockfile(&lock(&[("old", "1.0.0")])).expect("lock");
    let head = parse_lockfile(&lock(&[("old", "1.0.0"), ("fresh", "2.0.0")])).expect("lock");
    let r = vet(
        &head,
        Some(&base),
        &Snapshot::default(),
        &Allowlist::default(),
    );
    assert_eq!(r.examined, 1);
    assert_eq!(r.findings.len(), 1);
    assert_eq!(r.findings[0].rule, Rule::UnvettedDirect);
    assert_eq!(r.findings[0].package, "fresh");
    let allow = Allowlist::parse("allow = [\"fresh@2.0.0\"]").expect("allow");
    assert!(
        vet(&head, Some(&base), &Snapshot::default(), &allow)
            .findings
            .is_empty()
    );
}

#[test]
fn duplicate_versions_warn_without_failing() {
    let head = parse_lockfile(&lock(&[("dup", "1.0.0"), ("dup", "2.0.0")])).expect("lock");
    let r = vet(&head, None, &Snapshot::default(), &Allowlist::default());
    assert_eq!(r.findings.len(), 1);
    assert_eq!(r.findings[0].rule, Rule::Duplicate);
    assert_eq!(r.errors(), 0);
}

#[test]
fn snapshot_loads_advisory_files_from_a_directory() {
    let dir = tempfile::tempdir().expect("tempdir");
    let sub = dir.path().join("crates/badcrate");
    std::fs::create_dir_all(&sub).expect("mkdir");
    std::fs::write(sub.join("RUSTSEC-2099-0001.toml"), ADVISORY).expect("write");
    std::fs::write(dir.path().join("README.toml"), "not = 'an advisory'").expect("write");
    let snap = Snapshot::load(dir.path()).expect("load");
    let v = semver::Version::parse("1.1.0").expect("version");
    assert_eq!(snap.affecting("badcrate", &v).len(), 1);
}
