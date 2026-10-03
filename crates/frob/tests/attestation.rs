//! Attestation evidence through the CLI: who may attest, from where, and how it shows.
//!
//! A subprocess never has a terminal, so the binary-level tests prove the refusals; the
//! success paths run in process through the presence seam (`Presence`), never a global.

use std::path::Path;
use std::process::Output;
use std::time::Duration;

use assert_cmd::Command;
use frob_cli::milestone_evidence_cmd::add_evidence;
use frob_evidence::attestation::{Presence, Request, attest};
use frob_evidence::verbs::CaptureArgs;
use frob_evidence::{Provider, Workspace};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde_json::Value;

// frob:ticket 01M40AKKXBN7K30090V7KQSA8Z

fn git(dir: &Path, args: &[&str]) -> String {
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
    out.stdout.trim().to_owned()
}

/// A trunk-mode repository, `frob init` run, one commit, milestone 0.532.0 with criteria `a`, `b`.
struct Repo {
    dir: tempfile::TempDir,
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
        assert_eq!(code(&repo.frob(&["init"])), 0);
        git(repo.dir.path(), &["add", "-A"]);
        git(repo.dir.path(), &["commit", "-q", "-m", "base"]);
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
        ]);
        repo
    }

    fn frob_env(&self, args: &[&str], env: &[(&str, &str)]) -> Output {
        let mut cmd = Command::cargo_bin("frob").expect("frob binary");
        cmd.current_dir(self.dir.path())
            .env_remove("FROB_LOG")
            .env_remove("CLAUDECODE")
            .arg("--json")
            .args(args);
        for (k, v) in env {
            cmd.env(k, v);
        }
        cmd.output().expect("run frob")
    }

    fn frob(&self, args: &[&str]) -> Output {
        self.frob_env(args, &[])
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

    fn set_attesters(&self, list: &str) {
        let path = self.dir.path().join("frob.toml");
        let text = std::fs::read_to_string(&path).expect("read frob.toml");
        let out: Vec<String> = text
            .lines()
            .map(|l| {
                if l.starts_with("attesters") {
                    format!("attesters = {list}")
                } else {
                    l.to_owned()
                }
            })
            .collect();
        std::fs::write(path, out.join("\n") + "\n").expect("write frob.toml");
    }

    fn workspace(&self) -> Workspace {
        Workspace::open(self.dir.path()).expect("workspace")
    }
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout)
        .unwrap_or_else(|e| panic!("not JSON ({e}): {}", String::from_utf8_lossy(&out.stdout)))
}

fn code(out: &Output) -> i32 {
    out.status.code().expect("exit code")
}

fn args(statement: &str, facts: &[&str], accepts: &[usize]) -> CaptureArgs {
    CaptureArgs {
        provider: Provider::Attestation,
        reference: String::new(),
        accepts: accepts.to_vec(),
        statement: Some(statement.to_owned()),
        facts: facts.iter().map(|f| (*f).to_owned()).collect(),
    }
}

fn criterion(repo: &Repo, n: usize) -> Value {
    repo.ok(&["milestone", "show", "0.532.0"])["data"]["milestone"]["criteria"][n - 1].clone()
}

