//! Throwaway repositories the profiled commands run in.
//!
//! No scenario ever runs in the source checkout: `repo` is a local clone of it (every branch and
//! tag copied, `origin` removed so nothing can be pushed back, `experimental` a local branch at
//! the source HEAD), `tmp` a fresh repository. Both live in a temporary directory removed on drop.

use std::path::{Path, PathBuf};
use std::time::Duration;

use gob_exec::{Outcome, Program, Runner, Spec};
use tempfile::TempDir;

use super::ProfileError;
use super::scenarios::FixtureKind;

/// Wall-clock limit for one git call while building a fixture.
const GIT_TIMEOUT: Duration = Duration::from_mins(5);

/// A temporary repository; the directory is deleted when this is dropped.
#[derive(Debug)]
pub struct Fixture {
    dir: TempDir,
    kind: FixtureKind,
}

impl Fixture {
    /// The repository root commands run in.
    pub fn path(&self) -> PathBuf {
        self.dir.path().join("repo")
    }

    /// Which fixture this is.
    pub fn kind(&self) -> FixtureKind {
        self.kind
    }
}

/// Run `git args` in `cwd` and return its trimmed stdout.
///
/// # Errors
/// [`ProfileError::Git`] when git cannot start or exits non-zero.
pub fn git(runner: &Runner, cwd: &Path, args: &[&str]) -> Result<String, ProfileError> {
    let out = runner
        .run(&Spec {
            program: Program::Git,
            args: args.iter().map(|a| (*a).to_owned()).collect(),
            cwd: Some(cwd.to_path_buf()),
            env: Vec::new(),
            timeout: GIT_TIMEOUT,
            capture: true,
        })
        .map_err(|e| ProfileError::Git(format!("git {}: {e}", args.join(" "))))?;
    if out.status == Outcome::Exited(0) {
        Ok(out.stdout.trim().to_owned())
    } else {
        Err(ProfileError::Git(format!(
            "git {} ended {:?}: {}",
            args.join(" "),
            out.status,
            out.stderr.trim()
        )))
    }
}

/// Give the repository at `repo` a committer identity, so verbs that commit work in a clone.
fn identify(runner: &Runner, repo: &Path) -> Result<(), ProfileError> {
    git(runner, repo, &["config", "user.name", "profile"])?;
    git(
        runner,
        repo,
        &["config", "user.email", "profile@example.invalid"],
    )?;
    git(runner, repo, &["config", "commit.gpgsign", "false"])?;
    Ok(())
}

/// Build the fixture of `kind`; `source` is the checkout `repo` clones (never modified).
///
/// # Errors
/// [`ProfileError`] when the temporary directory or a git call fails.
pub fn create(runner: &Runner, kind: FixtureKind, source: &Path) -> Result<Fixture, ProfileError> {
    let dir = tempfile::tempdir().map_err(|e| ProfileError::Io(format!("temp dir: {e}")))?;
    let fixture = Fixture { dir, kind };
    let repo = fixture.path();
    match kind {
        FixtureKind::Repo => {
            let sha = git(runner, source, &["rev-parse", "HEAD"])?;
            let dest = repo.to_string_lossy().into_owned();
            let src = source.to_string_lossy().into_owned();
            let parent = fixture.dir.path();
            git(
                runner,
                parent,
                &["clone", "--quiet", "--local", "--no-checkout", &src, &dest],
            )?;
            // Detach first: a branch cannot be force-updated while it is checked out.
            git(runner, &repo, &["update-ref", "--no-deref", "HEAD", &sha])?;
            git(
                runner,
                &repo,
                &[
                    "fetch",
                    "--quiet",
                    "--tags",
                    "origin",
                    "+refs/heads/*:refs/heads/*",
                ],
            )?;
            git(runner, &repo, &["remote", "remove", "origin"])?;
            git(
                runner,
                &repo,
                &["checkout", "--quiet", "-B", "experimental", &sha],
            )?;
            identify(runner, &repo)?;
            tracing::info!(fixture = %repo.display(), %sha, "repo fixture cloned");
        }
        FixtureKind::Tmp => {
            std::fs::create_dir(&repo)
                .map_err(|e| ProfileError::Io(format!("{}: {e}", repo.display())))?;
            git(runner, &repo, &["init", "--quiet", "-b", "experimental"])?;
            identify(runner, &repo)?;
            git(
                runner,
                &repo,
                &["commit", "--quiet", "--allow-empty", "-m", "init"],
            )?;
            tracing::info!(fixture = %repo.display(), "tmp fixture created");
        }
    }
    Ok(fixture)
}

