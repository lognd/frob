//! End-to-end tests of the `frob` binary and the in-process root.

use std::path::Path;
use std::process::Output;

use assert_cmd::Command;
use insta::{assert_json_snapshot, assert_snapshot};
use serde_json::Value;

mod common;

/// A fresh git repository with a fixed local owner identity: init writes the email as `[evidence] attesters`, so snapshots must not depend on the machine's git config.
fn repo() -> tempfile::TempDir {
    common::git_repo()
}

fn frob(cwd: &Path, args: &[&str]) -> Output {
    Command::cargo_bin("frob")
        .expect("frob binary")
        .current_dir(cwd)
        .env_remove("FROB_LOG")
        .args(args)
        .output()
        .expect("run frob")
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout).unwrap_or_else(|e| {
        panic!(
            "stdout is not JSON ({e}): {}",
            String::from_utf8_lossy(&out.stdout)
        )
    })
}

fn code(out: &Output) -> i32 {
    out.status.code().expect("exit code")
}

#[test]
fn doctor_piped_is_json_envelope_even_with_cfg001() {
    let dir = repo();
    let out = frob(dir.path(), &["doctor"]);
    assert_eq!(code(&out), 0);
    let v = json(&out);
    assert_eq!(v["ok"], true);
    assert_eq!(v["verb"], "doctor");
    let findings = v["findings"].as_array().expect("findings");
    assert_eq!(findings.len(), 32, "one CFG001 per materialized knob");
    assert!(findings.iter().all(|f| f["rule"] == "CFG001"));
    assert_json_snapshot!("doctor_fresh_repo", v, {
        ".data.toolchain.rustc" => "[version]",
        ".data.toolchain.cargo" => "[version]",
        ".data.cache.dir" => "[path]",
        ".data.config.path" => "[path]",
        ".data.git.root" => "[path]",
        ".data.git.branch" => "[branch]",
        ".data.ledger.error" => "[error]",
        ".data.siblings" => "[environment]",
        ".data.gc.usage[].bytes" => "[bytes]",
    });
}

#[test]
fn doctor_languages_prints_fidelity_precisions_and_f0_extensions() {
    let dir = repo();
    std::fs::write(dir.path().join("a.rs"), "fn main() {}\n").expect("write");
    std::fs::write(dir.path().join("b.md"), "# B\n").expect("write");
    std::fs::write(dir.path().join("data.csv"), "1,2\n").expect("write");
    std::fs::write(dir.path().join("Makefile"), "all:\n").expect("write");
    let out = frob(dir.path(), &["doctor", "--languages"]);
    assert_eq!(code(&out), 0);
    let v = json(&out);
    let langs = &v["data"]["languages"];
    let row = |name: &str| {
        langs["adapters"]
            .as_array()
            .expect("adapters")
            .iter()
            .find(|r| r["language"] == name)
            .unwrap_or_else(|| panic!("no adapter row {name}"))
            .clone()
    };
    assert_eq!(row("rust")["fidelity"], "F3");
    assert_eq!(row("rust")["files"], 1);
    assert_eq!(row("markdown")["fidelity"], "F4");
    assert_eq!(row("opaque")["fidelity"], "F0");
    let apply = row("rust")["capabilities"]
        .as_array()
        .expect("capabilities")
        .iter()
        .find(|c| c["capability"] == "apply_targets")
        .expect("apply_targets")
        .clone();
    assert_eq!(apply["precision"], "by-name-in-crate (May)");
    let un = langs["unadapted"].as_array().expect("unadapted");
    let exts: Vec<&str> = un
        .iter()
        .map(|r| r["extension"].as_str().expect("ext"))
        .collect();
    assert!(
        exts.contains(&".csv") && exts.contains(&"(none)"),
        "{exts:?}"
    );
    assert!(un.iter().all(|r| r["fidelity"] == "F0"));
    // Without the flag the report is absent.
    let plain = json(&frob(dir.path(), &["doctor"]));
    assert!(plain["data"].get("languages").is_none());
}

#[test]
fn doctor_outside_a_repo_still_succeeds() {
    let dir = tempfile::tempdir().expect("tempdir");
    let out = frob(
        dir.path(),
        &["doctor", "--cwd", dir.path().to_str().expect("utf8")],
    );
    assert_eq!(code(&out), 0);
    let v = json(&out);
    assert_eq!(v["data"]["git"]["discovered"], false);
    assert_eq!(v["data"]["ledger"]["reachable"], false);
}

