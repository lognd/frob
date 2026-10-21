//! `Workspace::restore_claim` against a real bare remote: success, taken, nothing parked and offline (system git required).
// frob:ticket 01M5DN9Q57S88B7DQQH8BAXZ01

use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration;

use frob_lease::{LeaseConfig, LeaseStore};
use frob_ledger::event::EventBody;
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig};
use frob_worktree::claim::remote_claim;
use frob_worktree::claim_restore::{E_RESTORE_NOTHING, E_RESTORE_OFFLINE, E_RESTORE_TAKEN};
use frob_worktree::evict::{EvictOutcome, EvictRequest, evict};
use frob_worktree::{WorkOptions, Workspace, WorktreeConfig, WorktreeError};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use gob_git::{CommitOptions, RelPath, Repo};

const MAIN: &str = "refs/heads/main";
const T: Duration = Duration::from_secs(30);

fn git(cwd: &Path, args: &[&str]) -> bool {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|s| (*s).to_owned()).collect(),
        cwd: Some(cwd.to_path_buf()),
        env: Vec::new(),
        timeout: T,
        capture: true,
    };
    matches!(
        Runner::new(Limits { jobs: 1 }).run(&spec),
        Ok(o) if o.status == Outcome::Exited(0)
    )
}

/// A repository on `main` with a root commit and an `origin` remote.
struct Fixture {
    _tmp: tempfile::TempDir,
    root: PathBuf,
}

impl Fixture {
    fn new(remote_url: Option<&str>) -> Option<Self> {
        let tmp = tempfile::tempdir().ok()?;
        let root = tmp.path().join("repo");
        let bare = tmp.path().join("origin.git");
        std::fs::create_dir(&root).ok()?;
        std::fs::create_dir(&bare).ok()?;
        if !git(&bare, &["init", "--bare", "--quiet"]) {
            return None;
        }
        let repo = Repo::init(&root).ok()?;
        std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").ok()?;
        let cfg = std::fs::read_to_string(repo.git_dir().join("config")).ok()?;
        std::fs::write(
            repo.git_dir().join("config"),
            format!("{cfg}[user]\n\tname = Test User\n\temail = test@example.com\n"),
        )
        .ok()?;
        drop(repo);
        let repo = Repo::discover(&root).ok()?;
        repo.commit_paths(
            MAIN,
            &[(RelPath::new("README.md").ok()?, Some(b"hi\n".to_vec()))],
            "root",
            &CommitOptions::default(),
        )
        .ok()?;
        let url = remote_url.map_or_else(
            || gob_path::Shown::with_home(&bare, None).to_string(),
            str::to_owned,
        );
        git(&root, &["remote", "add", "origin", &url]).then_some(Self { _tmp: tmp, root })
    }

    fn repo(&self) -> Repo {
        Repo::discover(&self.root).expect("repo")
    }

    fn ledger(&self) -> Ledger {
        Ledger::open(
            self.repo(),
            LedgerConfig::default(),
            Arc::new(gob_time::SystemClock),
        )
    }

    fn leases(&self) -> LeaseStore {
        LeaseStore::open(
            &self.repo(),
            LeaseConfig::default(),
            Arc::new(gob_time::SystemClock),
        )
        .expect("leases")
    }

    fn tip(&self, branch: &str) -> Option<String> {
        remote_claim(&self.repo(), "origin", branch, T)
            .expect("spawn")
            .expect("answer")
    }

    /// Publish `ticket/<handle>` at `main` and evict it, leaving `parked/<handle>-1`.
    fn park(&self, handle: &str) -> String {
        let dst = format!("{MAIN}:refs/heads/ticket/{handle}");
        assert!(git(&self.root, &["push", "--quiet", "origin", &dst]));
        let observed = self.tip(&format!("ticket/{handle}")).expect("claim tip");
        let req = EvictRequest {
            handle: handle.to_owned(),
            holder: "ann".to_owned(),
            evictor: "bob".to_owned(),
            observed: observed.clone(),
            idle_secs: 300,
            window_secs: 200,
            reason: "gone".to_owned(),
        };
        let out = evict(&self.repo(), &req).expect("evict");
        assert!(matches!(out, EvictOutcome::Evicted { .. }), "{out:?}");
        observed
    }
}

