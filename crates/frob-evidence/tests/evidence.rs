//! Evidence end to end against temporary repositories: guard, store, verbs, redaction.

use std::path::Path;
use std::time::Duration;

use frob_evidence::events;
use frob_evidence::guard::{CODE_MISSING, EvidenceGuard};
use frob_evidence::provider::{self, build_record, hash_file};
use frob_evidence::record::{Provider, Status};
use frob_evidence::store::{BlobStore, Fetched, Stored};
use frob_evidence::{EvidenceTable, Workspace};
use frob_ledger::model::{Outcome, TicketType};
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig, LedgerError, TicketId};
use gob_exec::{Limits, Outcome as ExecOutcome, Program, Runner, Spec};
use gob_git::Repo;

fn git(dir: &Path, args: &[&str]) {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|a| (*a).to_owned()).collect(),
        cwd: Some(dir.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(30),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 }).run(&spec).expect("git");
    assert_eq!(
        out.status,
        ExecOutcome::Exited(0),
        "git {args:?}: {}",
        out.stderr
    );
}

/// A repository on `main` with one commit whose message is `message`.
fn repo(message: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    git(p, &["init", "-q"]);
    git(p, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(p, &["config", "user.name", "Test User"]);
    git(p, &["config", "user.email", "test@example.com"]);
    git(p, &["config", "core.autocrlf", "false"]);
    std::fs::write(p.join("data.txt"), "hello\n").expect("write");
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", message]);
    dir
}

fn ledger(dir: &Path) -> Ledger {
    Ledger::open(Repo::discover(dir).expect("repo"), LedgerConfig::default())
}

fn ticket(ledger: &Ledger, ty: TicketType) -> (TicketId, String) {
    let mut req = NewTicket::new("Do the thing", ty);
    req.acceptance = vec!["first".into(), "second".into()];
    let a = ledger.new_ticket(req).expect("new ticket");
    (a.ticket.front.id, a.handle)
}

fn store(dir: &Path, inline_max: u64) -> BlobStore {
    let cfg = EvidenceTable {
        inline_max_bytes: inline_max,
        ..EvidenceTable::default()
    };
    BlobStore::open(&cfg, &Repo::discover(dir).expect("repo")).expect("store")
}

#[test]
fn guard_refuses_a_task_without_evidence_and_passes_with_a_measured_record() {
    let dir = repo("base");
    let ledger = ledger(dir.path());
    let st = store(dir.path(), 16_384);
    let (id, handle) = ticket(&ledger, TicketType::Task);

    let guard = EvidenceGuard::for_ticket(&ledger, &st, id).expect("guard");
    let err = ledger
        .close(id, Some(Outcome::Done), None, &[&guard])
        .expect_err("no evidence");
    match err {
        LedgerError::GuardRefused {
            code,
            remedy,
            message,
        } => {
            assert_eq!(code, CODE_MISSING);
            assert!(remedy.expect("remedy").contains("frob test --base"));
            assert!(message.contains(&handle), "{message}");
        }
        other => panic!("unexpected {other}"),
    }

    let rec = hash_file(dir.path(), "data.txt", &[1]).expect("hash");
    events::append(&ledger, id, &rec).expect("append");
    let guard = EvidenceGuard::for_ticket(&ledger, &st, id).expect("guard");
    assert_eq!(guard.measured(), 1);
    ledger
        .close(id, Some(Outcome::Done), None, &[&guard])
        .expect("closes with evidence");

    // The appended event must not break fold == frontmatter.
    let tip = ledger.tip().expect("tip").expect("some").to_string();
    let stored = ledger
        .read_ticket_at(&tip, id)
        .expect("read")
        .expect("ticket");
    let folded = frob_ledger::fold::fold(id, &ledger.read_events_at(&tip, id).expect("events"))
        .expect("fold")
        .ticket;
    assert_eq!(stored, folded);
}

#[test]
fn non_code_tickets_need_no_evidence_and_bypass_is_recorded() {
    let dir = repo("base");
    let ledger = ledger(dir.path());
    let st = store(dir.path(), 16_384);
    let (chore, _) = ticket(&ledger, TicketType::Chore);
    let guard = EvidenceGuard::for_ticket(&ledger, &st, chore).expect("guard");
    ledger
        .close(chore, Some(Outcome::Done), None, &[&guard])
        .expect("chore closes");

    let (bug, _) = ticket(&ledger, TicketType::Bug);
    let guard = EvidenceGuard::for_ticket(&ledger, &st, bug)
        .expect("guard")
        .allow_bypass("verified by hand");
    ledger
        .close(bug, Some(Outcome::Fixed), None, &[&guard])
        .expect("bypass closes");
    let appended = guard
        .record_bypass(&ledger, bug)
        .expect("record")
        .expect("some");
    let tip = ledger.tip().expect("tip").expect("some").to_string();
    let events = ledger.read_events_at(&tip, bug).expect("events");
    assert!(
        events
            .iter()
            .any(|e| e.kind == events::KIND_BYPASS && e.id == appended.event)
    );
}

#[test]
fn failing_runs_and_unmeasured_records_do_not_satisfy_the_guard() {
    let dir = repo("base");
    let st = store(dir.path(), 16_384);
    let mut rec = hash_file(dir.path(), "data.txt", &[]).expect("hash");
    rec.passed = Some(false);
    assert_eq!(
        EvidenceGuard::from_records(&[rec.clone()], &st).measured(),
        0
    );
    rec.passed = None;
    rec.status = Status::Unmeasured;
    assert_eq!(EvidenceGuard::from_records(&[rec], &st).measured(), 0);
}

#[test]
fn transcripts_over_the_threshold_go_to_the_dir_store() {
    let dir = repo("base");
    let st = store(dir.path(), 10);
    assert_eq!(st.put("tiny").expect("put"), Stored::Inline("tiny".into()));
    let big = "x".repeat(11);
    let Stored::Uri(uri) = st.put(&big).expect("put") else {
        panic!("expected a uri");
    };
    assert!(uri.starts_with("dir:.git/frob/artifacts/"), "{uri}");
    let on_disk = dir
        .path()
        .join(".git/frob/artifacts")
        .join(uri.rsplit('/').next().unwrap());
    assert_eq!(std::fs::read_to_string(on_disk).expect("blob"), big);
    assert_eq!(st.fetch(&uri), Fetched::Found(big.into_bytes()));
}

#[test]
fn a_missing_blob_is_unmeasured_not_failed() {
    let dir = repo("base");
    let st = store(dir.path(), 10);
    let cap = provider::Capture {
        exit_code: Some(0),
        passed: true,
        measured: true,
        tests: vec![],
        failed_tests: vec![],
        transcript: "y".repeat(40),
    };
    let rec = build_record(&st, Provider::Command, "git status", &cap, &[]).expect("record");
    let uri = rec.uri.clone().expect("stored by uri");
    assert_eq!(rec.effective_status(&st), Status::Measured);
    std::fs::remove_file(dir.path().join(".git/frob/artifacts").join(&rec.digest)).expect("rm");
    assert!(matches!(
        st.fetch(&uri),
        Fetched::Unmeasured { ref reason, .. } if reason.contains("missing")
    ));
    assert_eq!(rec.effective_status(&st), Status::Unmeasured);
    assert_eq!(EvidenceGuard::from_records(&[rec], &st).measured(), 0);
    assert!(matches!(
        st.fetch("https://x.example/blob"),
        Fetched::Unmeasured { .. }
    ));
}

#[test]
fn command_transcripts_are_redacted_before_they_are_stored() {
    const TOKEN: &str = "ghp_0123456789abcdefghijklmnopqrstuvwxyz";
    let dir = repo(&format!("leak {TOKEN}"));
    let ws = Workspace::open(dir.path()).expect("workspace");
    let rec =
        provider::capture(&ws, Provider::Command, "git log -1 --format=%B", &[]).expect("capture");
    let text = rec.inline.as_deref().expect("inline");
    assert!(text.contains("[REDACTED]"), "{text}");
    assert!(!text.contains(TOKEN));
    assert_eq!(
        rec.digest,
        frob_evidence::record::digest_hex(text.as_bytes())
    );
    assert_eq!(rec.exit_code, Some(0));
    assert_eq!(rec.passed, Some(true));
}

#[test]
fn command_tools_outside_the_allowlist_are_refused() {
    let dir = repo("base");
    let ws = Workspace::open(dir.path()).expect("workspace");
    let err = provider::capture(&ws, Provider::Command, "rm -rf /", &[]).expect_err("refused");
    assert!(err.to_string().starts_with("E-EVIDENCE-TOOL"), "{err}");
}

fn cli() -> gob_cli::Cli {
    frob_evidence::register(gob_cli::Cli::new("frob", "0.0.0"))
}

fn json(out: &str) -> serde_json::Value {
    serde_json::from_str(out).unwrap_or_else(|e| panic!("json {e}: {out}"))
}

#[test]
fn verbs_add_list_and_fetch_round_trip() {
    let dir = repo("base");
    let ledger = ledger(dir.path());
    let (_, handle) = ticket(&ledger, TicketType::Task);
    drop(ledger);
    let cli = cli();
    let run = |args: &[&str]| gob_cli::run_for_test(&cli, args, dir.path());

    let (code, out, err) = run(&[
        "--json",
        "ticket",
        "evidence",
        "add",
        &handle,
        "--provider",
        "command",
        "--ref",
        "git log -1 --format=%s",
        "--accepts",
        "2",
    ]);
    assert_eq!(code, 0, "{out}{err}");
    let v = json(&out);
    assert_eq!(v["data"]["record"]["accepts"], serde_json::json!([2]));
    assert_eq!(v["data"]["record"]["provider"], "command");

    let (code, out, _) = run(&["--json", "ticket", "evidence", "list", &handle]);
    assert_eq!(code, 0, "{out}");
    let v = json(&out);
    assert_eq!(v["data"]["count"], 1);
    assert_eq!(v["data"]["records"][0]["index"], 1);
    assert_eq!(v["data"]["records"][0]["effective_status"], "measured");

    let (code, out, _) = run(&["--json", "ticket", "evidence", "fetch", &handle, "1"]);
    assert_eq!(code, 0, "{out}");
    let v = json(&out);
    assert_eq!(v["data"]["status"], "measured");
    assert!(
        v["data"]["content"]
            .as_str()
            .expect("content")
            .contains("tickets(new)")
    );

    // Out-of-range fetch, bad --accepts and a disallowed tool are refusals.
    let (code, ..) = run(&["--json", "ticket", "evidence", "fetch", &handle, "9"]);
    assert_eq!(code, 3);
    let (code, ..) = run(&[
        "--json",
        "ticket",
        "evidence",
        "add",
        &handle,
        "--provider",
        "file",
        "--ref",
        "data.txt",
        "--accepts",
        "3",
    ]);
    assert_eq!(code, 2);
    let (code, out, _) = run(&[
        "--json",
        "ticket",
        "evidence",
        "add",
        &handle,
        "--provider",
        "command",
        "--ref",
        "sh -c ls",
    ]);
    assert_eq!(code, 3, "{out}");
    assert_eq!(json(&out)["error"]["code"], "E-EVIDENCE-TOOL");
}

// frob:ticket 01M40K5J3B39TX30FC3PFY7RCD
#[test]
fn a_hyphen_led_ref_is_taken_whole() {
    // frob:tests crates/frob-evidence/src/verbs.rs::capture_args
    let dir = repo("base");
    let ledger = ledger(dir.path());
    let (_, handle) = ticket(&ledger, TicketType::Task);
    drop(ledger);
    let cli = cli();
    let (code, out, err) = gob_cli::run_for_test(
        &cli,
        &[
            "--json",
            "ticket",
            "evidence",
            "add",
            &handle,
            "--provider",
            "command",
            "--ref",
            "-p frob-cli -E 'test(x)'",
        ],
        dir.path(),
    );
    // Not a usage error about `-p`: the whole value reached the provider, which refused the tool `-p`.
    assert_eq!(code, 3, "{out}{err}");
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-EVIDENCE-TOOL");
    assert!(e["message"].as_str().expect("message").contains("`-p`"));
}

/// A repository holding a one-test cargo package, so nextest has something to match against.
fn cargo_repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    git(p, &["init", "-q"]);
    git(p, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(p, &["config", "user.name", "Test User"]);
    git(p, &["config", "user.email", "test@example.com"]);
    std::fs::write(
        p.join("Cargo.toml"),
        "[package]\nname = \"probe\"\nversion = \"0.0.0\"\nedition = \"2021\"\n\n[workspace]\n",
    )
    .expect("manifest");
    std::fs::create_dir(p.join("src")).expect("src");
    std::fs::write(p.join("src/lib.rs"), "#[test]\nfn present() {}\n").expect("lib");
    std::fs::write(p.join(".gitignore"), "target/\n").expect("ignore");
    // An explicit profile keeps an outer `NEXTEST_PROFILE` (set when this test runs under nextest) out of the probe.
    std::fs::write(
        p.join("frob.toml"),
        "[evidence]\nnextest_profile = \"default\"\n",
    )
    .expect("frob.toml");
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "base"]);
    dir
}

