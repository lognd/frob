//! Per-verb auto-refresh policy: `doable` probes in the foreground, reads kick a background refresh, CI turns both off.
// frob:ticket 01M5CW04GHM970H5KR4EV5KK0X

use crate::common;

use std::path::Path;
use std::time::Duration;

use serde_json::Value;

fn git(dir: &Path, args: &[&str]) {
    let st = std::process::Command::new("git")
        .args(args)
        .current_dir(dir)
        .env("GIT_AUTHOR_NAME", "t")
        .env("GIT_AUTHOR_EMAIL", "t@t")
        .env("GIT_COMMITTER_NAME", "t")
        .env("GIT_COMMITTER_EMAIL", "t@t")
        .status()
        .expect("git");
    assert!(st.success(), "git {args:?}");
}

fn frob(dir: &Path, ci: bool, args: &[&str]) -> (i32, Value) {
    let mut cmd = common::frob_command();
    cmd.current_dir(dir)
        .env_remove("FROB_LOG")
        .env_remove("FROB_SYNC_INNER")
        .arg("--json")
        .args(args);
    if ci {
        cmd.env("CI", "true");
    } else {
        cmd.env_remove("CI");
    }
    let out = cmd.output().expect("run frob");
    let json = serde_json::from_slice(&out.stdout).unwrap_or(Value::Null);
    (out.status.code().unwrap_or(-1), json)
}

/// A clone on `main` with a local `origin` that has `main`.
fn clone_with_origin() -> (tempfile::TempDir, tempfile::TempDir) {
    let origin = common::git_repo();
    git(
        origin.path(),
        &["commit", "-q", "--allow-empty", "-m", "c1"],
    );
    let clone = common::git_repo();
    git(clone.path(), &["commit", "-q", "--allow-empty", "-m", "c1"]);
    let url = gob_path::Shown::of(origin.path()).to_string();
    git(clone.path(), &["remote", "add", "origin", &url]);
    std::fs::write(
        clone.path().join("frob.toml"),
        "[tickets]\nref = \"main\"\n",
    )
    .expect("toml");
    (origin, clone)
}

fn state_file(clone: &Path) -> std::path::PathBuf {
    clone.join(".git").join("frob").join("refresh.toml")
}

fn warnings(v: &Value) -> String {
    v["warnings"].to_string()
}

// frob:tests crates/frob/src/ticket/read.rs::Doable
#[test]
fn doable_probes_in_the_foreground() {
    let (_origin, clone) = clone_with_origin();
    let (code, v) = frob(clone.path(), false, &["ticket", "doable"]);
    assert_eq!(code, 0, "{v}");
    assert!(state_file(clone.path()).exists(), "foreground probe ran");
    let (_, v) = frob(clone.path(), false, &["refresh", "--status"]);
    assert_eq!(v["data"]["status"], "frob:ok", "{v}");
}

/// Break the remote and rewrite the cached probe times to `stamp(last_ok_at)` (unix seconds).
fn offline_with_view_at(origin: &Path, clone: &Path, stamp: impl Fn(i64) -> i64) {
    std::fs::remove_dir_all(origin.join(".git")).expect("rm");
    let path = state_file(clone);
    let text = std::fs::read_to_string(&path).expect("state");
    let ok_at = text
        .lines()
        .find_map(|l| l.strip_prefix("last_ok_at = "))
        .and_then(|v| v.trim().parse::<i64>().ok())
        .expect("last_ok_at");
    let stamp = stamp(ok_at);
    let old = text
        .lines()
        .map(|l| match l.split_once(" = ") {
            Some((k @ ("probed_at" | "last_ok_at" | "next_attempt_at"), _)) => {
                format!("{k} = {stamp}")
            }
            _ => l.to_owned(),
        })
        .collect::<Vec<_>>()
        .join("\n");
    std::fs::write(&path, old).expect("age the state");
}

// frob:ticket 01M5D9NM6D3DSGD980M52CRMYV
// frob:tests crates/frob/src/ticket/read.rs::Doable
#[test]
fn doable_warns_when_offline_and_the_view_is_old() {
    let (origin, clone) = clone_with_origin();
    frob(clone.path(), false, &["refresh"]);
    offline_with_view_at(origin.path(), clone.path(), |ok| ok - 7200);
    // A probe that finds the per-clone refresh lock held (a straggling refresh under CI load)
    // leaves the aged state untouched and reports STALE; retry until the probe actually runs.
    let (code, v) = (0..40)
        .map(|_| {
            let r = frob(clone.path(), false, &["ticket", "doable"]);
            if warnings(&r.1).contains("W-SYNC-STALE") {
                std::thread::sleep(Duration::from_millis(250));
            }
            r
        })
        .find(|(_, v)| !warnings(v).contains("W-SYNC-STALE"))
        .expect("the probe never ran: refresh lock stayed busy");
    assert_eq!(code, 0, "{v}");
    assert!(warnings(&v).contains("W-SYNC-OFFLINE"), "{v}");
    assert_eq!(v["freshness"]["state"], "degraded", "{v}");
    assert!(
        v["freshness"]["age_secs"].as_i64().expect("age") >= 7200,
        "{v}"
    );
}

