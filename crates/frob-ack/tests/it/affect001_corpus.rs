//! `AFFECT001` markdown corpus: each block is `src/lib.rs` edited after `base` was acknowledged.

// frob:ticket 01M4YBK7YTVNC16GHFFK4JKY97

use std::path::Path;
use std::time::Duration;

use frob_ack::{Inputs, ack, check};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use gob_mdtest::Case;
use gob_rules::Finding;

/// The committed baseline: `caller` depends on `base`, and `base` is acknowledged.
const BASELINE: &str = "pub fn base(x: u32) -> u32 {\n    x * 2\n}\n\npub fn caller(x: u32) -> u32 {\n    base(x) + 1\n}\n";

/// Run `git` in `dir`, panicking on failure.
fn git(dir: &Path, args: &[&str]) {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|a| (*a).to_owned()).collect(),
        cwd: Some(dir.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(30),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 }).run(&spec).expect("run git");
    assert_eq!(
        out.status,
        Outcome::Exited(0),
        "git {args:?}: {}",
        out.stderr
    );
}

/// Commit and acknowledge the baseline, replace `src/lib.rs` with the block, return the findings.
fn runner(case: &Case) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    git(p, &["init", "-q"]);
    git(p, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(p, &["config", "user.name", "Test User"]);
    git(p, &["config", "user.email", "test@example.com"]);
    std::fs::write(p.join(".gitignore"), ".frob/\n").expect("gitignore");
    std::fs::create_dir_all(p.join("src")).expect("mkdir");
    std::fs::write(p.join("src/lib.rs"), BASELINE).expect("baseline");
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "baseline"]);
    ack(
        p,
        &["src/lib.rs::base".to_owned()],
        false,
        Some("reviewed the contract in full"),
        gob_time::Clock::now(&gob_time::SystemClock),
    )
    .expect("ack");
    std::fs::write(p.join("src/lib.rs"), &case.text).expect("write block");
    tracing::debug!("AFFECT001 corpus block");
    let inputs = Inputs::collect(p).expect("collect");
    check(&inputs)
        .into_iter()
        .filter(|f| f.rule.as_str() == "AFFECT001")
        .collect()
}

gob_mdtest::mdtest!(dir = "tests/mdtest", runner = runner);
