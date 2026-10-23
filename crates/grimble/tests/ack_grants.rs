//! `grimble ack --grants` and CAP005 through the real CLI: a new or widened `may` grant is a
//! finding of `grimble check` until a listed attester approves it; an agent or a stranger is
//! refused.

// frob:ticket 01M4GYBNW01DT1MJ6NJN2GX6NN

use std::path::Path;
use std::process::Command;

use gob_cli::run_for_test;
use grimble::ack::ack_grants;
use grimble::presence::{Presence, authorize};
use serde_json::Value;

const MODEL_NARROW: &str = "grimble = \"2\";\nmodule m;\nnode a : trusted { owns \"src/**\"; may fs.read at \"src/lib.rs\"; }\nnode d : trusted { owns \"design/**\"; }\n";
const MODEL_WIDE: &str = "grimble = \"2\";\nmodule m;\nnode a : trusted { owns \"src/**\"; may fs.read at \"src/**\"; }\nnode d : trusted { owns \"design/**\"; }\n";

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

fn git(dir: &Path, args: &[&str]) {
    let st = Command::new("git")
        .args(args)
        .current_dir(dir)
        .status()
        .expect("git runs");
    assert!(st.success(), "git {args:?}");
}

/// A git repository whose user is `email`, holding `model` and two sources.
fn repo(email: &str, model: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().unwrap();
    let d = dir.path();
    git(d, &["init", "-q", "-b", "main"]);
    git(d, &["config", "user.email", email]);
    git(d, &["config", "user.name", "Me"]);
    write(
        d,
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(
        d,
        "frob.toml",
        "[evidence]\nattesters = [\"me@example.com\"]\n",
    );
    write(d, "design/m.grmb", model);
    write(d, "src/lib.rs", "pub fn f() {}\n");
    write(d, "src/loose.rs", "pub fn g() {}\n");
    git(d, &["add", "-A"]);
    git(d, &["commit", "-q", "-m", "base"]);
    dir
}

fn cap005(dir: &Path) -> Vec<String> {
    let (_, out, _) = run_for_test(&grimble::cli(), &["check", "--json"], dir);
    let env: Value = serde_json::from_str(&out).unwrap_or(Value::Null);
    env["data"]["findings"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|f| f["rule"] == "CAP005")
        .map(|f| f["message"].as_str().unwrap_or_default().to_owned())
        .collect()
}

// frob:tests crates/grimble/src/ack.rs::ack_grants
#[test]
fn check_names_a_widened_grant_until_an_attester_acks_it() {
    let dir = repo("me@example.com", MODEL_NARROW);
    let d = dir.path();
    let human = Presence::interactive();
    let first = ack_grants(d, &human, "initial grants", "2026-10-02T00:00:00Z", false).unwrap();
    assert_eq!(first.grants.len(), 1, "{first:?}");
    assert!(first.commit.is_some(), "the ledger is committed");
    assert!(cap005(d).is_empty());

    write(d, "design/m.grmb", MODEL_WIDE);
    git(d, &["commit", "-q", "-am", "widen"]);
    let found = cap005(d);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(found[0].contains("fs.read at \"src/**\""), "{found:?}");

    let dry = ack_grants(d, &human, "ok", "2026-10-03T00:00:00Z", true).unwrap();
    assert_eq!(dry.grants.len(), 1);
    assert_eq!(cap005(d).len(), 1, "a dry run approves nothing");

    ack_grants(
        d,
        &human,
        "reviewed the widening",
        "2026-10-03T00:00:00Z",
        false,
    )
    .unwrap();
    assert!(cap005(d).is_empty());

    write(d, "design/m.grmb", MODEL_NARROW);
    git(d, &["commit", "-q", "-am", "narrow"]);
    assert!(cap005(d).is_empty(), "narrowing needs no ack");
}

// frob:tests crates/grimble/src/ack.rs::ack_grants
#[test]
fn a_stranger_may_not_approve_grants() {
    let dir = repo("stranger@example.com", MODEL_NARROW);
    let err = ack_grants(
        dir.path(),
        &Presence::interactive(),
        "why",
        "2026-10-02T00:00:00Z",
        false,
    )
    .unwrap_err();
    assert!(err.to_string().contains("E-ATTEST-NOT-ATTESTER"), "{err}");
    assert!(!dir.path().join("grimble.grants.toml").exists());
}

// frob:tests crates/grimble/src/presence.rs::authorize
#[test]
fn an_agent_or_a_pipe_is_refused_as_not_human() {
    let attesters = vec!["me@example.com".to_owned()];
    let piped = Presence::from_parts(false, false, |_| None);
    let err = authorize(&piped, Some("me@example.com"), &attesters).unwrap_err();
    assert!(err.to_string().contains("E-ATTEST-NOT-HUMAN"), "{err}");

    let agent = Presence::from_parts(true, true, |k| (k == "CLAUDECODE").then(|| "1".to_owned()));
    let err = authorize(&agent, Some("me@example.com"), &attesters).unwrap_err();
    assert!(err.to_string().contains("CLAUDECODE"), "{err}");

    let ok = authorize(&Presence::interactive(), Some("me@example.com"), &attesters).unwrap();
    assert_eq!(ok, "me@example.com");
    let none = authorize(&Presence::interactive(), None, &attesters).unwrap_err();
    assert!(none.to_string().contains("E-ATTEST-NOT-ATTESTER"), "{none}");
    let empty = authorize(&Presence::interactive(), Some("me@example.com"), &[]).unwrap_err();
    assert!(empty.to_string().contains("empty"), "{empty}");
}

// frob:tests crates/grimble/src/ack.rs::Ack
#[test]
fn the_cli_refuses_ack_grants_without_a_terminal() {
    let dir = repo("me@example.com", MODEL_NARROW);
    // The real binary with piped streams and no terminal, so the result never depends on the runner.
    let output = assert_cmd::Command::cargo_bin("grimble")
        .unwrap()
        .args(["ack", "--grants", "--reason", "why", "--json"])
        .current_dir(dir.path())
        .output()
        .unwrap();
    let text = format!(
        "{}{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    assert_ne!(output.status.code(), Some(0), "{text}");
    assert!(text.contains("E-ATTEST-NOT-HUMAN"), "{text}");
    assert!(!dir.path().join("grimble.grants.toml").exists());
}
