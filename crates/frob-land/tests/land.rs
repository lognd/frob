//! `land` end to end in temporary repositories (system git required: gob-git spawns it for worktrees and merges).

use gob_path::Shown;
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
        Self::configured(requirement, "")
    }

    /// A fixture whose `frob.toml` is the `[pm]` requirement followed by `extra` TOML.
    fn configured(requirement: &str, extra: &str) -> Self {
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
                    Some(
                        format!("[rules]\nramp = false\n[pm]\ndone_requires = [\"{requirement}\"]\n{extra}").into_bytes(),
                    ),
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
        Ledger::open(
            self.repo(),
            LedgerConfig::default(),
            std::sync::Arc::new(gob_time::SystemClock),
        )
    }

    fn leases(&self) -> LeaseStore {
        LeaseStore::open(
            &self.repo(),
            LeaseConfig::default(),
            std::sync::Arc::new(gob_time::SystemClock),
        )
        .expect("leases")
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
        self.start_typed(title, TicketType::Task, scope, acceptance)
    }

    /// Like `start_with`, with an explicit ticket type.
    fn start_typed(
        &self,
        title: &str,
        ty: TicketType,
        scope: &[&str],
        acceptance: &[&str],
    ) -> Started {
        let ledger = self.ledger();
        let leases = self.leases();
        let cfg = WorktreeConfig::load(&self.root).expect("config");
        let mut req = NewTicket::new(title, ty);
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
        let rec = hash_file(
            &s.wt,
            rel,
            &[],
            frob_ledger::model::Stamp::from_unix(1_800_000_000),
        )
        .expect("hash");
        // From the worktree, as `frob ticket evidence add` runs there: the ledger commit moves
        // `main` without syncing the primary checkout, which land must cope with.
        let from_wt = Ledger::open(
            Repo::discover(&s.wt).expect("repo"),
            LedgerConfig::default(),
            std::sync::Arc::new(gob_time::SystemClock),
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

    let out = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("land");
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

    let again = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("second land");
    assert!(again.already && !again.closed, "second land is a no-op");
}

// frob:ticket 01M5CW03RV49WAJZQ1B76X0RQ0
// frob:tests crates/frob-land/src/land.rs::land
#[test]
fn trunk_land_pushes_after_the_ledger_step_so_origin_has_the_close() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let origin = fx.root.with_file_name("origin.git");
    git(&fx.root, &["init", "-q", "--bare", "../origin.git"]);
    git(&fx.root, &["remote", "add", "origin", "../origin.git"]);
    let s = fx.start("Add pushed", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/p.rs", "fn p() {}\n");
    Fixture::evidence(&s, "src/p.rs");

    let out = land(
        &fx.root,
        &LandOptions {
            push: true,
            ..Fixture::opts(&s)
        },
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("land");
    assert!(out.closed && out.pushed, "{:?}", out.warnings);
    let (_, remote_tip) = git_out(&origin, &["rev-parse", "main"]);
    assert_eq!(
        remote_tip.trim(),
        fx.main_tip(),
        "one push carried code and close"
    );
    let (_, log) = git_out(&origin, &["log", "--format=%s", "main"]);
    assert!(
        log.contains("tickets(land)"),
        "origin lacks the land event: {log}"
    );
    assert!(
        log.contains("tickets(close)") || log.contains("tickets(transition)"),
        "origin lacks the close: {log}"
    );
}

/// Counts `repository discovered` events per git dir on the thread that installs it.
#[derive(Clone, Default)]
struct DiscoverCounter {
    seen: Arc<std::sync::Mutex<Vec<String>>>,
}

impl tracing::Subscriber for DiscoverCounter {
    fn enabled(&self, _: &tracing::Metadata<'_>) -> bool {
        true
    }
    fn new_span(&self, _: &tracing::span::Attributes<'_>) -> tracing::span::Id {
        tracing::span::Id::from_u64(1)
    }
    fn record(&self, _: &tracing::span::Id, _: &tracing::span::Record<'_>) {}
    fn record_follows_from(&self, _: &tracing::span::Id, _: &tracing::span::Id) {}
    fn enter(&self, _: &tracing::span::Id) {}
    fn exit(&self, _: &tracing::span::Id) {}
    fn event(&self, event: &tracing::Event<'_>) {
        struct V(String, String);
        impl tracing::field::Visit for V {
            fn record_debug(&mut self, f: &tracing::field::Field, v: &dyn std::fmt::Debug) {
                match f.name() {
                    "message" => self.0 = format!("{v:?}"),
                    "git_dir" => self.1 = format!("{v:?}"),
                    _ => {}
                }
            }
        }
        let mut v = V(String::new(), String::new());
        event.record(&mut v);
        if v.0 == "repository discovered" {
            self.seen.lock().expect("lock").push(v.1);
        }
    }
}

// frob:ticket 01M4CTE7T75F9XM8XN1R1VFD4X
// frob:tests crates/frob-land/src/land.rs::begin
#[test]
fn land_opens_each_repository_once() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add a", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/a.rs", "fn a() {}\n");
    Fixture::evidence(&s, "src/a.rs");

    let counter = DiscoverCounter::default();
    let out = tracing::subscriber::with_default(counter.clone(), || {
        land(
            &fx.root,
            &Fixture::opts(&s),
            &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
        )
    })
    .expect("land");
    assert!(out.closed);
    let seen = counter.seen.lock().expect("lock").clone();
    // The invoking (primary) checkout is opened once and shared by the workspace, the lease
    // store and gc; the ticket worktree and the ratchet checkout are opened by frob-check.
    // The logged value is Debug-escaped (backslashes doubled on Windows) and gix may log either
    // separator, so compare both sides as `/` text.
    let norm = |t: &str| t.trim_matches('"').replace("\\\\", "/").replace('\\', "/");
    let primary = norm(&Shown::with_home(fx.repo().git_dir(), None).to_string());
    let opens = seen.iter().filter(|d| norm(d) == primary).count();
    assert_eq!(opens, 1, "primary opened {opens} times: {seen:?}");
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
    let out = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("land");
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

    let err = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("red check");
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

    let err = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("red check");
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

    let err = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("dirty");
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
    Fixture::evidence(&s, "README.md");
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

    let err = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("conflict");
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

// frob:tests crates/frob-land/src/land.rs::merge_base_in
#[test]
fn a_conflict_in_frob_toml_refuses_with_the_conflict_code_and_restores_the_worktree() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Edit config", &["frob.toml"]);
    Fixture::commit_in(
        &s.wt,
        "frob.toml",
        "[pm]\ndone_requires = [\"criteria_evidenced\", \"no_open_children\"]\n",
    );
    Fixture::evidence(&s, "frob.toml");
    fx.repo()
        .commit_paths(
            MAIN,
            &[(
                RelPath::new("frob.toml").expect("path"),
                Some(
                    b"[pm]\ndone_requires = [\"criteria_evidenced\", \"objective_target_met\"]\n"
                        .to_vec(),
                ),
            )],
            "base config edit",
            &CommitOptions::default(),
        )
        .expect("base commit");
    let head = git_out(&s.wt, &["rev-parse", "HEAD"]).1;
    let status = git_out(&s.wt, &["status", "--porcelain"]).1;
    let toml = std::fs::read(s.wt.join("frob.toml")).expect("read");

    let err = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("conflict");
    let r = refusal(&err);
    assert_eq!(r.code, "E-LAND-CONFLICT", "{err}");
    assert!(r.message.contains("frob.toml"), "{}", r.message);
    assert_eq!(git_out(&s.wt, &["rev-parse", "HEAD"]).1, head);
    assert_eq!(git_out(&s.wt, &["status", "--porcelain"]).1, status);
    assert_eq!(std::fs::read(s.wt.join("frob.toml")).expect("read"), toml);
    let (merge_head, _) = git_out(&s.wt, &["rev-parse", "-q", "--verify", "MERGE_HEAD"]);
    assert_ne!(merge_head, 0, "no merge in progress");
}

// frob:tests crates/frob-land/src/land.rs::merge_base_in
#[test]
fn a_conflict_in_frob_toml_and_a_lockfile_probes_with_the_committed_config_and_refuses() {
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
    let s = fx.start("Edit config and lock", &["frob.toml", "uv.lock"]);
    Fixture::commit_in(&s.wt, "uv.lock", "ticket\n");
    Fixture::commit_in(
        &s.wt,
        "frob.toml",
        "[pm]\ndone_requires = [\"criteria_evidenced\", \"no_open_children\"]\n",
    );
    Fixture::evidence(&s, "frob.toml");
    move_main(&fx.root, "uv.lock", "moved\n");
    move_main(
        &fx.root,
        "frob.toml",
        "[pm]\ndone_requires = [\"criteria_evidenced\", \"objective_target_met\"]\n",
    );
    let head = git_out(&s.wt, &["rev-parse", "HEAD"]).1;
    let status = git_out(&s.wt, &["status", "--porcelain"]).1;
    let toml = std::fs::read(s.wt.join("frob.toml")).expect("read");

    let err = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("conflict");
    let r = refusal(&err);
    assert_eq!(r.code, "E-LAND-CONFLICT", "{err}");
    assert!(r.message.contains("frob.toml"), "{}", r.message);
    assert_eq!(git_out(&s.wt, &["rev-parse", "HEAD"]).1, head);
    assert_eq!(git_out(&s.wt, &["status", "--porcelain"]).1, status);
    assert_eq!(std::fs::read(s.wt.join("frob.toml")).expect("read"), toml);
    let (merge_head, _) = git_out(&s.wt, &["rev-parse", "-q", "--verify", "MERGE_HEAD"]);
    assert_ne!(merge_head, 0, "no merge in progress");
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

    let err = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("locked");
    let r = refusal(&err);
    assert_eq!(r.code, "E-LAND-LOCKED");
    assert_eq!(r.class, RefusalClass::GuardRetryByWaiting);
    assert!(r.class.retryable());
    assert!(r.message.contains("someone landing ~x"), "{}", r.message);
    assert_eq!(fx.main_tip(), before);
    drop(held);
    land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("lands once the lock is free");
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

    let a = land(
        &fx.root,
        &dry,
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("dry run");
    let b = land(
        &fx.root,
        &dry,
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("dry run again");
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

// frob:ticket 01M4FG552GZ9FMB000B76AS8XH
// frob:tests crates/frob-land/src/land.rs::ledger_only_ahead
#[test]
fn dry_run_treats_a_base_that_moved_only_by_ledger_commits_as_merged() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add g", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/g.rs", "fn g() {}\n");
    Fixture::evidence(&s, "src/g.rs");
    let dry = LandOptions {
        dry_run: true,
        ..Fixture::opts(&s)
    };
    let clock = || Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>;

    move_main(&fx.root, "tickets/zz-note.txt", "note\n");
    let ledger_only = land(&fx.root, &dry, &clock()).expect("dry run");
    assert!(
        !ledger_only
            .warnings
            .iter()
            .any(|w| w.contains("check skipped")),
        "{:?}",
        ledger_only.warnings
    );

    move_main(&fx.root, "src/other.rs", "fn other() {}\n");
    let code = land(&fx.root, &dry, &clock()).expect("dry run");
    assert!(
        code.warnings.iter().any(|w| w.contains("check skipped")),
        "a code commit on the base is still reported: {:?}",
        code.warnings
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

    let err = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("no evidence");
    assert_eq!(refusal(&err).code, "E-EVIDENCE-MISSING");

    let opts = LandOptions {
        no_evidence_reason: Some("covered elsewhere".to_owned()),
        ..Fixture::opts(&s)
    };
    let out = land(
        &fx.root,
        &opts,
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("bypassed land");
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

    let err = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("no fragment");
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
    let out = land(
        &fx.root,
        &opts,
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("exempt land");
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

    let err = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("unbound criterion");
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

// frob:ticket 01M4FJ57NER0WMX4FPNY7E721R
// frob:tests crates/frob-land/src/land.rs::prepare
#[test]
fn the_close_guards_refuse_before_the_base_is_merged_or_checked() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start_with("Add h", &["src/**"], &["h answers"]);
    Fixture::commit_in(&s.wt, "src/h.rs", "fn h() {}\n");
    Fixture::evidence(&s, "src/h.rs");
    // A code commit on the base: a land that got as far as the merge would move the branch tip.
    move_main(&fx.root, "src/other.rs", "fn other() {}\n");
    let tip = git_out(&s.wt, &["rev-parse", "HEAD"]).1;

    let err = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("unbound criterion");
    assert_eq!(refusal(&err).code, "E-DONE-CRITERIA-UNBOUND");
    assert_eq!(
        git_out(&s.wt, &["rev-parse", "HEAD"]).1,
        tip,
        "the base was not merged into the ticket branch"
    );
}

// frob:ticket 01M1T07NXZ5WQR200M5H1NWDN9
// frob:tests crates/frob-evidence/src/done.rs::DoneGuard.check
#[test]
fn a_story_without_criteria_refuses_its_own_land_and_a_task_without_still_lands() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start_typed("Add h", TicketType::Story, &["src/**"], &[]);
    Fixture::commit_in(&s.wt, "src/h.rs", "fn h() {}\n");
    Fixture::evidence(&s, "src/h.rs");
    let before = fx.main_tip();

    let err = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("zero criteria");
    let r = refusal(&err);
    assert_eq!(r.code, "E-DONE-NO-CRITERIA");
    assert!(r.message.contains("story"), "{}", r.message);
    assert_eq!(fx.main_tip(), before, "base did not move");

    let t = fx.start_typed("Add i", TicketType::Task, &["lib/**"], &[]);
    Fixture::commit_in(&t.wt, "lib/i.rs", "fn i() {}\n");
    Fixture::evidence(&t, "lib/i.rs");
    land(
        &fx.root,
        &Fixture::opts(&t),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("task is exempt");
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
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("not leased");
    assert_eq!(refusal(&err).code, "E-LAND-NOT-LEASED");

    let a = fx.start("A", &["src/a/**"]);
    let b = fx.start("B", &["src/b/**"]);
    let err = land(
        &b.wt,
        &Fixture::opts(&a),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("wrong worktree");
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

    let out = land(
        &s.wt,
        &LandOptions::default(),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("land from the worktree");
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
// frob:tests crates/frob-land/src/land.rs::verify_check
// frob:tests crates/frob-land/src/plan.rs::StageTiming
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

    let out = land(
        &fx.root,
        &opts,
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("land retried");
    assert!(out.closed, "landed without a manual retry");
    assert_eq!(out.attempts, 2);
    // frob:ticket 01M4W7DAHAVC5HDWJJ5NPGXR8M
    let names: Vec<&str> = out.stages.iter().map(|s| s.name.as_str()).collect();
    for want in [
        "lock-wait",
        "merge",
        "check",
        "check:scoped",
        "check:head",
        "check:base-findings",
        "retry-reuse",
        "publish",
    ] {
        assert!(names.contains(&want), "stage {want} timed in {names:?}");
    }
    assert!(
        !names.iter().any(|n| n.starts_with("recheck")),
        "a ledger-only base move reuses the first check: {names:?}"
    );
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

    let out = land(
        &fx.root,
        &opts,
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("land retried");
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

    let err = land(
        &fx.root,
        &opts,
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("budget spent");
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

// Covers ~XV9V6NR.
// frob:tests crates/frob-land/src/land.rs::Publish
#[test]
fn without_wait_a_ledger_only_base_move_folds() {
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
    let out = land(
        &fx.root,
        &opts,
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("folded");
    assert!(out.closed);
    assert_eq!(out.attempts, 2);
}

// Covers ~VMHTBE7.
#[test]
fn without_wait_a_code_moved_base_is_not_retried() {
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
            move_main(&root, "docs/other.md", "other\n");
        }
    });

    let err = land(
        &fx.root,
        &opts,
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("stale");
    assert_eq!(refusal(&err).code, "E-LAND-STALE");
    assert!(refusal(&err).message.ends_with("moved while landing"));
    let out = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("rerun resumes");
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

    land(
        &fx.root,
        &Fixture::opts(&one),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("first land");
    let out = land(
        &fx.root,
        &Fixture::opts(&two),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("second land regenerates the lockfile");
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
    Fixture::evidence(&s, "uv.lock");
    move_main(&fx.root, "uv.lock", "moved\n");
    let before = fx.main_tip();
    let err = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("no resolver");
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

    let out = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("pre-existing finding does not block");
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

    let err = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("new finding refuses");
    let msg = refusal(&err).message.clone();
    assert_eq!(refusal(&err).code, "E-LAND-CHECK-RED");
    assert!(msg.contains("has 1 new blocking finding(s)"), "{msg}");
    assert!(msg.contains("TODO001 src/new.rs"), "{msg}");
    assert!(!msg.contains("TODO001 src/old.rs"), "{msg}");
    assert_eq!(fx.main_tip(), before, "base did not move");
}

// frob:tests crates/frob-land/src/ratchet.rs::verdict
#[test]
fn a_second_identical_finding_in_the_ticket_refuses_though_the_base_has_one() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    commit_on_main(&fx, "src/old.rs", &marked(""));
    let s = fx.start("Duplicate the marker", &["src/**"]);
    let twice = format!("{}{}", marked(""), marked(""));
    Fixture::commit_in(&s.wt, "src/old.rs", &twice);
    Fixture::evidence(&s, "src/old.rs");
    let before = fx.main_tip();

    let err = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("duplicate occurrence refuses");
    let msg = refusal(&err).message.clone();
    assert_eq!(refusal(&err).code, "E-LAND-CHECK-RED");
    assert!(msg.contains("has 1 new blocking finding(s)"), "{msg}");
    assert!(msg.contains("TODO001 src/old.rs"), "{msg}");
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

    let out = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("land");
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

    let out = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("REL001 on the base does not block");
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
        "[rules]\nramp = false\n[pm]\ndone_requires = [\"criteria_evidenced\"]\n[release]\ntag = \"v{version}\"\n",
    );
    stray_tag(&fx, "v0.1.0");
    stray_tag(&fx, "app-v0.2.0");
    let s = fx.start("Rename tags", &["src/**", "frob.toml"]);
    Fixture::commit_in(
        &s.wt,
        "frob.toml",
        "[rules]\nramp = false\n[pm]\ndone_requires = [\"criteria_evidenced\"]\n[release]\ntag = \"{product}-v{version}\"\nproducts = [\"app\"]\n",
    );
    Fixture::evidence(&s, "frob.toml");
    let before = fx.main_tip();

    let err = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect_err("new REL001 refuses");
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

/// Plant a base set no real check would produce for the current main tip, where any land reads it.
fn plant_base_set(fx: &Fixture) -> PathBuf {
    let oid = fx.main_tip();
    let cfg = LedgerConfig::default();
    let key = frob_land::cache_key(&cfg);
    let tree = frob_land::code_tree_key(&fx.repo(), &fx.root, &oid, &cfg).expect("tree key");
    let planted = shared_state(fx)
        .join("land-base")
        .join(format!("{tree}-{key}.json"));
    std::fs::create_dir_all(planted.parent().expect("parent")).expect("mkdir");
    let fake = serde_json::json!({"oid": tree, "key": key, "findings": [{
        "fingerprint": "feedface", "rule": "PLANTED", "path": null, "message": "from the cached set"
    }]});
    std::fs::write(&planted, fake.to_string()).expect("plant");
    planted
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
    plant_base_set(&fx);

    let out = land(
        &fx.root,
        &Fixture::opts(&s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("land");
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
            gob_path::Shown::with_home(&wt, None).as_str(),
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

/// A clock three hours past now: every two-hour lease taken at real time has expired by it.
#[derive(Debug)]
struct LaterClock;

impl gob_time::Clock for LaterClock {
    fn now(&self) -> frob_ledger::model::Stamp {
        frob_ledger::model::Stamp::from_unix(gob_time::SystemClock.now().unix() + 3 * 3600)
    }
}

// frob:ticket 01M48TNCW1RS4TW9RYDG2Y8E0R
// frob:tests crates/frob-land/src/land.rs::reclaim_expired
#[test]
fn an_expired_lease_is_renewed_and_lands_when_nothing_overlapped_since() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add a", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/a.rs", "fn a() {}\n");
    Fixture::evidence(&s, "src/a.rs");
    let later: Arc<dyn gob_time::Clock> = Arc::new(LaterClock);
    let out = land(&fx.root, &Fixture::opts(&s), &later).expect("land after expiry");
    assert!(out.closed, "expired lease renewed, then landed");
}

// frob:tests crates/frob-land/src/land.rs::reclaim_expired
#[test]
fn an_expired_lease_is_not_renewed_when_another_holder_took_an_overlap() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add a", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/a.rs", "fn a() {}\n");
    Fixture::evidence(&s, "src/a.rs");
    let later: Arc<dyn gob_time::Clock> = Arc::new(LaterClock);
    let thief = fx
        .leases()
        .with_clock(later.clone())
        .acquire(
            TicketId::mint(),
            &frob_lease::Holder {
                actor: "bob".to_owned(),
                worktree: fx.root.join("bob-wt"),
            },
            &["src/**".to_owned()],
        )
        .expect("bob takes the scope after the expiry");
    let err = land(&fx.root, &Fixture::opts(&s), &later).expect_err("overlap taken");
    assert_eq!(refusal(&err).code, "E-LAND-NOT-LEASED");
    assert!(
        fx.ledger().show(s.id).expect("show").summary.category != Category::Done,
        "nothing landed"
    );
    drop(thief);
}

// frob:ticket 01M4BH0C9D5X79MFHTAYBHKQGE
// frob:tests crates/frob-land/src/land.rs::ticket_worktree
#[test]
fn a_pruned_expired_lease_is_renewed_for_the_ticket_worktree_when_landing_from_the_primary() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add a", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/a.rs", "fn a() {}\n");
    Fixture::evidence(&s, "src/a.rs");
    let later: Arc<dyn gob_time::Clock> = Arc::new(LaterClock);
    // Another lease verb prunes the expired file, as happens while the agent is down.
    fx.leases().with_clock(later.clone()).list().expect("prune");
    assert!(
        fx.leases().recorded_lease(s.id).expect("read").is_none(),
        "the expired lease record is gone"
    );
    let out = land(&fx.root, &Fixture::opts(&s), &later).expect("land from the primary");
    assert!(out.closed, "renewed for the ticket worktree, then landed");
}

/// Run one land with the system clock.
fn land_now(fx: &Fixture, s: &Started) -> Result<frob_land::LandOutcome, LandError> {
    land(
        &fx.root,
        &Fixture::opts(s),
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
}

// frob:ticket 01M4BMRY81T9B3T7SC3BWMVSPZ
// frob:tests crates/frob-land/src/land.rs::land
#[test]
fn two_lands_back_to_back_from_one_primary_both_succeed_without_failure_warnings() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let a = fx.start("Add a", &["src/a/**"]);
    let b = fx.start("Add b", &["src/b/**"]);
    Fixture::commit_in(&a.wt, "src/a/a.rs", "fn a() {}\n");
    Fixture::evidence(&a, "src/a/a.rs");
    Fixture::commit_in(&b.wt, "src/b/b.rs", "fn b() {}\n");
    Fixture::evidence(&b, "src/b/b.rs");
    let first = land_now(&fx, &a).expect("first land");
    assert!(first.closed && first.worktree_removed, "{first:?}");
    let second =
        land_now(&fx, &b).expect("second land exits ok after the first removed its branch");
    assert!(second.closed && second.worktree_removed, "{second:?}");
    assert!(
        second.warnings.iter().all(|w| !w.contains("failed")),
        "{:?}",
        second.warnings
    );
}

/// Land `s`, queueing on the land lock for up to two minutes instead of refusing.
fn land_waiting(fx: &Fixture, s: &Started) -> Result<frob_land::LandOutcome, LandError> {
    let opts = LandOptions {
        wait_secs: 120,
        ..Fixture::opts(s)
    };
    land(
        &fx.root,
        &opts,
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
}

// frob:ticket 01M4M27EDCXBRN2HZJXHAZK0F1
// frob:tests crates/frob-land/src/land.rs::land
#[test]
fn racing_lands_of_one_ticket_and_a_late_one_all_exit_ok_with_no_error() {
    if !git_available() {
        return;
    }
    for round in 0..if cfg!(windows) { 2 } else { 8 } {
        let fx = Fixture::new();
        let a = fx.start("Add a", &["src/a/**"]);
        Fixture::commit_in(&a.wt, "src/a/a.rs", "fn a() {}\n");
        Fixture::evidence(&a, "src/a/a.rs");
        let (x, y) = std::thread::scope(|scope| {
            let lx = scope.spawn(|| land_waiting(&fx, &a));
            let ly = scope.spawn(|| land_waiting(&fx, &a));
            (lx.join().expect("land x"), ly.join().expect("land y"))
        });
        let outs: Vec<_> = [x, y]
            .into_iter()
            .map(|r| r.unwrap_or_else(|e| panic!("round {round}: a racing land failed: {e}")))
            .collect();
        assert_eq!(
            outs.iter().filter(|o| o.closed && !o.already).count(),
            1,
            "round {round}: exactly one lander closes: {outs:?}"
        );
        assert!(!a.wt.exists(), "round {round}: worktree removed");
        let late = land_now(&fx, &a).expect("a land after the worktree is gone");
        assert!(late.already && !late.closed, "{late:?}");
    }
}

/// Create, pack and delete scratch branches until `stop` is set: the multi-process ref churn a busy primary sees.
fn churn_refs(root: &Path, stop: &std::sync::atomic::AtomicBool) {
    let run = |args: &[&str]| {
        let _ = std::process::Command::new("git")
            .args(args)
            .current_dir(root)
            .env("GIT_CONFIG_GLOBAL", "/dev/null")
            .env("GIT_CONFIG_SYSTEM", "/dev/null")
            .output();
    };
    let mut n = 0_u32;
    while !stop.load(std::sync::atomic::Ordering::Relaxed) {
        let name = format!("churn-{n}");
        run(&["branch", &name, "main"]);
        run(&["pack-refs", "--all"]);
        run(&["branch", "-D", &name]);
        n += 1;
    }
}

// frob:ticket 01M4CXTQ7DM4XEG3F1EAVNARNQ
// frob:tests crates/frob-land/src/land.rs::land
#[test]
fn concurrent_lands_under_branch_delete_and_pack_refs_churn_succeed_or_refuse_cleanly() {
    if !git_available() {
        return;
    }
    for round in 0..if cfg!(windows) { 3 } else { 20 } {
        let fx = Fixture::new();
        let a = fx.start("Add a", &["src/a/**"]);
        let b = fx.start("Add b", &["src/b/**"]);
        Fixture::commit_in(&a.wt, "src/a/a.rs", "fn a() {}\n");
        Fixture::evidence(&a, "src/a/a.rs");
        Fixture::commit_in(&b.wt, "src/b/b.rs", "fn b() {}\n");
        Fixture::evidence(&b, "src/b/b.rs");
        let stop = std::sync::atomic::AtomicBool::new(false);
        let results = std::thread::scope(|scope| {
            let churn = scope.spawn(|| churn_refs(&fx.root, &stop));
            let la = scope.spawn(|| land_now(&fx, &a));
            let lb = scope.spawn(|| land_now(&fx, &b));
            let out = (la.join().expect("land a"), lb.join().expect("land b"));
            stop.store(true, std::sync::atomic::Ordering::Relaxed);
            churn.join().expect("churn");
            out
        });
        for (name, result) in [("a", results.0), ("b", results.1)] {
            match result {
                Ok(out) => assert!(out.closed, "round {round} land {name}: {out:?}"),
                Err(e) => assert!(
                    e.refusal().is_some(),
                    "round {round} land {name} failed uncleanly: {e}"
                ),
            }
        }
    }
}

// frob:ticket 01M4BMRY81T9B3T7SC3BWMVSPZ
// frob:tests crates/frob-land/src/land.rs::land
#[test]
fn the_base_is_resolved_by_full_ref_so_a_same_named_tag_cannot_shadow_it() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Add t", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/t.rs", "fn t() {}\n");
    Fixture::evidence(&s, "src/t.rs");
    // A bare `main` now resolves to the tag (git prefers tags to heads).
    git(&fx.root, &["tag", "main", &fx.main_tip()]);
    let out = land_now(&fx, &s).expect("land with a tag named like the base");
    assert!(out.closed, "{out:?}");
    let blob = fx
        .repo()
        .read_blob_at("refs/heads/main", "src/t.rs")
        .expect("read");
    assert_eq!(blob.as_deref(), Some(b"fn t() {}\n".as_slice()));
}

/// Land a fresh ticket on the current main and report whether the planted base set was used.
fn lands_with_planted_set(fx: &Fixture, title: &str, rel: &str) -> bool {
    let s = fx.start(title, &["src/**"]);
    Fixture::commit_in(&s.wt, rel, "fn x() {}\n");
    Fixture::evidence(&s, rel);
    let out = land_now(fx, &s).expect("land");
    out.resolved.iter().any(|n| n.rule == "PLANTED")
}

// frob:ticket 01M4CTDXHZ5B85NXCN1KJ95784
// frob:tests crates/frob-land/src/ratchet.rs::base_findings
#[test]
fn base_commits_differing_only_under_tickets_share_the_cached_base_set() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    plant_base_set(&fx);
    // A ledger write: a new base commit, the same code tree.
    fx.ledger()
        .new_ticket(NewTicket::new("Unrelated ledger write", TicketType::Task))
        .expect("ticket write");
    assert!(
        lands_with_planted_set(&fx, "Add a", "src/a.rs"),
        "a ledger-only base commit must hit the cache"
    );
}

// frob:ticket 01M4CTDXHZ5B85NXCN1KJ95784
// frob:tests crates/frob-land/src/ratchet.rs::base_findings
#[test]
fn a_base_commit_changing_code_misses_the_cached_base_set() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    plant_base_set(&fx);
    commit_on_main(&fx, "src/new.rs", "fn n() {}\n");
    assert!(
        !lands_with_planted_set(&fx, "Add b", "src/b.rs"),
        "a code change on the base must recompute"
    );
}

/// The message of the base set's PM033 finding at the current main tip, through the cache.
fn pm033_message(fx: &Fixture) -> Option<String> {
    let oid = fx.main_tip();
    let set = frob_land::base_findings(&fx.repo(), &fx.root, &oid, &LedgerConfig::default())
        .expect("base findings");
    set.into_iter()
        .find(|n| n.rule == "PM033")
        .map(|n| n.message)
}

// frob:ticket 01M4CTDXHZ5B85NXCN1KJ95784
// frob:tests crates/frob-land/src/ratchet.rs::base_findings
#[test]
fn a_ledger_only_base_commit_changes_a_location_less_pm_finding_on_the_cache_hit_path() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    // A bare ticket makes the ledger exist without making anything ready.
    fx.ledger()
        .new_ticket(NewTicket::new("Bare", TicketType::Task))
        .expect("first ticket");
    let before = pm033_message(&fx).expect("a low ready queue trips PM033");
    // A ledger-only commit: a ready ticket changes the PM033 count, never the code tree.
    let mut req = NewTicket::new("Ready work", TicketType::Task);
    req.scope = vec!["src/**".to_owned()];
    req.acceptance = vec!["it works".to_owned()];
    fx.ledger().new_ticket(req).expect("ticket write");
    let cached_dir = shared_state(&fx).join("land-base");
    let files_before = std::fs::read_dir(&cached_dir).expect("cache dir").count();
    let after = pm033_message(&fx);
    assert_eq!(
        std::fs::read_dir(&cached_dir).expect("cache dir").count(),
        files_before,
        "same code tree: the second call reused the cache entry"
    );
    assert_ne!(
        after.as_deref(),
        Some(before.as_str()),
        "PM033 must reflect the new ledger content, not the cached one"
    );
}

/// A canned base-CI reader: returns one state and remembers the sha it was asked about.
#[derive(Debug)]
struct CannedCi {
    state: frob_release::ci::CiState,
    asked: std::sync::Mutex<Vec<String>>,
    runs: Option<Vec<frob_release::culprit::RunRecord>>,
}

impl CannedCi {
    fn new(state: frob_release::ci::CiState) -> Arc<Self> {
        Arc::new(Self {
            state,
            asked: std::sync::Mutex::new(Vec::new()),
            runs: None,
        })
    }

    /// A reader that also lists `runs` for culprit finding.
    fn with_runs(
        state: frob_release::ci::CiState,
        runs: Vec<frob_release::culprit::RunRecord>,
    ) -> Arc<Self> {
        Arc::new(Self {
            state,
            asked: std::sync::Mutex::new(Vec::new()),
            runs: Some(runs),
        })
    }
}

impl frob_land::CiReader for CannedCi {
    fn read(&self, _repo: &Repo, _cwd: &Path, sha: &str) -> frob_release::ci::CiState {
        self.asked.lock().expect("lock").push(sha.to_owned());
        self.state.clone()
    }

    fn runs(
        &self,
        _repo: &Repo,
        _cwd: &Path,
        _branch: &str,
    ) -> Option<Vec<frob_release::culprit::RunRecord>> {
        self.runs.clone()
    }
}

fn failing(name: &str) -> frob_release::ci::CiState {
    frob_release::ci::CiState::Red {
        failures: vec![frob_release::ci::CiFailure {
            name: name.to_owned(),
            conclusion: "failure".to_owned(),
            url: Some(format!(
                "https://github.com/acme/widget/actions/runs/1/{name}"
            )),
        }],
    }
}

/// A ready-to-land ticket plus options carrying `ci`.
fn ci_land(
    fx: &Fixture,
    ci: Arc<CannedCi>,
    tweak: impl FnOnce(&mut LandOptions),
) -> (Started, Result<frob_land::LandOutcome, LandError>) {
    let s = fx.start("Add ci", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/ci.rs", "fn ci() {}\n");
    Fixture::evidence(&s, "src/ci.rs");
    let mut opts = Fixture::opts(&s);
    opts.ci_reader = Some(ci);
    tweak(&mut opts);
    let out = land(
        &fx.root,
        &opts,
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    );
    (s, out)
}

// frob:ticket 01M4CTDWJRKBC64EBQPGHMWDGG
// frob:tests crates/frob-land/src/base_ci.rs::gate
#[test]
fn a_red_base_ci_refuses_naming_the_run_and_moves_nothing() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let ci = CannedCi::new(failing("rust (windows-latest)"));
    let (_, out) = ci_land(&fx, ci.clone(), |_| {});
    let err = out.expect_err("refused");
    let r = refusal(&err);
    assert_eq!(r.code, "E-LAND-BASE-RED");
    assert!(r.message.contains("actions/runs/1/"), "{}", r.message);
    assert_eq!(
        fx.main_tip(),
        ci.asked.lock().expect("lock")[0],
        "the base did not move past the commit whose CI was read"
    );
    let blob = fx.repo().read_blob_at(MAIN, "src/ci.rs").expect("read");
    assert!(blob.is_none(), "the ticket's code was not landed");
}

// frob:ticket 01M4CTDWJRKBC64EBQPGHMWDGG
// frob:tests crates/frob-land/src/base_ci.rs::gate
#[test]
fn a_publish_only_failure_on_the_base_does_not_block_the_land() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let (_, out) = ci_land(&fx, CannedCi::new(failing("dev-publish")), |_| {});
    let out = out.expect("lands");
    assert!(out.closed);
    assert!(
        out.warnings.iter().any(|w| w.contains("dev-publish")),
        "{:?}",
        out.warnings
    );
}

// frob:ticket 01M4CTDWJRKBC64EBQPGHMWDGG
// frob:tests crates/frob-land/src/base_ci.rs::gate
#[test]
fn an_unreadable_base_ci_is_reported_unresolved_and_the_default_policy_lands() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let unknown = frob_release::ci::CiState::Unknown(frob_release::ci::CiUnknown {
        reason: "gh is not installed".to_owned(),
        remedy: "install gh".to_owned(),
    });
    let (_, out) = ci_land(&fx, CannedCi::new(unknown), |_| {});
    let out = out.expect("lands");
    assert!(
        out.warnings.iter().any(|w| w.starts_with("Unresolved:")),
        "{:?}",
        out.warnings
    );
}

// frob:ticket 01M4CTDWJRKBC64EBQPGHMWDGG
// frob:tests crates/frob-land/src/base_ci.rs::gate
#[test]
fn a_configured_block_on_unknown_refuses_an_unreadable_base_ci() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    commit_on_main(
        &fx,
        "frob.toml",
        "[pm]\ndone_requires = [\"criteria_evidenced\"]\n[land]\nblock_on_unknown_ci = true\n",
    );
    let unknown = frob_release::ci::CiState::Unknown(frob_release::ci::CiUnknown {
        reason: "no network".to_owned(),
        remedy: "restore it".to_owned(),
    });
    let (_, out) = ci_land(&fx, CannedCi::new(unknown), |_| {});
    assert_eq!(
        refusal(&out.expect_err("refused")).code,
        "E-LAND-BASE-CI-UNKNOWN"
    );
}

// frob:ticket 01M4CTDWJRKBC64EBQPGHMWDGG
// frob:tests crates/frob-land/src/base_ci.rs::gate
#[test]
fn an_override_lands_on_a_red_base_and_records_a_decision_on_the_ticket() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let (s, out) = ci_land(&fx, CannedCi::new(failing("rust (linux)")), |o| {
        o.override_base_ci = Some("hotfix for the red base".to_owned());
    });
    assert!(out.expect("overridden land").closed);
    let events = fx.ledger().events(s.id).expect("events");
    assert!(
        events
            .iter()
            .any(|e| format!("{:?}", e.body).contains("hotfix for the red base")),
        "the override is on the ticket"
    );
}

