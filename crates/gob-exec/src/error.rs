//! Typed errors for process execution.

use std::io;

/// Failure to start or supervise a child process.
#[derive(Debug, thiserror::Error)]
pub enum ExecError {
    /// The program is not on the spawn allowlist.
    #[error("program is not on the spawn allowlist: {program}")]
    NotAllowed {
        /// Description of the rejected program.
        program: String,
    },
    /// The allowlisted program could not be located on this machine.
    #[error("program not found: {program}")]
    NotFound {
        /// Name of the missing program.
        program: String,
    },
    /// The program resolved to a path inside the work tree (security.md 2.4).
    #[error(
        "{program} resolves inside the work tree ({path}); a process pack must live outside it"
    )]
    InsideWorkTree {
        /// Name of the program.
        program: String,
        /// The resolved path.
        path: String,
    },
    /// The binary at a pack's path no longer matches the digest recorded for it.
    #[error("{program} changed since it was resolved: recorded {recorded}, found {found}")]
    DigestChanged {
        /// Name of the program.
        program: String,
        /// The digest recorded at resolve time.
        recorded: String,
        /// The digest found now.
        found: String,
    },
    /// The OS refused to spawn the child.
    #[error("failed to spawn child: {0}")]
    Spawn(#[source] io::Error),
    /// Waiting on or reading from the child failed.
    #[error("failed to wait on child: {0}")]
    Wait(#[source] io::Error),
    /// The child wrote more than the runner's output cap and was killed.
    #[error("child output exceeded the {limit} byte cap and the child was killed")]
    OutputCap {
        /// The cap in bytes that was exceeded.
        limit: usize,
    },
}
