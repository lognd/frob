//! The garbage-collection pass on fixture directories with fake artifacts and controlled mtimes.
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime};

use frob_worktree::gc::adapter::{BuildPolicy, Unit, UnitKind, plan};
use frob_worktree::gc::cargo::CargoAdapter;
use frob_worktree::gc::jail::{Jail, JailError};
use frob_worktree::gc::pass::{
    Env, Mode, TicketOracle, TicketState, default_adapters, report_only, run,
};
use frob_worktree::gc::{GcConfig, artifacts, caches, stamp};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use gob_git::{CommitOptions, RelPath, Repo};

const MAIN: &str = "refs/heads/main";
const HOUR: u64 = 3600;

/// The mode that deletes on this host: the automatic pass, except on Windows where it only reports (~EDPHHFS).
fn sweep_mode() -> Mode {
    if cfg!(windows) {
        Mode::Forced
    } else {
        Mode::Auto
    }
}

fn git(dir: &Path, args: &[&str]) -> String {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|a| (*a).to_owned()).collect(),
        cwd: Some(dir.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(30),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 }).run(&spec).expect("git");
    assert_eq!(
        out.status,
        Outcome::Exited(0),
        "git {args:?}: {}",
        out.stderr
    );
    out.stdout
}

/// A repository `<tmp>/repo` on `main` with one commit, its worktree parent `<tmp>/repo-wt`, and a fake ledger.
struct Fixture {
    _tmp: tempfile::TempDir,
    root: PathBuf,
    parent: PathBuf,
}

impl Fixture {
    fn new() -> Self {
        let tmp = tempfile::tempdir().expect("tempdir");
        let root = gob_exec::canonical(tmp.path()).expect("canon").join("repo");
        std::fs::create_dir(&root).expect("mkdir");
        let repo = Repo::init(&root).expect("init");
        std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").expect("head");
        let cfg = std::fs::read_to_string(repo.git_dir().join("config")).expect("config");
        std::fs::write(
            repo.git_dir().join("config"),
            format!(
                "{cfg}[user]\n\tname = T\n\temail = t@example.com\n[core]\n\tautocrlf = false\n"
            ),
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
        let parent = root.parent().expect("parent").join("repo-wt");
        Self {
            root,
            parent,
            _tmp: tmp,
        }
    }

    fn repo(&self) -> Repo {
        Repo::discover(&self.root).expect("repo")
    }

    /// Add a worktree for ticket `name` on branch `ticket/<name>` under the parent.
    fn worktree(&self, name: &str) -> PathBuf {
        let path = self.parent.join(name);
        std::fs::create_dir_all(&self.parent).expect("mkdir");
        self.repo()
            .worktree_add(&path, &format!("ticket/{name}"), "main")
            .expect("worktree add");
        path
    }
}

/// Ticket states by handle; digests referenced by open tickets.
#[derive(Default)]
struct Oracle {
    states: BTreeMap<String, TicketState>,
    digests: Option<BTreeSet<String>>,
}

impl TicketOracle for Oracle {
    fn state(&self, handle: &str) -> TicketState {
        self.states
            .get(handle)
            .copied()
            .unwrap_or(TicketState::Unknown)
    }
    fn referenced_digests(&self) -> Option<BTreeSet<String>> {
        self.digests.clone()
    }
}

fn config() -> GcConfig {
    GcConfig::default()
}

fn age(path: &Path, secs: u64) {
    let when = wall_now() - Duration::from_secs(secs);
    // A directory cannot be opened for writing; a read handle sets its time on unix.
    let file = std::fs::OpenOptions::new()
        .write(true)
        .open(path)
        .or_else(|_| std::fs::File::open(path))
        .expect("open");
    file.set_modified(when).expect("set mtime");
}

fn write(path: &Path, bytes: usize, age_secs: u64) {
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, vec![b'x'; bytes]).expect("write");
    age(path, age_secs);
}

struct Ctx<'a> {
    fx: &'a Fixture,
    oracle: &'a Oracle,
    live: Vec<PathBuf>,
    cfg: GcConfig,
    free: u64,
}

