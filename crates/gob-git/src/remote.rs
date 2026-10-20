//! The bounded, non-prompting `git ls-remote` probe behind `frob refresh` (`distributed-tickets.md` section 5.2).

use std::path::PathBuf;
use std::time::Duration;

use gob_exec::{Outcome, Program, Spec};
use tracing::{debug, info, warn};

use crate::{GitError, Repo, SpawnClass};

/// One advertised ref of a remote.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RemoteRef {
    /// Object id as git printed it (hex).
    pub oid: String,
    /// Full ref name such as `refs/heads/main`, or `HEAD`.
    pub name: String,
}

/// How an `ls-remote` ended.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RemoteProbe {
    /// The remote answered.
    Refs {
        /// The advertised refs matching the requested patterns (possibly none).
        refs: Vec<RemoteRef>,
        /// The branch the remote's `HEAD` points at, when it said (`--symref`).
        head_branch: Option<String>,
    },
    /// The timeout elapsed and the process was killed.
    TimedOut,
    /// git exited non-zero; `text` is its redacted output for classification.
    Failed {
        /// Exit code, or -1 when signaled.
        code: i32,
        /// Combined stdout and stderr.
        text: String,
    },
}

/// Parse `git ls-remote` output (`<oid>\t<ref>` per line); malformed lines are skipped.
#[must_use]
pub fn parse_ls_remote(text: &str) -> Vec<RemoteRef> {
    text.lines()
        .filter_map(|l| {
            let (oid, name) = l.split_once('\t')?;
            (!oid.is_empty() && !oid.starts_with("ref:") && !name.is_empty()).then(|| RemoteRef {
                oid: oid.trim().to_owned(),
                name: name.trim().to_owned(),
            })
        })
        .collect()
}

/// The branch a `--symref` line (`ref: refs/heads/main\tHEAD`) names, if any.
#[must_use]
pub fn parse_head_symref(text: &str) -> Option<String> {
    text.lines().find_map(|l| {
        let (lhs, rhs) = l.split_once('\t')?;
        let target = lhs.strip_prefix("ref:")?.trim();
        (rhs.trim() == "HEAD").then(|| {
            target
                .strip_prefix("refs/heads/")
                .unwrap_or(target)
                .to_owned()
        })
    })
}

/// The ssh command line with `BatchMode=yes` appended to the user's own `GIT_SSH_COMMAND`, so ssh can never prompt.
#[must_use]
pub fn batch_ssh_command(existing: Option<&str>) -> String {
    format!("{} -o BatchMode=yes", existing.unwrap_or("ssh"))
}

/// How a bounded `git fetch` or `git push` ended.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RemoteRun {
    /// git exited zero.
    Done,
    /// A push was refused because the remote ref was not at the expected value (lost the CAS) or is not a fast-forward.
    Rejected(String),
    /// The timeout elapsed and the process was killed; nothing changed.
    TimedOut,
    /// git exited non-zero for another reason (offline, auth, ...); `text` is its output.
    Failed {
        /// Exit code, or -1 when signaled.
        code: i32,
        /// Combined stdout and stderr.
        text: String,
    },
}

/// Whether `text` (git push stderr) says the remote refused the update because the ref moved.
#[must_use]
pub fn is_push_rejection(text: &str) -> bool {
    [
        "stale info",
        "[rejected]",
        "non-fast-forward",
        "fetch first",
    ]
    .iter()
    .any(|m| text.contains(m))
}

impl Repo {
    /// Ask `remote` for `patterns` within `timeout`, never prompting for credentials.
    ///
    /// Spawns `git ls-remote` (class [`SpawnClass::GitLsRemote`]) with `GIT_TERMINAL_PROMPT=0`
    /// and ssh `BatchMode=yes`; a hung remote is killed at `timeout`.
    ///
    /// # Errors
    /// [`GitError::Spawn`] when git cannot be started; timeouts and non-zero exits are values of [`RemoteProbe`].
    pub fn ls_remote(
        &self,
        remote: &str,
        patterns: &[String],
        timeout: Duration,
    ) -> Result<RemoteProbe, GitError> {
        let mut args = vec![
            "ls-remote".to_owned(),
            "--symref".to_owned(),
            remote.to_owned(),
        ];
        args.extend(patterns.iter().cloned());
        let spec = self.remote_spec(args.clone(), timeout);
        let joined = args.join(" ");
        info!(class = SpawnClass::GitLsRemote.label(), args = %joined, "spawn ls-remote");
        let out = self.runner.run(&spec).map_err(|e| GitError::Spawn {
            args: joined,
            detail: e.to_string(),
        })?;
        let probe = match out.status {
            Outcome::Exited(0) => RemoteProbe::Refs {
                refs: parse_ls_remote(&out.stdout_raw),
                head_branch: parse_head_symref(&out.stdout_raw),
            },
            Outcome::Exited(code) => RemoteProbe::Failed {
                code,
                text: format!("{}{}", out.stdout, out.stderr),
            },
            Outcome::Signaled => RemoteProbe::Failed {
                code: -1,
                text: out.stderr,
            },
            Outcome::TimedOut => RemoteProbe::TimedOut,
        };
        match &probe {
            RemoteProbe::Refs { refs, .. } => {
                debug!(remote, refs = refs.len(), "ls-remote answered");
            }
            other => warn!(remote, outcome = ?other, "ls-remote did not answer"),
        }
        Ok(probe)
    }

