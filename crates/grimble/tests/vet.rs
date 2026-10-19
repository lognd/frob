//! `grimble vet` end to end: advisories from an offline snapshot and unvetted new dependencies.

use std::path::Path;
use std::process::Command;

use gob_cli::run_for_test;
use serde_json::Value;

const REG: &str = "registry+https://github.com/rust-lang/crates.io-index";

fn lock(pkgs: &[(&str, &str)]) -> String {
    let mut s = String::from(
        "version = 4\n[[package]]\nname = \"app\"\nversion = \"0.1.0\"\ndependencies = [\n",
    );
    for (n, _) in pkgs {
        s.push_str(&format!(" \"{n}\",\n"));
    }
    s.push_str("]\n");
    for (n, v) in pkgs {
        s.push_str(&format!(
            "[[package]]\nname = \"{n}\"\nversion = \"{v}\"\nsource = \"{REG}\"\n"
        ));
    }
    s
}

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

fn grimble(dir: &Path, args: &[&str]) -> (i32, Value) {
    let (code, out, _) = run_for_test(&grimble::cli(), args, dir);
    (code, serde_json::from_str(&out).unwrap_or(Value::Null))
}

fn git(dir: &Path, args: &[&str]) {
    let ok = Command::new("git")
        .args(["-c", "user.name=t", "-c", "user.email=t@example.com"])
        .args(args)
        .current_dir(dir)
        .status()
        .unwrap()
        .success();
    assert!(ok, "git {args:?}");
}

// frob:tests crates/grimble/src/vet_cmd.rs::Vet
// frob:tests crates/grimble/src/vet_cmd.rs::run_vet
#[test]
fn vet_reports_advisory_id_and_fixed_versions() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "Cargo.lock", &lock(&[("badcrate", "1.1.0")]));
    write(
        dir.path(),
        ".grimble/advisory-db/crates/badcrate/RUSTSEC-2099-0001.toml",
        "[advisory]\nid = \"RUSTSEC-2099-0001\"\npackage = \"badcrate\"\ntitle = \"boom\"\n[versions]\npatched = [\">=1.2.3\"]\n",
    );
    let (code, env) = grimble(dir.path(), &["vet", "--json"]);
    assert_eq!(code, 1, "{env}");
    let text = env.to_string();
    assert!(text.contains("RUSTSEC-2099-0001"), "{text}");
    assert!(text.contains(">=1.2.3"), "{text}");
}

// frob:tests crates/grimble/src/vet_cmd.rs::check_warnings
#[test]
fn check_with_base_reports_unvetted_new_direct_dependency_unless_vetted() {
    let dir = tempfile::tempdir().unwrap();
    let d = dir.path();
    git(d, &["init", "-q", "-b", "main"]);
    write(d, "Cargo.lock", &lock(&[("old", "1.0.0")]));
    git(d, &["add", "-A"]);
    git(d, &["commit", "-q", "-m", "base"]);
    write(
        d,
        "Cargo.lock",
        &lock(&[("old", "1.0.0"), ("fresh", "2.0.0")]),
    );

    let (code, env) = grimble(d, &["vet", "--base", "HEAD", "--json"]);
    assert_eq!(code, 1, "{env}");
    assert!(env.to_string().contains("fresh"), "{env}");

    let (_, check) = grimble(d, &["check", "--base", "HEAD", "--json"]);
    assert!(
        check.to_string().contains("new direct dependency fresh"),
        "{check}"
    );

    write(d, ".grimble/vet.toml", "allow = [\"fresh\"]\n");
    let (code, env) = grimble(d, &["vet", "--base", "HEAD", "--json"]);
    assert_eq!(code, 0, "{env}");
    let (_, check) = grimble(d, &["check", "--base", "HEAD", "--json"]);
    assert!(!check.to_string().contains("fresh"), "{check}");
}
