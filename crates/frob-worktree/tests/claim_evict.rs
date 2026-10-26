//! `claim evict`: end an idle claim by hand, with the rate report and the flap guard (system git required).
// frob:ticket 01M5DTGG9XWMEBRA51PA6CYWAE

use std::path::{Path, PathBuf};
use std::time::Duration;

use frob_lease::{LeaseConfig, LeaseStore};
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig};
use frob_worktree::claim_evict::{E_EVICT_CONFIRM, E_EVICT_NO_CLAIM};
use frob_worktree::{WorkOptions, Workspace, WorktreeConfig, WorktreeError};
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

fn new_ticket(ledger: &Ledger) -> (String, String) {
    let mut req = NewTicket::new("Claim me", TicketType::Task);
    req.scope = vec!["crates/x/**".to_owned()];
    let id = ledger.new_ticket(req).expect("new").ticket.front.id;
    let handle = ledger.show(id).expect("show").summary.handle;
    (id.to_string(), handle.trim_start_matches('~').to_owned())
}

fn evict_policy(auto: bool) -> frob_worktree::next::EvictPolicy {
    evict_policy_at(auto, 0)
}

/// Local-day offset (seconds east of UTC) that puts `secs_ahead` from now at local noon, so a test spanning a few hours never straddles midnight.
fn noon_offset(secs_ahead: i64) -> i64 {
    let at = gob_time::SystemClock.now().unix() + secs_ahead;
    (12 * 3600 - at.rem_euclid(86_400)).rem_euclid(86_400)
}

fn evict_policy_at(auto: bool, utc_offset_secs: i64) -> frob_worktree::next::EvictPolicy {
    let claims = frob_ledger::claim_window::ClaimsTable {
        evict_agent: if auto {
            frob_ledger::claim_window::EvictKnob::Auto
        } else {
            frob_ledger::claim_window::EvictKnob::Confirm
        },
        ..frob_ledger::claim_window::ClaimsTable::default()
    };
    let class = frob_ledger::claim_window::ClaimsClassTable::default();
    frob_worktree::next::EvictPolicy {
        windows: frob_ledger::claim_window::ClaimWindows::from_tables(&claims, &class)
            .expect("windows"),
        utc_offset_secs,
        in_ci: false,
    }
}

/// A policy with `[claims] evict_human` set to `confirm` or `auto`.
fn human_policy(confirm: bool) -> frob_worktree::next::EvictPolicy {
    let mut p = evict_policy(true);
    let claims = frob_ledger::claim_window::ClaimsTable {
        evict_human: if confirm {
            frob_ledger::claim_window::EvictKnob::Confirm
        } else {
            frob_ledger::claim_window::EvictKnob::Auto
        },
        ..frob_ledger::claim_window::ClaimsTable::default()
    };
    let class = frob_ledger::claim_window::ClaimsClassTable::default();
    p.windows =
        frob_ledger::claim_window::ClaimWindows::from_tables(&claims, &class).expect("windows");
    p
}

/// Claim `handle` as an agent and seed this clone's observation so idle time counts from now.
fn agent_claim(fx: &Fixture, leases: &LeaseStore, handle: &str) {
    let ledger = fx.ledger();
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases,
        config: &cfg,
    };
    ws.work(&format!("~{handle}"), &WorkOptions::default())
        .expect("agent claim");
    // A re-claim resumes the old local branch; publish it again as the claim.
    let branch = format!("ticket/{handle}");
    git(&fx.root, &["push", "--quiet", "origin", &branch]);
    let repo = Repo::discover(&fx.root).expect("repo");
    let tip = frob_worktree::claim::remote_claim(
        &repo,
        "origin",
        &format!("ticket/{handle}"),
        Duration::from_secs(10),
    )
    .expect("probe")
    .expect("online")
    .expect("claim branch");
    let id = ledger
        .resolve(&format!("~{handle}"))
        .expect("id")
        .to_string();
    let mut seen = frob_worktree::activity::ObservedClaims::load(
        &frob_worktree::activity::observed_path(&repo),
    );
    seen.claims.insert(
        id,
        frob_worktree::activity::ClaimObservation {
            tip: Some(tip.clone()),
            hard: Some(frob_worktree::activity::Seen {
                key: tip,
                first_seen: gob_time::SystemClock.now().unix(),
            }),
            soft: None,
        },
    );
    seen.save(&frob_worktree::activity::observed_path(&repo))
        .expect("seed");
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

fn code(e: WorktreeError) -> String {
    match e {
        WorktreeError::Refused(r) => r.code,
        other => other.to_string(),
    }
}

