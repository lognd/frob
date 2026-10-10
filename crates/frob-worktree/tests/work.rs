//! `work`, `start` and `requeue` end to end in temporary repositories (system git required).
// frob:ticket 01M4069T76A6WSNHT3NZERXHAH
// frob:ticket 01M4069VZVMHVZ15RSPZQRNCXY

use std::path::{Path, PathBuf};
use std::time::Duration;

use frob_lease::{LeaseConfig, LeaseStore};
use frob_ledger::index::ListFilter;
use frob_ledger::model::{Category, Class, TicketType};
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig, TicketId};
use frob_worktree::{WorkOptions, Workspace, WorktreeConfig, WorktreeError};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use gob_git::{CommitOptions, RelPath, Repo};

const MAIN: &str = "refs/heads/main";

fn git_available() -> bool {
    let spec = Spec {
        program: Program::Git,
        args: vec!["--version".to_owned()],
        cwd: None,
        env: Vec::new(),
        timeout: Duration::from_secs(10),
        capture: true,
    };
    matches!(
        Runner::new(Limits { jobs: 1 }).run(&spec),
        Ok(o) if o.status == Outcome::Exited(0)
    )
}

/// A repository `<tmp>/repo` on `main` with a root commit, plus its sibling `<tmp>/repo-wt`.
struct Fixture {
    _tmp: tempfile::TempDir,
    root: PathBuf,
}

impl Fixture {
    fn new() -> Self {
        let tmp = tempfile::tempdir().expect("tempdir");
        let root = tmp.path().join("repo");
        std::fs::create_dir(&root).expect("mkdir");
        let repo = Repo::init(&root).expect("init");
        std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").expect("head");
        let cfg = std::fs::read_to_string(repo.git_dir().join("config")).expect("config");
        std::fs::write(
            repo.git_dir().join("config"),
            format!(
                "{cfg}[user]\n\tname = Test User\n\temail = test@example.com\n[core]\n\tautocrlf = false\n"
            ),
        )
        .expect("identity");
        drop(repo);
        let repo = Repo::discover(&root).expect("discover");
        repo.commit_paths(
            MAIN,
            &[(
                RelPath::new("README.md").expect("path"),
                Some(b"hello\n".to_vec()),
            )],
            "root",
            &CommitOptions::default(),
        )
        .expect("root commit");
        Self { _tmp: tmp, root }
    }

