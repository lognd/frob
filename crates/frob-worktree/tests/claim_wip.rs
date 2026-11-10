//! `frob refresh` pushes claimed ticket branches as WIP, fast-forward only (system git required).
// frob:ticket 01M7179W20SP4SF3GP0G32HAM7

use std::path::{Path, PathBuf};
use std::time::Duration;

use frob_lease::{LeaseConfig, LeaseStore};
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig};
use frob_worktree::claim_wip::{WipOutcome, push_wip};
use frob_worktree::{WorkOptions, Workspace, WorktreeConfig};
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
    tmp: tempfile::TempDir,
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
        Some(Self { tmp, root })
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

/// Claim a fresh ticket and publish its branch so the remote-tracking ref exists; returns the branch name.
fn claimed_and_published(fx: &Fixture, ledger: &Ledger, leases: &LeaseStore) -> String {
    let (_, handle) = new_ticket(ledger);
    let cfg = WorktreeConfig::load(&fx.root).expect("config");
    let ws = Workspace {
        ledger,
        leases,
        config: &cfg,
    };
    ws.work(&format!("~{handle}"), &WorkOptions::default())
        .expect("claim");
    let branch = format!("ticket/{handle}");
    assert!(git(&fx.root, &["push", "--quiet", "origin", &branch]));
    branch
}

/// Add one commit to the local `branch` without touching any work tree.
fn commit_on(fx: &Fixture, branch: &str, file: &str) {
    let repo = Repo::discover(&fx.root).expect("repo");
    repo.commit_paths(
        &format!("refs/heads/{branch}"),
        &[(RelPath::new(file).expect("path"), Some(b"wip\n".to_vec()))],
        "wip",
        &CommitOptions::default(),
    )
    .expect("wip commit");
}

fn outcomes(fx: &Fixture) -> Vec<(String, WipOutcome)> {
    push_wip(&fx.ledger(), &fx.leases()).expect("push_wip")
}

fn tip(dir: &Path, rev: &str) -> String {
    let out = std::process::Command::new("git")
        .args(["rev-parse", rev])
        .current_dir(dir)
        .output()
        .expect("rev-parse");
    String::from_utf8(out.stdout)
        .expect("utf8")
        .trim()
        .to_owned()
}

// frob:tests crates/frob-worktree/src/claim_wip.rs::push_wip
#[test]
fn an_ahead_claim_branch_is_pushed() {
    let Some(fx) = Fixture::new(None) else { return };
    let (ledger, leases) = (fx.ledger(), fx.leases());
    let branch = claimed_and_published(&fx, &ledger, &leases);
    commit_on(&fx, &branch, "wip.txt");
    let got = outcomes(&fx);
    assert_eq!(got, vec![(branch.clone(), WipOutcome::Pushed)]);
    let bare = fx.tmp.path().join("origin.git");
    assert_eq!(
        tip(&bare, &format!("refs/heads/{branch}")),
        tip(&fx.root, &format!("refs/heads/{branch}"))
    );
}

// frob:tests crates/frob-worktree/src/claim_wip.rs::push_wip
#[test]
fn an_equal_claim_branch_is_up_to_date() {
    let Some(fx) = Fixture::new(None) else { return };
    let (ledger, leases) = (fx.ledger(), fx.leases());
    let branch = claimed_and_published(&fx, &ledger, &leases);
    assert_eq!(outcomes(&fx), vec![(branch, WipOutcome::UpToDate)]);
}

// frob:tests crates/frob-worktree/src/claim_wip.rs::push_wip
#[test]
fn a_claim_branch_with_no_cached_remote_copy_is_left_to_republish() {
    let Some(fx) = Fixture::new(None) else { return };
    let (ledger, leases) = (fx.ledger(), fx.leases());
    let branch = claimed_and_published(&fx, &ledger, &leases);
    assert!(git(
        &fx.root,
        &["update-ref", "-d", &format!("refs/remotes/origin/{branch}")]
    ));
    assert_eq!(outcomes(&fx), vec![(branch, WipOutcome::NotPublished)]);
}

// frob:tests crates/frob-worktree/src/claim_wip.rs::push_wip
#[test]
fn a_diverged_claim_branch_is_never_pushed() {
    let Some(fx) = Fixture::new(None) else { return };
    let (ledger, leases) = (fx.ledger(), fx.leases());
    let branch = claimed_and_published(&fx, &ledger, &leases);
    let bare = fx.tmp.path().join("origin.git");
    let before = tip(&bare, &format!("refs/heads/{branch}"));
    // The remote-tracking ref says the remote has a commit this clone lacks.
    commit_on(&fx, &branch, "mine.txt");
    let ours = tip(&fx.root, &format!("refs/heads/{branch}"));
    assert!(git(
        &fx.root,
        &[
            "update-ref",
            &format!("refs/remotes/origin/{branch}"),
            &before
        ]
    ));
    assert!(git(&fx.root, &["branch", "-f", "side", &before]));
    commit_on(&fx, "side", "theirs.txt");
    let theirs = tip(&fx.root, "refs/heads/side");
    assert!(git(
        &fx.root,
        &[
            "update-ref",
            &format!("refs/remotes/origin/{branch}"),
            &theirs
        ]
    ));
    assert_ne!(ours, theirs);
    assert_eq!(outcomes(&fx), vec![(branch.clone(), WipOutcome::Diverged)]);
    assert_eq!(tip(&bare, &format!("refs/heads/{branch}")), before);
}
