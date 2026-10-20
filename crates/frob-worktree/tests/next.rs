//! `work --next`: allocate and claim with retry on a lost race (system git required).
// frob:ticket 01M5CW05BZQR83F5SJTQEH8MRN

use std::path::{Path, PathBuf};
use std::time::Duration;

use frob_lease::{LeaseConfig, LeaseStore};
use frob_ledger::guards::NoLeases;
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig};
use frob_worktree::next::{E_NO_DOABLE, MAX_ATTEMPTS};
use frob_worktree::{WorkOptions, Workspace, WorktreeConfig, WorktreeError};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use gob_git::{CommitOptions, RelPath, Repo};

const MAIN: &str = "refs/heads/main";

fn git(cwd: &Path, args: &[&str]) -> bool {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|s| (*s).to_owned()).collect(),
        cwd: Some(cwd.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(30),
        capture: true,
    };
    matches!(
        Runner::new(Limits { jobs: 1 }).run(&spec),
        Ok(o) if o.status == Outcome::Exited(0)
    )
}

/// A repository on `main` with a root commit and, optionally, an `origin` bare repository.
struct Fixture {
    _tmp: tempfile::TempDir,
    root: PathBuf,
}

impl Fixture {
    fn new(remote_url: Option<&str>) -> Option<Self> {
        let tmp = tempfile::tempdir().expect("tempdir");
        let root = tmp.path().join("repo");
        let bare = tmp.path().join("origin.git");
        std::fs::create_dir(&root).expect("mkdir");
        std::fs::create_dir(&bare).expect("mkdir bare");
        if !git(&bare, &["init", "--bare", "--quiet"]) {
            return None;
        }
        let repo = Repo::init(&root).expect("init");
        std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").expect("head");
        let cfg = std::fs::read_to_string(repo.git_dir().join("config")).expect("config");
        std::fs::write(
            repo.git_dir().join("config"),
            format!("{cfg}[user]\n\tname = Test User\n\temail = test@example.com\n"),
        )
        .expect("identity");
        drop(repo);
        let repo = Repo::discover(&root).expect("discover");
        repo.commit_paths(
            MAIN,
            &[(
                RelPath::new("README.md").expect("path"),
                Some(b"hi\n".to_vec()),
            )],
            "root",
            &CommitOptions::default(),
        )
        .expect("root commit");
        let url = remote_url.map_or_else(
            || gob_path::Shown::with_home(&bare, None).to_string(),
            str::to_owned,
        );
        assert!(git(&root, &["remote", "add", "origin", &url]));
        Some(Self { _tmp: tmp, root })
    }

    fn ledger(&self) -> Ledger {
        Ledger::open(
            Repo::discover(&self.root).expect("repo"),
            LedgerConfig::default(),
            std::sync::Arc::new(gob_time::SystemClock),
        )
    }

    fn leases(&self) -> LeaseStore {
        let repo = Repo::discover(&self.root).expect("repo");
        LeaseStore::open(
            &repo,
            LeaseConfig::default(),
            std::sync::Arc::new(gob_time::SystemClock),
        )
        .expect("leases")
    }
}

fn new_ticket(ledger: &Ledger) -> (String, String) {
    let mut req = NewTicket::new("Claim me", TicketType::Task);
    req.scope = vec!["crates/x/**".to_owned()];
    let id = ledger.new_ticket(req).expect("new").ticket.front.id;
    let handle = ledger.show(id).expect("show").summary.handle;
    (id.to_string(), handle.trim_start_matches('~').to_owned())
}

/// Push a rival `ticket/<handle>` branch to the remote, so the claim of `handle` is lost.
fn rival_claim(fx: &Fixture, handle: &str) {
    let repo = Repo::discover(&fx.root).expect("repo");
    repo.commit_paths(
        "refs/heads/rival",
        &[(
            RelPath::new("rival.txt").expect("path"),
            Some(b"x\n".to_vec()),
        )],
        "rival work",
        &CommitOptions::default(),
    )
    .expect("rival commit");
    let dst = format!("refs/heads/rival:refs/heads/ticket/{handle}");
    assert!(git(&fx.root, &["push", "--quiet", "origin", &dst]));
}

// frob:tests work_next
#[test]
fn a_lost_race_moves_on_to_the_next_candidate() {
    let Some(fx) = Fixture::new(None) else { return };
    let (ledger, leases) = (fx.ledger(), fx.leases());
    new_ticket(&ledger);
    new_ticket(&ledger);
    let order = ledger.doable(&NoLeases).expect("doable");
    assert_eq!(order.len(), 2);
    rival_claim(&fx, order[0].handle.trim_start_matches('~'));
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let started = ws
        .work_next(&WorkOptions::default(), MAX_ATTEMPTS)
        .expect("next");
    assert_eq!(started.handle, order[1].handle);
    assert!(leases.live_lease(order[0].id).expect("lease").is_none());
}

// frob:tests work_next
#[test]
fn work_next_refuses_when_every_candidate_is_taken_or_none_exist() {
    let Some(fx) = Fixture::new(None) else { return };
    let (ledger, leases) = (fx.ledger(), fx.leases());
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let none = ws
        .work_next(&WorkOptions::default(), MAX_ATTEMPTS)
        .expect_err("empty");
    assert!(matches!(&none, WorktreeError::Refused(r) if r.code == E_NO_DOABLE));
    let (_, handle) = new_ticket(&ledger);
    rival_claim(&fx, &handle);
    let lost = ws
        .work_next(&WorkOptions::default(), MAX_ATTEMPTS)
        .expect_err("lost");
    assert!(matches!(&lost, WorktreeError::Refused(r) if r.code == E_NO_DOABLE));
}

// frob:tests is_skippable
#[test]
fn only_candidate_scoped_refusals_are_skippable() {
    assert!(frob_worktree::next::is_skippable("E-CLAIM-LOST"));
    assert!(frob_worktree::next::is_skippable("E-LEASE-HELD"));
    assert!(!frob_worktree::next::is_skippable("E-PM-CYCLE-OVERDUE"));
    assert!(!frob_worktree::next::is_skippable("E-WIP-REPO"));
}