    fn ledger(&self, actor: Option<&str>) -> Ledger {
        let cfg = LedgerConfig {
            actor: actor.map(str::to_owned),
            ..LedgerConfig::default()
        };
        Ledger::open(
            Repo::discover(&self.root).expect("repo"),
            cfg,
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

    fn ticket(ledger: &Ledger, title: &str, ty: TicketType, scope: &[&str]) -> TicketId {
        let mut req = NewTicket::new(title, ty);
        req.scope = scope.iter().map(|s| (*s).to_owned()).collect();
        ledger.new_ticket(req).expect("new").ticket.front.id
    }
}

fn category(ledger: &Ledger, id: TicketId) -> Category {
    ledger.show(id).expect("show").summary.category
}

fn refusal_code(e: &WorktreeError) -> String {
    match e {
        WorktreeError::Refused(r) => r.code.clone(),
        other => panic!("not a refusal: {other}"),
    }
}

#[test]
fn work_creates_worktree_and_is_idempotent_for_the_holder() {
    if !git_available() {
        eprintln!("git not available; skipping");
        return;
    }
    let fx = Fixture::new();
    let ledger = fx.ledger(None);
    let leases = fx.leases();
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let id = Fixture::ticket(&ledger, "Do it", TicketType::Task, &["crates/x/**"]);

    let first = ws
        .work(&id.to_string(), &WorkOptions::default())
        .expect("work");
    assert!(!first.already && first.created_worktree);
    let expected_parent = fx.root.parent().expect("parent").join("repo-wt");
    assert_eq!(first.path.parent(), Some(expected_parent.as_path()));
    assert!(first.path.join("README.md").exists());
    let branch = first.branch.clone().expect("branch");
    assert!(branch.starts_with("ticket/"), "{branch}");
    assert_eq!(first.merge.as_deref(), Some("up-to-date"));
    assert_eq!(category(&ledger, id), Category::InProgress);
    assert_eq!(first.lease.holder.worktree, first.path);
    assert_eq!(first.lease.scope, ["crates/x/**"]);
    let worktrees = Repo::discover(&fx.root)
        .expect("repo")
        .list_worktrees()
        .expect("list");
    assert!(
        worktrees
            .iter()
            .any(|w| w.branch.as_deref() == Some(branch.as_str())),
        "{worktrees:?}"
    );
    let events = ledger.events(id).expect("events");
    assert!(events.iter().any(|e| matches!(
        &e.body,
        frob_ledger::event::EventBody::Transition(t)
            if t.to == Category::InProgress && t.reason.as_deref().is_some_and(|r| r.contains("lease:"))
    )));

    let again = ws
        .work(&id.to_string(), &WorkOptions::default())
        .expect("again");
    assert!(again.already, "second call is idempotent");
    assert!(!again.created_worktree);
    assert_eq!(again.path, first.path);
    assert_eq!(leases.list().expect("list").len(), 1);
}

#[test]
fn another_holder_is_refused_and_can_steal_with_a_reason() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let alice = fx.ledger(Some("alice"));
    let bob = fx.ledger(Some("bob"));
    let leases = fx.leases();
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws_a = Workspace {
        ledger: &alice,
        leases: &leases,
        config: &cfg,
    };
    let ws_b = Workspace {
        ledger: &bob,
        leases: &leases,
        config: &cfg,
    };
    let id = Fixture::ticket(&alice, "Do it", TicketType::Task, &["src/newmod/**"]);
    let other = Fixture::ticket(&alice, "Overlaps", TicketType::Task, &["src/newmod/a.rs"]);
    ws_a.work(&id.to_string(), &WorkOptions::default())
        .expect("alice works");

    let err = ws_b
        .work(&id.to_string(), &WorkOptions::default())
        .expect_err("held");
    let WorktreeError::Refused(r) = &err else {
        panic!("{err}")
    };
    assert_eq!(r.code, "E-LEASE-HELD");
    assert!(r.message.contains("alice"), "{}", r.message);
    assert!(r.class.retryable());
    assert!(r.remedy.as_deref().is_some_and(|c| c.contains("--steal")));

    let err = ws_b
        .work(&other.to_string(), &WorkOptions::default())
        .expect_err("overlap");
    assert_eq!(refusal_code(&err), "E-LEASE-HELD");
    assert_eq!(
        category(&bob, other),
        Category::Todo,
        "refused work changes nothing"
    );

    let stolen = ws_b
        .work(
            &id.to_string(),
            &WorkOptions {
                worktree: None,
                steal: Some("alice is gone".to_owned()),
                unplanned: None,
                sprint_gate: false,
            },
        )
        .expect("steal");
    assert_eq!(
        stolen.stolen_from.as_ref().map(|h| h.actor.as_str()),
        Some("alice")
    );
    assert_eq!(stolen.lease.holder.actor, "bob");
    assert_eq!(stolen.lease.history.len(), 1);
    let events = bob.events(id).expect("events");
    assert!(
        events.iter().any(|e| matches!(
            &e.body,
            frob_ledger::event::EventBody::Comment(c) if c.body.contains("alice is gone")
        )),
        "the steal is logged as an event: {events:?}"
    );
}

/// Lease and steal events record the worktree relative to the repository parent, never an absolute path.
// frob:tests crates/frob-worktree/src/work.rs::Workspace.ledger_path
#[test]
fn work_events_carry_no_absolute_path() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let alice = fx.ledger(Some("alice"));
    let bob = fx.ledger(Some("bob"));
    let leases = fx.leases();
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws_a = Workspace {
        ledger: &alice,
        leases: &leases,
        config: &cfg,
    };
    let ws_b = Workspace {
        ledger: &bob,
        leases: &leases,
        config: &cfg,
    };
    let id = Fixture::ticket(&alice, "Do it", TicketType::Task, &["src/newmod/**"]);
    let started = ws_a
        .work(&id.to_string(), &WorkOptions::default())
        .expect("work");
    ws_b.work(
        &id.to_string(),
        &WorkOptions {
            worktree: None,
            steal: Some("alice is gone".to_owned()),
            unplanned: None,
            sprint_gate: false,
        },
    )
    .expect("steal");
    let tmp = fx
        .root
        .parent()
        .expect("tmp parent")
        .to_string_lossy()
        .into_owned();
    let text = format!("{:?}", bob.events(id).expect("events"));
    assert!(!text.contains(&tmp), "no absolute path in events: {text}");
    let name = started
        .path
        .file_name()
        .expect("name")
        .to_string_lossy()
        .into_owned();
    assert!(
        text.contains(&format!("repo-wt/{name}")),
        "the worktree is recorded relative to the repository parent: {text}"
    );
    assert_eq!(
        started.lease.holder.worktree, started.path,
        "the live lease registry keeps the absolute path"
    );
}

#[test]
fn concurrent_work_on_overlapping_tickets_grants_exactly_one() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let ledger = fx.ledger(Some("alice"));
    let a = Fixture::ticket(&ledger, "A", TicketType::Task, &["src/newmod/**"]);
    let b = Fixture::ticket(&ledger, "B", TicketType::Task, &["src/newmod/**"]);
    drop(ledger);
    let barrier = std::sync::Arc::new(std::sync::Barrier::new(2));
    let threads: Vec<_> = [(a, "alice"), (b, "bob")]
        .into_iter()
        .map(|(id, who)| {
            let root = fx.root.clone();
            let barrier = std::sync::Arc::clone(&barrier);
            std::thread::spawn(move || {
                let repo = Repo::discover(&root).expect("repo");
                let leases = LeaseStore::open(
                    &repo,
                    LeaseConfig::default(),
                    std::sync::Arc::new(gob_time::SystemClock),
                )
                .expect("leases");
                let cfg = LedgerConfig {
                    actor: Some(who.to_owned()),
                    ..LedgerConfig::default()
                };
                let ledger = Ledger::open(repo, cfg, std::sync::Arc::new(gob_time::SystemClock));
                let wt = WorktreeConfig::load(&root).expect("config");
                let ws = Workspace {
                    ledger: &ledger,
                    leases: &leases,
                    config: &wt,
                };
                barrier.wait();
                ws.work(&id.to_string(), &WorkOptions::default())
                    .map(|s| s.lease.ticket)
            })
        })
        .collect();
    let results: Vec<_> = threads
        .into_iter()
        .map(|t| t.join().expect("thread"))
        .collect();
    let ok = results.iter().filter(|r| r.is_ok()).count();
    let held = results
        .iter()
        .filter(|r| matches!(r, Err(WorktreeError::Refused(x)) if x.code == "E-LEASE-HELD"))
        .count();
    assert_eq!((ok, held), (1, 1), "{results:?}");
    assert_eq!(fx.leases().list().expect("list").len(), 1);
}

