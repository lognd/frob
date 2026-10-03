//! The sibling stage end to end: a fake `grimble` binary driven through `frob check`.
//!
//! The real grimble cannot be a dev-dependency binary of this crate (cargo builds
//! only the bins of the package under test, and frob never depends on a grimble
//! crate), so the fake in `tests/support/fake_sibling.rs` speaks the contract and the
//! workspace-level run against the built grimble is recorded on the ticket.

use std::path::{Path, PathBuf};
use std::time::Instant;

use frob_check::{CheckOptions, CheckReport, run};
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig};
use gob_diagnostics::{ExitCode, RequiredReason};
use gob_git::{CommitOptions, RelPath, Repo};
use gob_rules::Severity;

const FAKE: &str = env!("CARGO_BIN_EXE_fake-sibling");

fn write(root: &Path, path: &str, text: &str) {
    let full = root.join(path);
    std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
    std::fs::write(full, text).expect("write");
}

fn opts() -> CheckOptions {
    CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        sibling_programs: vec![("grimble".to_owned(), PathBuf::from(FAKE))],
        ..CheckOptions::default()
    }
}

/// A configured-grimble repository whose fake sibling runs in `mode`.
fn repo(mode: &str, frob_toml: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "grimble.toml", "");
    write(dir.path(), ".fake-sibling", mode);
    write(dir.path(), "a.txt", "aaa\n");
    write(dir.path(), "b.txt", "bbb\n");
    write(dir.path(), "model/a.grmb", "node x {}\n");
    if !frob_toml.is_empty() {
        write(dir.path(), "frob.toml", frob_toml);
    }
    dir
}

fn of_rule<'a>(r: &'a CheckReport, rule: &str) -> Vec<&'a gob_rules::Finding> {
    r.findings
        .iter()
        .filter(|f| f.rule.as_str() == rule)
        .collect()
}

// frob:tests crates/frob-check/src/sibling/mod.rs::Siblings
#[test]
fn a_valid_document_is_merged_namespaced_and_gated_on_its_marks() {
    let dir = repo("valid -", "");
    let r = run(dir.path(), &opts()).expect("run");
    assert!(of_rule(&r, "SIB001").is_empty());
    let warn = of_rule(&r, "SYS006");
    assert_eq!(warn.len(), 1);
    assert_eq!(warn[0].severity, Severity::Warn);
    assert!(
        warn[0].message.contains("--base main"),
        "base passed: {}",
        warn[0].message
    );
    assert_eq!(
        r.fingerprint_of(warn[0]),
        format!("grimble:{}", "a".repeat(64))
    );
    let un = of_rule(&r, "SYS003");
    assert_eq!(un[0].severity, Severity::Unresolved);
    assert!(matches!(
        un[0].required,
        Some(RequiredReason::AnnotationRequired { .. })
    ));
    assert_eq!(
        r.suppressed.len(),
        1,
        "the sibling's suppressed list is carried"
    );
    assert_eq!(
        r.fingerprint_of(&r.suppressed[0].0),
        format!("grimble:{}", "c".repeat(64))
    );
    let row = &r.fidelity.languages["grimble:grmb"];
    assert_eq!(row.fidelity, "F3");
    assert_eq!(row.not_applicable.get("SYS"), Some(&1));
    let stage = r
        .timing
        .stages
        .iter()
        .find(|s| s.name == "sibling:grimble")
        .expect("timed");
    assert!(
        !stage.budgeted,
        "sibling time stays outside frob's own budget"
    );
    assert_eq!(
        r.exit_code(),
        ExitCode::Negative,
        "the required mark fails the default gate"
    );
}

// frob:tests crates/frob-check/src/sibling/mod.rs::Siblings
#[test]
fn frob_applies_its_own_gate_to_the_merged_marks() {
    let dir = repo("valid -", "[check]\nfail_on_unresolved = \"never\"\n");
    let r = run(dir.path(), &opts()).expect("run");
    assert_eq!(
        r.exit_code(),
        ExitCode::Ok,
        "warning is below fail_on and the gate is off"
    );
    let dir = repo("valid -", "[check]\nfail_on = \"warn\"\n");
    assert_eq!(
        run(dir.path(), &opts()).expect("run").exit_code(),
        ExitCode::Negative
    );
}

