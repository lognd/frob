//! `land` end to end in temporary repositories (system git required: gob-git spawns it for worktrees and merges).

use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration;

use frob_evidence::events;
use frob_evidence::provider::hash_file;
use frob_land::{LandError, LandLock, LandOptions, RetryPolicy, land};
use frob_lease::{LeaseConfig, LeaseStore};
use frob_ledger::model::{Category, Outcome, TicketType};
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig, TicketId};
use frob_worktree::{WorkOptions, Workspace, WorktreeConfig};
use gob_cli::CliError;
use gob_diagnostics::{ExitCode, RefusalClass};
use gob_exec::{Limits, Outcome as ExecOutcome, Program, Runner, Spec};
use gob_git::{CommitOptions, RelPath, Repo};

const MAIN: &str = "refs/heads/main";

fn git_out(dir: &Path, args: &[&str]) -> (i32, String) {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|s| (*s).to_owned()).collect(),
        cwd: Some(dir.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(60),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 })
        .run(&spec)
        .expect("git runs");
    let ExecOutcome::Exited(code) = out.status else {
        panic!("git {args:?} did not exit");
    };
    (code, format!("{}{}", out.stdout, out.stderr))
}

fn git(dir: &Path, args: &[&str]) {
    let (code, text) = git_out(dir, args);
    assert_eq!(code, 0, "git {args:?}: {text}");
}

fn git_available() -> bool {
    Runner::new(Limits { jobs: 1 })
        .run(&Spec {
            program: Program::Git,
            args: vec!["--version".to_owned()],
            cwd: None,
            env: Vec::new(),
            timeout: Duration::from_secs(10),
            capture: true,
        })
        .is_ok_and(|o| o.status == ExecOutcome::Exited(0))
}

fn marker() -> String {
    ["TO", "DO"].concat()
}

/// `<tmp>/repo` on `main` with a root commit; worktrees go to `<tmp>/repo-wt`.
struct Fixture {
    _tmp: tempfile::TempDir,
    root: PathBuf,
}

/// A started ticket: its id, handle and worktree.
struct Started {
    id: TicketId,
    handle: String,
    wt: PathBuf,
}

impl Fixture {
    fn new() -> Self {
        Self::requiring("criteria_evidenced")
    }

    /// A fixture whose `[pm] done_requires` is exactly `requirement`.
    fn requiring(requirement: &str) -> Self {
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
            &[
                (
                    RelPath::new("README.md").expect("path"),
                    Some(b"hello\n".to_vec()),
                ),
                (
                    RelPath::new("frob.toml").expect("path"),
                    Some(format!("[pm]\ndone_requires = [\"{requirement}\"]\n").into_bytes()),
                ),
                (
                    RelPath::new(".gitignore").expect("path"),
                    Some(b".frob/\n".to_vec()),
                ),
            ],
            "root",
            &CommitOptions::default(),
        )
        .expect("root commit");
        Self { _tmp: tmp, root }
    }

    fn repo(&self) -> Repo {
        Repo::discover(&self.root).expect("repo")
    }

    fn ledger(&self) -> Ledger {
        Ledger::open(self.repo(), LedgerConfig::default())
    }

    fn leases(&self) -> LeaseStore {
        LeaseStore::open(&self.repo(), LeaseConfig::default()).expect("leases")
    }

    fn main_tip(&self) -> String {
        self.repo().rev_parse("main").expect("main").to_string()
    }

    /// Create a task with `scope` and `work` it.
    fn start(&self, title: &str, scope: &[&str]) -> Started {
        self.start_with(title, scope, &[])
    }

    /// Like `start`, with acceptance criteria on the ticket.
    fn start_with(&self, title: &str, scope: &[&str], acceptance: &[&str]) -> Started {
        let ledger = self.ledger();
        let leases = self.leases();
        let cfg = WorktreeConfig::load(&self.root).expect("config");
        let mut req = NewTicket::new(title, TicketType::Task);
        req.scope = scope.iter().map(|s| (*s).to_owned()).collect();
        req.acceptance = acceptance.iter().map(|s| (*s).to_owned()).collect();
        let created = ledger.new_ticket(req).expect("new");
        let id = created.ticket.front.id;
        let ws = Workspace {
            ledger: &ledger,
            leases: &leases,
            config: &cfg,
        };
        let started = ws
            .work(&id.to_string(), &WorkOptions::default())
            .expect("work");
        Started {
            id,
            handle: created.handle,
            wt: started.path,
        }
    }

    /// Write `rel` in the worktree and commit it there.
    fn commit_in(wt: &Path, rel: &str, text: &str) {
        let full = wt.join(rel);
        std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
        std::fs::write(full, text).expect("write");
        git(wt, &["add", "-A"]);
        git(wt, &["commit", "-q", "-m", &format!("add {rel}")]);
    }

    /// Record a measured file evidence record for `rel` on the ticket.
    fn evidence(s: &Started, rel: &str) {
        let rec = hash_file(&s.wt, rel, &[]).expect("hash");
        // From the worktree, as `frob ticket evidence add` runs there: the ledger commit moves
        // `main` without syncing the primary checkout, which land must cope with.
        let from_wt = Ledger::open(
            Repo::discover(&s.wt).expect("repo"),
            LedgerConfig::default(),
        );
        events::append(&from_wt, s.id, &rec).expect("append");
    }

    fn opts(s: &Started) -> LandOptions {
        LandOptions {
            handle: Some(s.handle.clone()),
            ..LandOptions::default()
        }
    }
}