#[test]
fn worktree_dir_knob_moves_the_worktree() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    std::fs::write(
        fx.root.join("frob.toml"),
        "[worktree]\ndir = \"../custom/{repo}\"\n",
    )
    .expect("toml");
    let ledger = fx.ledger(Some("alice"));
    let leases = fx.leases();
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let id = Fixture::ticket(&ledger, "Do it", TicketType::Task, &["x/**"]);
    let s = ws
        .work(&id.to_string(), &WorkOptions::default())
        .expect("work");
    let want = fx
        .root
        .parent()
        .expect("parent")
        .join("custom")
        .join("repo");
    assert_eq!(s.path.parent(), Some(want.as_path()));
}

#[test]
fn unworkable_tickets_are_refused() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let ledger = fx.ledger(Some("alice"));
    let other = fx.ledger(Some("bob"));
    let leases = fx.leases();
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let ws_b = Workspace {
        ledger: &other,
        leases: &leases,
        config: &cfg,
    };
    let epic = Fixture::ticket(&ledger, "Epic", TicketType::Epic, &[]);
    let err = ws
        .work(&epic.to_string(), &WorkOptions::default())
        .expect_err("epic");
    assert_eq!(refusal_code(&err), "E-TICKET-NOT-WORKABLE");

    let done = Fixture::ticket(&ledger, "Done", TicketType::Task, &["d/**"]);
    ledger
        .transition(
            done,
            Category::Done,
            Some(frob_ledger::model::Outcome::Done),
            None,
        )
        .expect("close");
    let err = ws
        .work(&done.to_string(), &WorkOptions::default())
        .expect_err("done");
    assert_eq!(refusal_code(&err), "E-TICKET-NOT-WORKABLE");

    let busy = Fixture::ticket(&ledger, "Busy", TicketType::Task, &["b/**"]);
    ledger
        .transition(busy, Category::InProgress, None, None)
        .expect("move");
    let err = ws_b
        .work(&busy.to_string(), &WorkOptions::default())
        .expect_err("busy");
    assert_eq!(refusal_code(&err), "E-TICKET-NOT-WORKABLE");
}

#[test]
fn start_leases_the_current_checkout_and_requeue_releases() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let ledger = fx.ledger(Some("alice"));
    let leases = fx.leases();
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let id = Fixture::ticket(&ledger, "Do it", TicketType::Task, &["s/**"]);

    let s = ws.start(&id.to_string(), &fx.root, None).expect("start");
    assert_eq!(s.path, fx.root);
    assert!(s.branch.is_none() && !s.created_worktree);
    assert!(
        ws.start(&id.to_string(), &fx.root, None)
            .expect("again")
            .already
    );
    assert_eq!(category(&ledger, id), Category::InProgress);

    assert!(matches!(
        ws.requeue(&id.to_string(), " "),
        Err(WorktreeError::Usage(_))
    ));
    let r = ws
        .requeue(&id.to_string(), "wrong approach")
        .expect("requeue");
    assert!(r.released.is_some() && !r.already);
    assert_eq!(category(&ledger, id), Category::Todo);
    assert!(leases.list().expect("list").is_empty());
    assert!(ws.requeue(&id.to_string(), "again").expect("again").already);
}

#[test]
fn doable_hides_tickets_overlapping_a_live_lease() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let ledger = fx.ledger(Some("alice"));
    let leases = fx.leases();
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let a = Fixture::ticket(&ledger, "A", TicketType::Task, &["src/newmod/**"]);
    let b = Fixture::ticket(&ledger, "B", TicketType::Task, &["src/newmod/x.rs"]);
    let c = Fixture::ticket(&ledger, "C", TicketType::Task, &["docs/**"]);
    ws.start(&a.to_string(), &fx.root, None).expect("start a");
    let guard = frob_lease::LeaseGuard::discover(
        &fx.root,
        frob_lease::LeaseConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    )
    .expect("guard");
    let ids: Vec<TicketId> = ledger
        .doable(&guard)
        .expect("doable")
        .iter()
        .map(|s| s.id)
        .collect();
    assert!(ids.contains(&c) && !ids.contains(&b), "{ids:?}");
    assert_eq!(ledger.list(&ListFilter::default()).expect("list").len(), 3);
}

fn json(out: &str) -> serde_json::Value {
    serde_json::from_str(out).unwrap_or_else(|e| panic!("json {e}: {out}"))
}

