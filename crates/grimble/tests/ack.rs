//! `grimble ack` end to end: the lock is written, `grimble check --json` runs SYS006 to SYS008
//! against it, and a stale scheme forces re-attestation.

// frob:ticket 01M3Z714820D1SK6X44T9R1B70
// frob:ticket 01M4D6NMS0EQA0B6NB9KEBHDRN

use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

const MODEL: &str = "grimble = \"2\";\nmodule m;\nnode p : trusted { owns \"p/**\"; }\nnode c : trusted { owns \"c/**\"; }\nnode d : trusted { owns \"design/**\"; }\nflow f : p -> c {\n  producer \"p/lib.rs::emit\";\n  consumer \"c/lib.rs::take\";\n}\n";
const BIG: &str =
    "{ let mut t = x; for i in 0..x { t = t + i * 2; } if t > 10 { t - 1 } else { t + 1 } }";

fn grimble(dir: &Path, args: &[&str]) -> (i32, Value, String) {
    let (code, out, err) = run_for_test(&grimble::cli(), args, dir);
    (code, serde_json::from_str(&out).unwrap_or(Value::Null), err)
}

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

fn rules(env: &Value) -> Vec<String> {
    env["data"]["findings"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(|f| f["rule"].as_str())
        .filter(|r| matches!(*r, "SYS006" | "SYS007" | "SYS008"))
        .map(str::to_owned)
        .collect()
}

fn fixture(dir: &Path) {
    write(
        dir,
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(dir, "design/m.grmb", MODEL);
    write(
        dir,
        "p/lib.rs",
        &format!("pub fn emit(x: u32) -> u32 {BIG}\n"),
    );
    write(
        dir,
        "c/lib.rs",
        &format!("pub fn take(x: u32) -> u32 {BIG}\n"),
    );
}

// frob:tests crates/grimble/src/ack.rs::Ack
#[test]
fn ack_writes_the_lock_and_check_reports_contract_skew_after_a_producer_edit() {
    let dir = tempfile::tempdir().unwrap();
    fixture(dir.path());
    let (code, env, err) = grimble(
        dir.path(),
        &["ack", "flow/f", "--reason", "initial", "--json"],
    );
    assert_eq!(code, 0, "{env} {err}");
    assert_eq!(env["data"]["acked"].as_array().unwrap().len(), 3, "{env}");
    assert!(dir.path().join("grimble.lock").is_file());
    let (_, env, _) = grimble(dir.path(), &["check", "--json"]);
    assert_eq!(rules(&env), Vec::<String>::new(), "{env}");
    let (code, env, _) = grimble(
        dir.path(),
        &["ack", "flow/f", "--reason", "again", "--json"],
    );
    assert_eq!(code, 0);
    assert_eq!(env["already"], true, "a second ack changes nothing: {env}");

    write(
        dir.path(),
        "p/lib.rs",
        &format!("pub fn emit(x: u64) -> u64 {BIG}\n"),
    );
    let (code, env, _) = grimble(dir.path(), &["check", "--json"]);
    assert_eq!(code, 1, "{env}");
    let r = rules(&env);
    assert!(r.contains(&"SYS006".to_owned()), "{r:?}");
    let f = env["data"]["findings"]
        .as_array()
        .unwrap()
        .iter()
        .find(|f| f["rule"] == "SYS006")
        .unwrap();
    assert!(f["message"].as_str().unwrap().contains("flow/f"));
}

// frob:tests crates/grimble/src/ack.rs::Ack
#[test]
fn ack_refuses_a_stale_scheme_for_a_targeted_ack_and_all_with_reason_migrates() {
    let dir = tempfile::tempdir().unwrap();
    fixture(dir.path());
    grimble(
        dir.path(),
        &["ack", "flow/f", "--reason", "initial", "--json"],
    );
    let lock = std::fs::read_to_string(dir.path().join("grimble.lock")).unwrap();
    write(
        dir.path(),
        "grimble.lock",
        &lock.replace("digest_scheme = 2", "digest_scheme = 1"),
    );
    let (code, _, err) = grimble(
        dir.path(),
        &["ack", "p/lib.rs::emit", "--reason", "stale", "--json"],
    );
    assert_eq!(code, 2, "usage error: {err}");
    let (code, env, _) = grimble(dir.path(), &["ack", "--all", "--reason", "bump", "--json"]);
    assert_eq!(code, 0, "{env}");
    assert_eq!(
        env["data"]["reattested"].as_array().unwrap().len(),
        3,
        "{env}"
    );
    let (_, env, _) = grimble(dir.path(), &["check", "--json"]);
    assert_eq!(rules(&env), Vec::<String>::new(), "{env}");
}

// frob:tests crates/grimble/src/ack.rs::Ack
#[test]
fn ack_dry_run_writes_nothing_and_a_node_target_is_refused() {
    let dir = tempfile::tempdir().unwrap();
    fixture(dir.path());
    let (code, env, _) = grimble(
        dir.path(),
        &["ack", "flow/f", "--reason", "try", "--dry-run", "--json"],
    );
    assert_eq!(code, 0, "{env}");
    assert!(!dir.path().join("grimble.lock").exists());
    let (code, _, _) = grimble(dir.path(), &["ack", "node/p", "--reason", "node", "--json"]);
    assert_ne!(code, 0);
}

// frob:ticket 01M3ZPNT7KCE66E6SAKV4E149M
// frob:tests crates/grimble/src/ack.rs::Ack
#[test]
fn ack_without_a_reason_is_a_usage_error_with_the_remedy() {
    let dir = tempfile::tempdir().unwrap();
    fixture(dir.path());
    let (code, env, err) = grimble(dir.path(), &["ack", "flow/f", "--json"]);
    assert_eq!(code, 2, "{env} {err}");
    assert_eq!(env["error"]["code"], "E-USAGE", "{env}");
    assert!(env.to_string().contains("--reason"), "{env}");
    assert!(!dir.path().join("grimble.lock").exists());
}

// frob:ticket 01M3ZPNT7KCE66E6SAKV4E149M
// frob:tests crates/grimble/src/ack.rs::Ack
#[test]
fn ack_honours_the_grimble_table_like_check() {
    let dir = tempfile::tempdir().unwrap();
    fixture(dir.path());
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"nowhere.grmb\"]\n",
    );
    let (code, env, _) = grimble(dir.path(), &["ack", "flow/f", "--reason", "x", "--json"]);
    assert_ne!(code, 0, "no declared model root means nothing binds: {env}");
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    let (code, env, err) = grimble(dir.path(), &["ack", "flow/f", "--reason", "x", "--json"]);
    assert_eq!(code, 0, "{env} {err}");
}

// frob:tests crates/grimble/src/ack.rs::Ack
#[test]
fn invalid_arguments_are_refused_before_the_repository_is_bound() {
    let dir = tempfile::tempdir().unwrap();
    fixture(dir.path());
    // A config that cannot load: binding would fail first and replace the argument error.
    write(dir.path(), "grimble.toml", "[grimble\n");
    let (code, env, err) = grimble(dir.path(), &["ack", "flow/f", "--json"]);
    assert_eq!(code, 2, "{env} {err}");
    assert!(
        env["error"]["message"]
            .as_str()
            .unwrap_or(&err)
            .contains("E-ACK-REASON"),
        "{env} {err}"
    );
    let (code, env, err) = grimble(dir.path(), &["ack", "--reason", "x", "--json"]);
    assert_eq!(code, 2, "{env} {err}");
    assert!(
        env["error"]["message"]
            .as_str()
            .unwrap_or(&err)
            .contains("E-ACK-EMPTY"),
        "{env} {err}"
    );
    // --all over a lock with nothing in it is E-ACK-EMPTY without binding either.
    let (code, env, err) = grimble(dir.path(), &["ack", "--all", "--reason", "x", "--json"]);
    assert_eq!(code, 2, "{env} {err}");
    assert!(
        env["error"]["message"]
            .as_str()
            .unwrap_or(&err)
            .contains("E-ACK-EMPTY"),
        "{env} {err}"
    );
}
