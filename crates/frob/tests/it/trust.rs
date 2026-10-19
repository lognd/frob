//! `frob trust`: refuses off a terminal with exit 3 and takes no `--yes`.
// frob:ticket 01M3ZX7VDVTM9DJCW5228YRZ8Z

use serde_json::Value;

use crate::common;

fn repo() -> tempfile::TempDir {
    let dir = common::git_repo();
    std::fs::write(
        dir.path().join("frob.toml"),
        "[tickets]\nref_mode = \"orphan\"\n",
    )
    .expect("config");
    dir
}

// frob:tests crates/frob/src/trust_cmd.rs::run
#[test]
fn non_tty_stdin_exits_3_and_is_marked_requires_human() {
    let dir = repo();
    let out = common::frob_command()
        .current_dir(dir.path())
        .args(["--json", "trust"])
        .output()
        .expect("run frob");
    assert_eq!(
        out.status.code(),
        Some(3),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let v: Value = serde_json::from_slice(&out.stdout).expect("json");
    assert_eq!(v["error"]["requires_human"], true);
    assert_eq!(v["error"]["code"], "E-TRUST-NEEDS-HUMAN");
    let text = v.to_string();
    assert!(!text.contains("--yes"), "{text}");
}

// frob:tests crates/frob/src/trust_cmd.rs::configure
#[test]
fn yes_is_an_unknown_flag() {
    let dir = repo();
    let out = common::frob_command()
        .current_dir(dir.path())
        .args(["trust", "--yes"])
        .output()
        .expect("run frob");
    assert_eq!(out.status.code(), Some(2));
}

// frob:tests crates/frob/src/trust_cmd.rs::gate
#[test]
fn gate_refuses_without_terminals_or_under_an_agent() {
    use frob_cli::trust_cmd::gate;
    let none = |_: &str| None;
    let r = gate(false, true, none).expect_err("no tty");
    assert!(r.requires_human);
    assert!(!r.message.contains("demo"), "no pack facts in the refusal");
    let agent = |k: &str| (k == "CLAUDECODE").then(|| "1".to_owned());
    let r = gate(true, true, agent).expect_err("agent");
    assert!(r.message.contains("tell the user"));
    assert!(gate(true, true, none).is_ok());
}