#[test]
fn cli_work_twice_reports_already_and_other_actor_gets_exit_3() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let ledger = fx.ledger(Some("alice"));
    let id = Fixture::ticket(&ledger, "Do it", TicketType::Task, &["crates/x/**"]);
    drop(ledger);
    let cli = frob_worktree::register(gob_cli::Cli::new("frob", "0.0.0"));
    let ticket = id.to_string();

    let (code, out, err) = gob_cli::run_for_test(&cli, &["work", &ticket], &fx.root);
    assert_eq!(code, 0, "{out}{err}");
    let first = json(&out);
    assert_eq!(first["already"], false);
    let (code, out, err) = gob_cli::run_for_test(&cli, &["work", &ticket], &fx.root);
    assert_eq!(code, 0, "{out}{err}");
    let second = json(&out);
    assert_eq!(second["already"], true);
    assert_eq!(second["data"]["path"], first["data"]["path"]);

    set_actor(&fx.root, "mallory");
    let (code, out, _) = gob_cli::run_for_test(&cli, &["work", &ticket], &fx.root);
    assert_eq!(code, 3, "{out}");
    let v = json(&out);
    assert_eq!(v["error"]["code"], "E-LEASE-HELD");
    assert!(
        v["error"]["message"]
            .as_str()
            .is_some_and(|m| m.contains("Test User"))
    );
    assert_eq!(v["error"]["retryable"], true);

    let (code, out, _) = gob_cli::run_for_test(&cli, &["work", &ticket, "--steal"], &fx.root);
    assert_eq!(code, 2, "--steal needs --reason: {out}");
    let (code, out, _) =
        gob_cli::run_for_test(&cli, &["requeue", &ticket, "--reason", "no"], &fx.root);
    assert_eq!(code, 3, "other actor cannot requeue a live lease: {out}");
}

/// Change the git identity so the next verb runs as a different actor.
fn set_actor(root: &Path, name: &str) {
    let config = root.join(".git/config");
    let text = std::fs::read_to_string(&config).expect("config");
    std::fs::write(&config, text.replace("Test User", name)).expect("write");
}

/// Take `n` disjoint tickets with `work`, returning their ids and the workspace pieces used.
fn fill_wip(ledger: &Ledger, leases: &LeaseStore, cfg: &WorktreeConfig, n: usize) -> Vec<TicketId> {
    let ws = Workspace {
        ledger,
        leases,
        config: cfg,
    };
    (0..n)
        .map(|i| {
            let scope = format!("area{i}/**");
            let id = Fixture::ticket(ledger, &format!("Holder {i}"), TicketType::Task, &[&scope]);
            ws.work(&id.to_string(), &WorkOptions::default())
                .expect("fill");
            id
        })
        .collect()
}

fn refusal_message(e: &WorktreeError) -> String {
    match e {
        WorktreeError::Refused(r) => r.message.clone(),
        other => panic!("not a refusal: {other}"),
    }
}

// frob:tests crates/frob-worktree/src/wip.rs::check
#[test]
fn work_refuses_past_the_repository_limit_naming_both_holders() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let ledger = fx.ledger(None);
    let leases = fx.leases();
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    fill_wip(&ledger, &leases, &cfg, 2);
    let limited = fx.leases().with_repo_limit(2);
    let ws = Workspace {
        ledger: &ledger,
        leases: &limited,
        config: &cfg,
    };
    let third = Fixture::ticket(&ledger, "Third", TicketType::Task, &["area9/**"]);
    let err = ws
        .work(&third.to_string(), &WorkOptions::default())
        .expect_err("third refused");
    assert_eq!(refusal_code(&err), "E-WIP-REPO");
    let msg = refusal_message(&err);
    assert!(
        msg.contains("Holder 0") && msg.contains("Holder 1"),
        "{msg}"
    );
    assert!(msg.contains("worktree") && msg.contains("since"), "{msg}");
    assert_eq!(category(&ledger, third), Category::Todo);
    // start obeys the same limit
    let err = ws
        .start(&third.to_string(), &fx.root, None)
        .expect_err("start refused");
    assert_eq!(refusal_code(&err), "E-WIP-REPO");
    // requeue frees a slot
    let held = ledger
        .list(&ListFilter {
            category: Some(Category::InProgress),
            ..ListFilter::default()
        })
        .expect("list");
    ws.requeue(&held[0].id.to_string(), "make room")
        .expect("requeue");
    ws.work(&third.to_string(), &WorkOptions::default())
        .expect("third fits now");
}

// frob:ticket 01M40Q3S4T9QTYX0Z1MPAZP9JM
// frob:tests crates/frob-worktree/src/wip.rs::check
// frob:tests crates/frob-worktree/src/work.rs::take
#[test]
fn concurrent_work_for_the_last_wip_slot_grants_exactly_one() {
    if !git_available() {
        return;
    }
    for round in 0..5 {
        let fx = Fixture::new();
        let ledger = fx.ledger(None);
        let cfg = WorktreeConfig::load(&fx.root).expect("config");
        fill_wip(&ledger, &fx.leases(), &cfg, 1);
        let a = Fixture::ticket(&ledger, "A", TicketType::Task, &["racea/**"]);
        let b = Fixture::ticket(&ledger, "B", TicketType::Task, &["raceb/**"]);
        drop(ledger);
        let barrier = std::sync::Arc::new(std::sync::Barrier::new(2));
        let threads: Vec<_> = [(a, "alice"), (b, "bob")]
            .into_iter()
            .map(|(id, who)| {
                let root = fx.root.clone();
                let barrier = std::sync::Arc::clone(&barrier);
                std::thread::spawn(move || {
                    let repo = Repo::discover(&root).expect("repo");
                    let leases = LeaseStore::open(
                        &repo,
                        LeaseConfig::default(),
                        std::sync::Arc::new(gob_time::SystemClock),
                    )
                    .expect("leases")
                    .with_repo_limit(2);
                    let cfg = LedgerConfig {
                        actor: Some(who.to_owned()),
                        ..LedgerConfig::default()
                    };
                    let ledger =
                        Ledger::open(repo, cfg, std::sync::Arc::new(gob_time::SystemClock));
                    let wt = WorktreeConfig::load(&root).expect("config");
                    let ws = Workspace {
                        ledger: &ledger,
                        leases: &leases,
                        config: &wt,
                    };
                    barrier.wait();
                    ws.work(&id.to_string(), &WorkOptions::default())
                        .map(|s| s.lease.ticket)
                })
            })
            .collect();
        let results: Vec<_> = threads
            .into_iter()
            .map(|t| t.join().expect("thread"))
            .collect();
        let ok = results.iter().filter(|r| r.is_ok()).count();
        let refused = results
            .iter()
            .filter(|r| matches!(r, Err(WorktreeError::Refused(x)) if x.code == "E-WIP-REPO"))
            .count();
        assert_eq!((ok, refused), (1, 1), "round {round}: {results:?}");
        assert_eq!(fx.leases().list().expect("list").len(), 2);
    }
}

