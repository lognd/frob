//! `milestone new`, `add`, `show` and `list`: acceptance, refusals and idempotency.

mod common;

use std::path::Path;
use std::process::Output;
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde_json::Value;

/// A trunk-mode repository with `frob init` run and one commit.
struct Repo {
    dir: tempfile::TempDir,
}

fn git(dir: &Path, args: &[&str]) {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|a| (*a).to_owned()).collect(),
        cwd: Some(dir.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(30),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 }).run(&spec).expect("run git");
    assert_eq!(
        out.status,
        Outcome::Exited(0),
        "git {args:?}: {}",
        out.stderr
    );
}

impl Repo {
    fn new() -> Self {
        let dir = tempfile::tempdir().expect("tempdir");
        git(dir.path(), &["init", "-q"]);
        git(dir.path(), &["symbolic-ref", "HEAD", "refs/heads/main"]);
        git(dir.path(), &["config", "user.name", "Test User"]);
        git(dir.path(), &["config", "user.email", "test@example.com"]);
        git(dir.path(), &["config", "core.autocrlf", "false"]);
        let repo = Self { dir };
        assert_eq!(code(&repo.run(&["--json", "init"])), 0);
        git(repo.dir.path(), &["add", "-A"]);
        git(repo.dir.path(), &["commit", "-q", "-m", "base"]);
        repo
    }

    fn run(&self, args: &[&str]) -> Output {
        common::frob_command()
            .current_dir(self.dir.path())
            .env_remove("FROB_LOG")
            .args(args)
            .output()
            .expect("run frob")
    }

    fn frob(&self, args: &[&str]) -> Output {
        let mut a = vec!["--json"];
        a.extend_from_slice(args);
        self.run(&a)
    }

    fn ok(&self, args: &[&str]) -> Value {
        let out = self.frob(args);
        assert_eq!(
            code(&out),
            0,
            "{args:?}: {}",
            String::from_utf8_lossy(&out.stdout)
        );
        json(&out)
    }

    fn ticket(&self, ty: &str) -> String {
        self.ok(&["ticket", "new", "--title", "t", "--type", ty])["data"]["id"]
            .as_str()
            .expect("id")
            .to_owned()
    }
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout)
        .unwrap_or_else(|e| panic!("not JSON ({e}): {}", String::from_utf8_lossy(&out.stdout)))
}

fn code(out: &Output) -> i32 {
    out.status.code().expect("exit code")
}

#[test]
fn new_creates_the_milestone_with_unbound_criteria() {
    let repo = Repo::new();
    let v = repo.ok(&[
        "milestone",
        "new",
        "0.532.0",
        "--goal",
        "Ship PM",
        "--target",
        "2026-11-01",
        "--criterion",
        "a, b stays whole",
        "--criterion",
        "second",
    ]);
    assert_eq!(v["verb"], "milestone.new");
    assert_eq!(v["already"], false);
    let m = &v["data"]["milestone"];
    assert_eq!(m["version"], "0.532.0");
    assert_eq!(m["goal"], "Ship PM");
    assert_eq!(m["target"], "2026-11-01");
    assert_eq!(m["state"], "open");
    let c = m["criteria"].as_array().expect("criteria");
    assert_eq!(c.len(), 2);
    assert_eq!(c[0]["text"], "a, b stays whole");
    assert_eq!(c[0]["position"], 1);
    assert_eq!(c[0]["bound"], false);
    assert_eq!(c[1]["bound"], false);
    let shown = repo.ok(&["milestone", "show", "0.532.0"]);
    assert_eq!(shown["data"]["milestone"]["criteria"], m["criteria"]);
}