fn refusal(e: &LandError) -> &gob_diagnostics::Refusal {
    e.refusal().unwrap_or_else(|| panic!("not a refusal: {e}"))
}

#[test]
fn happy_path_lands_closes_and_cleans_up() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add a", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/a.rs", "fn a() {}\n");
    Fixture::evidence(&s, "src/a.rs");

    let out = land(&fx.root, &Fixture::opts(&s)).expect("land");
    assert!(!out.already && out.closed && !out.dry_run);
    assert_eq!(out.outcome, Some(Outcome::Done));
    let blob = fx.repo().read_blob_at("main", "src/a.rs").expect("read");
    assert_eq!(
        blob.as_deref(),
        Some(b"fn a() {}\n".as_slice()),
        "base has the commit"
    );
    assert!(
        fx.root.join("src/a.rs").exists(),
        "primary checkout updated"
    );

    let ledger = fx.ledger();
    let view = ledger.show(s.id).expect("show");
    assert_eq!(view.summary.category, Category::Done);
    assert_eq!(view.ticket.front.outcome, Some(Outcome::Done));
    let kinds: Vec<String> = ledger
        .events(s.id)
        .expect("events")
        .into_iter()
        .map(|e| e.kind)
        .collect();
    assert!(kinds.iter().any(|k| k == "land"), "{kinds:?}");
    assert!(
        fx.leases().live_lease(s.id).expect("lease").is_none(),
        "lease released"
    );
    assert!(!s.wt.exists(), "worktree removed");
    let (_, branches) = git_out(&fx.root, &["branch", "--list", "ticket/*"]);
    assert!(branches.trim().is_empty(), "branch deleted: {branches}");
    let (_, log) = git_out(&fx.root, &["log", "--format=%s", "main"]);
    assert!(
        log.contains("tickets(land)"),
        "ledger commit on the ledger ref: {log}"
    );
    assert!(
        log.contains("tickets(close)") || log.contains("tickets(transition)"),
        "{log}"
    );

    let again = land(&fx.root, &Fixture::opts(&s)).expect("second land");
    assert!(again.already && !again.closed, "second land is a no-op");
}

// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29
#[test]
fn land_runs_the_throttled_gc_pass_after_removing_the_worktree() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add g", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/g.rs", "fn g() {}\n");
    Fixture::evidence(&s, "src/g.rs");
    let out = land(&fx.root, &Fixture::opts(&s)).expect("land");
    assert!(out.closed && !s.wt.exists());
    let stamp = fx.repo().common_dir().join("frob").join("gc.json");
    let text = std::fs::read_to_string(&stamp).expect("land left a gc stamp");
    assert!(text.contains("\"passes\": 1"), "{text}");
}