// frob:tests crates/frob-worktree/src/wip.rs::check
#[test]
fn limit_zero_is_off_and_reentry_is_not_a_new_slot() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let ledger = fx.ledger(None);
    let leases = fx.leases();
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ids = fill_wip(&ledger, &leases, &cfg, 3);
    let off_leases = fx.leases().with_repo_limit(0);
    let off = Workspace {
        ledger: &ledger,
        leases: &off_leases,
        config: &cfg,
    };
    let more = Fixture::ticket(&ledger, "More", TicketType::Task, &["area8/**"]);
    off.work(&more.to_string(), &WorkOptions::default())
        .expect("limit 0 does not check");
    // Four in progress, limit 2: re-entering a held ticket still works.
    let tight_leases = fx.leases().with_repo_limit(2);
    let tight = Workspace {
        ledger: &ledger,
        leases: &tight_leases,
        config: &cfg,
    };
    let again = tight
        .work(&ids[0].to_string(), &WorkOptions::default())
        .expect("re-entry");
    assert!(again.already);
}

// frob:tests crates/frob-worktree/src/wip.rs::check
#[test]
fn a_stale_in_progress_ticket_does_not_count_and_is_named() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let ledger = fx.ledger(None);
    let leases = fx.leases();
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    fill_wip(&ledger, &leases, &cfg, 1);
    let stale = Fixture::ticket(&ledger, "Abandoned", TicketType::Task, &["old/**"]);
    ledger
        .transition(stale, Category::InProgress, None, None)
        .expect("in progress without a lease");
    let limited = fx.leases().with_repo_limit(2);
    let ws = Workspace {
        ledger: &ledger,
        leases: &limited,
        config: &cfg,
    };
    let next = Fixture::ticket(&ledger, "Next", TicketType::Task, &["area7/**"]);
    ws.work(&next.to_string(), &WorkOptions::default())
        .expect("stale does not count: one live holder, limit 2");
    let last = Fixture::ticket(&ledger, "Last", TicketType::Task, &["area6/**"]);
    let err = ws
        .work(&last.to_string(), &WorkOptions::default())
        .expect_err("two live holders now");
    let msg = refusal_message(&err);
    assert!(msg.contains("Stale") && msg.contains("Abandoned"), "{msg}");
    assert!(msg.contains("frob requeue"), "{msg}");
}

// frob:tests crates/frob-worktree/src/verbs.rs::Work
#[test]
fn cli_work_past_the_repository_limit_exits_3_with_the_wip_code() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    std::fs::write(fx.root.join("frob.toml"), "[pm.wip]\nin_progress = 1\n").expect("config");
    let ledger = fx.ledger(None);
    let a = Fixture::ticket(&ledger, "First", TicketType::Task, &["a/**"]);
    let b = Fixture::ticket(&ledger, "Second", TicketType::Task, &["b/**"]);
    drop(ledger);
    let cli = frob_worktree::register(gob_cli::Cli::new("frob", "0.0.0"));
    let (code, out, err) = gob_cli::run_for_test(&cli, &["work", &a.to_string()], &fx.root);
    assert_eq!(code, 0, "{out}{err}");
    let (code, out, _) = gob_cli::run_for_test(&cli, &["work", &b.to_string()], &fx.root);
    assert_eq!(code, 3, "{out}");
    let v = json(&out);
    assert_eq!(v["error"]["code"], "E-WIP-REPO");
    assert!(
        v["error"]["message"]
            .as_str()
            .is_some_and(|m| m.contains("First")),
        "{out}"
    );
    let (code, out, _) = gob_cli::run_for_test(&cli, &["work", "--here", &b.to_string()], &fx.root);
    assert_eq!(code, 3, "work --here obeys the limit: {out}");
    let (code, out, err) = gob_cli::run_for_test(&cli, &["start", &b.to_string()], &fx.root);
    assert_eq!(code, 3, "the start alias obeys the limit: {out}");
    assert!(err.contains("`start` is deprecated"), "{err}");
}

/// Commit `text` as `frob.toml` on the ledger ref, leaving the work tree file alone.
fn commit_base_config(fx: &Fixture, text: &str) {
    let repo = Repo::discover(&fx.root).expect("repo");
    repo.commit_paths(
        MAIN,
        &[(
            RelPath::new("frob.toml").expect("path"),
            Some(text.as_bytes().to_vec()),
        )],
        "raise the cap",
        &CommitOptions::default(),
    )
    .expect("commit config");
}