impl Ctx<'_> {
    fn run(&self, mode: Mode) -> frob_worktree::gc::Report {
        let repo = self.fx.repo();
        let adapters = default_adapters();
        let free = self.free;
        let free_fn = move |_: &Path| Some(free);
        let env = Env {
            repo: &repo,
            primary: &self.fx.root,
            worktree_parent: &self.fx.parent,
            base: "main",
            config: &self.cfg,
            tickets: self.oracle,
            live_worktrees: &self.live,
            now: wall_now(),
            free_bytes: &free_fn,
            adapters: &adapters,
        };
        run(&env, mode)
    }
}

fn ctx<'a>(fx: &'a Fixture, oracle: &'a Oracle) -> Ctx<'a> {
    Ctx {
        fx,
        oracle,
        live: Vec::new(),
        cfg: config(),
        free: u64::MAX,
    }
}

fn names(dir: &Path) -> BTreeSet<String> {
    std::fs::read_dir(dir)
        .map(|rd| {
            rd.filter_map(Result::ok)
                .map(|e| e.file_name().to_string_lossy().into_owned())
                .collect()
        })
        .unwrap_or_default()
}

fn unit(label: &str, kind: UnitKind, bytes: u64, age_secs: u64, now: SystemTime) -> Unit {
    Unit {
        paths: vec![PathBuf::from(label)],
        kind,
        bytes,
        modified: now - Duration::from_secs(age_secs),
        label: label.to_owned(),
    }
}

fn policy(budget: u64) -> BuildPolicy {
    BuildPolicy {
        incremental_max_age: Duration::from_secs(6 * HOUR),
        keep_recent: Duration::from_secs(HOUR),
        budget_bytes: budget,
        keep_binaries: vec!["frob".to_owned(), "grimble".to_owned()],
    }
}

// frob:tests crates/frob-worktree/src/gc/adapter.rs::plan
#[test]
fn plan_evicts_oldest_artifacts_until_under_budget_and_keeps_the_latest_build() {
    let now = wall_now();
    let units = vec![
        unit("old-a", UnitKind::Artifact, 100, 30 * HOUR, now),
        unit("old-b", UnitKind::Artifact, 100, 20 * HOUR, now),
        unit("old-c", UnitKind::Artifact, 100, 10 * HOUR, now),
        unit("new-a", UnitKind::Artifact, 100, 0, now),
        unit("new-b", UnitKind::Artifact, 100, HOUR / 2, now),
    ];
    let p = plan(units, 500, now, &policy(250));
    let evicted: Vec<_> = p.evict.iter().map(|u| u.label.as_str()).collect();
    assert_eq!(
        evicted,
        ["old-a", "old-b", "old-c"],
        "oldest first, stops at the recent ones"
    );
    assert_eq!(p.remaining_bytes, 200);
    assert!(!p.over_budget_kept_recent);
}

// frob:tests crates/frob-worktree/src/gc/adapter.rs::plan
#[test]
fn plan_never_evicts_the_latest_build_even_over_budget() {
    let now = wall_now();
    let units = vec![
        unit("old", UnitKind::Artifact, 100, 30 * HOUR, now),
        unit("new-a", UnitKind::Artifact, 400, 0, now),
        unit("new-b", UnitKind::Artifact, 400, HOUR / 2, now),
    ];
    let p = plan(units, 900, now, &policy(10));
    let evicted: Vec<_> = p.evict.iter().map(|u| u.label.as_str()).collect();
    assert_eq!(evicted, ["old"]);
    assert!(p.over_budget_kept_recent);
}

// frob:tests crates/frob-worktree/src/gc/adapter.rs::plan
#[test]
fn plan_removes_stale_incremental_regardless_of_budget_and_keeps_fresh_incremental() {
    let now = wall_now();
    let units = vec![
        unit("inc-stale", UnitKind::Incremental, 50, 7 * HOUR, now),
        unit("inc-fresh", UnitKind::Incremental, 50, HOUR, now),
        unit("art", UnitKind::Artifact, 10, 0, now),
    ];
    let p = plan(units, 110, now, &policy(u64::MAX));
    let evicted: Vec<_> = p.evict.iter().map(|u| u.label.as_str()).collect();
    assert_eq!(evicted, ["inc-stale"]);
}

