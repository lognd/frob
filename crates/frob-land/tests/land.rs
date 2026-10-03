//! `land` end to end in temporary repositories (system git required: gob-git spawns it for worktrees and merges).

use std::path::{Path, PathBuf};
use std::time::Duration;

use frob_evidence::events;
use frob_evidence::provider::hash_file;
use frob_land::{LandError, LandLock, LandOptions, land};
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
                    Some(b"[pm]\ndone_requires = [\"criteria_evidenced\"]\n".to_vec()),
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
    assert!(msg.contains("has 1 blocking finding(s)"), "{msg}");
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