#[test]
fn init_twice_second_is_already_and_changes_nothing() {
    let dir = repo();
    let first = frob(dir.path(), &["init"]);
    assert_eq!(
        code(&first),
        0,
        "{}",
        String::from_utf8_lossy(&first.stdout)
    );
    let v1 = json(&first);
    assert_eq!(v1["already"], false);
    assert_eq!(v1["data"]["merge_driver"]["changed"], true);

    let snapshot = |p: &str| std::fs::read_to_string(dir.path().join(p)).unwrap_or_default();
    let (toml1, ignore1, attrs1) = (
        snapshot("frob.toml"),
        snapshot(".gitignore"),
        snapshot(".gitattributes"),
    );
    assert_snapshot!("init_frob_toml", toml1);
    assert_eq!(ignore1, ".frob/\n");
    assert_eq!(
        attrs1,
        "tickets/**/ticket.md merge=frob-ledger\n\
         tickets/_milestones/*/milestone.md merge=frob-ledger\n\
         tickets/_cycles/*/cycle.md merge=frob-ledger\n"
    );

    let second = frob(dir.path(), &["init"]);
    assert_eq!(code(&second), 0);
    let v2 = json(&second);
    assert_eq!(v2["already"], true);
    assert_eq!(v2["data"]["config"]["added"], serde_json::json!([]));
    assert_eq!(toml1, snapshot("frob.toml"));
    assert_eq!(ignore1, snapshot(".gitignore"));
    assert_eq!(attrs1, snapshot(".gitattributes"));

    // After init, doctor reports no missing knobs and no findings.
    let doc = json(&frob(dir.path(), &["doctor"]));
    assert_eq!(doc["data"]["config"]["missing_knobs"], 0);
    assert_eq!(doc["findings"], serde_json::json!([]));
}

#[test]
fn init_dry_run_writes_nothing() {
    let dir = repo();
    let out = frob(dir.path(), &["init", "--dry-run"]);
    assert_eq!(code(&out), 0);
    let v = json(&out);
    assert_eq!(v["already"], false);
    assert_eq!(v["data"]["config"]["dry_run"], true);
    assert!(!dir.path().join("frob.toml").exists());
    assert!(!dir.path().join(".gitignore").exists());
}

#[test]
fn init_outside_a_repo_is_a_refusal() {
    let dir = tempfile::tempdir().expect("tempdir");
    let out = frob(
        dir.path(),
        &["init", "--cwd", dir.path().to_str().expect("utf8")],
    );
    assert_eq!(code(&out), 3);
    let v = json(&out);
    assert_eq!(v["ok"], false);
    assert_eq!(v["error"]["code"], "E-NOT-A-REPO");
    assert_eq!(v["error"]["remedy"], "git init");
}

#[test]
fn schema_flag_prints_the_verb_schema() {
    let dir = repo();
    let out = frob(dir.path(), &["--schema", "doctor"]);
    assert_eq!(code(&out), 0);
    let v = json(&out);
    assert!(v["properties"]["toolchain"].is_object(), "{v}");
    assert_json_snapshot!("doctor_schema", v);
}

#[test]
fn schema_verb_dumps_envelope_and_config() {
    let dir = repo();
    let out = frob(dir.path(), &["schema"]);
    assert_eq!(code(&out), 0);
    let v = json(&out);
    assert!(v["data"]["envelope"].is_object());
    assert!(v["data"]["config"]["properties"]["tickets"].is_object());
}

#[test]
fn unknown_verb_exits_2_with_a_suggestion() {
    let dir = repo();
    let out = frob(dir.path(), &["docter"]);
    assert_eq!(code(&out), 2);
    let v = json(&out);
    assert_eq!(v["error"]["code"], "E-USAGE");
    assert_eq!(v["error"]["remedy"], "frob doctor");
}

#[test]
fn text_format_goes_to_stdout_and_errors_to_stderr() {
    let dir = repo();
    let out = frob(
        dir.path(),
        &["--format", "text", "--color", "never", "doctor"],
    );
    assert_eq!(code(&out), 0);
    let text = String::from_utf8_lossy(&out.stdout);
    assert!(text.starts_with("doctor: ok\n"), "{text}");
    assert!(!text.contains('\u{1b}'), "no ANSI with --color never");
    assert!(text.contains("CFG001"));

    let bad = frob(dir.path(), &["--text", "docter"]);
    assert_eq!(code(&bad), 2);
    assert!(bad.stdout.is_empty());
    assert!(String::from_utf8_lossy(&bad.stderr).starts_with("error[E-USAGE]"));
}

#[test]
fn json_flag_is_an_alias_and_conflicts_with_text() {
    let dir = repo();
    let out = frob(dir.path(), &["--json", "doctor"]);
    assert_eq!(code(&out), 0);
    assert_eq!(json(&out)["ok"], true);
    let both = frob(dir.path(), &["--json", "--text", "doctor"]);
    assert_eq!(code(&both), 2);
}