// frob:ticket 01M4GWKEMB266C6GTFEP4R3G7W
// frob:tests crates/frob-worktree/src/verbs.rs::Work
#[test]
fn work_takes_the_repository_wip_limit_from_the_base_ref_not_the_worktree_copy() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    // The worktree copy is stale (cap 1); the base ref raised it to 3.
    commit_base_config(&fx, "[pm.wip]\nin_progress = 3\n");
    std::fs::write(fx.root.join("frob.toml"), "[pm.wip]\nin_progress = 1\n").expect("stale");
    let ledger = fx.ledger(None);
    let a = Fixture::ticket(&ledger, "First", TicketType::Task, &["a/**"]);
    let b = Fixture::ticket(&ledger, "Second", TicketType::Task, &["b/**"]);
    drop(ledger);
    let cli = frob_worktree::register(gob_cli::Cli::new("frob", "0.0.0"));
    for t in [a, b] {
        let (code, out, err) = gob_cli::run_for_test(&cli, &["work", &t.to_string()], &fx.root);
        assert_eq!(code, 0, "base cap 3 admits both: {out}{err}");
    }
}

fn classed_ticket(ledger: &Ledger, title: &str, class: Class, scope: &str) -> TicketId {
    let mut req = NewTicket::new(title, TicketType::Task);
    req.class = class;
    req.scope = vec![scope.to_owned()];
    ledger.new_ticket(req).expect("new").ticket.front.id
}

// frob:tests crates/frob-worktree/src/wip.rs::check
#[test]
fn expedite_is_granted_as_the_single_exception_when_the_limit_is_reached() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    std::fs::write(fx.root.join("frob.toml"), "[pm.wip]\nin_progress = 2\n").expect("config");
    let ledger = fx.ledger(None);
    let a = classed_ticket(&ledger, "Std A", Class::Standard, "a/**");
    let b = classed_ticket(&ledger, "Std B", Class::Standard, "b/**");
    let std_c = classed_ticket(&ledger, "Std C", Class::Standard, "c/**");
    let hot = classed_ticket(&ledger, "Hotfix", Class::Expedite, "hot/**");
    drop(ledger);
    let cli = frob_worktree::register(gob_cli::Cli::new("frob", "0.0.0"));
    for t in [a, b] {
        let (code, out, err) = gob_cli::run_for_test(&cli, &["work", &t.to_string()], &fx.root);
        assert_eq!(code, 0, "{out}{err}");
    }
    let (code, out, _) = gob_cli::run_for_test(&cli, &["work", &std_c.to_string()], &fx.root);
    assert_eq!(code, 3, "a standard ticket is refused at the limit: {out}");
    assert_eq!(json(&out)["error"]["code"], "E-WIP-REPO");
    let (code, out, err) = gob_cli::run_for_test(&cli, &["work", &hot.to_string()], &fx.root);
    assert_eq!(code, 0, "expedite exceeds the limit by one: {out}{err}");
    let ledger = fx.ledger(None);
    assert_eq!(category(&ledger, hot), Category::InProgress);
    let (code, out, _) = gob_cli::run_for_test(&cli, &["work", &std_c.to_string()], &fx.root);
    assert_eq!(code, 3, "the exception does not open the floodgates: {out}");
}

// frob:tests crates/frob-worktree/src/wip.rs::expedite_refusal
#[test]
fn a_second_expedite_exits_3_while_one_is_running() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    std::fs::write(fx.root.join("frob.toml"), "[pm.wip]\nin_progress = 5\n").expect("config");
    let ledger = fx.ledger(None);
    let one = classed_ticket(&ledger, "Hotfix one", Class::Expedite, "h1/**");
    let two = classed_ticket(&ledger, "Hotfix two", Class::Expedite, "h2/**");
    drop(ledger);
    let cli = frob_worktree::register(gob_cli::Cli::new("frob", "0.0.0"));
    let (code, out, err) = gob_cli::run_for_test(&cli, &["work", &one.to_string()], &fx.root);
    assert_eq!(code, 0, "{out}{err}");
    let (code, out, _) = gob_cli::run_for_test(&cli, &["work", &two.to_string()], &fx.root);
    assert_eq!(code, 3, "{out}");
    let v = json(&out);
    assert_eq!(v["error"]["code"], "E-WIP-EXPEDITE");
    assert!(
        v["error"]["message"]
            .as_str()
            .is_some_and(|m| m.contains("Hotfix one")),
        "{out}"
    );
    // raising the lane lets it through
    std::fs::write(
        fx.root.join("frob.toml"),
        "[pm.wip]\nin_progress = 5\n[pm.classes]\nexpedite_max = 2\n",
    )
    .expect("config");
    let (code, out, err) = gob_cli::run_for_test(&cli, &["work", &two.to_string()], &fx.root);
    assert_eq!(code, 0, "{out}{err}");
}

