//! The error type of the test-selection crate.

use gob_cli::CliError;

/// Everything touched-set computation, selection and runs can fail with.
#[derive(Debug, thiserror::Error)]
pub enum TestsError {
    /// A git diff or blob read failed (for example an unknown `--base`).
    #[error("E-TESTS-GIT: {0}")]
    Git(#[from] gob_git::GitError),
    /// Walking the work tree failed.
    #[error("E-TESTS-WALK: {0}")]
    Walk(#[from] gob_walk::WalkError),
    /// Evidence capture or storage failed.
    #[error(transparent)]
    Evidence(#[from] frob_evidence::EvidenceError),
    /// A process could not be started.
    #[error(transparent)]
    Exec(#[from] gob_exec::ExecError),
    /// A file could not be read.
    #[error("E-TESTS-IO: {path}: {source}")]
    Io {
        /// The path involved.
        path: String,
        /// The OS error.
        #[source]
        source: std::io::Error,
    },
}

impl TestsError {
    /// The CLI error: a refusal when the caller can fix it, else internal.
    pub fn into_cli(self) -> CliError {
        match self {
            Self::Evidence(e) => e.into_cli(),
            Self::Git(gob_git::GitError::Rev { spec, detail }) => gob_cli::Refusal::new(
                "E-TESTS-BASE",
                gob_cli::RefusalClass::GuardNeedsAction,
                format!("cannot resolve --base `{spec}`: {detail}"),
            )
            .with_remedy("frob test --base <an existing ref>")
            .into(),
            other => CliError::internal(other),
        }
    }
}

/// The result type of this crate.
pub type Result<T> = std::result::Result<T, TestsError>;
