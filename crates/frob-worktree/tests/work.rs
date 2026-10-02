//! `work`, `start` and `requeue` end to end in temporary repositories (system git required).

use std::path::{Path, PathBuf};
use std::time::Duration;

use frob_lease::{LeaseConfig, LeaseStore};
use frob_ledger::index::ListFilter;
use frob_ledger::model::{Category, TicketType};
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
        Ledger::open(Repo::discover(&self.root).expect("repo"), cfg)
    }

    fn leases(&self) -> LeaseStore {
        let repo = Repo::discover(&self.root).expect("repo");
        LeaseStore::open(&repo, LeaseConfig::default()).expect("leases")
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
                let leases = LeaseStore::open(&repo, LeaseConfig::default()).expect("leases");
                let cfg = LedgerConfig {
                    actor: Some(who.to_owned()),
                    ..LedgerConfig::default()
                };
                let ledger = Ledger::open(repo, cfg);
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
    let guard = frob_lease::LeaseGuard::discover(&fx.root).expect("guard");
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