fn new_ticket(ledger: &Ledger) -> (String, String) {
    let mut req = NewTicket::new("Restore me", TicketType::Task);
    req.scope = vec!["crates/x/**".to_owned()];
    let id = ledger.new_ticket(req).expect("new").ticket.front.id;
    let handle = ledger.show(id).expect("show").summary.handle;
    (id.to_string(), handle.trim_start_matches('~').to_owned())
}

fn code(err: &WorktreeError) -> &str {
    match err {
        WorktreeError::Refused(r) => &r.code,
        other => panic!("not a refusal: {other}"),
    }
}

// frob:tests crates/frob-worktree/src/claim_restore.rs::restore_claim
#[test]
fn restore_puts_parked_work_back_and_records_a_lease_event() {
    let Some(fx) = Fixture::new(None) else { return };
    let (ledger, leases) = (fx.ledger(), fx.leases());
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let (id, handle) = new_ticket(&ledger);
    fx.park(&handle);
    assert_eq!(fx.tip(&format!("ticket/{handle}")), None);
    let done = ws.restore_claim(&id, "owner is back").expect("restore");
    assert_eq!(done.parked, format!("parked/{handle}-1"));
    assert_eq!(fx.tip(&format!("ticket/{handle}")), Some(done.tip.clone()));
    let ops: Vec<_> = ledger
        .events(ledger.resolve(&id).expect("id"))
        .expect("events")
        .into_iter()
        .filter_map(|e| match e.body {
            EventBody::Lease(l) => Some(l),
            _ => None,
        })
        .collect();
    assert_eq!(ops.len(), 1, "{ops:?}");
    assert_eq!(ops[0].op, frob_ledger::event::LeaseOp::Restore);
    assert_eq!(ops[0].tip.as_deref(), Some(done.tip.as_str()));
    assert_eq!(ops[0].reason.as_deref(), Some("owner is back"));
    let again = ws
        .restore_claim(&id, "twice")
        .expect_err("already restored");
    assert!(
        matches!(again, WorktreeError::Refused(_)),
        "second restore refused: {again}"
    );
}

// frob:tests crates/frob-worktree/src/claim_restore.rs::restore_claim
#[test]
fn a_reclaimed_ticket_refuses_the_restore_as_taken() {
    let Some(fx) = Fixture::new(None) else { return };
    let (ledger, leases) = (fx.ledger(), fx.leases());
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let (id, handle) = new_ticket(&ledger);
    fx.park(&handle);
    ws.work(&id, &WorkOptions::default()).expect("reclaim");
    let err = ws.restore_claim(&id, "too late").expect_err("taken");
    assert_eq!(code(&err), E_RESTORE_TAKEN);
}

// frob:tests crates/frob-worktree/src/claim_restore.rs::restore_claim
#[test]
fn nothing_parked_refuses_the_restore() {
    let Some(fx) = Fixture::new(None) else { return };
    let (ledger, leases) = (fx.ledger(), fx.leases());
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let (id, _) = new_ticket(&ledger);
    let err = ws.restore_claim(&id, "nothing").expect_err("nothing");
    assert_eq!(code(&err), E_RESTORE_NOTHING);
}

// frob:tests crates/frob-worktree/src/claim_restore.rs::restore_claim
#[test]
fn an_unreachable_remote_refuses_the_restore_as_offline() {
    let Some(fx) = Fixture::new(Some("/nonexistent/frob-restore-remote.git")) else {
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
    let err = ws.restore_claim(&id, "offline").expect_err("offline");
    assert_eq!(code(&err), E_RESTORE_OFFLINE);
}