// frob:tests crates/frob-worktree/src/gc/pass.rs::run
#[test]
fn target_over_budget_evicts_old_artifacts_and_keeps_latest_build_and_binaries() {
    let fx = Fixture::new();
    let debug = fx.root.join("target").join("debug");
    write(&debug.join("deps").join("libold-aaa.rlib"), 4000, 30 * HOUR);
    write(
        &debug.join("deps").join("libold-aaa.rmeta"),
        1000,
        30 * HOUR,
    );
    write(&debug.join("deps").join("libmid-bbb.rlib"), 4000, 10 * HOUR);
    write(&debug.join("deps").join("libnew-ccc.rlib"), 4000, 60);
    write(&debug.join("deps").join("frob-ddd"), 4000, 40 * HOUR);
    write(&debug.join("deps").join("grimble-eee.exe"), 4000, 40 * HOUR);
    write(&debug.join("frob"), 4000, 40 * HOUR);
    let oracle = Oracle::default();
    let mut c = ctx(&fx, &oracle);
    c.cfg.target_budget_gb = 0;
    let report = c.run(sweep_mode());
    assert!(report.ran, "{report:?}");
    let left = names(&debug.join("deps"));
    assert!(
        !left.contains("libold-aaa.rlib") && !left.contains("libold-aaa.rmeta"),
        "{left:?}"
    );
    assert!(!left.contains("libmid-bbb.rlib"), "{left:?}");
    assert!(
        left.contains("libnew-ccc.rlib"),
        "latest build kept: {left:?}"
    );
    assert!(
        left.contains("frob-ddd") && left.contains("grimble-eee.exe"),
        "binaries kept: {left:?}"
    );
    assert!(debug.join("frob").is_file());
    assert_eq!(report.reclaimed_bytes, 9000);
}

// frob:tests crates/frob-worktree/src/gc/cargo.rs::CargoAdapter
#[cfg(unix)]
#[test]
fn stale_incremental_directories_are_removed_and_fresh_ones_kept() {
    let fx = Fixture::new();
    let inc = fx.root.join("target").join("debug").join("incremental");
    write(&inc.join("stale-1").join("s.bin"), 2000, 8 * HOUR);
    write(&inc.join("fresh-1").join("f.bin"), 2000, 60);
    age(&inc.join("stale-1"), 8 * HOUR);
    let oracle = Oracle::default();
    let report = ctx(&fx, &oracle).run(sweep_mode());
    assert_eq!(
        names(&inc),
        BTreeSet::from(["fresh-1".to_owned()]),
        "{report:?}"
    );
}

// frob:tests crates/frob-worktree/src/gc/cargo.rs::CargoAdapter
#[test]
fn cargo_adapter_groups_a_compilation_unit_and_skips_kept_binaries() {
    use frob_worktree::gc::adapter::BuildAdapter;
    let fx = Fixture::new();
    let debug = fx.root.join("target").join("debug");
    write(&debug.join("deps").join("libfoo-1.rlib"), 10, 0);
    write(&debug.join("deps").join("libfoo-1.rmeta"), 10, 0);
    write(&debug.join("deps").join("foo-1.d"), 10, 0);
    write(&debug.join("deps").join("frob-2"), 10, 0);
    write(&debug.join("deps").join("frob-2.d"), 10, 0);
    write(&debug.join("build").join("frob-3").join("out"), 10, 0);
    write(&debug.join("build").join("dep-4").join("out"), 10, 0);
    let units = CargoAdapter.units(&fx.root.join("target"), &policy(0));
    let labels: BTreeSet<_> = units.iter().map(|u| u.label.clone()).collect();
    assert_eq!(
        labels,
        BTreeSet::from(["deps/foo-1".to_owned(), "build/dep-4".to_owned()])
    );
    let foo = units.iter().find(|u| u.label == "deps/foo-1").expect("foo");
    assert_eq!(foo.paths.len(), 3);
}

