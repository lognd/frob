//! The few git operations `land` needs that `gob-git` does not offer, spawned through `gob-exec`.
//!
//! `gob-git` has no ref update, worktree removal or branch deletion, so these
//! run `git` through the repository's own runner (the spawn counter sees them).

use gob_path::Shown;
use std::path::Path;
use std::time::Duration;

use gob_exec::{Outcome, Program, Spec};
use gob_git::Repo;

use crate::error::LandError;

/// Wall-clock limit of one git spawn.
const TIMEOUT: Duration = Duration::from_secs(120);

/// The exit code and combined output of a finished git process.
#[derive(Debug, Clone)]
pub(crate) struct GitRun {
    /// Process exit code.
    pub code: i32,
    /// Stdout followed by stderr.
    pub text: String,
}

impl GitRun {
    /// True when git exited zero.
    pub(crate) fn ok(&self) -> bool {
        self.code == 0
    }
}

/// Attempts a git command gets while another process holds a git lock file.
const LOCK_ATTEMPTS: u32 = 8;
/// First backoff ceiling after a lock collision; doubles per attempt up to [`LOCK_BACKOFF_MAX`].
const LOCK_BACKOFF_BASE: Duration = Duration::from_millis(100);
/// Largest backoff ceiling after a lock collision.
const LOCK_BACKOFF_MAX: Duration = Duration::from_secs(2);

/// True when git's output says it could not take `index.lock` (or another `.lock`) because it exists,
/// or (Windows) could not open a `.git` file a concurrent writer was mid-rename on ("Permission denied").
fn is_lock_collision(text: &str) -> bool {
    (text.contains(".lock")
        && (text.contains("File exists") || text.contains("another git process")))
        || (text.contains("unable to access") && text.contains("Permission denied"))
}

/// Run `git <args>` in `cwd` through `repo`'s runner, retrying with backoff while a concurrent writer holds a git lock (frob:ticket 01M4DYPDCTK6KR5DXFQW7NXA6R).
pub(crate) fn git(repo: &Repo, cwd: &Path, args: &[&str]) -> Result<GitRun, LandError> {
    git_with_backoff(repo, cwd, args, LOCK_BACKOFF_BASE, LOCK_BACKOFF_MAX)
}

/// [`git`] with an explicit backoff, so a test need not wait seconds.
fn git_with_backoff(
    repo: &Repo,
    cwd: &Path,
    args: &[&str],
    base: Duration,
    max: Duration,
) -> Result<GitRun, LandError> {
    let mut run = spawn(repo, cwd, Program::Git, args)?;
    for attempt in 1..LOCK_ATTEMPTS {
        if run.ok() || !is_lock_collision(&run.text) {
            return Ok(run);
        }
        let ceiling = base.saturating_mul(1_u32 << attempt.min(16)).min(max);
        // Half the ceiling fixed, half jittered by clock entropy, so racing processes spread out.
        let jitter_ns = (ceiling.as_nanos() / 2).max(1);
        let spread = u64::try_from(gob_time::SystemClock::entropy_nanos() % jitter_ns).unwrap_or(0);
        let pause = ceiling / 2 + Duration::from_nanos(spread);
        tracing::warn!(attempt, ?pause, args = %args.join(" "), "git lock held by another process; backing off");
        std::thread::sleep(pause);
        run = spawn(repo, cwd, Program::Git, args)?;
    }
    if !run.ok() && is_lock_collision(&run.text) {
        tracing::warn!(args = %args.join(" "), "git lock still held after the retry budget");
    }
    Ok(run)
}

/// Run `cargo <args>` in `cwd` through `repo`'s runner (frob:ticket 01M418TM2GZ24YPQE7ECTKE1J4).
pub(crate) fn cargo(repo: &Repo, cwd: &Path, args: &[&str]) -> Result<GitRun, LandError> {
    spawn(repo, cwd, Program::Cargo, args)
}

fn spawn(repo: &Repo, cwd: &Path, program: Program, args: &[&str]) -> Result<GitRun, LandError> {
    let name = format!("{program:?}");
    let spec = Spec {
        program,
        args: args.iter().map(|s| (*s).to_owned()).collect(),
        cwd: Some(cwd.to_path_buf()),
        env: Vec::new(),
        timeout: TIMEOUT,
        capture: true,
    };
    tracing::info!(program = %name, args = %args.join(" "), cwd = %Shown::of(cwd), "land spawn");
    let out = repo
        .runner()
        .run(&spec)
        .map_err(|e| LandError::Config(format!("{name} {}: {e}", args.join(" "))))?;
    match out.status {
        Outcome::Exited(code) => Ok(GitRun {
            code,
            text: format!("{}{}", out.stdout, out.stderr).trim().to_owned(),
        }),
        other => Err(LandError::Config(format!(
            "{name} {}: {other:?}: {}",
            args.join(" "),
            out.stderr
        ))),
    }
}

