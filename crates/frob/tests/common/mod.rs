//! Fixture helpers shared by the integration tests of the `frob` binary.
// frob:ticket 01M40WS6200M99J09D5XGAS05X
#![allow(dead_code)] // each test binary compiles this module and uses a subset

use std::path::Path;

/// A fresh git repository in a temp dir with a repo-local identity (`Test` / `test@example.com`), so no test reads the host's git config.
pub fn git_repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    gob_git::Repo::init(dir.path()).expect("git init");
    for (key, value) in [("user.name", "Test"), ("user.email", "test@example.com")] {
        let status = std::process::Command::new("git")
            .args(["config", key, value])
            .current_dir(dir.path())
            .status()
            .expect("git config");
        assert!(status.success(), "git config {key}");
    }
    dir
}

/// Rewrite `[pm] done_requires` in `<root>/frob.toml` to `requires`, so a fixture closes only what it means to test.
pub fn set_done_requires(root: &Path, requires: &[&str]) {
    let path = root.join("frob.toml");
    let text = std::fs::read_to_string(&path).expect("read frob.toml");
    let list = requires
        .iter()
        .map(|r| format!("\"{r}\""))
        .collect::<Vec<_>>()
        .join(", ");
    let lines: Vec<String> = text
        .lines()
        .map(|l| {
            if l.starts_with("done_requires") {
                format!("done_requires = [{list}]")
            } else {
                l.to_owned()
            }
        })
        .collect();
    std::fs::write(&path, lines.join("\n") + "\n").expect("write frob.toml");
}