#[test]
fn new_repeat_is_already_and_a_different_repeat_is_refused() {
    let repo = Repo::new();
    let args = [
        "milestone",
        "new",
        "0.532.0",
        "--goal",
        "g",
        "--criterion",
        "c",
    ];
    assert_eq!(repo.ok(&args)["already"], false);
    let again = repo.ok(&args);
    assert_eq!(again["already"], true);
    assert_eq!(again["data"]["commit"], Value::Null);
    let out = repo.frob(&["milestone", "new", "0.532.0", "--goal", "other"]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-MILESTONE-EXISTS");
    assert!(e["message"].as_str().expect("message").contains("goal"));
    assert_eq!(e["remedy"], "frob milestone show 0.532.0");
    assert_eq!(repo.ok(&["milestone", "list"])["data"]["count"], 1);
}

#[test]
fn non_semver_version_is_refused_with_a_remedy() {
    let repo = Repo::new();
    for bad in ["v1", "1.2", "01.2.3", "latest"] {
        let out = repo.frob(&["milestone", "new", bad, "--goal", "g"]);
        assert_eq!(
            code(&out),
            2,
            "{bad}: {}",
            String::from_utf8_lossy(&out.stdout)
        );
        let e = &json(&out)["error"];
        assert_eq!(e["code"], "E-MILESTONE-VERSION");
        assert!(
            e["remedy"]
                .as_str()
                .expect("remedy")
                .contains("MAJOR.MINOR.PATCH")
        );
    }
    assert_eq!(repo.ok(&["milestone", "list"])["data"]["count"], 0);
}

#[test]
fn add_lists_the_epic_in_show_and_a_repeat_is_already() {
    let repo = Repo::new();
    repo.ok(&["milestone", "new", "0.532.0", "--goal", "g"]);
    let epic = repo.ticket("epic");
    let first = repo.ok(&["milestone", "add", &epic, "0.532.0"]);
    assert_eq!(first["already"], false);
    let again = repo.ok(&["milestone", "add", &epic, "0.532.0"]);
    assert_eq!(again["already"], true);
    assert_eq!(again["data"]["events"].as_array().expect("events").len(), 0);
    let shown = repo.ok(&["milestone", "show", "0.532.0"]);
    let epics = shown["data"]["milestone"]["epics"]
        .as_array()
        .expect("epics");
    assert_eq!(epics.len(), 1);
    assert_eq!(epics[0]["id"], epic.as_str());
    assert_eq!(epics[0]["title"], "t");
}

#[test]
fn add_refuses_a_ticket_that_is_not_an_epic() {
    let repo = Repo::new();
    repo.ok(&["milestone", "new", "0.532.0", "--goal", "g"]);
    let task = repo.ticket("task");
    let out = repo.frob(&["milestone", "add", &task, "0.532.0"]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-MILESTONE-NOT-EPIC");
    assert!(e["remedy"].is_string());
    let shown = repo.ok(&["milestone", "show", "0.532.0"]);
    assert_eq!(
        shown["data"]["milestone"]["epics"]
            .as_array()
            .expect("epics")
            .len(),
        0
    );
}

#[test]
fn show_of_an_unknown_version_suggests_existing_ones() {
    let repo = Repo::new();
    repo.ok(&["milestone", "new", "0.532.0", "--goal", "g"]);
    let out = repo.frob(&["milestone", "show", "0.533.0"]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-MILESTONE-NOT-FOUND");
    assert!(
        e["message"]
            .as_str()
            .expect("message")
            .contains("did you mean 0.532.0")
    );
    assert_eq!(e["remedy"], "frob milestone show 0.532.0");
}

#[test]
fn schema_works_without_positionals() {
    let repo = Repo::new();
    for verb in ["new", "add", "show", "list"] {
        let out = repo.run(&["--schema", "milestone", verb]);
        assert_eq!(
            code(&out),
            0,
            "{verb}: {}",
            String::from_utf8_lossy(&out.stderr)
        );
        assert!(json(&out).is_object(), "{verb}");
    }
}

#[test]
fn text_view_shows_the_milestone() {
    let repo = Repo::new();
    repo.ok(&["milestone", "new", "0.532.0", "--goal", "Ship PM"]);
    let out = repo.run(&["--format", "text", "milestone", "show", "0.532.0"]);
    assert_eq!(code(&out), 0);
    let text = String::from_utf8_lossy(&out.stdout);
    assert!(
        text.contains("0.532.0") && text.contains("Ship PM"),
        "{text}"
    );
}

// frob:ticket 01M4069RACAQ8Z2C8APK0YKGNK

/// A repo with milestone 0.532.0 holding criteria `a`, `b`, `c`.
fn three() -> Repo {
    let repo = Repo::new();
    repo.ok(&[
        "milestone",
        "new",
        "0.532.0",
        "--goal",
        "g",
        "--criterion",
        "a",
        "--criterion",
        "b",
        "--criterion",
        "c",
    ]);
    repo
}

/// Offer `provider`/`reference` for criteria `accepts`; returns the raw output.
fn offer(repo: &Repo, provider: &str, reference: &str, accepts: &[&str]) -> Output {
    let mut args = vec![
        "milestone",
        "evidence",
        "add",
        "0.532.0",
        "--provider",
        provider,
        "--ref",
        reference,
    ];
    for n in accepts {
        args.push("--accepts");
        args.push(n);
    }
    repo.frob(&args)
}

/// The `state` of each criterion of 0.532.0 as `milestone show` prints it.
fn states(repo: &Repo) -> Vec<String> {
    repo.ok(&["milestone", "show", "0.532.0"])["data"]["milestone"]["criteria"]
        .as_array()
        .expect("criteria")
        .iter()
        .map(|c| c["state"].as_str().expect("state").to_owned())
        .collect()
}

#[test]
fn a_passing_measured_record_binds_and_show_names_the_evidence() {
    // frob:tests crates/frob-pm/src/milestone/criteria.rs::bindings
    // frob:tests crates/frob-evidence/src/verbs.rs::capture_args
    // frob:tests crates/frob-evidence/src/verbs.rs::CaptureArgs.from_matches
    let repo = three();
    assert_eq!(states(&repo), ["unbound", "unbound", "unbound"]);
    std::fs::write(repo.dir.path().join("proof.txt"), "proof").expect("write");
    let out = offer(&repo, "file", "proof.txt", &["2"]);
    assert_eq!(code(&out), 0, "{}", String::from_utf8_lossy(&out.stdout));
    let v = json(&out);
    let event = v["data"]["event"].as_str().expect("event").to_owned();
    assert_eq!(states(&repo), ["unbound", "bound", "unbound"]);
    let shown = repo.ok(&["milestone", "show", "0.532.0"]);
    let c = &shown["data"]["milestone"]["criteria"][1];
    assert_eq!(c["bound"], true);
    assert_eq!(c["bound_by"][0]["event"], event);
    assert_eq!(c["bound_by"][0]["provider"], "file");
    let list = repo.ok(&["milestone", "evidence", "list", "0.532.0"]);
    assert_eq!(list["data"]["count"], 1);
    assert_eq!(list["data"]["records"][0]["event"], event);
    assert_eq!(list["data"]["records"][0]["effective_status"], "measured");
}

#[test]
fn a_failing_record_does_not_bind_and_warns() {
    // frob:tests crates/frob-pm/src/milestone/criteria.rs::bindings
    // frob:tests crates/frob-evidence/src/verbs.rs::capture_args
    // frob:tests crates/frob-evidence/src/verbs.rs::CaptureArgs.from_matches
    // frob:tests crates/frob-evidence/src/verbs.rs::with_record_warnings
    let repo = three();
    let out = offer(
        &repo,
        "command",
        "git rev-parse --verify refs/tags/nope",
        &["1"],
    );
    assert_eq!(code(&out), 0);
    let v = json(&out);
    assert_eq!(v["data"]["record"]["passed"], false);
    assert!(
        !v["warnings"].as_array().expect("warnings").is_empty(),
        "{v}"
    );
    assert_eq!(states(&repo), ["unbound", "unbound", "unbound"]);
}

#[test]
fn the_latest_record_per_provider_ref_criterion_decides() {
    // frob:tests crates/frob-pm/src/milestone/criteria.rs::bindings
    // frob:tests crates/frob-evidence/src/verbs.rs::capture_args
    // frob:tests crates/frob-evidence/src/verbs.rs::CaptureArgs.from_matches
    let repo = three();
    let probe = "git rev-parse --verify refs/tags/probe";
    offer(&repo, "command", probe, &["1"]);
    assert_eq!(states(&repo)[0], "unbound");
    git(repo.dir.path(), &["tag", "probe"]);
    offer(&repo, "command", probe, &["1"]);
    assert_eq!(states(&repo)[0], "bound");
    git(repo.dir.path(), &["tag", "-d", "probe"]);
    offer(&repo, "command", probe, &["1"]);
    assert_eq!(states(&repo)[0], "unbound", "a later failure supersedes");
}

#[test]
fn removing_a_criterion_remaps_bound_evidence() {
    // frob:tests crates/frob-pm/src/milestone/criteria.rs::bindings
    // frob:tests crates/frob-evidence/src/verbs.rs::capture_args
    // frob:tests crates/frob-evidence/src/verbs.rs::CaptureArgs.from_matches
    let repo = three();
    std::fs::write(repo.dir.path().join("p.txt"), "p").expect("write");
    offer(&repo, "file", "p.txt", &["3"]);
    assert_eq!(states(&repo), ["unbound", "unbound", "bound"]);
    let removed = repo.ok(&["milestone", "criterion", "remove", "0.532.0", "1"]);
    let texts: Vec<&str> = removed["data"]["milestone"]["criteria"]
        .as_array()
        .expect("criteria")
        .iter()
        .map(|c| c["text"].as_str().expect("text"))
        .collect();
    assert_eq!(texts, ["b", "c"]);
    assert_eq!(states(&repo), ["unbound", "bound"], "evidence follows c");
    repo.ok(&["milestone", "criterion", "remove", "0.532.0", "2"]);
    assert_eq!(
        states(&repo),
        ["unbound"],
        "a removed criterion binds nothing"
    );
    let out = repo.frob(&["milestone", "criterion", "remove", "0.532.0", "9"]);
    assert_eq!(code(&out), 2, "{}", String::from_utf8_lossy(&out.stdout));
    assert_eq!(json(&out)["error"]["code"], "E-MILESTONE-CRITERION");
}

#[test]
fn the_ticket_allowlist_and_accepts_range_apply() {
    // frob:tests crates/frob-pm/src/milestone/criteria.rs::bindings
    // frob:tests crates/frob-evidence/src/verbs.rs::capture_args
    // frob:tests crates/frob-evidence/src/verbs.rs::CaptureArgs.from_matches
    let repo = three();
    let out = offer(&repo, "command", "rm -rf /", &["1"]);
    assert_ne!(code(&out), 0);
    assert_eq!(json(&out)["error"]["code"], "E-EVIDENCE-TOOL");
    let out = offer(&repo, "command", "git --version", &["4"]);
    assert_ne!(code(&out), 0);
    assert_eq!(json(&out)["error"]["code"], "E-EVIDENCE-ACCEPTS");
    let out = offer(&repo, "command", "git --version", &["0"]);
    assert_ne!(code(&out), 0);
    assert_eq!(
        repo.ok(&["milestone", "evidence", "list", "0.532.0"])["data"]["count"],
        0
    );
}

#[test]
fn criterion_add_is_idempotent_and_starts_unbound() {
    // frob:tests crates/frob-pm/src/milestone/criteria.rs::bindings
    // frob:tests crates/frob-evidence/src/verbs.rs::capture_args
    // frob:tests crates/frob-evidence/src/verbs.rs::CaptureArgs.from_matches
    let repo = three();
    let v = repo.ok(&["milestone", "criterion", "add", "0.532.0", "d"]);
    assert_eq!(v["already"], false);
    assert_eq!(states(&repo).len(), 4);
    let again = repo.ok(&["milestone", "criterion", "add", "0.532.0", "d"]);
    assert_eq!(again["already"], true);
    assert_eq!(states(&repo).len(), 4);
}

// frob:ticket 01M40K5J3B39TX30FC3PFY7RCD
#[test]
fn a_hyphen_led_ref_is_taken_whole_by_milestone_evidence_add() {
    // frob:tests crates/frob-evidence/src/verbs.rs::capture_args
    let repo = three();
    let out = offer(&repo, "command", "-p frob-cli -E 'test(x)'", &["1"]);
    // The value reached the provider (which refused the tool `-p`) instead of failing in clap.
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    assert_eq!(json(&out)["error"]["code"], "E-EVIDENCE-TOOL");
}

/// The severity `frob check` reports for `rule` in `repo`, if it fires.
fn check_severity(repo: &Repo, rule: &str) -> Option<String> {
    let out = repo.run(&["check", "--json", "--fail-on", "none"]);
    let v = json(&out);
    v["data"]["findings"]
        .as_array()
        .unwrap_or_else(|| panic!("no findings array: {v}"))
        .iter()
        .find(|f| f["rule"] == rule)
        .map(|f| f["severity"].as_str().expect("severity").to_owned())
}

// frob:ticket 01M41B2PD4NAV8VACA13750GWB
// frob:tests apply_strict
#[test]
fn pm_strict_escalates_pm001_to_error() {
    let repo = Repo::new();
    repo.ok(&["milestone", "new", "0.532.0", "--goal", "g"]);
    let _ = repo.ticket("epic");
    assert_eq!(check_severity(&repo, "PM001").as_deref(), Some("warning"));
    let toml = repo.dir.path().join("frob.toml");
    let text = std::fs::read_to_string(&toml).expect("frob.toml");
    assert!(text.contains("strict = false"), "{text}");
    std::fs::write(&toml, text.replace("strict = false", "strict = true")).expect("write");
    assert_eq!(check_severity(&repo, "PM001").as_deref(), Some("error"));
}

// frob:ticket 01M41DQF8CJG567CJ1AWETTCK4
// frob:tests open_ledger
#[test]
fn pm001_fires_on_a_milestone_with_no_tickets() {
    let repo = Repo::new();
    repo.ok(&["milestone", "new", "0.1.0", "--goal", "g"]);
    assert_eq!(check_severity(&repo, "PM001").as_deref(), Some("warning"));
}
