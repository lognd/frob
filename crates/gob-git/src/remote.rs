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
        let cwd: PathBuf = self
            .work_dir()
            .unwrap_or_else(|| self.git_dir())
            .to_path_buf();
        let mut args = vec![
            "ls-remote".to_owned(),
            "--symref".to_owned(),
            remote.to_owned(),
        ];
        args.extend(patterns.iter().cloned());
        let ssh = batch_ssh_command(std::env::var("GIT_SSH_COMMAND").ok().as_deref());
        let spec = Spec {
            program: Program::Git,
            args: args.clone(),
            cwd: Some(cwd),
            env: vec![
                ("GIT_TERMINAL_PROMPT".to_owned(), "0".to_owned()),
                ("GIT_SSH_COMMAND".to_owned(), ssh),
            ],
            timeout,
            capture: true,
        };
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
