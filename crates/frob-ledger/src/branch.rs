//! The ticket branch: name checks and orphan-branch bootstrap (design: `mirror.md` section 1, D79).
//!
//! The branch is created through [`gob_git::Repo::commit_paths`] on a ref that
//! does not exist yet, which makes a root commit with compare-and-swap; no
//! index, `HEAD` or work tree of any checkout is read or written (decision D23).

use gob_git::{CommitOptions, GitError, Oid, RelPath, Repo};

/// Placeholder `README.md` of a fresh ticket branch (the generated pages replace it later).
pub const README_PLACEHOLDER: &str = "# Tickets\n\n\
This branch holds the frob ticket ledger of this repository. It is written by\n\
`frob` only; do not edit files here by hand.\n\n\
Browse tickets with `frob ticket list` from a checkout of the code branch.\n";

/// What [`init_branch`] found or did.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BranchInit {
    /// The branch did not exist; this root commit created it.
    Created(Oid),
    /// The branch already existed at this tip; nothing was written.
    Already(Oid),
}

/// Why the ticket branch could not be bootstrapped.
#[derive(Debug, thiserror::Error)]
pub enum BranchError {
    /// The configured name is not a usable branch name.
    #[error("`{name}` is not a usable branch name: {why}")]
    InvalidName {
        /// The configured name.
        name: String,
        /// What is wrong with it.
        why: &'static str,
    },
    /// Only a remote-tracking copy exists; creating a fresh orphan would fork the ledger history.
    #[error(
        "`{remote_ref}` exists but no local branch `{branch}`; creating an orphan would fork the ledger"
    )]
    RemoteOnly {
        /// The configured branch.
        branch: String,
        /// The remote-tracking ref found.
        remote_ref: String,
    },
    /// A git operation failed.
    #[error(transparent)]
    Git(#[from] GitError),
}

/// Check that `name` is a plain branch name (not a ref path, option or revision expression).
///
/// # Errors
///
/// [`BranchError::InvalidName`] naming what is wrong.
pub fn check_branch_name(name: &str) -> Result<(), BranchError> {
    let why = if name.is_empty() {
        Some("it is empty")
    } else if name.starts_with("refs/") {
        Some("give the bare branch name, not a ref path")
    } else if name.starts_with(['-', '/', '.']) || name.ends_with(['/', '.']) {
        Some("it starts or ends with `-`, `/` or `.`")
    } else if name.rsplit_once('.').is_some_and(|(_, ext)| ext == "lock")
        || name.contains("..")
        || name.contains("//")
    {
        Some("it contains `..`, `//` or ends in `.lock`")
    } else if !name
        .chars()
        .all(|c| c.is_ascii_graphic() && !"~^:?*[\\@{".contains(c))
    {
        Some("it has a space, control or git-reserved character")
    } else {
        None
    };
    match why {
        Some(why) => Err(BranchError::InvalidName {
            name: name.to_owned(),
            why,
        }),
        None => Ok(()),
    }
}

/// Create the orphan ticket branch `branch` with a placeholder `README.md` and the merge-driver `.gitattributes`, or report it as already there.
///
/// # Errors
///
/// [`BranchError::InvalidName`], [`BranchError::RemoteOnly`] when only
/// `refs/remotes/origin/<branch>` exists, or a git failure (CAS exhaustion,
/// missing identity).
pub fn init_branch(repo: &Repo, branch: &str, cas_retries: u32) -> Result<BranchInit, BranchError> {
    check_branch_name(branch)?;
    let full = format!("refs/heads/{branch}");
    match repo.rev_parse(&full) {
        Ok(tip) => {
            tracing::info!(%branch, %tip, "ticket branch already exists");
            return Ok(BranchInit::Already(tip));
        }
        Err(GitError::Rev { .. }) => {}
        Err(e) => return Err(e.into()),
    }
    let remote_ref = format!("refs/remotes/origin/{branch}");
    if repo.rev_parse(&remote_ref).is_ok() {
        tracing::warn!(%branch, %remote_ref, "ticket branch exists only on the remote");
        return Err(BranchError::RemoteOnly {
            branch: branch.to_owned(),
            remote_ref,
        });
    }
    let changes = [
        (
            RelPath::new("README.md")?,
            Some(README_PLACEHOLDER.as_bytes().to_vec()),
        ),
        (
            RelPath::new(".gitattributes")?,
            Some(crate::layout::branch_gitattributes("tickets").into_bytes()),
        ),
    ];
    let opts = CommitOptions {
        cas_retries,
        author: None,
    };
    let out = repo.commit_paths(
        &full,
        &changes,
        "tickets(init): orphan ticket branch",
        &opts,
    )?;
    tracing::info!(%branch, commit = %out.oid, "ticket branch created");
    Ok(BranchInit::Created(out.oid))
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M3ZX8141MTBF6G2E6BAD33TS
    #[test]
    fn names_are_checked() {
        for ok in ["frob-tickets", "a/b", "t_1"] {
            assert!(check_branch_name(ok).is_ok(), "{ok}");
        }
        for bad in [
            "",
            "refs/heads/x",
            "-x",
            "a..b",
            "a b",
            "x.lock",
            "a/",
            "a~1",
            "a@{1}",
        ] {
            assert!(check_branch_name(bad).is_err(), "{bad}");
        }
    }
}