// frob:ticket 01M40K5J3B39TX30FC3PFY7RCD
#[test]
fn a_filter_matching_no_test_refuses_and_records_nothing() {
    // frob:tests crates/frob-evidence/src/provider.rs::capture
    let dir = cargo_repo();
    let ledger = ledger(dir.path());
    let (_, handle) = ticket(&ledger, TicketType::Task);
    drop(ledger);
    let cli = cli();
    let run = |args: &[&str]| gob_cli::run_for_test(&cli, args, dir.path());
    let (code, out, err) = run(&[
        "--json",
        "ticket",
        "evidence",
        "add",
        &handle,
        "--provider",
        "nextest",
        "--ref",
        "-E 'test(=no_such_test)'",
    ]);
    assert_eq!(code, 2, "{out}{err}");
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-EVIDENCE-NO-TESTS");
    let msg = e["message"].as_str().expect("message");
    assert!(
        msg.contains("matched no tests") && msg.contains("no_such_test"),
        "{msg}"
    );
    assert!(
        e["remedy"]
            .as_str()
            .expect("remedy")
            .contains("cargo nextest list")
    );
    let (code, out, _) = run(&["--json", "ticket", "evidence", "list", &handle]);
    assert_eq!(code, 0, "{out}");
    assert_eq!(json(&out)["data"]["count"], 0);
    // The same package with a matching filter still records a measured pass.
    let (code, out, err) = run(&[
        "--json",
        "ticket",
        "evidence",
        "add",
        &handle,
        "--provider",
        "nextest",
        "--ref",
        "-E 'test(=present)'",
        "--accepts",
        "1",
    ]);
    assert_eq!(code, 0, "{out}{err}");
}