// frob:ticket 01M4CTDWJRKBC64EBQPGHMWDGG
// frob:tests crates/frob-land/src/base_ci.rs::gate
#[test]
fn require_base_green_false_skips_the_ci_read_entirely() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    commit_on_main(
        &fx,
        "frob.toml",
        "[pm]\ndone_requires = [\"criteria_evidenced\"]\n[land]\nrequire_base_green = false\n",
    );
    let ci = CannedCi::new(failing("rust (linux)"));
    let (_, out) = ci_land(&fx, ci.clone(), |_| {});
    assert!(out.expect("lands").closed);
    assert!(ci.asked.lock().expect("lock").is_empty());
}

// frob:ticket 01M4GWS3GBJTFXFEGSNFB7J4FQ
// frob:tests crates/frob-land/src/base_ci.rs::with_culprit
#[test]
fn a_red_base_files_one_blocking_fix_ticket_and_later_lands_wait_for_it() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let tip = fx.main_tip();
    let red = vec![frob_release::culprit::RunRecord {
        sha: tip,
        verdict: frob_release::culprit::Verdict::Red,
    }];
    let ci = CannedCi::with_runs(failing("rust (linux)"), red);
    let (_, out) = ci_land(&fx, ci.clone(), |_| {});
    let first = refusal(&out.expect_err("refused")).message.clone();
    assert!(first.contains("fix ticket ~"), "{first}");
    let blockers = |fx: &Fixture| {
        fx.ledger()
            .list(&frob_ledger::index::ListFilter {
                label: Some("blocks-lands".to_owned()),
                ..Default::default()
            })
            .expect("list")
            .len()
    };
    assert_eq!(blockers(&fx), 1);
    let t = fx.start("Add other", &["lib/**"]);
    Fixture::commit_in(&t.wt, "lib/o.rs", "fn o() {}\n");
    Fixture::evidence(&t, "lib/o.rs");
    let mut opts = Fixture::opts(&t);
    opts.ci_reader = Some(ci);
    let again = land(
        &fx.root,
        &opts,
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    );
    let second = refusal(&again.expect_err("still refused")).message.clone();
    assert!(
        second.contains("blocked until the fix ticket closes"),
        "{second}"
    );
    assert_eq!(blockers(&fx), 1, "no second fix ticket");
}