/// The mode, frob.toml and the `SIB001` reason code each failure must report.
const FAILURES: &[(&str, &str, &str)] = &[
    ("incompatible", "", "incompatible"),
    ("badproduct", "", "incompatible"),
    ("baddigest", "", "incompatible"),
    ("malformed", "", "malformed"),
    ("flood", "[check]\noutput_cap_bytes = 100000\n", "malformed"),
    ("nomark", "", "malformed"),
    ("exit3", "", "failed"),
    ("failenv", "", "failed"),
    ("hang", "[check]\nsibling_timeout_secs = 1\n", "timeout"),
];

// frob:tests crates/frob-check/src/sibling/mod.rs::Sib001
#[test]
fn every_failure_is_one_required_sib001_with_its_reason_and_fails_the_gate() {
    for (mode, toml, code) in FAILURES {
        let dir = repo(mode, toml);
        let started = Instant::now();
        let r = run(dir.path(), &opts()).expect("run");
        assert!(started.elapsed().as_secs() < 30, "{mode} returned promptly");
        let sib = of_rule(&r, "SIB001");
        assert_eq!(sib.len(), 1, "{mode}: exactly one SIB001");
        assert_eq!(sib[0].severity, Severity::Unresolved);
        assert_eq!(
            sib[0].required,
            Some(RequiredReason::SiblingMissing {
                product: "grimble".to_owned()
            }),
            "{mode}"
        );
        assert!(
            sib[0].message.contains(&format!("({code})")),
            "{mode}: {}",
            sib[0].message
        );
        assert!(
            of_rule(&r, "SYS006").is_empty(),
            "{mode}: no findings read from a bad document"
        );
        assert_eq!(r.exit_code(), ExitCode::Negative, "{mode}");
    }
}

// frob:tests crates/frob-check/src/sibling/mod.rs::Sib001
#[test]
fn an_absent_sibling_is_required_and_a_failure_envelope_remedy_is_kept() {
    let dir = repo("valid -", "");
    let mut o = opts();
    o.sibling_programs = vec![("grimble".to_owned(), dir.path().join("no-such-binary"))];
    let r = run(dir.path(), &o).expect("run");
    let sib = of_rule(&r, "SIB001");
    assert_eq!(sib.len(), 1);
    assert!(sib[0].message.contains("(absent)") && sib[0].message.contains("uv tool install frob"));
    assert_eq!(r.exit_code(), ExitCode::Negative);

    let dir = repo("failenv", "");
    let r = run(dir.path(), &opts()).expect("run");
    assert!(
        of_rule(&r, "SIB001")[0]
            .message
            .contains("remedy: grimble fmt --check")
    );
}

// frob:tests crates/frob-check/src/sibling/mod.rs::unavailable
#[test]
fn require_siblings_false_drops_the_mark_but_all_still_fails() {
    let dir = repo("malformed", "[check]\nrequire_siblings = false\n");
    let r = run(dir.path(), &opts()).expect("run");
    let sib = of_rule(&r, "SIB001");
    assert_eq!(sib.len(), 1);
    assert_eq!(sib[0].required, None);
    assert_eq!(r.exit_code(), ExitCode::Ok);
    let dir = repo(
        "malformed",
        "[check]\nrequire_siblings = false\nfail_on_unresolved = \"all\"\n",
    );
    assert_eq!(
        run(dir.path(), &opts()).expect("run").exit_code(),
        ExitCode::Negative
    );
}

// frob:tests crates/frob-check/src/sibling/mod.rs::wanted
#[test]
fn only_sib_keeps_the_stage_and_other_families_skip_it() {
    let dir = repo("malformed", "");
    let only = |name: &str| CheckOptions {
        only: vec![name.to_owned()],
        ..opts()
    };
    let r = run(dir.path(), &only("SIB")).expect("run");
    assert_eq!(of_rule(&r, "SIB001").len(), 1);
    let r = run(dir.path(), &only("TODO")).expect("run");
    assert!(of_rule(&r, "SIB001").is_empty());
    assert!(r.timing.stages.iter().all(|s| s.name != "sibling:grimble"));
    let dir = repo("valid -", "");
    let r = run(dir.path(), &only("SIB")).expect("run");
    assert!(
        r.findings.is_empty(),
        "sibling findings obey --only: {:?}",
        r.findings
    );
}

