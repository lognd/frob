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

/// The `frob` binary under test with a hermetic `PATH` and `FROB_LOG` unset: spawns a real process, for exit status, stdio, signals, `PATH`, environment and timeouts.
pub fn process_command() -> assert_cmd::Command {
    let mut cmd = assert_cmd::Command::cargo_bin("frob").expect("frob binary");
    cmd.env("PATH", hermetic_path()).env_remove("FROB_LOG");
    cmd
}

/// True when the ambient `PATH` already holds no real sibling, so an in-process run sees the same siblings a hermetic spawn would.
fn ambient_path_is_hermetic() -> bool {
    static HERMETIC: std::sync::OnceLock<bool> = std::sync::OnceLock::new();
    *HERMETIC.get_or_init(|| {
        let ambient = std::env::var_os("PATH").unwrap_or_default();
        hermetic_path_from(&ambient) == ambient
    })
}

/// A `std::process::Output` carrying `code` as the exit status, so in-process runs look like spawned ones.
fn output_with_code(code: i32, stdout: String, stderr: String) -> std::process::Output {
    #[cfg(unix)]
    let status = std::os::unix::process::ExitStatusExt::from_raw(code << 8);
    #[cfg(windows)]
    let status =
        std::os::windows::process::ExitStatusExt::from_raw(u32::try_from(code).unwrap_or(1));
    std::process::Output {
        status,
        stdout: stdout.into_bytes(),
        stderr: stderr.into_bytes(),
    }
}

/// The command builder tests use to run `frob`: in process by default (no spawn, no link of a second binary), a real process when the test needs `PATH`, environment, timeout or an unhermetic host `PATH`.
#[derive(Debug, Default)]
pub struct FrobCmd {
    cwd: Option<PathBuf>,
    args: Vec<std::ffi::OsString>,
    envs: Vec<(std::ffi::OsString, std::ffi::OsString)>,
    removed: Vec<std::ffi::OsString>,
    timeout: Option<std::time::Duration>,
    force_process: bool,
}

impl FrobCmd {
    /// Run in `dir`.
    pub fn current_dir(&mut self, dir: impl AsRef<Path>) -> &mut Self {
        self.cwd = Some(dir.as_ref().to_path_buf());
        self
    }

    /// Append one argument.
    pub fn arg(&mut self, arg: impl AsRef<std::ffi::OsStr>) -> &mut Self {
        self.args.push(arg.as_ref().to_os_string());
        self
    }

    /// Append arguments.
    pub fn args<I, S>(&mut self, args: I) -> &mut Self
    where
        I: IntoIterator<Item = S>,
        S: AsRef<std::ffi::OsStr>,
    {
        self.args
            .extend(args.into_iter().map(|a| a.as_ref().to_os_string()));
        self
    }

    /// Set an environment variable; forces a real process.
    pub fn env(
        &mut self,
        key: impl AsRef<std::ffi::OsStr>,
        value: impl AsRef<std::ffi::OsStr>,
    ) -> &mut Self {
        self.envs
            .push((key.as_ref().to_os_string(), value.as_ref().to_os_string()));
        self
    }

    /// Unset an environment variable; `FROB_LOG` is a no-op in process (no subscriber is installed), any other name forces a real process.
    pub fn env_remove(&mut self, key: impl AsRef<std::ffi::OsStr>) -> &mut Self {
        self.removed.push(key.as_ref().to_os_string());
        self
    }

    /// Kill the run after `limit`; forces a real process.
    pub fn timeout(&mut self, limit: std::time::Duration) -> &mut Self {
        self.timeout = Some(limit);
        self
    }

    /// Insist on a real process, for tests that observe `current_exe` or other process identity.
    pub fn real_process(&mut self) -> &mut Self {
        self.force_process = true;
        self
    }

    /// Whether this run needs a real process rather than the in-process runner; `init` always does, since it records `current_exe` as the git merge driver and the test binary cannot serve as one.
    fn needs_process(&self) -> bool {
        self.force_process
            || self.args.iter().any(|a| a == "init")
            || !self.envs.is_empty()
            || self.timeout.is_some()
            || self.removed.iter().any(|k| k != "FROB_LOG")
            || !ambient_path_is_hermetic()
    }

    /// Run to completion and capture the output.
    pub fn output(&mut self) -> std::io::Result<std::process::Output> {
        if self.needs_process() {
            let mut cmd = process_command();
            if let Some(dir) = &self.cwd {
                cmd.current_dir(dir);
            }
            for key in &self.removed {
                cmd.env_remove(key);
            }
            for (key, value) in &self.envs {
                cmd.env(key, value);
            }
            if let Some(limit) = self.timeout {
                cmd.timeout(limit);
            }
            cmd.args(&self.args);
            return cmd.output();
        }
        let cwd = self.cwd.clone().unwrap_or_else(|| PathBuf::from("."));
        let argv: Vec<String> = self
            .args
            .iter()
            .map(|a| gob_path::Shown::with_home(std::path::Path::new(a), None).to_string())
            .collect();
        let argv: Vec<&str> = argv.iter().map(String::as_str).collect();
        let (code, stdout, stderr) = gob_cli::run_for_test(&frob_cli::cli(), &argv, &cwd);
        Ok(output_with_code(code, stdout, stderr))
    }
}

/// The `frob` command under test, in process unless the test asks for a real process: the one way tests should build their command.
pub fn frob_command() -> FrobCmd {
    FrobCmd::default()
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
