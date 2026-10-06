//! Fixture helpers shared by the integration tests of the `frob` binary.
// frob:ticket 01M40WS6200M99J09D5XGAS05X
#![allow(dead_code)] // each test binary compiles this module and uses a subset

use std::path::{Path, PathBuf};

/// A fresh git repository in a temp dir on branch `main` with a repo-local identity (`Test` / `test@example.com`), so no test reads the host's git config.
pub fn git_repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    gob_git::Repo::init(dir.path()).expect("git init");
    // git for Windows defaults to `master`; pin the branch so snapshots and `base = ...` agree everywhere.
    let head = std::process::Command::new("git")
        .args(["symbolic-ref", "HEAD", "refs/heads/main"])
        .current_dir(dir.path())
        .status()
        .expect("git symbolic-ref");
    assert!(head.success(), "git symbolic-ref HEAD");
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

/// `PATH` with every directory that already holds a real sibling (`crunk`, `grimble`) removed, keeping git and the toolchain; so sibling discovery never depends on what the developer installed.
pub fn hermetic_path() -> std::ffi::OsString {
    hermetic_path_from(&std::env::var_os("PATH").unwrap_or_default())
}

/// `ambient` (a `PATH` value) with every directory holding a real sibling removed.
pub fn hermetic_path_from(ambient: &std::ffi::OsStr) -> std::ffi::OsString {
    let kept: Vec<PathBuf> = std::env::split_paths(ambient)
        .filter(|d| {
            ["crunk", "grimble"]
                .iter()
                .all(|name| !d.join(name).exists() && !d.join(format!("{name}.exe")).exists())
        })
        .collect();
    std::env::join_paths(kept).expect("join PATH")
}

/// The `frob` binary under test with a hermetic `PATH` and `FROB_LOG` unset: the one way tests should build their command.
pub fn frob_command() -> assert_cmd::Command {
    let mut cmd = assert_cmd::Command::cargo_bin("frob").expect("frob binary");
    cmd.env("PATH", hermetic_path()).env_remove("FROB_LOG");
    cmd
}

/// The markdown view of ticket `id` (`ticket show --format md`), run in `dir`.
// frob:tests crates/frob/src/ticket/read.rs::Show
pub fn ticket_markdown(dir: &std::path::Path, id: &str) -> String {
    let out = frob_command()
        .current_dir(dir)
        .env_remove("FROB_LOG")
        .args(["ticket", "show", id, "--format", "md"])
        .output()
        .expect("run frob");
    assert!(
        out.status.success(),
        "ticket show --format md: {}",
        String::from_utf8_lossy(&out.stderr)
    );
    String::from_utf8(out.stdout).expect("utf-8 markdown")
}