/// Take the exclusive advisory lock at `lock` (creating it and its parent) until the returned file drops.
pub(crate) fn lock_exclusive(lock: &Path) -> Result<std::fs::File, LandError> {
    gob_fs::ensure_parent(lock)
        .map_err(|e| LandError::io(format!("creating the parent of {}", Shown::of(lock)), e))?;
    let file = std::fs::OpenOptions::new()
        .create(true)
        .truncate(false)
        .write(true)
        .open(lock)
        .map_err(|e| LandError::io(format!("opening {}", Shown::of(lock)), e))?;
    file.lock()
        .map_err(|e| LandError::io(format!("locking {}", Shown::of(lock)), e))?;
    Ok(file)
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M4DYPDCTK6KR5DXFQW7NXA6R
    // frob:tests crates/frob-land/src/git.rs::git_with_backoff
    #[test]
    fn a_git_command_waits_out_a_held_index_lock() {
        let dir = tempfile::tempdir().expect("tempdir");
        let repo = Repo::init(dir.path()).expect("init");
        std::fs::write(dir.path().join("f.txt"), "x\n").expect("file");
        let lock = repo.git_dir().join("index.lock");
        std::fs::write(&lock, b"").expect("lock");
        let blocked = spawn(&repo, dir.path(), Program::Git, &["add", "f.txt"]).expect("spawn");
        assert!(
            !blocked.ok() && is_lock_collision(&blocked.text),
            "{}",
            blocked.text
        );
        let releaser = {
            let lock = lock.clone();
            std::thread::spawn(move || {
                std::thread::sleep(Duration::from_millis(300));
                std::fs::remove_file(lock).expect("release");
            })
        };
        let run = git_with_backoff(
            &repo,
            dir.path(),
            &["add", "f.txt"],
            Duration::from_millis(50),
            Duration::from_millis(400),
        )
        .expect("git");
        releaser.join().expect("join");
        assert!(run.ok(), "retried until the lock cleared: {}", run.text);
    }

    // frob:ticket 01M4DYPDCTK6KR5DXFQW7NXA6R
    // frob:tests crates/frob-land/src/git.rs::is_lock_collision
    #[test]
    fn only_lock_collisions_are_retried() {
        assert!(is_lock_collision(
            "fatal: Unable to create '/r/.git/index.lock': File exists."
        ));
        assert!(!is_lock_collision("fatal: not a git repository"));
        assert!(!is_lock_collision(
            "error: Your local changes would be overwritten"
        ));
    }

    /// Marker variable: set, the test binary runs the probe body instead of spawning itself.
    const PROBE_VAR: &str = "FROB_LAND_CARGO_ENV_PROBE";

    // frob:ticket 01M5EH4JK63Q7HEJ2PZ3A55YQE
    // frob:tests crates/frob-land/src/git.rs::cargo
    #[test]
    fn land_cargo_inherits_the_callers_profile_env() {
        if std::env::var_os(PROBE_VAR).is_some() {
            // Child: the build script fails the build unless the profile override arrived.
            let dir = tempfile::tempdir().expect("tempdir");
            let p = dir.path();
            std::fs::write(
                p.join("Cargo.toml"),
                "[package]\nname = \"probe\"\nversion = \"0.0.0\"\nedition = \"2021\"\n\n[workspace]\n",
            )
            .expect("manifest");
            std::fs::create_dir(p.join("src")).expect("src");
            std::fs::write(p.join("src/lib.rs"), "").expect("lib");
            std::fs::write(
                p.join("build.rs"),
                "fn main() { assert_eq!(std::env::var(\"OPT_LEVEL\").unwrap(), \"2\"); }\n",
            )
            .expect("build.rs");
            let repo = Repo::init(p).expect("init");
            let run = cargo(&repo, p, &["build", "--offline"]).expect("spawn cargo");
            assert!(
                run.ok(),
                "CARGO_PROFILE_* did not reach cargo: {}",
                run.text
            );
            return;
        }
        let exe = std::env::current_exe().expect("current_exe");
        let out = std::process::Command::new(exe)
            .args([
                "--exact",
                "git::tests::land_cargo_inherits_the_callers_profile_env",
            ])
            .args(["--nocapture", "--test-threads=1"])
            .env(PROBE_VAR, "1")
            .env("CARGO_INCREMENTAL", "0")
            .env("CARGO_PROFILE_DEV_OPT_LEVEL", "2")
            .output()
            .expect("re-exec test binary");
        assert!(
            out.status.success(),
            "{}{}",
            String::from_utf8_lossy(&out.stdout),
            String::from_utf8_lossy(&out.stderr)
        );
    }
}