// frob:tests crates/frob-worktree/src/gc/worktrees.rs::assess
#[test]
fn closed_ticket_worktree_with_uncommitted_changes_is_kept_and_reported() {
    let fx = Fixture::new();
    let wt = fx.worktree("DIRTY01");
    std::fs::write(wt.join("scratch.txt"), "unsaved").expect("write");
    let mut oracle = Oracle::default();
    oracle
        .states
        .insert("~DIRTY01".to_owned(), TicketState::Closed);
    let report = ctx(&fx, &oracle).run(Mode::Auto);
    assert!(wt.join("scratch.txt").is_file(), "kept with its change");
    assert!(
        report
            .kept
            .iter()
            .any(|k| k.target.contains("DIRTY01") && k.reason.contains("uncommitted")),
        "{report:?}"
    );
    assert!(report.actions.iter().all(|a| a.category != "worktrees"));
}

// frob:tests crates/frob-worktree/src/gc/worktrees.rs::remove
#[test]
fn clean_closed_ticket_worktree_is_removed_and_a_merged_branch_deleted() {
    let fx = Fixture::new();
    let wt = fx.worktree("DONE001");
    let mut oracle = Oracle::default();
    oracle
        .states
        .insert("~DONE001".to_owned(), TicketState::Closed);
    let report = ctx(&fx, &oracle).run(sweep_mode());
    assert!(!wt.exists(), "{report:?}");
    assert!(report.actions.iter().any(|a| a.category == "worktrees"));
    let branches = git(&fx.root, &["branch", "--list", "ticket/DONE001"]);
    assert!(
        branches.trim().is_empty(),
        "merged branch deleted: {branches}"
    );
}

// frob:tests crates/frob-worktree/src/gc/worktrees.rs::assess
#[test]
fn open_ticket_with_unpushed_commits_is_never_removed() {
    let fx = Fixture::new();
    let wt = fx.worktree("OPEN001");
    std::fs::write(wt.join("work.txt"), "committed work").expect("write");
    git(&wt, &["add", "work.txt"]);
    git(
        &wt,
        &[
            "-c",
            "user.name=T",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-q",
            "-m",
            "wip",
        ],
    );
    let mut oracle = Oracle::default();
    oracle
        .states
        .insert("~OPEN001".to_owned(), TicketState::Open);
    let report = ctx(&fx, &oracle).run(Mode::Auto);
    assert!(wt.join("work.txt").is_file(), "{report:?}");
    assert!(report.kept.iter().any(|k| k.reason.contains("unpushed")));
    // The same worktree of a CLOSED ticket holds only saved commits, so removal loses nothing (the branch stays).
    let mut closed = Oracle::default();
    closed
        .states
        .insert("~OPEN001".to_owned(), TicketState::Closed);
    let mut c = ctx(&fx, &closed);
    c.cfg.interval_secs = 0;
    c.run(Mode::Forced);
    assert!(!wt.exists());
    let branches = git(&fx.root, &["branch", "--list", "ticket/OPEN001"]);
    assert!(!branches.trim().is_empty(), "unmerged branch kept");
}

// frob:tests crates/frob-worktree/src/gc/worktrees.rs::assess
#[test]
fn open_ticket_with_nothing_unsaved_is_removed_only_when_its_lease_is_not_live() {
    let fx = Fixture::new();
    let wt = fx.worktree("OPEN002");
    let mut oracle = Oracle::default();
    oracle
        .states
        .insert("~OPEN002".to_owned(), TicketState::Open);
    let mut c = ctx(&fx, &oracle);
    c.live = vec![wt.clone()];
    c.run(Mode::Forced);
    assert!(wt.exists(), "a live lease keeps it");
    c.live = Vec::new();
    c.run(Mode::Forced);
    assert!(
        !wt.exists(),
        "an expired lease with nothing unsaved lets it go"
    );
    let branches = git(&fx.root, &["branch", "--list", "ticket/OPEN002"]);
    assert!(
        !branches.trim().is_empty(),
        "the open ticket keeps its branch"
    );
}