// frob:ticket 01M5D9NM6D3DSGD980M52CRMYV
// frob:tests crates/frob/src/ticket/mod.rs::refuse_if_stale
#[test]
fn doable_refuses_e_sync_stale_when_offline_and_the_view_is_ancient() {
    let (origin, clone) = clone_with_origin();
    frob(clone.path(), false, &["refresh"]);
    offline_with_view_at(origin.path(), clone.path(), |_| 1);
    let (code, v) = frob(clone.path(), false, &["ticket", "doable"]);
    assert_ne!(code, 0, "{v}");
    assert_eq!(v["error"]["code"], "E-SYNC-STALE", "{v}");
    let (code, v) = frob(clone.path(), true, &["ticket", "doable"]);
    assert_eq!(code, 0, "CI tolerates a stale view: {v}");
}

// frob:ticket 01M5D5PZVVDVE6ZJ2Z9CERYYYA
// frob:tests crates/frob/src/ticket/read.rs::mark_may_be_taken
#[test]
fn doable_marks_rows_may_be_taken_when_a_stale_view_is_tolerated() {
    let (origin, clone) = clone_with_origin();
    frob(clone.path(), false, &["refresh"]);
    let (code, v) = frob(
        clone.path(),
        true,
        &["ticket", "new", "--title", "t", "--scope", "a/**"],
    );
    assert_eq!(code, 0, "{v}");
    let (_, fresh) = frob(clone.path(), true, &["ticket", "doable"]);
    let rows = fresh["data"]["tickets"].as_array().expect("rows");
    assert!(!rows.is_empty(), "the new ticket is doable: {fresh}");
    assert!(
        rows.iter().all(|r| r.get("may_be_taken").is_none()),
        "{fresh}"
    );
    offline_with_view_at(origin.path(), clone.path(), |_| 1);
    let (code, v) = frob(clone.path(), true, &["ticket", "doable"]);
    assert_eq!(code, 0, "{v}");
    let rows = v["data"]["tickets"].as_array().expect("rows");
    assert!(rows.iter().all(|r| r["may_be_taken"] == true), "{v}");
}

// frob:ticket 01M5D5PZVVDVE6ZJ2Z9CERYYYA
// frob:tests crates/frob/src/ticket/read.rs::List
// frob:tests crates/frob/src/ticket/read.rs::Show
#[test]
fn list_and_show_carry_the_freshness_field() {
    let (origin, clone) = clone_with_origin();
    frob(clone.path(), false, &["refresh"]);
    let (_, v) = frob(
        clone.path(),
        true,
        &["ticket", "new", "--title", "t", "--scope", "a/**"],
    );
    let id = v["data"]["id"].as_str().expect("id").to_owned();
    offline_with_view_at(origin.path(), clone.path(), |ok| ok - 7200);
    let (code, v) = frob(clone.path(), true, &["ticket", "list"]);
    assert_eq!(code, 0, "{v}");
    assert_eq!(v["freshness"]["state"], "stale", "{v}");
    let (code, v) = frob(clone.path(), true, &["ticket", "show", &id]);
    assert_eq!(code, 0, "{v}");
    assert_eq!(v["freshness"]["state"], "stale", "{v}");
}

// frob:tests crates/frob/src/ticket/read.rs::Doable
#[test]
fn ci_disables_the_foreground_probe_and_the_kick() {
    let (_origin, clone) = clone_with_origin();
    let (code, v) = frob(clone.path(), true, &["ticket", "doable"]);
    assert_eq!(code, 0, "{v}");
    let (code, v) = frob(clone.path(), true, &["ticket", "list"]);
    assert_eq!(code, 0, "{v}");
    // Give a (wrongly) spawned detached refresh time to write its state file.
    std::thread::park_timeout(Duration::from_millis(500));
    assert!(!state_file(clone.path()).exists(), "CI never syncs");
}

// frob:tests crates/frob/src/ticket/mod.rs::open
#[test]
fn reads_kick_a_background_refresh() {
    let (_origin, clone) = clone_with_origin();
    let (code, v) = frob(clone.path(), false, &["ticket", "list"]);
    assert_eq!(code, 0, "{v}");
    // Poll for the detached refresh's state file, bounded at 100 x 100ms.
    for _ in 0..100 {
        if state_file(clone.path()).exists() {
            break;
        }
        std::thread::park_timeout(Duration::from_millis(100));
    }
    assert!(state_file(clone.path()).exists(), "background refresh ran");
}