// frob:tests evict_claim
#[test]
fn an_idle_claim_is_evicted_with_the_rate_reported_and_a_repeat_needs_yes() {
    let Some(fx) = Fixture::new(None) else { return };
    let leases = fx.leases().with_agent(Some("claude".to_owned()));
    let (_, handle) = new_ticket(&fx.ledger());
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    // The rate counts the local day; centre the 5h..10h span on local noon so the
    // test does not depend on the time of day it runs at (it failed after 14:00 UTC).
    let policy = evict_policy_at(true, noon_offset(7 * 3600 + 1800));
    let rate = policy.windows.evict_rate();
    agent_claim(&fx, &leases, &handle);
    let ledger = ledger_ahead(&fx, 5 * 3600);
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let t = format!("~{handle}");
    let first = ws
        .evict_claim(&t, "stalled", false, &policy)
        .expect("evict");
    assert!(first.parked.contains(&handle), "{}", first.parked);
    assert_eq!(first.rate_left, rate - 1);
    assert!(!first.flapped);
    // Nothing left to evict.
    let again = ws.evict_claim(&t, "stalled", false, &policy).unwrap_err();
    assert_eq!(code(again), E_EVICT_NO_CLAIM);
    // The same holder claims again and idles again: a repeat inside 14 days.
    agent_claim(&fx, &leases, &handle);
    let ledger = ledger_ahead(&fx, 10 * 3600);
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let refused = ws.evict_claim(&t, "stalled", false, &policy).unwrap_err();
    assert_eq!(code(refused), E_EVICT_CONFIRM);
    let second = ws
        .evict_claim(&t, "stalled", true, &policy)
        .expect("confirmed");
    assert!(second.flapped);
    assert_eq!(second.rate_left, rate.saturating_sub(2));
}

// frob:tests evict_claim
#[test]
fn a_fresh_claim_and_a_missing_reason_are_refused() {
    let Some(fx) = Fixture::new(None) else { return };
    let leases = fx.leases().with_agent(Some("claude".to_owned()));
    let (_, handle) = new_ticket(&fx.ledger());
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    agent_claim(&fx, &leases, &handle);
    let ledger = fx.ledger();
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let t = format!("~{handle}");
    let policy = evict_policy(true);
    let fresh = ws.evict_claim(&t, "why", false, &policy).unwrap_err();
    assert_eq!(code(fresh), "E-CLAIM-NOT-IDLE");
    let blank = ws.evict_claim(&t, "  ", false, &policy).unwrap_err();
    assert!(matches!(blank, WorktreeError::Usage(_)));
}

// frob:ticket 01M5DZJ9CK1TJFCDX2T2NF1WE3
// frob:tests evict_claim
#[test]
fn evict_human_confirm_needs_yes_for_a_human_holder_and_auto_does_not() {
    let Some(fx) = Fixture::new(None) else { return };
    let leases = fx.leases().with_agent(None);
    let (_, handle) = new_ticket(&fx.ledger());
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    agent_claim(&fx, &leases, &handle);
    let ledger = ledger_ahead(&fx, 4 * 24 * 3600);
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let t = format!("~{handle}");
    let refused = ws
        .evict_claim(&t, "away", false, &human_policy(true))
        .unwrap_err();
    assert_eq!(code(refused), E_EVICT_CONFIRM);
    let done = ws
        .evict_claim(&t, "away", false, &human_policy(false))
        .expect("auto evicts a human claim");
    assert!(!done.flapped);
}

// frob:ticket 01M5DZJ99WRFPNK6WS3KZWDC0G
// frob:tests evict_claim_confirming
#[test]
fn evict_confirming_asks_and_a_no_refuses_while_a_yes_evicts() {
    let Some(fx) = Fixture::new(None) else { return };
    let leases = fx.leases().with_agent(None);
    let (_, handle) = new_ticket(&fx.ledger());
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    agent_claim(&fx, &leases, &handle);
    let ledger = ledger_ahead(&fx, 4 * 24 * 3600);
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let t = format!("~{handle}");
    let mut asked = Vec::new();
    let no = ws
        .evict_claim_confirming(&t, "away", &human_policy(true), &mut |q| {
            asked.push(q.to_owned());
            false
        })
        .unwrap_err();
    assert_eq!(code(no), E_EVICT_CONFIRM);
    assert_eq!(asked.len(), 1);
    ws.evict_claim_confirming(&t, "away", &human_policy(true), &mut |_| true)
        .expect("a yes evicts");
}
