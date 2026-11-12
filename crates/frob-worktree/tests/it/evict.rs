//! Eviction against a real bare remote: park, compare-and-swap delete, lost races and batch limits (system git required).
// frob:ticket 01M5CW051RTDRTFH0X96CVW7F9

use std::path::{Path, PathBuf};
use std::time::Duration;

use frob_worktree::claim::remote_claim;
use frob_worktree::evict::{
    BatchItem, EvictOutcome, EvictRequest, RestoreOutcome, evict, evict_batch, parked_refs,
    read_park_record, restore,
};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use gob_git::Repo;

const T: Duration = Duration::from_secs(30);

fn git(cwd: &Path, args: &[&str]) -> Option<String> {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|s| (*s).to_owned()).collect(),
        cwd: Some(cwd.to_path_buf()),
        env: Vec::new(),
        timeout: T,
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 }).run(&spec).ok()?;
    (out.status == Outcome::Exited(0)).then(|| out.stdout.trim().to_owned())
}

struct Fixture {
    _tmp: tempfile::TempDir,
    root: PathBuf,
}

impl Fixture {
    fn new() -> Option<Self> {
        let tmp = tempfile::tempdir().ok()?;
        let (root, bare) = (tmp.path().join("repo"), tmp.path().join("origin.git"));
        std::fs::create_dir(&root).ok()?;
        std::fs::create_dir(&bare).ok()?;
        git(&bare, &["init", "--bare", "--quiet"])?;
        git(&root, &["init", "--quiet", "-b", "main"])?;
        git(&root, &["config", "user.name", "Test"])?;
        git(&root, &["config", "user.email", "t@example.com"])?;
        git(
            &root,
            &[
                "remote",
                "add",
                "origin",
                &gob_path::Shown::with_home(&bare, None).to_string(),
            ],
        )?;
        git(&root, &["commit", "--quiet", "--allow-empty", "-m", "root"])?;
        Some(Self { _tmp: tmp, root })
    }

    /// Publish `ticket/<handle>` at a fresh commit and return its oid.
    fn claim(&self, handle: &str) -> Option<String> {
        git(
            &self.root,
            &["commit", "--quiet", "--allow-empty", "-m", handle],
        )?;
        let oid = git(&self.root, &["rev-parse", "HEAD"])?;
        git(
            &self.root,
            &[
                "push",
                "--quiet",
                "origin",
                &format!("HEAD:refs/heads/ticket/{handle}"),
            ],
        )?;
        Some(oid)
    }

    fn repo(&self) -> Repo {
        Repo::discover(&self.root).expect("repo")
    }

    fn tip(&self, handle: &str) -> Option<String> {
        remote_claim(&self.repo(), "origin", &format!("ticket/{handle}"), T)
            .expect("spawn")
            .expect("answer")
    }
}

fn request(handle: &str, observed: &str) -> EvictRequest {
    EvictRequest {
        handle: handle.to_owned(),
        holder: "ann".to_owned(),
        evictor: "bob".to_owned(),
        observed: observed.to_owned(),
        idle_secs: 300,
        window_secs: 200,
        reason: "gone".to_owned(),
    }
}

// frob:tests evict
// frob:tests parked_refs
// frob:tests read_park_record
#[test]
fn eviction_parks_the_work_and_deletes_the_claim() {
    let Some(fx) = Fixture::new() else { return };
    let x = fx.claim("ABC").expect("claim");
    let repo = fx.repo();
    let out = evict(&repo, &request("ABC", &x)).expect("evict");
    assert_eq!(
        out,
        EvictOutcome::Evicted {
            parked: "parked/ABC-1".to_owned()
        }
    );
    assert_eq!(fx.tip("ABC"), None);
    let parked = parked_refs(&repo, "origin", "ABC", T)
        .expect("spawn")
        .expect("answer");
    assert_eq!(parked, vec!["refs/heads/parked/ABC-1".to_owned()]);
    git(
        &fx.root,
        &[
            "fetch",
            "--quiet",
            "origin",
            "refs/heads/parked/ABC-1:refs/remotes/origin/parked/ABC-1",
        ],
    )
    .expect("fetch");
    let rec = read_park_record(&repo, "refs/remotes/origin/parked/ABC-1")
        .expect("read")
        .expect("record");
    assert_eq!(rec.observed, x);
    assert_eq!(rec.evictor, "bob");
    let parent = git(
        &fx.root,
        &["rev-parse", "refs/remotes/origin/parked/ABC-1^"],
    )
    .expect("parent");
    assert_eq!(parent, x);
}