// frob:ticket 01M713HQC2TF14B5F316HMYVT3
// frob:tests crates/frob-worktree/src/verbs.rs::Opened.gate_claim
#[test]
fn work_refuses_e_sync_stale_when_offline_and_the_view_is_ancient() {
    let (origin, clone) = clone_with_origin();
    frob(clone.path(), false, &["refresh"]);
    let (_, v) = frob(
        clone.path(),
        true,
        &["ticket", "new", "--title", "t", "--scope", "a/**"],
    );
    let id = v["data"]["id"].as_str().expect("id").to_owned();
    offline_with_view_at(origin.path(), clone.path(), |_| 1);
    let (code, v) = frob(clone.path(), false, &["work", &id, "--here"]);
    assert_ne!(code, 0, "{v}");
    assert_eq!(v["error"]["code"], "E-SYNC-STALE", "{v}");
    let (_, v) = frob(clone.path(), true, &["work", &id, "--here"]);
    assert_ne!(v["error"]["code"], "E-SYNC-STALE", "CI tolerates it: {v}");
}

// frob:ticket 01M5DBVTN06Y1MBT6EDFKR7TYT
// frob:tests crates/frob-ledger/src/freshness.rs::sync_then_gate
#[test]
fn work_offline_with_a_reason_skips_the_stale_gate_and_records_it() {
    let (origin, clone) = clone_with_origin();
    frob(clone.path(), false, &["refresh"]);
    let (_, v) = frob(
        clone.path(),
        true,
        &["ticket", "new", "--title", "t", "--scope", "a/**"],
    );
    let id = v["data"]["id"].as_str().expect("id").to_owned();
    offline_with_view_at(origin.path(), clone.path(), |_| 1);
    let (code, v) = frob(
        clone.path(),
        false,
        &["work", &id, "--here", "--offline", "--reason", "on a plane"],
    );
    assert_ne!(v["error"]["code"], "E-SYNC-STALE", "{v}");
    assert_eq!(code, 0, "{v}");
    assert!(warnings(&v).contains("on a plane"), "{v}");
    assert!(warnings(&v).contains("W-SYNC-OFFLINE"), "{v}");
}

// frob:ticket 01M5DBVTN06Y1MBT6EDFKR7TYT
// frob:tests crates/frob-worktree/src/verbs.rs::flag_reasons
#[test]
fn work_offline_without_a_reason_is_a_usage_error() {
    let (_origin, clone) = clone_with_origin();
    let (code, v) = frob(clone.path(), false, &["work", "T-0001", "--offline"]);
    assert_eq!(code, 2, "{v}");
}

// frob:ticket 01M5DBVTN06Y1MBT6EDFKR7TYT
// frob:tests crates/frob-ledger/src/freshness.rs::sync_then_gate
#[test]
fn work_syncs_in_the_foreground_before_claiming() {
    let (_origin, clone) = clone_with_origin();
    let (_, v) = frob(
        clone.path(),
        true,
        &["ticket", "new", "--title", "t", "--scope", "a/**"],
    );
    let id = v["data"]["id"].as_str().expect("id").to_owned();
    assert!(!state_file(clone.path()).exists());
    let (code, v) = frob(clone.path(), false, &["work", &id, "--here"]);
    assert_eq!(code, 0, "{v}");
    assert!(state_file(clone.path()).exists(), "work probed first");
}

// frob:ticket 01M713HQC2TF14B5F316HMYVT3
// frob:tests crates/frob-land/src/verb.rs::gate_land
#[test]
fn land_refuses_e_sync_stale_when_offline_and_the_view_is_ancient() {
    let (origin, clone) = clone_with_origin();
    frob(clone.path(), false, &["refresh"]);
    offline_with_view_at(origin.path(), clone.path(), |_| 1);
    let (code, v) = frob(clone.path(), false, &["land", "T-0001"]);
    assert_ne!(code, 0, "{v}");
    assert_eq!(v["error"]["code"], "E-SYNC-STALE", "{v}");
    let (_, v) = frob(clone.path(), true, &["land", "T-0001"]);
    assert_ne!(v["error"]["code"], "E-SYNC-STALE", "CI tolerates it: {v}");
}

// frob:ticket 01M5D5PZS2AHFT7Z8C2QX7NQN7
// frob:tests crates/frob-land/src/verb.rs::gate_land
#[test]
fn land_refuses_e_sync_stale_unless_offline_with_a_reason() {
    let (origin, clone) = clone_with_origin();
    frob(clone.path(), false, &["refresh"]);
    offline_with_view_at(origin.path(), clone.path(), |_| 1);
    let (code, v) = frob(clone.path(), false, &["land", "T-0001"]);
    assert_ne!(code, 0, "{v}");
    assert_eq!(v["error"]["code"], "E-SYNC-STALE", "{v}");
    let (_, v) = frob(
        clone.path(),
        false,
        &["land", "T-0001", "--offline", "--reason", "on a plane"],
    );
    assert_ne!(v["error"]["code"], "E-SYNC-STALE", "{v}");
    let (code, v) = frob(clone.path(), false, &["land", "T-0001", "--offline"]);
    assert_eq!(code, 2, "{v}");
}
