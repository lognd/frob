//! Publishing the claim on `work`: create-only push, loser refusal and the offline warning (system git required).
// frob:ticket 01M5CW04QCRZ860BZMT46BECG2

use std::path::{Path, PathBuf};
use std::time::Duration;

use frob_lease::{LeaseConfig, LeaseStore};
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig};
use frob_worktree::claim::{E_CLAIM_LOST, W_CLAIM_UNPUBLISHED, remote_claim};
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
    bare: PathBuf,
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
        Some(Self {
            _tmp: tmp,
            root,
            bare,
        })
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

fn remote_tip(fx: &Fixture, handle: &str) -> Option<String> {
    let repo = Repo::discover(&fx.root).expect("repo");
    remote_claim(
        &repo,
        "origin",
        &format!("ticket/{handle}"),
        Duration::from_secs(30),
    )
    .expect("spawn")
    .expect("answer")
}

// frob:tests crates/frob-worktree/src/claim.rs::publish
#[test]
fn work_publishes_the_claim_branch_with_a_create_only_push() {
    let Some(fx) = Fixture::new(None) else { return };
    let (ledger, leases) = (fx.ledger(), fx.leases());
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let (id, handle) = new_ticket(&ledger);
    let base = Repo::discover(&fx.root)
        .expect("repo")
        .rev_parse(MAIN)
        .expect("main");
    let started = ws.work(&id, &WorkOptions::default()).expect("work");
    assert!(
        started
            .warnings
            .iter()
            .all(|w| !w.contains(W_CLAIM_UNPUBLISHED))
    );
    assert_eq!(remote_tip(&fx, &handle), Some(base.to_string()));
}

// frob:tests crates/frob-worktree/src/claim.rs::classify_rejection
#[test]
fn a_branch_already_on_the_remote_loses_the_claim_and_releases_the_lease() {
    let Some(fx) = Fixture::new(None) else { return };
    let (ledger, leases) = (fx.ledger(), fx.leases());
    let (id, handle) = new_ticket(&ledger);
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
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let err = ws.work(&id, &WorkOptions::default()).expect_err("lost");
    match &err {
        WorktreeError::Refused(r) => assert_eq!(r.code, E_CLAIM_LOST),
        other => panic!("not a refusal: {other}"),
    }
    assert!(
        leases
            .live_lease(ledger.resolve(&id).expect("id"))
            .expect("lease")
            .is_none()
    );
    assert!(fx.bare.exists());
}

// frob:tests crates/frob-worktree/src/claim.rs::publish
#[test]
fn an_unreachable_remote_warns_and_proceeds_with_an_unpublished_claim() {
    let Some(fx) = Fixture::new(Some("/nonexistent/frob-claim-remote.git")) else {
        return;
    };
    let (ledger, leases) = (fx.ledger(), fx.leases());
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let (id, _) = new_ticket(&ledger);
    let started = ws
        .work(&id, &WorkOptions::default())
        .expect("work proceeds offline");
    assert!(started.created_worktree);
    assert!(
        started
            .warnings
            .iter()
            .any(|w| w.starts_with(W_CLAIM_UNPUBLISHED)),
        "{:?}",
        started.warnings
    );
}
