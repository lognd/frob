//! Idle-window notices for live claims (system git required).
// frob:ticket 01M5DCZ3PVHP2ZNP9SVYFFQSVP

use std::path::{Path, PathBuf};
use std::time::Duration;

use frob_lease::{LeaseConfig, LeaseStore};
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig};
use frob_worktree::{WorkOptions, Workspace, WorktreeConfig};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use gob_git::{CommitOptions, RelPath, Repo};
use gob_time::Clock as _;

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

fn policy() -> frob_worktree::next::EvictPolicy {
    let claims = frob_ledger::claim_window::ClaimsTable::default();
    let class = frob_ledger::claim_window::ClaimsClassTable::default();
    frob_worktree::next::EvictPolicy {
        windows: frob_ledger::claim_window::ClaimWindows::from_tables(&claims, &class)
            .expect("windows"),
        utc_offset_secs: 0,
        in_ci: false,
    }
}

/// A ledger whose clock reads `secs` seconds from now, to age a claim without sleeping.
fn ledger_ahead(fx: &Fixture, secs: i64) -> Ledger {
    let at = gob_time::Stamp::from_unix(gob_time::SystemClock.now().unix() + secs);
    Ledger::open(
        Repo::discover(&fx.root).expect("repo"),
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::FixedClock::new(at)),
    )
}

/// Claim a fresh ticket and seed this clone's observation of it at the real now.
fn claimed(fx: &Fixture, leases: &LeaseStore) -> String {
    let ledger = fx.ledger();
    let mut req = NewTicket::new("Claim me", TicketType::Task);
    req.scope = vec!["crates/x/**".to_owned()];
    let id = ledger.new_ticket(req).expect("new").ticket.front.id;
    let handle = ledger.show(id).expect("show").summary.handle;
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    Workspace {
        ledger: &ledger,
        leases,
        config: &cfg,
    }
    .work(&handle, &WorkOptions::default())
    .expect("claim");
    let repo = Repo::discover(&fx.root).expect("repo");
    let now = gob_time::SystemClock.now().unix();
    let mut seen = frob_worktree::activity::ObservedClaims::load(
        &frob_worktree::activity::observed_path(&repo),
    );
    seen.claims.insert(
        id.to_string(),
        frob_worktree::activity::ClaimObservation {
            tip: Some("t".to_owned()),
            hard: Some(frob_worktree::activity::Seen {
                key: "t".to_owned(),
                first_seen: now,
            }),
            soft: None,
            acked_rank: None,
        },
    );
    seen.save(&frob_worktree::activity::observed_path(&repo))
        .expect("seed");
    handle
}

// frob:tests claim_idle_notices
// frob:tests crates/frob-worktree/src/claim_notice.rs::ClaimNotice.line
#[test]
fn a_fresh_claim_is_quiet_and_an_old_one_warns_its_holder() {
    let Some(fx) = Fixture::new(None) else { return };
    let leases = fx.leases();
    let handle = claimed(&fx, &leases);
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let fresh = fx.ledger();
    let ws = Workspace {
        ledger: &fresh,
        leases: &leases,
        config: &cfg,
    };
    let quiet = ws.claim_idle_notices(&policy()).expect("notices");
    assert_eq!(quiet.len(), 1);
    assert!(quiet[0].mine);
    assert_eq!(quiet[0].line(), None);

    let later = ledger_ahead(&fx, 6 * 86_400);
    let ws = Workspace {
        ledger: &later,
        leases: &leases,
        config: &cfg,
    };
    let aged = ws.claim_idle_notices(&policy()).expect("notices");
    assert_eq!(aged[0].handle, handle);
    let line = aged[0].line().expect("holder line");
    assert!(line.contains(&handle), "{line}");
    assert!(
        aged[0]
            .others_line
            .as_deref()
            .is_some_and(|l| l.contains("evictable"))
    );
}

// frob:tests ack_claim_notices
// frob:tests crates/frob-worktree/src/activity.rs::ObservedClaims.set_acked_rank
#[test]
fn acknowledging_silences_the_holder_until_the_next_threshold() {
    let Some(fx) = Fixture::new(None) else { return };
    let leases = fx.leases();
    let handle = claimed(&fx, &leases);
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let later = ledger_ahead(&fx, 6 * 86_400);
    let ws = Workspace {
        ledger: &later,
        leases: &leases,
        config: &cfg,
    };
    assert!(
        ws.claim_idle_notices(&policy()).expect("n")[0]
            .line()
            .is_some()
    );
    let acked = ws.ack_claim_notices(&policy()).expect("ack");
    assert_eq!(acked, vec![handle]);
    let after = ws.claim_idle_notices(&policy()).expect("n");
    assert_eq!(after[0].line(), None);
    assert!(after[0].others_line.is_some(), "others still see it");
}