// frob:tests evict
#[test]
fn a_holder_who_pushed_since_is_active_and_nothing_is_parked() {
    let Some(fx) = Fixture::new() else { return };
    let x = fx.claim("ABC").expect("claim");
    let _newer = fx.claim("ABC").expect("holder pushes again");
    let repo = fx.repo();
    let out = evict(&repo, &request("ABC", &x)).expect("evict");
    assert!(matches!(out, EvictOutcome::Active { .. }), "{out:?}");
    assert!(fx.tip("ABC").is_some());
    let parked = parked_refs(&repo, "origin", "ABC", T)
        .expect("spawn")
        .expect("answer");
    assert!(parked.is_empty(), "{parked:?}");
}

// frob:tests evict
#[test]
fn a_second_evictor_sees_already_evicted() {
    let Some(fx) = Fixture::new() else { return };
    let x = fx.claim("ABC").expect("claim");
    let repo = fx.repo();
    assert!(matches!(
        evict(&repo, &request("ABC", &x)).expect("first"),
        EvictOutcome::Evicted { .. }
    ));
    let second = evict(&repo, &request("ABC", &x)).expect("second");
    assert_eq!(second, EvictOutcome::AlreadyEvicted);
    let parked = parked_refs(&repo, "origin", "ABC", T)
        .expect("spawn")
        .expect("answer");
    assert_eq!(
        parked.len(),
        1,
        "the loser withdrew its parked ref: {parked:?}"
    );
}

// frob:tests evict_batch
#[test]
fn batch_eviction_stops_at_the_rate_limit() {
    let Some(fx) = Fixture::new() else { return };
    let a = fx.claim("AAA").expect("a");
    let b = fx.claim("BBB").expect("b");
    let repo = fx.repo();
    let res = evict_batch(&repo, &[request("AAA", &a), request("BBB", &b)], 1).expect("batch");
    assert!(matches!(
        res[0].1,
        BatchItem::Ran(EvictOutcome::Evicted { .. })
    ));
    assert_eq!(res[1].1, BatchItem::RateLimited);
    assert!(fx.tip("BBB").is_some());
}

// frob:tests evict
#[test]
fn no_remote_is_offline() {
    let Some(fx) = Fixture::new() else { return };
    git(&fx.root, &["remote", "remove", "origin"]).expect("remove");
    let out = evict(&fx.repo(), &request("ABC", "deadbeef")).expect("evict");
    assert!(matches!(out, EvictOutcome::Offline(_)), "{out:?}");
}

// frob:tests restore
#[test]
fn restore_recreates_the_claim_from_parked_work_once() {
    let Some(fx) = Fixture::new() else { return };
    let Some(x) = fx.claim("RST") else { return };
    let repo = fx.repo();
    let out = evict(&repo, &request("RST", &x)).expect("evict");
    let EvictOutcome::Evicted { parked } = out else {
        panic!("expected eviction, got {out:?}");
    };
    assert_eq!(fx.tip("RST"), None);
    let first = restore(&repo, "RST", &parked).expect("restore");
    let RestoreOutcome::Restored { tip } = first else {
        panic!("expected restore, got {first:?}");
    };
    assert_eq!(fx.tip("RST"), Some(tip));
    assert_eq!(
        restore(&repo, "RST", &parked).expect("restore again"),
        RestoreOutcome::Taken
    );
}