#[cfg(test)]
mod tests {
    use super::*;
    use gob_exec::Limits;

    fn runner() -> Runner {
        Runner::new(Limits { jobs: 1 })
    }

    /// Everything about a repository a profiled command could change: HEAD, every ref, the index
    /// and the working-tree status.
    fn snapshot(r: &Runner, repo: &Path) -> Vec<String> {
        [
            "rev-parse HEAD",
            "for-each-ref",
            "ls-files -s",
            "status --porcelain=v1 -uall",
            "config --list --local",
        ]
        .iter()
        .map(|a| git(r, repo, &a.split(' ').collect::<Vec<_>>()).unwrap())
        .collect()
    }

    fn source(r: &Runner) -> TempDir {
        let src = tempfile::tempdir().unwrap();
        let p = src.path();
        git(r, p, &["init", "--quiet", "-b", "experimental"]).unwrap();
        identify(r, p).unwrap();
        std::fs::create_dir(p.join("tickets")).unwrap();
        std::fs::write(p.join("tickets/T-1.md"), "ledger\n").unwrap();
        git(r, p, &["add", "."]).unwrap();
        git(r, p, &["commit", "--quiet", "-m", "ledger"]).unwrap();
        git(r, p, &["branch", "frob-tickets"]).unwrap();
        git(r, p, &["tag", "v0"]).unwrap();
        src
    }

    // frob:tests crates/gob-dev/src/profile/fixture.rs::create
    #[test]
    fn mutating_the_clone_leaves_the_source_checkout_untouched() {
        let r = runner();
        let src = source(&r);
        let before = snapshot(&r, src.path());
        let fx = create(&r, FixtureKind::Repo, src.path()).unwrap();
        let repo = fx.path();
        assert!(repo.starts_with(fx.dir.path()) && !repo.starts_with(src.path()));
        // The clone has the ledger, every branch and the tag, with experimental checked out.
        assert!(repo.join("tickets/T-1.md").is_file());
        assert_eq!(
            git(&r, &repo, &["branch", "--show-current"]).unwrap(),
            "experimental"
        );
        git(
            &r,
            &repo,
            &["rev-parse", "--verify", "refs/heads/frob-tickets"],
        )
        .unwrap();
        git(&r, &repo, &["rev-parse", "--verify", "refs/tags/v0"]).unwrap();
        // What mutating verbs do: commit, move refs, edit the index, write files.
        std::fs::write(repo.join("tickets/T-2.md"), "new\n").unwrap();
        git(&r, &repo, &["add", "."]).unwrap();
        git(&r, &repo, &["commit", "--quiet", "-m", "mutated"]).unwrap();
        git(&r, &repo, &["branch", "-f", "frob-tickets", "HEAD"]).unwrap();
        git(&r, &repo, &["tag", "-f", "v0"]).unwrap();
        // Nothing can reach back: the clone has no remote to push to.
        assert!(git(&r, &repo, &["push", "origin", "experimental"]).is_err());
        assert!(git(&r, &repo, &["remote"]).unwrap().is_empty());
        assert_eq!(before, snapshot(&r, src.path()), "source checkout changed");
        assert!(!src.path().join("tickets/T-2.md").exists());
    }

    // frob:tests crates/gob-dev/src/profile/fixture.rs::create
    #[test]
    fn tmp_fixture_is_an_isolated_repository() {
        let r = runner();
        let fx = create(&r, FixtureKind::Tmp, Path::new("/nonexistent")).unwrap();
        assert_eq!(
            git(&r, &fx.path(), &["rev-list", "--count", "HEAD"]).unwrap(),
            "1"
        );
        let kept = fx.path();
        drop(fx);
        assert!(!kept.exists(), "fixture directory must be removed on drop");
    }
}