#[test]
fn dry_run_is_rejected_on_verbs_that_do_not_opt_in() {
    let dir = repo();
    assert_eq!(code(&frob(dir.path(), &["doctor", "--dry-run"])), 2);
}

#[test]
fn config_show_effective_reports_provenance() {
    let dir = repo();
    std::fs::write(dir.path().join("frob.toml"), "[git]\ncas_retries = 9\n").expect("write");
    let out = frob(dir.path(), &["config", "show", "--effective"]);
    assert_eq!(code(&out), 0, "{}", String::from_utf8_lossy(&out.stdout));
    let v = json(&out);
    let tables = v["data"]["tables"].as_array().expect("tables");
    let git = tables
        .iter()
        .find(|t| t["table"] == "git")
        .expect("git table");
    assert_eq!(git["keys"][0]["value"], 9);
    assert_eq!(git["keys"][0]["provenance"], "file");
    let check = tables
        .iter()
        .find(|t| t["table"] == "check")
        .expect("check table");
    assert_eq!(check["keys"][0]["value"], "error");
    assert_eq!(check["keys"][0]["provenance"], "default");
}

#[test]
fn config_show_rejects_unknown_keys_with_a_suggestion() {
    let dir = repo();
    std::fs::write(dir.path().join("frob.toml"), "[git]\ncas_retrys = 9\n").expect("write");
    let out = frob(dir.path(), &["config", "show", "--effective"]);
    assert_eq!(code(&out), 3);
    assert!(
        json(&out)["error"]["message"]
            .as_str()
            .expect("msg")
            .contains("cas_retries")
    );
}

#[test]
fn config_sync_adds_missing_knobs_once() {
    let dir = repo();
    std::fs::write(
        dir.path().join("frob.toml"),
        "# mine\n[git]\ncas_retries = 9\n",
    )
    .expect("write");
    let first = json(&frob(dir.path(), &["config", "sync"]));
    assert_eq!(first["already"], false);
    assert_eq!(
        first["data"]["added"],
        serde_json::json!([
            "check.fail_on",
            "check.fail_on_unresolved",
            "check.base",
            "check.sibling_timeout_secs",
            "check.require_siblings",
            "compute.public_signatures",
            "compute.effects",
            "compute.dynamic_calls",
            "compute.expansion_steps",
            "compute.normalization",
            "compute.notebook_order",
            "directives.namespaces",
            "evidence.attesters",
            "pm.strict",
            "pm.pull",
            "pm.ready_min",
            "pm.ready_requires",
            "pm.done_requires",
            "pm.cycle_days",
            "pm.min_history",
            "pm.capacity_k",
            "pm.classes.expedite_max",
            "pm.classes.intangible_share",
            "pm.wip.in_progress_per_identity",
            "pm.wip.in_progress",
            "release.require_ci",
            "release.tag",
            "release.products",
            "release.preview",
            "tickets.ref",
            "tickets.ref_mode"
        ])
    );
    let text = std::fs::read_to_string(dir.path().join("frob.toml")).expect("read");
    assert!(text.starts_with("# mine\n"));
    assert!(text.contains("cas_retries = 9"));
    let second = json(&frob(dir.path(), &["config", "sync"]));
    assert_eq!(second["already"], true);
}

#[test]
fn in_process_root_matches_the_binary_contract() {
    let dir = repo();
    let cli = frob_cli::cli();
    let (exit, stdout, stderr) = gob_cli::run_for_test(&cli, &["init"], dir.path());
    assert_eq!(exit, 0, "{stderr}");
    let v: Value = serde_json::from_str(&stdout).expect("json");
    assert_eq!(v["verb"], "init");
    let (exit, _, stderr) = gob_cli::run_for_test(&cli, &["nope"], dir.path());
    assert_eq!(exit, 2);
    assert!(stderr.is_empty(), "json mode keeps errors off stderr");
}

#[test]
fn every_verb_is_in_the_command_inventory() {
    let verbs: Vec<_> = gob_cli::all_commands().map(|m| m.verb).collect();
    for v in [
        "doctor",
        "init",
        "config show",
        "config sync",
        "schema",
        "ticket new",
        "ticket show",
        "ticket list",
        "ticket update",
        "ticket link",
        "ticket unlink",
        "ticket comment",
        "ticket close",
        "ticket drop",
        "ticket reopen",
        "ticket doable",
        "ticket brief",
        "ticket doctor",
        "merge-driver",
        "lease list",
        "lease widen",
        "ticket contention",
        "work",
        "start",
        "requeue",
        "ticket evidence add",
        "ticket evidence list",
        "ticket evidence fetch",
        "test",
        "ack",
        "graph why",
        "graph affects",
    ] {
        assert!(verbs.contains(&v), "{v} missing from {verbs:?}");
    }
}