// frob:tests crates/frob-check/src/sibling/mod.rs::Siblings
#[test]
fn an_unconfigured_sibling_is_not_run_and_says_nothing() {
    let dir = repo("malformed", "");
    std::fs::remove_file(dir.path().join("grimble.toml")).expect("remove");
    let r = run(dir.path(), &opts()).expect("run");
    assert!(of_rule(&r, "SIB001").is_empty());
    assert!(r.timing.stages.iter().all(|s| s.name != "sibling:grimble"));
}

/// A repository with a ledger holding an open ticket scoped to `src/a/**` and a dropped one.
fn ledger_repo(mode_for: impl Fn(&str, &str) -> String) -> (tempfile::TempDir, String, String) {
    let dir = tempfile::tempdir().expect("tempdir");
    let repo = Repo::init(dir.path()).expect("init");
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").expect("head");
    let cfg = std::fs::read_to_string(repo.git_dir().join("config")).expect("config");
    std::fs::write(
        repo.git_dir().join("config"),
        format!("{cfg}[user]\n\tname = Test User\n\temail = test@example.com\n"),
    )
    .expect("identity");
    drop(repo);
    let repo = Repo::discover(dir.path()).expect("discover");
    repo.commit_paths(
        "refs/heads/main",
        &[(
            RelPath::new(".gitignore").expect("path"),
            Some(b".frob/\n".to_vec()),
        )],
        "root",
        &CommitOptions::default(),
    )
    .expect("root commit");
    let ledger = Ledger::open(repo, LedgerConfig::default());
    let mut open = NewTicket::new("Open work", TicketType::Task);
    open.scope = vec!["src/a/**".to_owned()];
    let open = ledger.new_ticket(open).expect("ticket").ticket.front.id;
    let done = ledger
        .new_ticket(NewTicket::new("Dead work", TicketType::Task))
        .expect("ticket")
        .ticket
        .front
        .id;
    ledger.drop_ticket(done, "not needed").expect("drop");
    let (open, done) = (open.to_string(), done.to_string());
    write(dir.path(), "grimble.toml", "");
    write(dir.path(), ".fake-sibling", &mode_for(&open, &done));
    write(dir.path(), "src/a/lib.rs", "//! A.\n");
    write(dir.path(), "model/a.grmb", "node x {}\n");
    (dir, open, done)
}

// frob:tests crates/frob-obligations/src/sibling.rs::sibling_exception_findings
#[test]
fn ticket_bound_sibling_exceptions_get_frobs_exits() {
    let (dir, _, _) = ledger_repo(|_, done| format!("valid {done}"));
    let r = run(dir.path(), &opts()).expect("run");
    let exc = of_rule(&r, "EXC003");
    assert_eq!(exc.len(), 1, "defer on a terminal ticket: {:?}", r.findings);
    assert!(exc[0].message.contains("grimble") && exc[0].message.contains("SYS006"));
    let at = exc[0].span.and_then(|s| r.files.path(s.file));
    assert_eq!(at, Some("model/a.grmb"), "located at the exception's file");
    assert_eq!(
        r.suppressed.len(),
        1,
        "the sibling's suppression stands; the EXC finding fails the gate"
    );

    let (dir, _, _) = ledger_repo(|_, _| "valid 01ARZ3NDEKTSV4RRFFQ69G5FAV".to_owned());
    let r = run(dir.path(), &opts()).expect("run");
    assert_eq!(of_rule(&r, "EXC007").len(), 1);
    assert!(of_rule(&r, "EXC003").is_empty());

    let (dir, open, _) = ledger_repo(|open, _| format!("valid {open}"));
    let r = run(dir.path(), &opts()).expect("run");
    assert!(
        of_rule(&r, "EXC003").is_empty() && of_rule(&r, "EXC007").is_empty(),
        "{open}"
    );
}

// frob:tests crates/frob-check/src/product.rs::start_external
#[test]
fn the_ticket_scope_is_passed_through_to_the_sibling() {
    let (dir, open, _) = ledger_repo(|open, _| format!("valid {open}"));
    let r = run(
        dir.path(),
        &CheckOptions {
            ticket: Some(open),
            ..opts()
        },
    )
    .expect("run");
    let warn = of_rule(&r, "SYS006");
    assert_eq!(warn.len(), 1);
    assert!(
        warn[0].message.contains("--ticket-scope src/a/lib.rs"),
        "scope paths forwarded: {}",
        warn[0].message
    );
}