    /// The non-prompting, bounded `git` spec every remote spawn shares.
    fn remote_spec(&self, args: Vec<String>, timeout: Duration) -> Spec {
        let cwd: PathBuf = self
            .work_dir()
            .unwrap_or_else(|| self.git_dir())
            .to_path_buf();
        let ssh = batch_ssh_command(std::env::var("GIT_SSH_COMMAND").ok().as_deref());
        Spec {
            program: Program::Git,
            args,
            cwd: Some(cwd),
            env: vec![
                ("GIT_TERMINAL_PROMPT".to_owned(), "0".to_owned()),
                ("GIT_SSH_COMMAND".to_owned(), ssh),
            ],
            timeout,
            capture: true,
        }
    }

    fn run_remote(
        &self,
        class: SpawnClass,
        args: Vec<String>,
        timeout: Duration,
    ) -> Result<RemoteRun, GitError> {
        let joined = args.join(" ");
        let spec = self.remote_spec(args, timeout);
        info!(class = class.label(), args = %joined, "spawn remote");
        let out = self.runner.run(&spec).map_err(|e| GitError::Spawn {
            args: joined,
            detail: e.to_string(),
        })?;
        let text = format!("{}{}", out.stdout, out.stderr);
        let run = match out.status {
            Outcome::Exited(0) => RemoteRun::Done,
            Outcome::Exited(_) if is_push_rejection(&text) => RemoteRun::Rejected(text),
            Outcome::Exited(code) => RemoteRun::Failed { code, text },
            Outcome::Signaled => RemoteRun::Failed {
                code: -1,
                text: out.stderr,
            },
            Outcome::TimedOut => RemoteRun::TimedOut,
        };
        match &run {
            RemoteRun::Done => debug!(class = class.label(), "remote command done"),
            other => {
                warn!(class = class.label(), outcome = ?other, "remote command did not complete");
            }
        }
        Ok(run)
    }

    /// Fetch exactly `refspecs` from `remote` within `timeout`, never prompting, no tags, no submodule recursion.
    ///
    /// A killed fetch leaves the repository as it was (git updates refs only after the pack is in).
    ///
    /// # Errors
    /// [`GitError::Spawn`] when git cannot be started; timeouts and non-zero exits are values of [`RemoteRun`].
    // frob:ticket 01M5CW049SPSRGGP5ENQD7BPB3
    pub fn fetch_refs(
        &self,
        remote: &str,
        refspecs: &[String],
        timeout: Duration,
    ) -> Result<RemoteRun, GitError> {
        let mut args: Vec<String> = [
            "fetch",
            "--no-tags",
            "--no-recurse-submodules",
            "--quiet",
            remote,
        ]
        .iter()
        .map(|s| (*s).to_owned())
        .collect();
        args.extend(refspecs.iter().cloned());
        self.run_remote(SpawnClass::GitFetch, args, timeout)
    }

    /// Push local `src` to `dst` on `remote` only if the remote `dst` still equals `expected` (`None` = must not exist).
    ///
    /// Spawns `git push --force-with-lease=<dst>:<expected>`, the server-side compare-and-swap; a lost
    /// race is [`RemoteRun::Rejected`].
    ///
    /// # Errors
    /// [`GitError::Spawn`] when git cannot be started.
    // frob:ticket 01M5CW049SPSRGGP5ENQD7BPB3
    pub fn push_cas(
        &self,
        remote: &str,
        src: &str,
        dst: &str,
        expected: Option<&str>,
        timeout: Duration,
    ) -> Result<RemoteRun, GitError> {
        let args = vec![
            "push".to_owned(),
            "--quiet".to_owned(),
            format!("--force-with-lease={dst}:{}", expected.unwrap_or("")),
            remote.to_owned(),
            format!("{src}:{dst}"),
        ];
        self.run_remote(SpawnClass::GitPush, args, timeout)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_ls_remote_lines() {
        let r = parse_ls_remote("abc\trefs/heads/main\ndef\tHEAD\nbroken\n");
        assert_eq!(r.len(), 2);
        assert_eq!(r[0].name, "refs/heads/main");
        assert_eq!(r[1].oid, "def");
    }

    #[test]
    fn parses_symref_head() {
        let t = "ref: refs/heads/main\tHEAD\nabc\tHEAD\nabc\trefs/heads/main\n";
        assert_eq!(parse_head_symref(t).as_deref(), Some("main"));
        assert_eq!(parse_ls_remote(t).len(), 2);
        assert_eq!(parse_head_symref("abc\tHEAD\n"), None);
    }

    #[test]
    fn ssh_command_gains_batch_mode() {
        assert_eq!(batch_ssh_command(None), "ssh -o BatchMode=yes");
        assert_eq!(
            batch_ssh_command(Some("ssh -i k")),
            "ssh -i k -o BatchMode=yes"
        );
    }
}
