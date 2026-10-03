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