// frob:ticket 01M4CTDWJRKBC64EBQPGHMWDGG
// frob:tests crates/frob-land/src/base_ci.rs::gate
#[test]
fn the_base_ci_gate_asks_about_the_remote_tracking_tip_when_there_is_one() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let pushed = fx.main_tip();
    // The remote-tracking ref is what GitHub ran CI for; local main has moved on since.
    let remote = fx.root.join(".git/refs/remotes/origin");
    std::fs::create_dir_all(&remote).expect("remote dir");
    std::fs::write(remote.join("main"), format!("{pushed}\n")).expect("remote ref");
    commit_on_main(&fx, "unpushed.txt", "local only\n");
    assert_ne!(fx.main_tip(), pushed, "local main is ahead of the remote");
    let ci = CannedCi::new(failing("rust (linux)"));
    let (_, out) = ci_land(&fx, ci.clone(), |_| {});
    assert_eq!(refusal(&out.expect_err("red")).code, "E-LAND-BASE-RED");
    assert_eq!(
        ci.asked.lock().expect("lock")[0],
        pushed,
        "the pushed tip, not the local one"
    );
}

// frob:ticket 01M4CTDWJRKBC64EBQPGHMWDGG
// frob:tests crates/frob-land/src/base_ci.rs::gate
#[test]
fn the_base_ci_gate_falls_back_to_the_local_tip_without_a_remote_tracking_ref() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    assert!(
        !fx.root.join(".git/refs/remotes/origin/main").exists(),
        "no remote-tracking ref in the fixture"
    );
    commit_on_main(&fx, "unpushed.txt", "local only\n");
    let ci = CannedCi::new(failing("rust (linux)"));
    let (_, out) = ci_land(&fx, ci.clone(), |_| {});
    assert_eq!(refusal(&out.expect_err("red")).code, "E-LAND-BASE-RED");
    assert_eq!(ci.asked.lock().expect("lock")[0], fx.main_tip());
}

