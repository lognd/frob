//! Shared fixtures: a temp repository tree, a tiny ledger and evaluation helpers.

#![allow(dead_code, reason = "each test binary uses a subset")]

use std::path::Path;

use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig};
use frob_obligations::{Evaluation, InvariantsConfig, collect};
use gob_git::{CommitOptions, RelPath, Repo};
use gob_lock::LockFile;

/// A ledger on `main` holding one open and one done (dropped) ticket.
pub struct Tickets {
    /// Keeps the repository alive.
    pub dir: tempfile::TempDir,
    /// The open ledger.
    pub ledger: Ledger,
    /// Full ULID of the open ticket.
    pub open: String,
    /// Full ULID of the done ticket.
    pub done: String,
}

/// Build the ledger fixture.
pub fn tickets() -> Tickets {
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
            RelPath::new("README.md").expect("path"),
            Some(b"hello\n".to_vec()),
        )],
        "root",
        &CommitOptions::default(),
    )
    .expect("root commit");
    let ledger = Ledger::open(
        repo,
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
    let open = ledger
        .new_ticket(NewTicket::new("Open work", TicketType::Task))
        .expect("open ticket")
        .ticket
        .front
        .id;
    let done = ledger
        .new_ticket(NewTicket::new("Finished work", TicketType::Task))
        .expect("done ticket")
        .ticket
        .front
        .id;
    ledger
        .drop_ticket(done, "not needed any more")
        .expect("drop ticket");
    Tickets {
        dir,
        ledger,
        open: open.to_string(),
        done: done.to_string(),
    }
}

thread_local! {
    static SHARED: std::rc::Rc<Tickets> = std::rc::Rc::new(tickets());
}

/// The ledger fixture of this thread, built on first use.
pub fn shared_tickets() -> std::rc::Rc<Tickets> {
    SHARED.with(std::rc::Rc::clone)
}

/// Write `files` (path, text) under `root`, creating directories.
pub fn write_tree(root: &Path, files: &[(&str, &str)]) {
    for (path, text) in files {
        let full = root.join(path);
        std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
        std::fs::write(full, text).expect("write");
    }
}

/// Collect inputs for `root` and evaluate every rule.
pub fn evaluate_tree(
    root: &Path,
    ledger: Option<&Ledger>,
    config: &InvariantsConfig,
    lock: Option<LockFile>,
) -> Evaluation {
    let mut collected = collect(root).expect("collect");
    if let Some(l) = lock {
        collected.lock = l;
    }
    let inputs = collected.inputs(root, ledger, config);
    frob_obligations::evaluate(&inputs)
}

/// Rule ids of `findings`, in order.
pub fn ids(findings: &[gob_rules::Finding]) -> Vec<String> {
    findings.iter().map(|f| f.rule.to_string()).collect()
}