#[test]
fn red_check_refuses_with_exit_3_and_moves_nothing() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add b", &["src/**"]);
    Fixture::commit_in(
        &s.wt,
        "src/b.rs",
        &format!("// {}: finish this\nfn b() {{}}\n", marker()),
    );
    Fixture::evidence(&s, "src/b.rs");
    let before = fx.main_tip();

    let err = land(&fx.root, &Fixture::opts(&s)).expect_err("red check");
    let r = refusal(&err);
    assert_eq!(r.code, "E-LAND-CHECK-RED");
    assert_eq!(r.class, RefusalClass::GuardNeedsAction);
    assert_eq!(
        r.remedy.as_deref(),
        Some(format!("frob check --ticket {}", s.handle).as_str())
    );
    assert_eq!(CliError::from(err).exit_code(), ExitCode::Refused);
    assert_eq!(fx.main_tip(), before, "base did not move");
    assert_eq!(
        fx.ledger().show(s.id).expect("show").summary.category,
        Category::InProgress
    );
    assert!(s.wt.exists() && fx.leases().live_lease(s.id).expect("lease").is_some());
}

/// One error among non-blocking findings: only the error is listed, the rest are counted.
#[test]
fn red_check_lists_only_blocking_findings_and_counts_the_rest() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add b", &["src/**"]);
    Fixture::commit_in(
        &s.wt,
        "src/b.rs",
        &format!("// {}: finish this\nfn b() {{}}\n", marker()),
    );
    Fixture::evidence(&s, "src/b.rs");

    let err = land(&fx.root, &Fixture::opts(&s)).expect_err("red check");
    let msg = refusal(&err).message.clone();
    assert!(msg.contains("has 1 new blocking finding(s)"), "{msg}");
    assert!(msg.contains("TODO001 src/b.rs"), "error is listed: {msg}");
    let (listed, tail) = msg.split_once("; and ").expect("tail counts the rest");
    assert_eq!(
        listed.matches(" src/").count() + listed.matches(" -:").count(),
        1,
        "only the blocking finding is listed: {msg}"
    );
    assert!(tail.contains("non-blocking findings"), "{msg}");
}

#[test]
fn dirty_worktree_refuses_and_lists_paths() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add c", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/c.rs", "fn c() {}\n");
    std::fs::write(s.wt.join("src/scratch.rs"), "fn x() {}\n").expect("write");
    let before = fx.main_tip();

    let err = land(&fx.root, &Fixture::opts(&s)).expect_err("dirty");
    let r = refusal(&err);
    assert_eq!(r.code, "E-LAND-DIRTY");
    assert_eq!(r.class, RefusalClass::GuardNeedsAction);
    assert!(r.message.contains("src/scratch.rs"), "{}", r.message);
    assert_eq!(fx.main_tip(), before);
}

#[test]
fn conflicting_base_refuses_with_paths_and_leaves_the_worktree_clean() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Edit readme", &["README.md"]);
    Fixture::commit_in(&s.wt, "README.md", "from the ticket\n");
    fx.repo()
        .commit_paths(
            MAIN,
            &[(
                RelPath::new("README.md").expect("path"),
                Some(b"from the base\n".to_vec()),
            )],
            "base edit",
            &CommitOptions::default(),
        )
        .expect("base commit");
    let before = fx.main_tip();

    let err = land(&fx.root, &Fixture::opts(&s)).expect_err("conflict");
    let r = refusal(&err);
    assert_eq!(r.code, "E-LAND-CONFLICT");
    assert!(r.message.contains("README.md"), "{}", r.message);
    assert_eq!(fx.main_tip(), before);
    let (_, status) = git_out(&s.wt, &["status", "--porcelain"]);
    assert!(
        !status.lines().any(|l| l.starts_with("UU")),
        "merge was aborted: {status}"
    );
}

#[test]
fn lock_contention_refuses_retryably_naming_the_holder() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add d", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/d.rs", "fn d() {}\n");
    Fixture::evidence(&s, "src/d.rs");
    let held = LandLock::acquire(fx.repo().common_dir(), Duration::ZERO, "someone landing ~x")
        .expect("lock");
    let before = fx.main_tip();

    let err = land(&fx.root, &Fixture::opts(&s)).expect_err("locked");
    let r = refusal(&err);
    assert_eq!(r.code, "E-LAND-LOCKED");
    assert_eq!(r.class, RefusalClass::GuardRetryByWaiting);
    assert!(r.class.retryable());
    assert!(r.message.contains("someone landing ~x"), "{}", r.message);
    assert_eq!(fx.main_tip(), before);
    drop(held);
    land(&fx.root, &Fixture::opts(&s)).expect("lands once the lock is free");
}

#[test]
fn dry_run_plan_is_deterministic_and_changes_nothing() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add e", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/e.rs", "fn e() {}\n");
    Fixture::evidence(&s, "src/e.rs");
    let before = fx.main_tip();
    let dry = LandOptions {
        dry_run: true,
        ..Fixture::opts(&s)
    };

    let a = land(&fx.root, &dry).expect("dry run");
    let b = land(&fx.root, &dry).expect("dry run again");
    assert!(a.dry_run && !a.closed);
    assert_eq!(a.plan, b.plan);
    assert_eq!(a.digest, b.digest);
    assert!(a.digest.as_deref().is_some_and(|d| d.len() == 64));
    assert!(a.plan.len() >= 6, "{:?}", a.plan);
    assert_eq!(fx.main_tip(), before, "nothing moved");
    assert!(s.wt.exists());
    assert_eq!(
        fx.ledger().show(s.id).expect("show").summary.category,
        Category::InProgress
    );
}

#[test]
fn missing_evidence_refuses_unless_bypassed_with_a_reason() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add f", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/f.rs", "fn f() {}\n");

    let err = land(&fx.root, &Fixture::opts(&s)).expect_err("no evidence");
    assert_eq!(refusal(&err).code, "E-EVIDENCE-MISSING");

    let opts = LandOptions {
        no_evidence_reason: Some("covered elsewhere".to_owned()),
        ..Fixture::opts(&s)
    };
    let out = land(&fx.root, &opts).expect("bypassed land");
    assert!(out.closed);
}

// frob:ticket 01M412CMSRCHNXHEEENY8ZYBDW
// frob:tests crates/frob-land/src/land.rs::land
#[test]
fn no_changelog_with_a_reason_lands_without_a_fragment_and_records_the_event() {
    if !git_available() {
        return;
    }
    let fx = Fixture::requiring("changelog_fragment");
    let s = fx.start("Design doc", &["docs/**"]);
    Fixture::commit_in(&s.wt, "docs/d.md", "design\n");
    Fixture::evidence(&s, "docs/d.md");

    let err = land(&fx.root, &Fixture::opts(&s)).expect_err("no fragment");
    let r = refusal(&err);
    assert!(
        r.code == "E-DONE-CHANGELOG-FRAGMENT" || r.code == "E-LAND-CHECK-RED",
        "{}",
        r.code
    );

    let opts = LandOptions {
        no_changelog_reason: Some("design only".to_owned()),
        ..Fixture::opts(&s)
    };
    let out = land(&fx.root, &opts).expect("exempt land");
    assert!(out.closed);
    assert_eq!(out.changelog_exempt.as_deref(), Some("design only"));
    let events = fx.ledger().events(s.id).expect("events");
    let x = frob_ledger::event::changelog_exemption(&events).expect("changelog-exempt event");
    assert_eq!(x.reason, "design only");
}

// frob:ticket 01M40WS6200M99J09D5XGAS05X
#[test]
fn an_unbound_criterion_refuses_the_land_naming_it_and_the_bypass_and_moves_nothing() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start_with("Add g", &["src/**"], &["g answers"]);
    Fixture::commit_in(&s.wt, "src/g.rs", "fn g() {}\n");
    Fixture::evidence(&s, "src/g.rs");
    let before = fx.main_tip();

    let err = land(&fx.root, &Fixture::opts(&s)).expect_err("unbound criterion");
    let r = refusal(&err);
    assert_eq!(r.code, "E-DONE-CRITERIA-UNBOUND");
    assert!(r.message.contains("g answers"), "{}", r.message);
    assert!(
        r.remedy
            .as_deref()
            .is_some_and(|c| c.contains("--no-evidence --reason")),
        "{:?}",
        r.remedy
    );
    assert_eq!(fx.main_tip(), before, "base did not move");
    assert_eq!(
        fx.ledger().show(s.id).expect("show").summary.category,
        Category::InProgress
    );
}

#[test]
fn an_unleased_ticket_and_another_worktree_are_refused() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let ledger = fx.ledger();
    let mut req = NewTicket::new("Untouched", TicketType::Task);
    req.scope = vec!["docs/**".to_owned()];
    let idle = ledger.new_ticket(req).expect("new");
    let err = land(
        &fx.root,
        &LandOptions {
            handle: Some(idle.handle.clone()),
            ..LandOptions::default()
        },
    )
    .expect_err("not leased");
    assert_eq!(refusal(&err).code, "E-LAND-NOT-LEASED");

    let a = fx.start("A", &["src/a/**"]);
    let b = fx.start("B", &["src/b/**"]);
    let err = land(&b.wt, &Fixture::opts(&a)).expect_err("wrong worktree");
    assert_eq!(refusal(&err).code, "E-LAND-WRONG-WORKTREE");
}

#[test]
fn landing_from_inside_the_worktree_defaults_to_its_ticket() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add g", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/g.rs", "fn g() {}\n");
    Fixture::evidence(&s, "src/g.rs");

    let out = land(&s.wt, &LandOptions::default()).expect("land from the worktree");
    assert_eq!(out.id, s.id);
    assert!(out.closed && !s.wt.exists());
}

/// A retry policy with millisecond backoff that runs `mover(attempt)` before each compare-and-swap.
fn retry_with(budget_ms: u64, mover: impl Fn(u32) + Send + Sync + 'static) -> RetryPolicy {
    RetryPolicy {
        backoff_base: Duration::from_millis(1),
        backoff_max: Duration::from_millis(2),
        budget: Some(Duration::from_millis(budget_ms)),
        before_attempt: Some(Arc::new(mover)),
    }
}

/// Commit `rel` straight onto `main`, the way another agent's ledger or code commit moves the base.
fn move_main(root: &Path, rel: &str, text: &str) {
    let repo = Repo::discover(root).expect("repo");
    repo.commit_paths(
        MAIN,
        &[(
            RelPath::new(rel).expect("path"),
            Some(text.as_bytes().to_vec()),
        )],
        "other agent",
        &CommitOptions::default(),
    )
    .expect("move main");
}

// Covers ~VMHTBE7.
#[test]
fn wait_retries_a_base_that_moved_once_with_ledger_only_commits() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add a", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/a.rs", "fn a() {}\n");
    Fixture::evidence(&s, "src/a.rs");
    let root = fx.root.clone();
    let mut opts = Fixture::opts(&s);
    opts.wait_secs = 5;
    opts.retry = retry_with(4000, move |n| {
        if n == 1 {
            move_main(&root, "tickets/zz-note.txt", "note\n");
        }
    });

    let out = land(&fx.root, &opts).expect("land retried");
    assert!(out.closed, "landed without a manual retry");
    assert_eq!(out.attempts, 2);
    let blob = fx.repo().read_blob_at("main", "src/a.rs").expect("read");
    assert_eq!(blob.as_deref(), Some(b"fn a() {}\n".as_slice()));
    let note = fx
        .repo()
        .read_blob_at("main", "tickets/zz-note.txt")
        .expect("read");
    assert!(note.is_some(), "the other agent's commit is kept");
}

// Covers ~VMHTBE7.
#[test]
fn wait_retries_a_base_that_moved_with_a_code_change() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add a", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/a.rs", "fn a() {}\n");
    Fixture::evidence(&s, "src/a.rs");
    let root = fx.root.clone();
    let mut opts = Fixture::opts(&s);
    opts.wait_secs = 5;
    opts.retry = retry_with(4000, move |n| {
        if n == 1 {
            move_main(&root, "docs/other.md", "other\n");
        }
    });

    let out = land(&fx.root, &opts).expect("land retried");
    assert!(out.closed);
    assert_eq!(out.attempts, 2);
}

// Covers ~VMHTBE7.
#[test]
fn wait_gives_up_naming_the_attempts_when_the_base_keeps_moving() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add a", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/a.rs", "fn a() {}\n");
    Fixture::evidence(&s, "src/a.rs");
    let root = fx.root.clone();
    let mut opts = Fixture::opts(&s);
    opts.wait_secs = 1;
    opts.retry = retry_with(30, move |n| {
        move_main(&root, &format!("tickets/zz-note-{n}.txt"), "note\n");
    });

    let err = land(&fx.root, &opts).expect_err("budget spent");
    let r = refusal(&err);
    assert_eq!(r.code, "E-LAND-STALE");
    assert_eq!(r.class, RefusalClass::GuardRetryByWaiting);
    assert!(r.message.contains("gave up after"), "{}", r.message);
    assert!(r.message.contains("attempt"), "{}", r.message);
    assert!(
        fx.leases().live_lease(s.id).expect("lease").is_some(),
        "the lease is kept so `frob land` resumes"
    );
}

// Covers ~VMHTBE7.
#[test]
fn without_wait_a_moved_base_is_not_retried() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add a", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/a.rs", "fn a() {}\n");
    Fixture::evidence(&s, "src/a.rs");
    let root = fx.root.clone();
    let mut opts = Fixture::opts(&s);
    opts.retry = retry_with(4000, move |n| {
        if n == 1 {
            move_main(&root, "tickets/zz-note.txt", "note\n");
        }
    });

    let err = land(&fx.root, &opts).expect_err("stale");
    assert_eq!(refusal(&err).code, "E-LAND-STALE");
    assert!(refusal(&err).message.ends_with("moved while landing"));
    let out = land(&fx.root, &Fixture::opts(&s)).expect("rerun resumes");
    assert!(out.closed);
    assert_eq!(out.attempts, 1);
}

const BASE_LOCK: &str = "# This file is automatically @generated by Cargo.\n# It is not intended for manual editing.\nversion = 4\n\n[[package]]\nname = \"base\"\nversion = \"0.1.0\"\n";

fn cargo_ok(dir: &Path, args: &[&str]) -> bool {
    let spec = Spec {
        program: Program::Cargo,
        args: args.iter().map(|s| (*s).to_owned()).collect(),
        cwd: Some(dir.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(120),
        capture: true,
    };
    Runner::new(Limits { jobs: 1 })
        .run(&spec)
        .is_ok_and(|o| o.status == ExecOutcome::Exited(0))
}

/// Add workspace member `crates/<name>` in `wt`, regenerate `Cargo.lock` offline and commit.
fn add_member(wt: &Path, name: &str) {
    Fixture::commit_in(
        wt,
        &format!("crates/{name}/Cargo.toml"),
        &format!("[package]\nname = \"{name}\"\nversion = \"0.1.0\"\nedition = \"2021\"\n"),
    );
    Fixture::commit_in(wt, &format!("crates/{name}/src/lib.rs"), "\n");
    assert!(cargo_ok(
        wt,
        &["metadata", "--offline", "--format-version", "1"]
    ));
    git(wt, &["add", "-A"]);
    git(wt, &["commit", "-q", "-m", &format!("lock {name}")]);
}

// Covers ~CTKE1J4.
#[test]
fn a_conflict_confined_to_cargo_lock_is_regenerated_at_land() {
    if !git_available() || !cargo_ok(Path::new("."), &["--version"]) {
        return;
    }
    let fx = Fixture::new();
    fx.repo()
        .commit_paths(
            MAIN,
            &[
                (
                    RelPath::new("Cargo.toml").expect("path"),
                    Some(b"[workspace]\nmembers = [\"crates/*\"]\nresolver = \"2\"\n".to_vec()),
                ),
                (
                    RelPath::new("crates/base/Cargo.toml").expect("path"),
                    Some(
                        b"[package]\nname = \"base\"\nversion = \"0.1.0\"\nedition = \"2021\"\n"
                            .to_vec(),
                    ),
                ),
                (
                    RelPath::new("crates/base/src/lib.rs").expect("path"),
                    Some(b"\n".to_vec()),
                ),
                (
                    RelPath::new("Cargo.lock").expect("path"),
                    Some(BASE_LOCK.as_bytes().to_vec()),
                ),
            ],
            "workspace",
            &CommitOptions::default(),
        )
        .expect("workspace commit");
    let one = fx.start("Add one", &["crates/one/**", "Cargo.lock"]);
    let two = fx.start("Add two", &["crates/two/**", "Cargo.lock"]);
    add_member(&one.wt, "one");
    add_member(&two.wt, "two");
    Fixture::evidence(&one, "crates/one/src/lib.rs");
    Fixture::evidence(&two, "crates/two/src/lib.rs");

    land(&fx.root, &Fixture::opts(&one)).expect("first land");
    let out = land(&fx.root, &Fixture::opts(&two)).expect("second land regenerates the lockfile");
    assert!(out.closed);
    assert_eq!(
        out.base_merge.as_deref(),
        Some("merged (lockfile regenerated)")
    );
    let lock = fx.repo().read_blob_at("main", "Cargo.lock").expect("read");
    let lock = String::from_utf8(lock.expect("lock")).expect("utf8");
    for name in ["base", "one", "two"] {
        assert!(lock.contains(&format!("name = \"{name}\"")), "{lock}");
    }
    assert!(!lock.contains("<<<<<<<"), "{lock}");
}

// Covers ~CTKE1J4.
#[test]
fn a_conflict_in_a_lockfile_without_a_resolver_refuses_and_aborts() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    fx.repo()
        .commit_paths(
            MAIN,
            &[(
                RelPath::new("uv.lock").expect("path"),
                Some(b"base\n".to_vec()),
            )],
            "uv base",
            &CommitOptions::default(),
        )
        .expect("commit");
    let s = fx.start("Touch uv", &["uv.lock"]);
    Fixture::commit_in(&s.wt, "uv.lock", "ticket\n");
    move_main(&fx.root, "uv.lock", "moved\n");
    let before = fx.main_tip();
    let err = land(&fx.root, &Fixture::opts(&s)).expect_err("no resolver");
    let r = refusal(&err);
    assert_eq!(r.code, "E-LAND-LOCKFILE");
    assert!(r.message.contains("uv.lock"), "{}", r.message);
    assert_eq!(fx.main_tip(), before);
    let (_, status) = git_out(&s.wt, &["status", "--porcelain"]);
    assert!(!status.lines().any(|l| l.starts_with("UU")), "{status}");
}

/// Commit `rel` onto `main` of the fixture (a finding that exists on the base before the ticket starts).
fn commit_on_main(fx: &Fixture, rel: &str, text: &str) {
    fx.repo()
        .commit_paths(
            MAIN,
            &[(
                RelPath::new(rel).expect("path"),
                Some(text.as_bytes().to_vec()),
            )],
            "add base file",
            &CommitOptions::default(),
        )
        .expect("main commit");
}

/// The text of a source file carrying one unfinished-work marker finding.
fn marked(body: &str) -> String {
    format!("// {}: finish this\nfn old() {{}}\n{body}", marker())
}

// frob:tests crates/frob-land/src/land.rs::land
#[test]
fn a_finding_already_on_the_base_lands_and_is_reported_pre_existing() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    commit_on_main(&fx, "src/old.rs", &marked(""));
    let s = fx.start("Touch old", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/old.rs", &marked("fn more() {}\n"));
    Fixture::evidence(&s, "src/old.rs");

    let out = land(&fx.root, &Fixture::opts(&s)).expect("pre-existing finding does not block");
    assert!(out.closed);
    assert!(
        out.pre_existing
            .iter()
            .any(|n| n.rule == "TODO001" && n.path.as_deref() == Some("src/old.rs")),
        "{:?}",
        out.pre_existing
    );
    assert!(out.resolved.is_empty(), "{:?}", out.resolved);
}

// frob:tests crates/frob-land/src/land.rs::land
#[test]
fn a_new_finding_refuses_naming_only_the_new_one() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    commit_on_main(&fx, "src/old.rs", &marked(""));
    let s = fx.start("Touch old and add new", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/old.rs", &marked("fn more() {}\n"));
    Fixture::commit_in(&s.wt, "src/new.rs", &marked(""));
    Fixture::evidence(&s, "src/new.rs");
    let before = fx.main_tip();

    let err = land(&fx.root, &Fixture::opts(&s)).expect_err("new finding refuses");
    let msg = refusal(&err).message.clone();
    assert_eq!(refusal(&err).code, "E-LAND-CHECK-RED");
    assert!(msg.contains("has 1 new blocking finding(s)"), "{msg}");
    assert!(msg.contains("TODO001 src/new.rs"), "{msg}");
    assert!(!msg.contains("TODO001 src/old.rs"), "{msg}");
    assert_eq!(fx.main_tip(), before, "base did not move");
}

// frob:tests crates/frob-land/src/land.rs::land
#[test]
fn fixing_a_base_finding_is_reported_resolved() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    commit_on_main(&fx, "src/old.rs", &marked(""));
    let s = fx.start("Fix old", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/old.rs", "fn old() {}\n");
    Fixture::evidence(&s, "src/old.rs");

    let out = land(&fx.root, &Fixture::opts(&s)).expect("land");
    assert!(
        out.resolved
            .iter()
            .any(|n| n.rule == "TODO001" && n.path.as_deref() == Some("src/old.rs")),
        "{:?}",
        out.resolved
    );
    assert!(out.pre_existing.is_empty(), "{:?}", out.pre_existing);
}

/// Make `v0.1.0` a hand-made release tag (no recorded cut): REL001 fires wherever it is checked.
fn stray_tag(fx: &Fixture, name: &str) {
    git(&fx.root, &["tag", name, "main"]);
}

// frob:tests crates/frob-land/src/land.rs::land
#[test]
fn a_repository_level_finding_on_the_base_does_not_block_an_unrelated_ticket() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    stray_tag(&fx, "v0.1.0");
    let s = fx.start("Unrelated", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/a.rs", "fn a() {}\n");
    Fixture::evidence(&s, "src/a.rs");

    let out = land(&fx.root, &Fixture::opts(&s)).expect("REL001 on the base does not block");
    assert!(out.closed);
    assert!(
        out.pre_existing.iter().any(|n| n.rule == "REL001"),
        "{:?}",
        out.pre_existing
    );
}

// frob:tests crates/frob-land/src/land.rs::land
#[test]
fn a_release_finding_the_ticket_introduces_refuses() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    // Base: only `v0.1.0` is a product tag (it is stray, so REL001 already fires); `app-v0.2.0` is not a product tag yet.
    commit_on_main(
        &fx,
        "frob.toml",
        "[pm]\ndone_requires = [\"criteria_evidenced\"]\n[release]\ntag = \"v{version}\"\n",
    );
    stray_tag(&fx, "v0.1.0");
    stray_tag(&fx, "app-v0.2.0");
    let s = fx.start("Rename tags", &["src/**", "frob.toml"]);
    Fixture::commit_in(
        &s.wt,
        "frob.toml",
        "[pm]\ndone_requires = [\"criteria_evidenced\"]\n[release]\ntag = \"{product}-v{version}\"\nproducts = [\"app\"]\n",
    );
    Fixture::evidence(&s, "frob.toml");
    let before = fx.main_tip();

    let err = land(&fx.root, &Fixture::opts(&s)).expect_err("new REL001 refuses");
    let msg = refusal(&err).message.clone();
    assert_eq!(refusal(&err).code, "E-LAND-CHECK-RED");
    assert!(msg.contains("REL001"), "{msg}");
    assert!(msg.contains("app-v0.2.0"), "names the new tag: {msg}");
    assert!(
        !msg.contains("v0.1.0:") && !msg.contains("`v0.1.0`"),
        "{msg}"
    );
    assert_eq!(fx.main_tip(), before, "base did not move");
}

/// The repository-shared state directory under the git common dir.
fn shared_state(fx: &Fixture) -> PathBuf {
    fx.repo().common_dir().join("frob")
}

// frob:tests crates/frob-land/src/ratchet.rs::base_findings
#[test]
fn a_second_ticket_on_the_same_base_reuses_the_shared_base_set_without_a_base_check() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add a file", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/a.rs", "fn a() {}\n");
    Fixture::evidence(&s, "src/a.rs");
    // A set no real base check would produce, planted where any ticket's land reads it.
    let oid = fx.main_tip();
    let planted = shared_state(&fx)
        .join("land-base")
        .join(format!("{oid}.json"));
    std::fs::create_dir_all(planted.parent().expect("parent")).expect("mkdir");
    let fake = serde_json::json!({"oid": oid, "findings": [{
        "fingerprint": "feedface", "rule": "PLANTED", "path": null, "message": "from the cached set"
    }]});
    std::fs::write(&planted, fake.to_string()).expect("plant");

    let out = land(&fx.root, &Fixture::opts(&s)).expect("land");
    assert!(
        out.resolved.iter().any(|n| n.rule == "PLANTED"),
        "the cached set was not used: {:?}",
        out.resolved
    );
    assert!(
        !fx.root.join(".frob").join("land-base").exists(),
        "no per-checkout base set is written any more"
    );
}

// frob:tests crates/frob-land/src/ratchet.rs::base_findings
#[test]
fn a_check_in_a_fresh_worktree_hits_the_cache_the_primary_warmed() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    commit_on_main(&fx, "src/old.rs", "fn old() {}\n");
    let opts = frob_check::CheckOptions {
        skip_telemetry: true,
        ..frob_check::CheckOptions::default()
    };
    frob_check::run(&fx.root, &opts).expect("warm check");
    let shared = gob_cache::shared_dir(&fx.root, ".frob").expect("shared dir");
    let warm = gob_cache::Cache::open(&shared).stats();
    assert!(!warm.null && warm.findings + warm.artifacts > 0, "{warm:?}");
    assert!(!fx.root.join(".frob").join("cache.sqlite").exists());

    let wt = fx.root.parent().expect("tmp").join("base-checkout");
    git(
        &fx.root,
        &[
            "worktree",
            "add",
            "--detach",
            wt.to_str().expect("utf8"),
            "main",
        ],
    );
    frob_check::run(&wt, &opts).expect("base check");
    let after = gob_cache::Cache::open(&shared).stats();
    assert_eq!(
        (after.findings, after.artifacts, after.repo_rule),
        (warm.findings, warm.artifacts, warm.repo_rule),
        "an unchanged tree adds no rows: every lookup in the new worktree hit"
    );
}