/// Whether a directory the probe logged names `wt`, ignoring slash style, verbatim prefix and case.
fn same_dir(logged: &str, wt: &Path) -> bool {
    let norm = |s: &str| {
        s.trim()
            .trim_start_matches(r"\\?\")
            .replace('\\', "/")
            .to_lowercase()
    };
    norm(logged) == norm(&gob_path::Shown::with_home(wt, None).to_string())
}

// frob:ticket 01M4MH61ZJD4VYYXPANZ8132AR
// frob:ticket 01M4QDWQN6QM6Q89TG6NXY7BCD
// frob:tests crates/frob-land/src/land.rs::verify_check
#[cfg_attr(
    windows,
    ignore = "frob:todo T-NXY7BCD: the sh tool probe spawns nothing on the Windows runner"
)]
#[test]
fn land_reuses_a_recorded_tool_pass_for_an_unchanged_tree_and_reruns_after_an_input_changes() {
    if !git_available() {
        return;
    }
    let spawns_dir = tempfile::tempdir().expect("tempdir");
    let log = spawns_dir.path().join("spawns.log");
    // The probe is a git alias: git runs it through its own bundled sh, which a bare `sh` is not on Windows.
    let extra = format!(
        "[[check.tool]]\nname = \"probe\"\ncommand = \"git\"\nargs = [\"-c\", \"alias.probe=!(pwd -W 2>/dev/null || pwd) >> '{}'\", \"probe\"]\ninputs = [\"src/**\"]\n",
        // Forward slashes: backslashes are TOML escapes and sh escapes alike on Windows.
        Shown::with_home(&log, None).to_string().replace('\\', "/")
    );
    // The probe logs its working directory, so spawns in a ticket worktree are told apart from
    // the one land's base-set run makes in the persistent base checkout.
    let spawned_in = |wt: &Path| {
        std::fs::read_to_string(&log)
            .unwrap_or_default()
            .lines()
            .filter(|l| same_dir(l, wt))
            .count()
    };
    let clock = || Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>;
    let check = |s: &Started| {
        let opts = frob_check::CheckOptions {
            ticket: Some(s.handle.clone()),
            skip_telemetry: true,
            ..frob_check::CheckOptions::default()
        };
        frob_check::run(&s.wt, &opts).expect("check");
    };

    // Same tree checked, then landed: the land runs no tool process.
    let fx = Fixture::configured("criteria_evidenced", &extra);
    let s = fx.start("Add a", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/a.rs", "fn a() {}\n");
    Fixture::evidence(&s, "src/a.rs");
    let s_wt = gob_exec::canonical(&s.wt).expect("worktree");
    check(&s);
    assert_eq!(spawned_in(&s_wt), 1, "the check ran the tool once");
    land(&fx.root, &Fixture::opts(&s), &clock()).expect("land");
    assert_eq!(spawned_in(&s_wt), 1, "land reused the recorded pass");

    // A tree whose input differs from every recorded pass runs the tool again.
    let t = fx.start("Add b", &["src/**"]);
    Fixture::commit_in(&t.wt, "src/b.rs", "fn b() {}\n");
    Fixture::evidence(&t, "src/b.rs");
    let t_wt = gob_exec::canonical(&t.wt).expect("worktree");
    land(&fx.root, &Fixture::opts(&t), &clock()).expect("land b");
    assert_eq!(
        spawned_in(&t_wt),
        1,
        "a changed input misses and runs the tool"
    );
}

// frob:ticket 01M4CXTP6NCCZ7YNQCER0RXNYF
#[test]
fn retrying_the_land_record_after_a_failed_close_leaves_exactly_one_land_event() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Retry record", &["src/**"]);
    let ledger = fx.ledger();
    let body = frob_land::events::LandEvent {
        base_ref: MAIN,
        commit: "0123456789abcdef0123456789abcdef01234567",
        branch: "ticket/retry",
        pushed: false,
    };
    // First attempt records the land, then the close "fails" (never runs); the retry records again.
    frob_land::events::append_land(&ledger, s.id, &body).expect("first");
    frob_land::events::append_land(&ledger, s.id, &body).expect("retry");
    let lands = ledger
        .events(s.id)
        .expect("events")
        .iter()
        .filter(|e| matches!(e.body, frob_ledger::event::EventBody::Land(_)))
        .count();
    assert_eq!(lands, 1, "a retry must not duplicate the land event");
}

/// A train runner that fails any batch holding `poison` and counts its checks.
struct Poison {
    poison: Option<String>,
    calls: std::sync::atomic::AtomicU32,
}

impl frob_land::bisect::Runner for Poison {
    fn check(
        &self,
        subset: &[String],
    ) -> Result<frob_land::bisect::Verdict, frob_land::bisect::CheckFault> {
        self.calls.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
        match &self.poison {
            Some(p) if subset.contains(p) => Ok(frob_land::bisect::Verdict::Red(format!(
                "{p}: test failed (assertion left != right)"
            ))),
            _ => Ok(frob_land::bisect::Verdict::Green),
        }
    }
}

/// `n` disjoint started tickets, each with one committed and evidenced file, all enqueued.
fn enqueued(fx: &Fixture, n: usize) -> Vec<Started> {
    (0..n)
        .map(|i| {
            let dir = format!("t{i:02}");
            let s = fx.start(&format!("Add {dir}"), &[&format!("{dir}/**")]);
            let rel = format!("{dir}/{dir}.rs");
            Fixture::commit_in(&s.wt, &rel, "fn f() {}\n");
            Fixture::evidence(&s, &rel);
            let clock = Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>;
            let lo = LandOptions {
                handle: Some(s.handle.clone()),
                ..LandOptions::default()
            };
            let q = frob_land::enqueue(&s.wt, &lo, &clock).expect("enqueue");
            assert!(matches!(q, frob_land::Enqueued::Queued { .. }));
            s
        })
        .collect()
}

fn train_clock() -> Arc<dyn gob_time::Clock> {
    Arc::new(gob_time::SystemClock)
}

// frob:ticket 01M4Z1ND9ZM2NPAFJBF67JHDV6
// frob:tests crates/frob-land/src/train.rs::train_drain
#[test]
fn twelve_ready_tickets_with_one_failing_land_eleven_and_return_the_culprit() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let tickets = enqueued(&fx, 12);
    let culprit = &tickets[3];
    let store = frob_land::train_state::TrainStore::new(fx.repo().common_dir());
    store
        .set_batch(&frob_land::train_state::BatchSize { current: 8, max: 8 })
        .expect("batch");
    let runner = Arc::new(Poison {
        poison: Some(culprit.handle.clone()),
        calls: 0.into(),
    });
    let opts = frob_land::TrainOptions {
        land: LandOptions::default(),
        runner: Some(runner),
        enqueue_only: false,
    };
    let report = frob_land::train_drain(&fx.root, &opts, &train_clock()).expect("drain");
    let landed: usize = report.rounds.iter().map(|r| r.landed.len()).sum();
    assert_eq!(landed, 11, "{report:?}");
    assert_eq!(report.remaining, 0);
    for s in &tickets {
        let view = fx.ledger().show(s.id).expect("show");
        if s.id == culprit.id {
            assert_eq!(view.summary.category, Category::InProgress);
            assert!(fx.leases().live_lease(s.id).expect("lease").is_some());
            let res = store.result(&s.id).expect("result").expect("recorded");
            assert_eq!(res.status, frob_land::train_state::MemberStatus::Red);
            // the red result is on the ticket itself, and its lease is back in the WIP count
            assert!(view.ticket.front.labels.contains(&"train-red".to_owned()));
            let comments: Vec<String> = fx
                .ledger()
                .events(s.id)
                .expect("events")
                .iter()
                .filter_map(|e| match &e.body {
                    frob_ledger::event::EventBody::Comment(c) => Some(c.body.clone()),
                    _ => None,
                })
                .collect();
            assert!(
                comments.iter().any(|c| c.contains("test failed")),
                "{comments:?}"
            );
            let lease = fx
                .leases()
                .recorded_lease(s.id)
                .expect("lease")
                .expect("held");
            assert!(!lease.queued, "a red ticket is back with its agent");
            assert!(
                res.reason.as_deref().unwrap_or("").contains("test failed"),
                "failing evidence travels with the culprit: {res:?}"
            );
        } else {
            assert_eq!(view.summary.category, Category::Done);
        }
    }
    let rel = "t00/t00.rs";
    assert!(fx.repo().read_blob_at("main", rel).expect("read").is_some());
    assert!(
        fx.repo()
            .read_blob_at("main", "t03/t03.rs")
            .expect("read")
            .is_none(),
        "the culprit did not land"
    );
    // the culprit's agent gets the evidence when it asks the train again
    let lo = LandOptions {
        handle: Some(culprit.handle.clone()),
        ..LandOptions::default()
    };
    assert!(matches!(
        frob_land::enqueue(&culprit.wt, &lo, &train_clock()).expect("re-enqueue"),
        frob_land::Enqueued::Queued { .. }
    ));
}

// frob:ticket 01M51CKGA207PC030VWRPM3ECA
// frob:tests crates/frob-land/src/train.rs::train_drain
#[test]
fn the_driver_renews_a_queued_members_lease_each_round() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let tickets = enqueued(&fx, 1);
    let s = &tickets[0];
    // age the lease (still live) so a renewal is visible
    let path = fx
        .repo()
        .common_dir()
        .join("frob/leases")
        .join(format!("{}.toml", s.id));
    let text = std::fs::read_to_string(&path).expect("lease file");
    let old = text
        .lines()
        .find(|l| l.starts_with("renewed_at"))
        .expect("renewed_at")
        .to_owned();
    std::fs::write(
        &path,
        text.replace(&old, "renewed_at = \"2020-01-01T00:00:00Z\"")
            .replace("ttl_secs = 7200", "ttl_secs = 99999999999"),
    )
    .expect("age lease");
    let before = fx
        .leases()
        .recorded_lease(s.id)
        .expect("lease")
        .expect("held");
    let runner = Arc::new(Poison {
        poison: Some(s.handle.clone()),
        calls: 0.into(),
    });
    let opts = frob_land::TrainOptions {
        land: LandOptions::default(),
        runner: Some(runner),
        enqueue_only: false,
    };
    frob_land::train_drain(&fx.root, &opts, &train_clock()).expect("drain");
    let after = fx
        .leases()
        .recorded_lease(s.id)
        .expect("lease")
        .expect("held");
    assert!(
        after.renewed_at > before.renewed_at,
        "the round renewed the lease"
    );
    assert!(
        !after.scope.is_empty(),
        "the scope is the lease's, never empty"
    );
}

// frob:ticket 01M51CKG205D0WF5XNGPRK8GZ3
// frob:tests crates/frob-land/src/train.rs::train_drain
#[test]
fn a_member_that_does_not_merge_is_evicted_and_the_rest_land() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let clock = train_clock();
    let tickets: Vec<Started> = (0..3)
        .map(|i| {
            let dir = format!("t{i:02}");
            let s = fx.start(&format!("Add {dir}"), &[&format!("{dir}/**")]);
            let rel = format!("{dir}/{dir}.rs");
            Fixture::commit_in(&s.wt, &rel, "fn f() {}\n");
            Fixture::evidence(&s, &rel);
            let lo = LandOptions {
                handle: Some(s.handle.clone()),
                ..LandOptions::default()
            };
            frob_land::enqueue(&s.wt, &lo, &clock).expect("enqueue");
            s
        })
        .collect();
    let clash = &tickets[1];
    // the base gains the clash member's file with other content after enqueue: an add/add conflict
    // that only shows once the member is merged onto the moving base, so the ticket rules stay green
    Fixture::commit_in(&fx.root, "t01/t01.rs", "fn other() {}\n");
    let store = frob_land::train_state::TrainStore::new(fx.repo().common_dir());
    store
        .set_batch(&frob_land::train_state::BatchSize { current: 8, max: 8 })
        .expect("batch");
    let opts = frob_land::TrainOptions {
        land: LandOptions::default(),
        runner: Some(Arc::new(Poison {
            poison: None,
            calls: 0.into(),
        })),
        enqueue_only: false,
    };
    let report = frob_land::train_drain(&fx.root, &opts, &train_clock()).expect("drain");
    let landed: usize = report.rounds.iter().map(|r| r.landed.len()).sum();
    assert_eq!(landed, 2, "{report:?}");
    let res = store.result(&clash.id).expect("result").expect("recorded");
    assert_eq!(res.status, frob_land::train_state::MemberStatus::Evicted);
    let labels = fx
        .ledger()
        .show(clash.id)
        .expect("show")
        .ticket
        .front
        .labels;
    assert!(labels.contains(&"train-evicted".to_owned()), "{labels:?}");
    assert!(
        res.reason
            .as_deref()
            .unwrap_or("")
            .contains("did not merge"),
        "{res:?}"
    );
    assert_eq!(
        fx.ledger()
            .show(tickets[2].id)
            .expect("show")
            .summary
            .category,
        Category::Done
    );
}

/// A runner that moves a member's branch once, as an agent pushing mid-round would.
struct MovesBranch {
    wt: std::path::PathBuf,
    moved: std::sync::atomic::AtomicBool,
}

impl frob_land::bisect::Runner for MovesBranch {
    fn check(
        &self,
        _subset: &[String],
    ) -> Result<frob_land::bisect::Verdict, frob_land::bisect::CheckFault> {
        if !self.moved.swap(true, std::sync::atomic::Ordering::SeqCst) {
            Fixture::commit_in(&self.wt, "moved.txt", "late\n");
        }
        Ok(frob_land::bisect::Verdict::Green)
    }
}

// frob:ticket 01M52RT3Z0E1SSXA3RHFE8QFTF
// frob:tests crates/frob-land/src/train.rs::train_drain
#[test]
fn a_member_dropped_from_the_final_candidate_is_evicted_not_a_round_fault() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let clock = train_clock();
    let tickets = enqueued(&fx, 3);
    let store = frob_land::train_state::TrainStore::new(fx.repo().common_dir());
    store
        .set_batch(&frob_land::train_state::BatchSize { current: 8, max: 8 })
        .expect("batch");
    let opts = frob_land::TrainOptions {
        land: LandOptions::default(),
        runner: Some(Arc::new(MovesBranch {
            wt: tickets[1].wt.clone(),
            moved: false.into(),
        })),
        enqueue_only: false,
    };
    let report = frob_land::train_drain(&fx.root, &opts, &clock).expect("drain does not fault");
    let res = store
        .result(&tickets[1].id)
        .expect("result")
        .expect("recorded");
    assert_eq!(res.status, frob_land::train_state::MemberStatus::Evicted);
    let landed: usize = report.rounds.iter().map(|r| r.landed.len()).sum();
    assert_eq!(landed, 2, "{report:?}");
}

// frob:ticket 01M4Z1ND9ZM2NPAFJBF67JHDV6
// frob:tests crates/frob-land/src/train.rs::train_status
#[test]
fn train_status_reports_queue_candidate_and_batch_size_as_an_envelope() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let tickets = enqueued(&fx, 2);
    let st = frob_land::train_status(&fx.root, &train_clock()).expect("status");
    assert_eq!(st.queue.len(), 2);
    assert_eq!(st.queue[0].id, tickets[0].id, "oldest first");
    assert!(st.current.is_none());
    assert_eq!((st.batch.current, st.batch.max), (1, 8));
    assert!(st.enabled);
    assert!(st.dropped.is_empty(), "clean queue has no dropped hunks");
    let json = serde_json::to_value(&st).expect("json");
    for key in [
        "summary", "enabled", "queue", "batch", "live", "stale", "dropped",
    ] {
        assert!(json.get(key).is_some(), "{key} in {json}");
    }
    let schema = schemars::schema_for!(frob_land::TrainStatusReport);
    let text = serde_json::to_string(&schema).expect("schema");
    assert!(text.contains("queue") && text.contains("batch"), "{text}");
}

// frob:ticket 01M4Z1ND9ZM2NPAFJBF67JHDV6
// frob:tests crates/frob-land/src/train.rs::land_train
#[test]
fn a_lone_ticket_lands_as_a_batch_of_one() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Lone", &["solo/**"]);
    Fixture::commit_in(&s.wt, "solo/solo.rs", "fn f() {}\n");
    Fixture::evidence(&s, "solo/solo.rs");
    let runner = Arc::new(Poison {
        poison: None,
        calls: 0.into(),
    });
    let opts = frob_land::TrainOptions {
        land: LandOptions {
            handle: Some(s.handle.clone()),
            ..LandOptions::default()
        },
        runner: Some(runner.clone()),
        enqueue_only: false,
    };
    let out = frob_land::land_train(&s.wt, &opts, &train_clock()).expect("land --train");
    assert!(out.closed, "{out:?}");
    assert!(
        fx.repo()
            .read_blob_at("main", "solo/solo.rs")
            .expect("read")
            .is_some()
    );
    assert_eq!(
        runner.calls.load(std::sync::atomic::Ordering::SeqCst),
        1,
        "the train checked the lone ticket as a batch of one"
    );
    let store = frob_land::train_state::TrainStore::new(fx.repo().common_dir());
    assert!(store.queue().expect("queue").is_empty());
}

// frob:ticket 01M51CKGHR8XECF9SBCZ5TQW0Z
// frob:tests crates/frob-land/src/train.rs::land_train
// frob:tests crates/frob-land/src/train.rs::enqueue
#[test]
fn enqueue_only_queues_the_ticket_and_flags_its_lease_without_driving() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("Queued", &["solo/**"]);
    Fixture::commit_in(&s.wt, "solo/solo.rs", "fn f() {}\n");
    Fixture::evidence(&s, "solo/solo.rs");
    let mut opts = frob_land::TrainOptions::new(LandOptions {
        handle: Some(s.handle.clone()),
        ..LandOptions::default()
    });
    opts.enqueue_only = true;
    let out = frob_land::land_train(&s.wt, &opts, &train_clock()).expect("enqueue-only");
    assert!(!out.closed, "{out:?}");
    assert!(out.warnings.iter().any(|w| w.contains("queued")), "{out:?}");
    let store = frob_land::train_state::TrainStore::new(fx.repo().common_dir());
    assert_eq!(store.queue().expect("queue").len(), 1);
    assert!(
        fx.repo()
            .read_blob_at("main", "solo/solo.rs")
            .expect("read")
            .is_none(),
        "nothing landed"
    );
    let lease = fx
        .leases()
        .recorded_lease(s.id)
        .expect("lease")
        .expect("held");
    assert!(lease.queued, "a queued ticket's lease leaves the WIP count");
}

// frob:ticket 01M4Z1ND9ZM2NPAFJBF67JHDV6
// frob:tests crates/frob-land/src/train.rs::land_train
#[test]
fn with_the_train_disabled_land_train_behaves_as_plain_land() {
    if !git_available() {
        return;
    }
    let fx = Fixture::configured("criteria_evidenced", "\n[land]\ntrain = false\n");
    let s = fx.start("Plain", &["plain/**"]);
    Fixture::commit_in(&s.wt, "plain/plain.rs", "fn f() {}\n");
    Fixture::evidence(&s, "plain/plain.rs");
    let opts = frob_land::TrainOptions::new(LandOptions {
        handle: Some(s.handle.clone()),
        ..LandOptions::default()
    });
    let out = frob_land::land_train(&s.wt, &opts, &train_clock()).expect("land --train");
    assert!(out.closed, "{out:?}");
    let err = frob_land::train_run(&fx.root, &opts, &train_clock()).expect_err("off");
    assert_eq!(
        err.refusal().map(|r| r.code.as_str()),
        Some("E-LAND-TRAIN-OFF")
    );
}

// frob:ticket 01M4D6NTFHJT2BRA8VCRD8WDJ4
// frob:tests crates/frob-land/src/ratchet.rs::base_findings
#[test]
#[cfg(unix)]
fn a_cache_miss_checks_out_the_base_once_for_both_passes() {
    use std::os::unix::fs::PermissionsExt;
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    // A post-checkout hook logs every checkout of the shared base worktree (git runs it on `worktree add` too).
    let hooks = fx.repo().common_dir().join("hooks");
    std::fs::create_dir_all(&hooks).expect("hooks dir");
    let log = fx.root.join("..").join("base-checkouts.log");
    let hook = hooks.join("post-checkout");
    std::fs::write(
        &hook,
        format!(
            "#!/bin/sh\necho \"$PWD\" >> \"{}\"\n",
            Shown::with_home(&log, None)
        ),
    )
    .expect("hook");
    std::fs::set_permissions(&hook, std::fs::Permissions::from_mode(0o755)).expect("chmod");
    let oid = fx.main_tip();
    frob_land::base_findings(&fx.repo(), &fx.root, &oid, &LedgerConfig::default())
        .expect("base findings on a miss");
    let base_runs = std::fs::read_to_string(&log)
        .unwrap_or_default()
        .lines()
        .filter(|l| l.ends_with("land-checkout"))
        .count();
    assert_eq!(
        base_runs, 1,
        "one checkout serves the exact and full passes"
    );
}

// frob:ticket 01M51CKH0VJ2AVAWHG8WA6YETF
// frob:tests crates/frob-land/src/train.rs::train_drop
#[test]
fn train_drop_removes_one_entry_with_a_reason_and_refuses_an_unqueued_ticket() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let tickets = enqueued(&fx, 2);
    let report = frob_land::train_drop(&fx.root, &tickets[0].handle, "superseded", &train_clock())
        .expect("drop");
    assert_eq!(report.remaining, 1);
    let st = frob_land::train_status(&fx.root, &train_clock()).expect("status");
    assert_eq!(st.queue.len(), 1);
    assert_eq!(st.queue[0].id, tickets[1].id);
    let store = frob_land::train_state::TrainStore::new(fx.repo().common_dir());
    let res = store.result(&tickets[0].id).expect("result").expect("some");
    assert!(
        res.reason.as_deref().unwrap_or("").contains("superseded"),
        "{res:?}"
    );
    let again = frob_land::train_drop(&fx.root, &tickets[0].handle, "x", &train_clock())
        .expect_err("not queued");
    assert_eq!(refusal(&again).code, "E-TRAIN-NOT-QUEUED");
}

/// Land a ticket with its branch kept, then make `origin/main` a commit that diverged from the land (a file the land lacks).
fn landed_locally_with_a_diverged_origin(fx: &Fixture) -> Started {
    git(&fx.root, &["branch", "side", "main"]);
    let s = fx.start("Add a", &["src/**"]);
    Fixture::commit_in(&s.wt, "src/a.rs", "fn a() {}\n");
    Fixture::evidence(&s, "src/a.rs");
    let mut opts = Fixture::opts(&s);
    opts.keep_worktree = true;
    land(
        &fx.root,
        &opts,
        &(Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>),
    )
    .expect("land");
    fx.repo()
        .commit_paths(
            "refs/heads/side",
            &[(
                RelPath::new("remote.txt").expect("path"),
                Some(b"from origin\n".to_vec()),
            )],
            "origin moved",
            &CommitOptions::default(),
        )
        .expect("side commit");
    git(
        &fx.root,
        &["update-ref", "refs/remotes/origin/main", "refs/heads/side"],
    );
    s
}

// frob:ticket 01M5CW05WX0TMSBKDFTPEHB5R3
// frob:tests crates/frob-land/src/relaunch.rs::relaunch
#[test]
fn relaunch_merges_the_remote_base_into_the_kept_branch_and_leaves_the_local_base() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = landed_locally_with_a_diverged_origin(&fx);
    let main_before = fx.main_tip();
    let clock = Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>;
    let out =
        frob_land::relaunch::relaunch(&fx.root, &Fixture::opts(&s), &clock).expect("relaunch");
    assert_eq!(out.base_merge.as_deref(), Some("merged"));
    assert_eq!(fx.main_tip(), main_before, "the local base is untouched");
    let branch = out.branch.expect("branch");
    let blob = fx.repo().read_blob_at(&branch, "remote.txt").expect("read");
    assert_eq!(blob.as_deref(), Some(b"from origin\n".as_slice()));
    let again = frob_land::relaunch::relaunch(&fx.root, &Fixture::opts(&s), &clock).expect("again");
    assert_eq!(again.base_merge.as_deref(), Some("up-to-date"));
}

// frob:ticket 01M5CW05WX0TMSBKDFTPEHB5R3
// frob:ticket 01M5DRXHC16AATVXYDWY7BTP5S
// frob:tests crates/frob-land/src/relaunch.rs::relaunch
#[test]
fn relaunch_follows_the_configured_sync_remote_and_pushes_only_when_asked() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = landed_locally_with_a_diverged_origin(&fx);
    let bare = fx.root.join("up.git");
    git(&fx.root, &["init", "--bare", "-q", "up.git"]);
    let bare_s = gob_path::Shown::of(&bare).to_string();
    git(&fx.root, &["remote", "add", "up", &bare_s]);
    git(&fx.root, &["push", "-q", "up", "side:main"]);
    git(&fx.root, &["fetch", "-q", "up"]);
    git(&fx.root, &["update-ref", "-d", "refs/remotes/origin/main"]);
    let toml = fx.root.join("frob.toml");
    let mut cfg = std::fs::read_to_string(&toml).unwrap_or_default();
    cfg.push_str("\n[sync]\nremote = \"up\"\n");
    std::fs::write(&toml, cfg).expect("write frob.toml");
    let clock = Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>;

    let plain = frob_land::relaunch::relaunch(&fx.root, &Fixture::opts(&s), &clock).expect("plain");
    assert!(!plain.pushed);
    assert!(
        plain.warnings.iter().any(|w| w.contains("to up")),
        "{:?}",
        plain.warnings
    );
    let mut opts = Fixture::opts(&s);
    opts.push = true;
    let out = frob_land::relaunch::relaunch(&fx.root, &opts, &clock).expect("push");
    assert!(out.pushed, "{:?}", out.warnings);
}

// frob:tests crates/frob-land/src/relaunch.rs::relaunch
#[test]
fn relaunch_refuses_an_unlanded_ticket_and_is_a_no_op_when_origin_has_the_land() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let clock = Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>;
    let open = fx.start("Open", &["docs/**"]);
    let err = frob_land::relaunch::relaunch(&fx.root, &Fixture::opts(&open), &clock)
        .expect_err("not landed");
    assert_eq!(refusal(&err).code, "E-RELAUNCH-NOT-LANDED");

    let s = landed_locally_with_a_diverged_origin(&fx);
    git(
        &fx.root,
        &["update-ref", "refs/remotes/origin/main", "refs/heads/main"],
    );
    let out = frob_land::relaunch::relaunch(&fx.root, &Fixture::opts(&s), &clock).expect("noop");
    assert!(out.already);
}

// frob:tests crates/frob-land/src/hostland.rs::record_host_lands
#[test]
fn a_hosting_side_squash_with_the_ticket_trailer_is_recorded_as_a_land_and_closes_the_ticket() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("hosted", &["src/**"]);
    let ledger = fx.ledger();
    let none = frob_land::hostland::record_host_lands(&ledger, "main", MAIN).expect("scan");
    assert!(none.is_empty(), "no trailer yet: {none:?}");
    git(
        &fx.root,
        &[
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            &format!("squash\n\nFrob-Ticket: {}", s.id),
        ],
    );
    let tip = fx.main_tip();
    let found = frob_land::hostland::record_host_lands(&ledger, "main", MAIN).expect("record");
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].commit, tip);
    assert_eq!(
        ledger.show(s.id).expect("show").summary.category,
        Category::Done
    );
    let again = frob_land::hostland::record_host_lands(&ledger, "main", MAIN).expect("again");
    assert!(again.is_empty(), "a done ticket is not recorded twice");
}

// frob:ticket 01M5DT8FKY9HJW3R9Q4CZB283M
// frob:tests record_host_lands
#[test]
fn a_hosting_side_squash_without_a_trailer_is_matched_by_patch_id() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = fx.start("hosted by patch", &["src/**"]);
    let ledger = fx.ledger();
    Fixture::commit_in(&s.wt, "src/a.txt", "one\n");
    let none = frob_land::hostland::record_host_lands(&ledger, "main", MAIN).expect("scan");
    assert!(none.is_empty(), "branch not merged yet: {none:?}");
    // The host squashes the same change onto main with no trailer.
    std::fs::create_dir_all(fx.root.join("src")).expect("mkdir");
    std::fs::write(fx.root.join("src/a.txt"), "one\n").expect("write");
    git(&fx.root, &["add", "-A"]);
    git(&fx.root, &["commit", "-q", "-m", "squash without trailer"]);
    let tip = fx.main_tip();
    let found = frob_land::hostland::record_host_lands(&ledger, "main", MAIN).expect("record");
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].commit, tip);
    assert_eq!(
        ledger.show(s.id).expect("show").summary.category,
        Category::Done
    );
}

// frob:ticket 01M5DRXH9KKWX3W0A99VESJVC8
// frob:tests crates/frob-land/src/divergence.rs::diverged_lands
// frob:tests crates/frob-land/src/divergence.rs::summary
#[test]
fn diverged_lands_counts_local_lands_origin_lacks_and_clears_after_relaunch_is_pushed() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let s = landed_locally_with_a_diverged_origin(&fx);
    let ledger = fx.ledger();
    let mut d = frob_land::divergence::diverged_lands(&ledger, "refs/remotes/origin/main")
        .expect("diverged");
    assert_eq!(d.lands.len(), 1, "{d:?}");
    assert_eq!(d.lands[0].id, s.id);
    d.conflicts = 2;
    assert_eq!(
        frob_land::divergence::summary(&d, "origin").as_deref(),
        Some("1 local lands not on origin; 0 claims evicted; 2 conflicts")
    );
    git(
        &fx.root,
        &["update-ref", "refs/remotes/origin/main", "refs/heads/main"],
    );
    let after =
        frob_land::divergence::diverged_lands(&ledger, "refs/remotes/origin/main").expect("after");
    assert!(after.lands.is_empty());
    assert_eq!(frob_land::divergence::summary(&after, "origin"), None);
    let gone =
        frob_land::divergence::diverged_lands(&ledger, "refs/remotes/nope/main").expect("gone");
    assert!(gone.lands.is_empty());
}

// frob:ticket 01M4H1QJWECA2N5P2F28RET6B0
// frob:tests crates/frob-land/src/verb.rs::land_batch
#[test]
fn a_batch_lands_in_order_reports_every_outcome_and_continues_past_a_refusal() {
    if !git_available() {
        return;
    }
    let fx = Fixture::new();
    let a = fx.start("Add a", &["src/a.rs"]);
    Fixture::commit_in(&a.wt, "src/a.rs", "fn a() {}\n");
    Fixture::evidence(&a, "src/a.rs");
    let b = fx.start("Add b", &["src/b.rs"]);
    Fixture::commit_in(&b.wt, "src/b.rs", "fn b() {}\n");
    Fixture::evidence(&b, "src/b.rs");
    let x = fx.start_with("Add x", &["src/x.rs"], &["x answers"]);
    Fixture::commit_in(&x.wt, "src/x.rs", "fn x() {}\n");
    Fixture::evidence(&x, "src/x.rs");
    let c = fx.start("Add c", &["src/c.rs"]);
    Fixture::commit_in(&c.wt, "src/c.rs", "fn c() {}\n");
    Fixture::evidence(&c, "src/c.rs");

    let handles: Vec<String> = [&a, &b, &x, &c].iter().map(|s| s.handle.clone()).collect();
    let clock = Arc::new(gob_time::SystemClock) as Arc<dyn gob_time::Clock>;
    let err = frob_land::verb::land_batch(&fx.root, &handles, &LandOptions::default(), &clock)
        .expect_err("one ticket is refused, so the batch gate fails");
    let CliError::Gate { data, .. } = err else {
        panic!("expected a gate failure carrying the report");
    };
    assert_eq!(data["landed"], 3);
    assert_eq!(data["refused"], 1);
    let statuses: Vec<&str> = data["tickets"]
        .as_array()
        .expect("tickets")
        .iter()
        .map(|t| t["status"].as_str().expect("status"))
        .collect();
    assert_eq!(statuses, ["landed", "landed", "refused", "landed"]);
    assert_eq!(data["tickets"][2]["code"], "E-DONE-CRITERIA-UNBOUND");
    for (rel, text) in [
        ("src/a.rs", "fn a() {}\n"),
        ("src/b.rs", "fn b() {}\n"),
        ("src/c.rs", "fn c() {}\n"),
    ] {
        let blob = fx.repo().read_blob_at("main", rel).expect("read");
        assert_eq!(blob.as_deref(), Some(text.as_bytes()), "{rel} landed");
    }
    assert_eq!(
        fx.repo().read_blob_at("main", "src/x.rs").expect("read"),
        None
    );
    assert_eq!(
        fx.ledger().show(x.id).expect("show").summary.category,
        Category::InProgress
    );
}