// frob:tests crates/frob-worktree/src/gc/worktrees.rs::assess
#[test]
fn worktrees_outside_the_frob_parent_or_unknown_to_the_ledger_are_kept() {
    let fx = Fixture::new();
    let elsewhere = fx.root.parent().expect("p").join("other-wt").join("X");
    std::fs::create_dir_all(elsewhere.parent().expect("p")).expect("mkdir");
    fx.repo()
        .worktree_add(&elsewhere, "ticket/X", "main")
        .expect("add");
    let unknown = fx.worktree("GHOST01");
    let mut oracle = Oracle::default();
    oracle.states.insert("~X".to_owned(), TicketState::Closed);
    let report = ctx(&fx, &oracle).run(Mode::Auto);
    assert!(elsewhere.exists(), "outside the parent: {report:?}");
    assert!(unknown.exists(), "ticket unknown to the ledger: {report:?}");
}

// frob:tests crates/frob-worktree/src/gc/pass.rs::run
#[test]
fn throttle_is_honored_and_the_guard_forces_a_pass() {
    let fx = Fixture::new();
    let oracle = Oracle::default();
    let mut c = ctx(&fx, &oracle);
    let first = c.run(Mode::Auto);
    assert!(first.ran);
    let second = c.run(Mode::Auto);
    assert!(!second.ran, "inside the interval no pass runs");
    assert!(
        second
            .skipped
            .as_deref()
            .is_some_and(|s| s.contains("interval"))
    );
    c.free = 1 << 20;
    let guarded = c.run(Mode::Auto);
    assert!(guarded.ran && guarded.forced_by_guard, "{guarded:?}");
    c.free = u64::MAX;
    assert!(c.run(Mode::Forced).ran, "doctor --fix is unthrottled");
    let st = stamp::load(fx.repo().common_dir());
    assert_eq!(st.passes, 3);
}

// frob:tests crates/frob-worktree/src/gc/pass.rs::run
#[test]
fn disabled_gc_skips_auto_and_a_dry_run_changes_nothing() {
    let fx = Fixture::new();
    let debug = fx.root.join("target").join("debug");
    write(&debug.join("deps").join("libold-aaa.rlib"), 4000, 30 * HOUR);
    write(&debug.join("deps").join("libnew-bbb.rlib"), 10, 0);
    let oracle = Oracle::default();
    let mut c = ctx(&fx, &oracle);
    c.cfg.target_budget_gb = 0;
    c.cfg.enabled = false;
    assert!(!c.run(Mode::Auto).ran);
    let dry = c.run(Mode::DryRun);
    assert!(dry.ran && dry.dry_run);
    assert_eq!(dry.reclaimed_bytes, 4000, "would reclaim the old artifact");
    assert!(
        debug.join("deps").join("libold-aaa.rlib").is_file(),
        "dry run removes nothing"
    );
    assert_eq!(
        stamp::load(fx.repo().common_dir()).passes,
        0,
        "dry run leaves the stamp"
    );
    assert!(dry.usage.iter().any(|u| u.category == "build"));
}

// frob:tests crates/frob-worktree/src/gc/jail.rs::Jail
#[test]
fn jail_admits_by_components_not_string_prefix_and_refuses_roots_and_dotdot() {
    let tmp = tempfile::tempdir().expect("tempdir");
    let base = gob_exec::canonical(tmp.path()).expect("canon");
    let target = base.join("target");
    let sibling = base.join("target-old");
    std::fs::create_dir_all(target.join("debug")).expect("mkdir");
    std::fs::create_dir_all(&sibling).expect("mkdir");
    let jail = Jail::new([target.clone()]);
    assert!(jail.admit(&target.join("debug")).is_ok());
    assert!(
        matches!(jail.admit(&sibling), Err(JailError::Outside(_))),
        "name prefix is not containment"
    );
    assert!(
        matches!(jail.admit(&target), Err(JailError::Outside(_))),
        "the root itself"
    );
    // Built as text so the dots survive: on a Windows verbatim base `Path::join("..")` pops
    // a component lexically (std documents this), which silently removed the dotdot from the
    // old fixture. Both separators are tried; none may be admitted on any platform.
    for sep in ["/", "\\"] {
        let mut text = target.clone().into_os_string();
        text.push(format!("{sep}debug{sep}..{sep}..{sep}target-old"));
        assert!(
            matches!(jail.admit(Path::new(&text)), Err(JailError::NotAbsolute(_))),
            "dotdot with {sep:?}"
        );
        let mut dot = target.clone().into_os_string();
        dot.push(format!("{sep}debug{sep}.{sep}deps"));
        assert!(
            matches!(jail.admit(Path::new(&dot)), Err(JailError::NotAbsolute(_))),
            "dot with {sep:?}"
        );
    }
    assert!(matches!(
        jail.admit(Path::new("target/debug")),
        Err(JailError::NotAbsolute(_))
    ));
}