// frob:tests crates/frob-worktree/src/wip.rs::check
// frob:tests crates/frob-pm/src/rules/wip.rs::count
#[test]
fn the_gate_and_pm013_count_the_same_holders() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    std::fs::write(
        fx.root.join("frob.toml"),
        "[pm.wip]\nin_progress = 1\n[pm.classes]\nexpedite_max = 1\n",
    )
    .expect("config");
    let ledger = fx.ledger(None);
    let a = classed_ticket(&ledger, "Std A", Class::Standard, "a/**");
    let hot = classed_ticket(&ledger, "Hotfix", Class::Expedite, "hot/**");
    let old = classed_ticket(&ledger, "Old stale", Class::Standard, "old/**");
    let next = classed_ticket(&ledger, "Std next", Class::Standard, "next/**");
    // `old` is in progress with no lease: stale for both the gate and the rule.
    ledger
        .transition(old, Category::InProgress, None, None)
        .expect("stale transition");
    drop(ledger);
    let cli = frob_worktree::register(gob_cli::Cli::new("frob", "0.0.0"));
    for t in [a, hot] {
        let (code, out, err) = gob_cli::run_for_test(&cli, &["work", &t.to_string()], &fx.root);
        assert_eq!(code, 0, "{out}{err}");
    }
    // Gate: standard `a` fills the limit of 1; expedite and stale are not counted.
    let (code, out, _) = gob_cli::run_for_test(&cli, &["work", &next.to_string()], &fx.root);
    assert_eq!(code, 3, "{out}");
    let gate = json(&out)["error"]["message"]
        .as_str()
        .expect("message")
        .to_owned();
    assert!(gate.contains("(1 of 1)"), "{gate}");
    assert!(gate.contains("Std A"), "{gate}");
    assert!(!gate.contains("Hotfix") || gate.contains("Stale"), "{gate}");
    // Rule: the same fixture, the same count, so no finding at the limit ...
    let ledger = fx.ledger(None);
    let live: std::collections::BTreeSet<TicketId> = fx
        .leases()
        .live_snapshot()
        .expect("live")
        .into_iter()
        .map(|l| l.ticket)
        .collect();
    let at = |limit: u32| {
        let limits = frob_pm::rules::wip::WipLimits {
            in_progress: limit,
            expedite_max: 1,
        };
        frob_pm::rules::wip::evaluate_with(&ledger, limits, Some(&live)).expect("pm013")
    };
    assert!(
        at(1).findings.is_empty(),
        "rule agrees with the gate at the limit"
    );
    // ... and it fires exactly when the gate's holder count is exceeded.
    let wip = frob_pm::rules::wip::read(&ledger, Some(&live), 1).expect("read");
    assert_eq!(wip.standard.len(), 1);
    assert_eq!(wip.expedite.len(), 1);
    assert_eq!(wip.stale.len(), 1);
    let over = at(1).subjects;
    assert_eq!(over, 2, "standard plus expedite holders, stale excluded");
}

/// A clock three hours past now: every two-hour lease taken at real time has expired by it.
#[derive(Debug)]
struct LaterClock;

impl gob_time::Clock for LaterClock {
    fn now(&self) -> frob_ledger::model::Stamp {
        frob_ledger::model::Stamp::from_unix(gob_time::SystemClock.now().unix() + 3 * 3600)
    }
}

/// Work `scope` as the default actor, then let its lease expire and be pruned; returns the worktree path and id.
fn expired_run(fx: &Fixture, scope: &[&str]) -> (TicketId, PathBuf) {
    let ledger = fx.ledger(None);
    let leases = fx.leases();
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let id = Fixture::ticket(&ledger, "Do it", TicketType::Task, scope);
    let started = ws
        .work(&id.to_string(), &WorkOptions::default())
        .expect("work");
    let later: std::sync::Arc<dyn gob_time::Clock> = std::sync::Arc::new(LaterClock);
    fx.leases().with_clock(later).list().expect("prune");
    assert!(leases.recorded_lease(id).expect("read").is_none());
    (id, started.path)
}

/// `work` for `id` run from inside `wt`, as an agent resuming there would.
fn work_from(wt: &Path, id: TicketId) -> Result<frob_worktree::Started, WorktreeError> {
    let repo = Repo::discover(wt).expect("repo");
    let ledger = Ledger::open(
        Repo::discover(wt).expect("repo"),
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
    let leases = LeaseStore::open(
        &repo,
        LeaseConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    )
    .expect("leases");
    let cfg = WorktreeConfig::load(wt).expect("config");
    Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    }
    .work(&id.to_string(), &WorkOptions::default())
}

// frob:ticket 01M4BH0C9D5X79MFHTAYBHKQGE
// frob:tests crates/frob-worktree/src/work.rs::resumed_worktree
#[test]
fn work_from_its_own_worktree_releases_an_expired_in_progress_ticket() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let (id, wt) = expired_run(&fx, &["crates/x/**"]);
    let again = work_from(&wt, id).expect("re-lease in place");
    assert_eq!(again.lease.holder.worktree, wt);
    assert!(!again.created_worktree);
    assert_eq!(category(&fx.ledger(None), id), Category::InProgress);
    assert!(fx.leases().live_lease(id).expect("live").is_some());
}

// frob:tests crates/frob-worktree/src/work.rs::resumed_worktree
#[test]
fn work_from_its_own_worktree_refuses_when_an_overlapping_lease_was_taken_since() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let (id, wt) = expired_run(&fx, &["crates/x/**"]);
    let other = Fixture::ticket(
        &fx.ledger(None),
        "Other",
        TicketType::Task,
        &["crates/x/a.rs"],
    );
    fx.leases()
        .acquire(
            other,
            &frob_lease::Holder {
                actor: "bob".to_owned(),
                worktree: fx.root.join("bob-wt"),
            },
            &["crates/x/a.rs".to_owned()],
        )
        .expect("bob takes an overlap");
    let err = work_from(&wt, id).expect_err("stolen scope");
    assert_eq!(refusal_code(&err), "E-LEASE-HELD");
}