#[test]
fn init_materializes_the_owner_as_the_attester() {
    // frob:tests crates/frob-evidence/src/config.rs::EvidenceTable
    let repo = Repo::new();
    let text = std::fs::read_to_string(repo.dir.path().join("frob.toml")).expect("frob.toml");
    assert!(text.contains("[evidence]"), "{text}");
    assert!(
        text.contains(r#"attesters = ["test@example.com"]"#),
        "{text}"
    );
}

#[test]
fn an_attester_at_a_terminal_binds_a_milestone_criterion_and_show_marks_it() {
    // frob:tests crates/frob/src/milestone_evidence_cmd.rs::add_evidence
    // frob:ticket 01M415HTAQ7YSKXW09DG39YHBW
    // frob:tests crates/frob/src/milestone_cmd.rs::MilestoneView
    let repo = Repo::new();
    let head = git(repo.dir.path(), &["rev-parse", "HEAD"]);
    let ws = repo.workspace();
    let out = add_evidence(
        &ws,
        "0.532.0",
        &args(
            "two outside repos managed for two cycles, \"no loss\"\nand done",
            &["https://example.com/log", &head[..8]],
            &[1],
        ),
        &Presence::interactive(),
    )
    .expect("attests");
    assert!(
        out.warnings
            .iter()
            .any(|w| w.contains("attestation, not a tool measurement")),
        "{:?}",
        out.warnings
    );
    let c = criterion(&repo, 1);
    assert_eq!(c["bound"], true);
    assert_eq!(c["attested"], true);
    assert_eq!(c["bound_by"][0]["provider"], "attestation");
    let label = c["bound_by"][0]["label"].as_str().expect("label");
    assert!(
        label.starts_with("[attested by test@example.com: \""),
        "{label}"
    );
    assert!(
        label.is_ascii() && !label.contains('\n'),
        "escaped: {label}"
    );
    assert_eq!(
        c["bound_by"][0]["attestation"]["statement"],
        "two outside repos managed for two cycles, \"no loss\"\nand done"
    );
    assert_eq!(criterion(&repo, 2)["attested"], false);
    let list = repo.ok(&["milestone", "evidence", "list", "0.532.0"]);
    assert_eq!(list["data"]["records"][0]["effective_status"], "measured");
    assert_eq!(list["data"]["records"][0]["label"], label);
    let status = repo.ok(&["release", "status", "0.532.0"]);
    let glance = status["data"]["report"]["at_a_glance"].to_string();
    assert!(glance.contains("attested by test@example.com"), "{glance}");
}

#[test]
fn the_binary_refuses_without_a_terminal_and_with_an_agent_marker_writing_nothing() {
    // frob:tests crates/frob-evidence/src/attestation.rs::Presence.detect
    let repo = Repo::new();
    for env in [&[][..], &[("CLAUDECODE", "1")][..]] {
        let out = repo.frob_env(
            &[
                "milestone",
                "evidence",
                "add",
                "0.532.0",
                "--provider",
                "attestation",
                "--statement",
                "I did it",
                "--accepts",
                "1",
            ],
            env,
        );
        assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
        let v = json(&out);
        assert_eq!(v["error"]["code"], "E-ATTEST-NOT-HUMAN");
        assert_eq!(v["error"]["requires_human"], true);
        let remedy = v["error"]["remedy"].as_str().expect("remedy");
        assert!(!remedy.contains("frob "), "no executable command: {remedy}");
    }
    let list = repo.ok(&["milestone", "evidence", "list", "0.532.0"]);
    assert_eq!(list["data"]["count"], 0);
    assert_eq!(criterion(&repo, 1)["bound"], false);
}

#[test]
fn the_flags_of_the_provider_are_checked() {
    // frob:tests crates/frob-evidence/src/verbs.rs::CaptureArgs.from_matches
    let repo = Repo::new();
    let out = repo.frob(&[
        "milestone",
        "evidence",
        "add",
        "0.532.0",
        "--provider",
        "attestation",
        "--ref",
        "x",
    ]);
    assert_eq!(code(&out), 2);
    let out = repo.frob(&[
        "milestone",
        "evidence",
        "add",
        "0.532.0",
        "--provider",
        "file",
        "--ref",
        "x",
        "--statement",
        "s",
    ]);
    assert_eq!(code(&out), 2);
}

#[test]
fn a_non_attester_an_empty_statement_and_a_missing_fact_refuse_through_the_milestone_path() {
    // frob:tests crates/frob/src/milestone_evidence_cmd.rs::add_evidence
    let repo = Repo::new();
    let ws = repo.workspace();
    let human = Presence::interactive();
    let refusal = |a: &CaptureArgs, ws: &Workspace| {
        let err = add_evidence(ws, "0.532.0", a, &human).expect_err("refused");
        let gob_cli::CliError::Refusal(r) = err else {
            panic!("a refusal, got {err:?}")
        };
        r
    };
    assert_eq!(
        refusal(&args("  ", &[], &[1]), &ws).code,
        "E-ATTEST-STATEMENT"
    );
    assert_eq!(
        refusal(&args("ok", &["deadbeefdeadbeef"], &[1]), &ws).code,
        "E-ATTEST-FACT-MISSING"
    );
    assert_eq!(
        refusal(&args("ok", &["~NOSUCHT"], &[1]), &ws).code,
        "E-ATTEST-FACT-MISSING"
    );
    repo.set_attesters(r#"["someone-else@example.com"]"#);
    let ws = repo.workspace();
    let r = refusal(&args("ok", &[], &[1]), &ws);
    assert_eq!(r.code, "E-ATTEST-NOT-ATTESTER");
    assert!(r.requires_human);
    assert_eq!(criterion(&repo, 1)["bound"], false, "nothing was written");
}

#[test]
fn an_attestation_on_a_ticket_criterion_binds_and_show_and_brief_label_it() {
    // frob:tests crates/frob/src/ticket/read.rs::EvidenceView
    // frob:tests crates/frob-evidence/src/attestation.rs::attest
    let repo = Repo::new();
    let t = repo.ok(&[
        "ticket",
        "new",
        "--title",
        "Soak",
        "--type",
        "task",
        "--acceptance",
        "thirty days managing three repositories",
    ]);
    let id = t["data"]["id"].as_str().expect("id").to_owned();
    let ws = repo.workspace();
    let rec = attest(
        &ws,
        &Presence::interactive(),
        &Request {
            statement: "I ran the three for thirty days".to_owned(),
            facts: Vec::new(),
            accepts: vec![1],
        },
    )
    .expect("attests");
    let tid = ws.ledger.resolve(&id).expect("resolve");
    frob_evidence::events::append(&ws.ledger, tid, &rec).expect("append");
    let shown = repo.ok(&["ticket", "show", &id]);
    assert_eq!(shown["data"]["evidence"][0]["provider"], "attestation");
    let label = shown["data"]["evidence"][0]["label"]
        .as_str()
        .expect("label");
    assert!(
        label.starts_with("[attested by test@example.com:"),
        "{label}"
    );
    let brief = repo.ok(&["ticket", "brief", &id]);
    let md = brief["data"]["markdown"].as_str().expect("markdown");
    assert!(md.contains("## Evidence"), "{md}");
    assert!(
        md.contains("criterion 1: [attested by test@example.com: \"I ran the three"),
        "{md}"
    );
    assert!(md.contains("1. [bound]"), "{md}");
    let out = repo.frob(&[
        "ticket",
        "evidence",
        "add",
        &id,
        "--provider",
        "attestation",
        "--statement",
        "x",
        "--accepts",
        "1",
    ]);
    assert_eq!(code(&out), 3);
    assert_eq!(json(&out)["error"]["requires_human"], true);
}

#[test]
fn removing_a_criterion_reports_the_evidence_it_loses() {
    // frob:tests crates/frob-pm/src/milestone/criteria.rs::lost_by_removal
    // frob:tests crates/frob/src/milestone_evidence_cmd.rs::CriterionRemove
    let repo = Repo::new();
    std::fs::write(repo.dir.path().join("proof.txt"), "proof").expect("write");
    for n in ["1", "2"] {
        let out = repo.frob(&[
            "milestone",
            "evidence",
            "add",
            "0.532.0",
            "--provider",
            "file",
            "--ref",
            "proof.txt",
            "--accepts",
            n,
        ]);
        assert_eq!(code(&out), 0, "{}", String::from_utf8_lossy(&out.stdout));
    }
    let v = repo.ok(&["milestone", "criterion", "remove", "0.532.0", "1"]);
    let lost = v["data"]["lost_evidence"].as_array().expect("lost");
    assert_eq!(lost.len(), 1, "{v}");
    assert_eq!(lost[0]["provider"], "file");
    assert_eq!(lost[0]["lost"], serde_json::json!([1]));
    assert_eq!(lost[0]["kept"], serde_json::json!([]));
    assert!(
        v["warnings"]
            .to_string()
            .contains("evidence lost its exit criterion"),
        "{}",
        v["warnings"]
    );
    assert_eq!(
        v["data"]["milestone"]["criteria"][0]["bound"], true,
        "criterion b kept its record"
    );
    let again = repo.ok(&["milestone", "criterion", "remove", "0.532.0", "1"]);
    assert!(again["data"]["lost_evidence"][0]["event"].is_string());
    let empty = Repo::new();
    let none = empty.ok(&["milestone", "criterion", "remove", "0.532.0", "1"]);
    assert_eq!(none["data"]["lost_evidence"], serde_json::json!([]));
}

#[test]
fn a_non_ascii_statement_is_a_usage_error_on_both_verbs_and_writes_nothing() {
    // frob:ticket 01M415HTAQ7YSKXW09DG39YHBW
    // frob:tests crates/frob-evidence/src/attestation.rs::attest
    // frob:tests crates/frob/src/milestone_evidence_cmd.rs::add_evidence
    let repo = Repo::new();
    let t = repo.ok(&[
        "ticket",
        "new",
        "--title",
        "Soak",
        "--type",
        "task",
        "--acceptance",
        "a thing",
    ]);
    let id = t["data"]["id"].as_str().expect("id").to_owned();
    let ws = repo.workspace();
    let human = Presence::interactive();
    let bad = args("caf\u{e9}", &[], &[1]);

    let err = add_evidence(&ws, "0.532.0", &bad, &human).expect_err("refused");
    let gob_cli::CliError::Refusal(r) = err else {
        panic!("a refusal, got {err:?}")
    };
    assert_eq!(r.code, "E-ATTEST-NON-ASCII");
    assert!(
        r.message.contains("\\u{00E9}") && r.message.contains("position 4"),
        "{}",
        r.message
    );
    assert_eq!(criterion(&repo, 1)["bound"], false, "milestone untouched");

    // The ticket verb captures through the same CaptureArgs::capture.
    let err = bad.capture(&ws, &human).expect_err("refused");
    assert!(matches!(err, frob_evidence::EvidenceError::NonAscii { .. }));
    let bad_fact = args("ok", &["https://example.com/\u{e9}"], &[1]);
    assert!(bad_fact.capture(&ws, &human).is_err());
    let list = repo.ok(&["ticket", "evidence", "list", &id]);
    assert_eq!(list["data"]["count"], 0, "{list}");
    assert_eq!(
        git(repo.dir.path(), &["status", "--porcelain"]),
        "",
        "nothing written"
    );

    let good = args("cafe", &[], &[1]);
    assert!(add_evidence(&ws, "0.532.0", &good, &human).is_ok());
}