// frob:tests crates/frob-worktree/src/gc/jail.rs::Jail
/// What `admit` returned for the Windows CI input, modelled on Linux with the pure style functions.
///
/// The failing input was `target.join("debug").join("..").join("..").join("target-old")` on a
/// verbatim base. `PathBuf::push` on a verbatim path resolves `..` lexically, so the jail was
/// given `\\?\C:\w\target-old`, an existing sibling: it returned `Outside` (refused, not
/// `NotAbsolute`, and never `Ok`). The same path with a literal `..` is refused up front.
#[test]
fn windows_verbatim_dotdot_was_outside_not_admitted_and_literal_dotdot_is_refused() {
    use gob_exec::{Style, has_dot_component, strictly_inside};
    let root = r"\\?\C:\w\target";
    let as_joined_on_windows = r"\\?\C:\w\target-old";
    assert!(!has_dot_component(as_joined_on_windows));
    assert!(
        !strictly_inside(Style::Windows, root, as_joined_on_windows),
        "Outside"
    );
    let literal = r"\\?\C:\w\target\debug\..\..\target-old";
    assert!(has_dot_component(literal), "NotAbsolute");
    assert!(!strictly_inside(Style::Windows, root, literal));
    let slashes = r"\\?\C:\w\target\debug/../../target-old";
    assert!(has_dot_component(slashes), "NotAbsolute");
    assert!(!strictly_inside(Style::Windows, root, slashes));
}

// frob:tests crates/frob-worktree/src/gc/pass.rs::report_only
#[test]
fn the_automatic_pass_only_reports_on_windows_and_nothing_else_does() {
    assert!(report_only(Mode::Auto, true));
    assert!(!report_only(Mode::Auto, false));
    for mode in [Mode::Forced, Mode::DryRun] {
        assert!(!report_only(mode, true), "{mode:?} is explicit");
    }
}

// frob:tests crates/frob-worktree/src/gc/pass.rs::run
#[cfg(windows)]
#[test]
fn the_automatic_pass_deletes_nothing_on_windows() {
    let fx = Fixture::new();
    let debug = fx.root.join("target").join("debug");
    let old = debug.join("deps").join("libold-aaa.rlib");
    write(&old, 4000, 40 * HOUR);
    let oracle = Oracle::default();
    let mut c = ctx(&fx, &oracle);
    c.cfg.target_budget_gb = 0;
    let report = c.run(Mode::Auto);
    assert!(report.dry_run, "reports only");
    assert!(old.is_file(), "nothing is deleted");
}