/// Create a cycle whose first and last day are `start` and `end` days from today (UTC).
fn cycle_at(ledger: &Ledger, start: i64, end: i64) -> frob_pm::ObjectId {
    let store = frob_pm::PmStore::new(ledger);
    let today = store.today();
    store
        .create(frob_pm::NewObject::Cycle {
            start: today.plus_days(start).expect("start"),
            end: today.plus_days(end).expect("end"),
            goal: "goal".to_owned(),
            capacity_points: None,
        })
        .expect("cycle")
        .object
        .id()
}

// frob:ticket 01M4CSZFC0QF9PH544ARF60RCZ
// frob:tests crates/frob-worktree/src/cycle_gate.rs::check_overdue
// frob:tests crates/frob-worktree/src/cycle_gate.rs::overdue_refusal
#[test]
fn an_overdue_active_cycle_refuses_standard_work_but_not_expedite() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let ledger = fx.ledger(None);
    let leases = fx.leases();
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    cycle_at(&ledger, -8, -2);
    let plain = Fixture::ticket(&ledger, "Plain", TicketType::Task, &["a/**"]);
    let err = ws
        .work(&plain.to_string(), &WorkOptions::default())
        .expect_err("overdue refuses");
    assert_eq!(refusal_code(&err), "E-PM-CYCLE-OVERDUE");
    let msg = refusal_message(&err);
    assert!(msg.contains("2 day(s) overdue"), "{msg}");
    assert_eq!(category(&ledger, plain), Category::Todo);
    let err = ws
        .start(&plain.to_string(), &fx.root, None)
        .expect_err("start refuses too");
    assert_eq!(refusal_code(&err), "E-PM-CYCLE-OVERDUE");

    let mut hot = NewTicket::new("Hot", TicketType::Task);
    hot.scope = vec!["b/**".to_owned()];
    hot.class = Class::Expedite;
    let hot = ledger.new_ticket(hot).expect("new").ticket.front.id;
    ws.work(&hot.to_string(), &WorkOptions::default())
        .expect("expedite starts");
    assert_eq!(category(&ledger, hot), Category::InProgress);
}

// frob:ticket 01M4CT016NKN4QRVY0Y57FX1J2
// frob:tests crates/frob-worktree/src/cycle_gate.rs::check_sprint
// frob:tests crates/frob-worktree/src/cycle_gate.rs::not_in_cycle_refusal
// frob:tests crates/frob-pm/src/rules/cycle.rs::assign_unplanned
#[test]
fn the_sprint_gate_refuses_outside_the_active_cycle_and_unplanned_joins_it() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let ledger = fx.ledger(None);
    let leases = fx.leases();
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &cfg,
    };
    let gated = WorkOptions {
        sprint_gate: true,
        ..WorkOptions::default()
    };
    let planned = Fixture::ticket(&ledger, "Planned", TicketType::Task, &["a/**"]);
    // No active cycle: the gate is silent.
    ws.work(&planned.to_string(), &gated)
        .expect("no cycle, no gate");
    ws.requeue(&planned.to_string(), "test").expect("requeue");

    let cycle = cycle_at(&ledger, -1, 5);
    frob_pm::PmStore::new(&ledger)
        .set_member(
            frob_pm::ObjectKind::Cycle,
            cycle,
            planned,
            frob_pm::event::Op::Add,
        )
        .expect("member");
    let stranger = Fixture::ticket(&ledger, "Stranger", TicketType::Task, &["b/**"]);
    let err = ws
        .work(&stranger.to_string(), &gated)
        .expect_err("outside the cycle");
    assert_eq!(refusal_code(&err), "E-PM-NOT-IN-CYCLE");
    let hint = match &err {
        WorktreeError::Refused(r) => r.remedy.clone().unwrap_or_default(),
        other => panic!("{other}"),
    };
    assert!(
        hint.contains("cycle assign") && hint.contains("--unplanned"),
        "{hint}"
    );
    assert_eq!(category(&ledger, stranger), Category::Todo);

    // A member of the cycle starts.
    ws.work(&planned.to_string(), &gated)
        .expect("member starts");

    // Expedite is exempt.
    let mut hot = NewTicket::new("Hot", TicketType::Task);
    hot.scope = vec!["c/**".to_owned()];
    hot.class = Class::Expedite;
    let hot = ledger.new_ticket(hot).expect("new").ticket.front.id;
    ws.work(&hot.to_string(), &gated).expect("expedite starts");

    // --unplanned --reason joins the cycle as an over-commit and starts.
    let opts = WorkOptions {
        unplanned: Some("customer escalation".to_owned()),
        ..gated.clone()
    };
    ws.work(&stranger.to_string(), &opts)
        .expect("unplanned starts");
    assert_eq!(category(&ledger, stranger), Category::InProgress);
    let store = frob_pm::PmStore::new(&ledger);
    let folded = store
        .get(frob_pm::ObjectKind::Cycle, cycle)
        .expect("get")
        .expect("cycle");
    assert!(folded.object.members().contains(&stranger));
    let tip = ledger.tip_hex().expect("tip").expect("some tip");
    let events = store
        .read_events_at(&tip, frob_pm::ObjectKind::Cycle, cycle)
        .expect("events");
    let reasons: Vec<String> = events
        .iter()
        .filter_map(|e| match &e.body {
            frob_pm::event::PmBody::Cycle(c) if c.op == frob_pm::event::CycleOp::OverCommit => {
                c.text.clone()
            }
            _ => None,
        })
        .collect();
    assert_eq!(reasons, ["customer escalation"]);
}
