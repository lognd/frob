//! Helpers shared by the frob-tests integration tests: run git in a temp repo and write fixture files.

use std::path::Path;
use std::time::Duration;

use gob_exec::{Limits, Outcome as ExecOutcome, Program, Runner, Spec};

pub fn git(dir: &Path, args: &[&str]) -> String {
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
        ExecOutcome::Exited(0),
        "git {args:?}: {}",
        out.stderr
    );
    out.stdout.trim().to_owned()
}

pub fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}