// frob:tests crates/frob-worktree/src/gc/jail.rs::Jail
#[cfg(unix)]
#[test]
fn jail_refuses_symlinks_out_of_the_tree_and_never_deletes_their_target() {
    let tmp = tempfile::tempdir().expect("tempdir");
    let base = gob_exec::canonical(tmp.path()).expect("canon");
    let target = base.join("target");
    let outside = base.join("precious");
    std::fs::create_dir_all(&target).expect("mkdir");
    std::fs::create_dir_all(&outside).expect("mkdir");
    std::fs::write(outside.join("keep.txt"), "keep").expect("write");
    std::os::unix::fs::symlink(&outside, target.join("escape")).expect("symlink");
    let jail = Jail::new([target.clone()]);
    assert!(matches!(
        jail.admit(&target.join("escape")),
        Err(JailError::Symlink(_))
    ));
    assert!(jail.remove(&target.join("escape")).is_err());
    assert!(matches!(
        jail.admit(&target.join("escape").join("keep.txt")),
        Err(JailError::Outside(_))
    ));
    // A symlink inside a removed tree is unlinked, not followed.
    let tree = target.join("tree");
    std::fs::create_dir_all(&tree).expect("mkdir");
    std::os::unix::fs::symlink(&outside, tree.join("link")).expect("symlink");
    jail.remove(&tree).expect("remove tree");
    assert!(
        outside.join("keep.txt").is_file(),
        "the link target survives"
    );
}

// frob:tests crates/frob-worktree/src/gc/jail.rs::Jail
#[cfg(unix)]
#[test]
fn a_symlinked_target_dir_is_not_collected() {
    let fx = Fixture::new();
    let real = fx.root.parent().expect("p").join("elsewhere");
    write(
        &real.join("debug").join("deps").join("libold-a.rlib"),
        100,
        40 * HOUR,
    );
    std::os::unix::fs::symlink(&real, fx.root.join("target")).expect("symlink");
    let oracle = Oracle::default();
    let mut c = ctx(&fx, &oracle);
    c.cfg.target_budget_gb = 0;
    c.run(Mode::Auto);
    assert!(
        real.join("debug")
            .join("deps")
            .join("libold-a.rlib")
            .is_file()
    );
}

// frob:tests crates/frob-worktree/src/gc/caches.rs::plan
#[test]
fn cache_budget_evicts_least_recent_and_only_allowlisted_files() {
    let fx = Fixture::new();
    let frob = fx.root.join(".frob");
    write(&frob.join("cache.sqlite"), 3000, 5 * HOUR);
    write(&frob.join("land-base").join("aaa.json"), 1000, 20 * HOUR);
    write(&frob.join("land-base").join("bbb.json"), 1000, 2 * HOUR);
    write(&frob.join("land-base").join("ccc.json"), 1000, 60);
    write(&frob.join("tickets.sqlite"), 9000, 99 * HOUR);
    write(&frob.join("land.lock"), 10, 99 * HOUR);
    let entries = caches::entries(&fx.root);
    assert_eq!(entries.len(), 4, "tickets index and locks are not caches");
    let evict = caches::plan(entries, 2500, wall_now());
    assert_eq!(evict.len(), 2, "oldest two evicted until under budget");
    assert!(evict.iter().any(|e| e.paths[0].ends_with("aaa.json")));
    assert!(evict.iter().any(|e| e.paths[0].ends_with("cache.sqlite")));
}

// frob:tests crates/frob-worktree/src/gc/caches.rs::shared_entries
#[test]
fn shared_cache_and_base_sets_under_the_common_dir_are_evictable_and_nothing_else() {
    let fx = Fixture::new();
    let common = fx.repo().common_dir().to_path_buf();
    let frob = common.join("frob");
    write(
        &frob.join("cache").join("frob").join("cache.sqlite"),
        3000,
        5 * HOUR,
    );
    write(
        &frob.join("cache").join("frob").join("cache.sqlite-wal"),
        100,
        5 * HOUR,
    );
    write(
        &frob.join("cache").join("frob").join("other.dat"),
        500,
        99 * HOUR,
    );
    write(&frob.join("land-base").join("aaa.json"), 1000, 20 * HOUR);
    write(&frob.join("land.lock"), 10, 99 * HOUR);
    let entries = caches::shared_entries(&common);
    assert_eq!(entries.len(), 2, "database with companions, one base set");
    let evict = caches::plan(entries, 1500, wall_now());
    assert_eq!(evict.len(), 2, "both are over the budget and old enough");
    assert!(
        evict.iter().any(|e| e.paths.len() == 2),
        "the database goes with its wal"
    );
    let jail = Jail::new([frob.clone()]);
    for p in evict.iter().flat_map(|e| &e.paths) {
        assert!(jail.admit(p).is_ok(), "{}", p.display());
    }
}

