//! Attestation evidence against temporary repositories: who may attest, from where, resting on what.

use std::path::Path;
use std::time::Duration;

use frob_evidence::attestation::{Presence, Request, attest};
use frob_evidence::events;
use frob_evidence::{EvidenceError, Workspace};
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use gob_exec::{Limits, Outcome as ExecOutcome, Program, Runner, Spec};

fn git(dir: &Path, args: &[&str]) -> String {
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
    out.stdout.trim().to_owned()
}

/// A repository on `main` with one commit and `attesters` written to its frob.toml.
fn repo(attesters: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    git(p, &["init", "-q"]);
    git(p, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(p, &["config", "user.name", "Owner"]);
    git(p, &["config", "user.email", "owner@example.com"]);
    git(p, &["config", "core.autocrlf", "false"]);
    std::fs::write(
        p.join("frob.toml"),
        format!("[evidence]\nattesters = {attesters}\n"),
    )
    .expect("write");
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "base"]);
    dir
}

fn request(statement: &str, facts: &[&str]) -> Request {
    Request {
        statement: statement.to_owned(),
        facts: facts.iter().map(|f| (*f).to_owned()).collect(),
        accepts: vec![1],
    }
}

fn refused(ws: &Workspace, presence: &Presence, req: &Request) -> EvidenceError {
    attest(ws, presence, req).expect_err("must refuse")
}

#[test]
fn an_attester_at_a_terminal_binds_a_ticket_criterion() {
    // frob:ticket 01M40AKKXBN7K30090V7KQSA8Z
    // frob:tests crates/frob-evidence/src/attestation.rs::attest
    let dir = repo(r#"["owner@example.com"]"#);
    let ws = Workspace::open(dir.path()).expect("workspace");
    let mut t = NewTicket::new("Manage two repos", TicketType::Task);
    t.acceptance = vec!["two outside repositories managed for two cycles".into()];
    let a = ws.ledger.new_ticket(t).expect("ticket");
    let id = a.ticket.front.id;
    let commit = git(dir.path(), &["rev-parse", "HEAD"]);
    let rec = attest(
        &ws,
        &Presence::interactive(),
        &request(
            "I managed both repositories for two cycles with no data loss",
            &["https://example.com/report", &commit[..10], &a.handle],
        ),
    )
    .expect("attests");
    assert_eq!(rec.passed, Some(true));
    events::append(&ws.ledger, id, &rec).expect("append");
    let view = ws.ledger.show(id).expect("show");
    assert!(
        view.ticket.front.acceptance[0].bound,
        "the attestation binds"
    );
    let label = rec.attestation_label().expect("label");
    assert!(
        label.starts_with("[attested by owner@example.com: \""),
        "{label}"
    );
    let stored = events::list(&ws.ledger, id).expect("list");
    assert_eq!(
        stored[0]
            .record
            .attestation
            .as_ref()
            .expect("a")
            .facts
            .len(),
        3
    );
}

#[test]
fn an_agent_marker_or_a_pipe_refuses_and_names_a_human_remedy() {
    // frob:ticket 01M40AKKXBN7K30090V7KQSA8Z
    // frob:tests crates/frob-evidence/src/attestation.rs::Presence.require_human
    let dir = repo(r#"["owner@example.com"]"#);
    let ws = Workspace::open(dir.path()).expect("workspace");
    let agent = Presence::from_parts(true, true, |n| (n == "CLAUDECODE").then(|| "1".to_owned()));
    let err = refused(&ws, &agent, &request("fine", &[]));
    assert!(matches!(err, EvidenceError::NotHuman { .. }), "{err}");
    assert!(err.to_string().contains("CLAUDECODE"));
    let piped = Presence::from_parts(false, false, |_| None);
    let err = refused(&ws, &piped, &request("fine", &[]));
    assert!(err.to_string().contains("stdin is not a terminal"), "{err}");
    let gob_cli::CliError::Refusal(r) = err.into_cli() else {
        panic!("a refusal")
    };
    assert!(r.requires_human);
    assert_eq!(r.code, "E-ATTEST-NOT-HUMAN");
    assert!(
        !r.remedy.expect("remedy").contains("frob "),
        "never a command line"
    );
}

#[test]
fn a_non_attester_and_an_empty_list_refuse() {
    // frob:ticket 01M40AKKXBN7K30090V7KQSA8Z
    // frob:tests crates/frob-evidence/src/attestation.rs::attest
    let other = repo(r#"["someone-else@example.com"]"#);
    let ws = Workspace::open(other.path()).expect("workspace");
    let err = refused(&ws, &Presence::interactive(), &request("fine", &[]));
    assert!(matches!(err, EvidenceError::NotAttester { .. }), "{err}");
    assert!(err.to_string().contains("owner@example.com"));
    let empty = repo("[]");
    let ws = Workspace::open(empty.path()).expect("workspace");
    let err = refused(&ws, &Presence::interactive(), &request("fine", &[]));
    assert!(err.to_string().contains("nobody may attest"), "{err}");
}

#[test]
fn an_empty_statement_refuses() {
    // frob:ticket 01M40AKKXBN7K30090V7KQSA8Z
    // frob:tests crates/frob-evidence/src/attestation.rs::attest
    let dir = repo(r#"["owner@example.com"]"#);
    let ws = Workspace::open(dir.path()).expect("workspace");
    for s in ["", "   \n"] {
        let err = refused(&ws, &Presence::interactive(), &request(s, &[]));
        assert!(matches!(err, EvidenceError::EmptyStatement), "{err}");
    }
}

#[test]
fn facts_must_have_a_shape_and_commits_and_tickets_must_exist() {
    // frob:ticket 01M40AKKXBN7K30090V7KQSA8Z
    // frob:tests crates/frob-evidence/src/attestation.rs::validate_facts
    let dir = repo(r#"["owner@example.com"]"#);
    let ws = Workspace::open(dir.path()).expect("workspace");
    let at = |fact: &str| refused(&ws, &Presence::interactive(), &request("fine", &[fact]));
    assert!(matches!(
        at("deadbeefdeadbeef"),
        EvidenceError::MissingFact { kind: "commit", .. }
    ));
    assert!(matches!(
        at("~ZZZZZZZ"),
        EvidenceError::MissingFact { kind: "ticket", .. }
    ));
    assert!(matches!(
        at("01M40AKKXBN7K30090V7KQSA8Z"),
        EvidenceError::MissingFact { kind: "ticket", .. }
    ));
    assert!(matches!(at("just words"), EvidenceError::BadFact { .. }));
    assert!(matches!(
        at("ftp://example.com/x"),
        EvidenceError::BadFact { .. }
    ));
}

#[test]
fn a_tampered_statement_degrades_to_unmeasured() {
    // frob:ticket 01M40AKKXBN7K30090V7KQSA8Z
    // frob:tests crates/frob-evidence/src/record.rs::EvidenceRecord.effective_status
    let dir = repo(r#"["owner@example.com"]"#);
    let ws = Workspace::open(dir.path()).expect("workspace");
    let mut rec = attest(
        &ws,
        &Presence::interactive(),
        &request("true statement", &[]),
    )
    .expect("ok");
    assert_eq!(
        rec.effective_status(&ws.store),
        frob_evidence::Status::Measured
    );
    rec.attestation.as_mut().expect("a").statement = "forged".to_owned();
    assert_eq!(
        rec.effective_status(&ws.store),
        frob_evidence::Status::Unmeasured
    );
}