// frob:tests crates/frob-worktree/src/gc/artifacts.rs::plan
#[test]
fn only_old_unreferenced_digest_named_blobs_are_collected() {
    let fx = Fixture::new();
    let common = fx.repo().common_dir().to_path_buf();
    let dir = artifacts::dir(&common);
    let (old, kept, young) = ("a".repeat(64), "b".repeat(64), "c".repeat(64));
    write(&dir.join(&old), 100, 40 * 24 * HOUR);
    write(&dir.join(&kept), 100, 40 * 24 * HOUR);
    write(&dir.join(&young), 100, HOUR);
    write(&dir.join("notes.txt"), 100, 40 * 24 * HOUR);
    let refs = BTreeSet::from([kept.clone()]);
    let blobs = artifacts::plan(
        &common,
        &refs,
        Duration::from_secs(30 * 24 * HOUR),
        wall_now(),
    );
    assert_eq!(blobs.len(), 1);
    assert!(blobs[0].path.ends_with(&old));
    let mut found = BTreeSet::new();
    artifacts::digests_in(
        &format!("uri dir:.git/frob/artifacts/{kept} end"),
        &mut found,
    );
    assert!(found.contains(&kept));
}

// frob:tests crates/frob-worktree/src/gc/pass.rs::run
#[test]
fn unreadable_open_ticket_evidence_removes_no_blob_and_warns() {
    let fx = Fixture::new();
    let common = fx.repo().common_dir().to_path_buf();
    let blob = artifacts::dir(&common).join("d".repeat(64));
    write(&blob, 100, 40 * 24 * HOUR);
    let oracle = Oracle::default();
    let report = ctx(&fx, &oracle).run(Mode::Auto);
    assert!(blob.is_file());
    assert!(
        report.warnings.iter().any(|w| w.contains("evidence")),
        "{report:?}"
    );
}

// frob:tests crates/frob-worktree/src/gc/pass.rs::run
#[cfg(unix)]
#[test]
fn abandoned_land_base_checkouts_are_swept_and_recent_ones_left() {
    let fx = Fixture::new();
    let common = fx.repo().common_dir().to_path_buf();
    let stale = common.join("frob").join("land-base-abc-1");
    let recent = common.join("frob").join("land-base-abc-2");
    write(&stale.join("f.txt"), 100, 5 * HOUR);
    age(&stale, 5 * HOUR);
    write(&recent.join("f.txt"), 100, 10);
    let oracle = Oracle {
        digests: Some(BTreeSet::new()),
        ..Oracle::default()
    };
    ctx(&fx, &oracle).run(sweep_mode());
    assert!(!stale.exists());
    assert!(recent.exists());
}

// frob:ticket 01M4HF7GJZZ2EX5JNABSVTM10F
// frob:tests crates/frob-worktree/src/gc/removing.rs::leftovers
// frob:tests crates/frob-worktree/src/gc/pass.rs::run
#[cfg(unix)]
#[test]
fn unregistered_removing_leftovers_are_swept_and_registered_ones_kept() {
    let fx = Fixture::new();
    let registered = fx.worktree("LIVE001.removing");
    let stale = fx.parent.join("OLD001.removing");
    write(&stale.join("target").join("big.bin"), 4096, 10);
    let oracle = Oracle::default();
    let dry = ctx(&fx, &oracle).run(Mode::DryRun);
    assert!(stale.exists(), "a dry run deletes nothing");
    assert!(dry.actions.iter().any(|a| a.category == "removing"));
    let report = ctx(&fx, &oracle).run(sweep_mode());
    assert!(!stale.exists(), "{report:?}");
    assert!(registered.exists(), "a registered worktree is never swept");
    assert!(report.actions.iter().any(|a| a.category == "removing"));
}

/// The current wall time through the one clock, as a `SystemTime` for file-time arithmetic.
fn wall_now() -> SystemTime {
    gob_time::Clock::now(&gob_time::SystemClock).to_system_time()
}
