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
    // frob:ticket 01M44YQXBGJW1VKDF64YJ5RTJ6
    /// Unity assembly tests were selected but no unity evidence provider exists yet, so nothing was run.
    #[error("E-TESTS-UNITY-PROVIDER: {} Unity test assembl{} selected, but the unity evidence provider (~F17DMKH) does not exist yet; nothing was run{}", .assemblies.len(), if .assemblies.len() == 1 { "y" } else { "ies" }, plan_note(.plan))]
    UnityProviderMissing {
        /// The selected Unity assembly packages.
        assemblies: Vec<String>,
        /// The plan lines of the selected Unity tests (empty under `--all`).
        plan: Vec<String>,
    },
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

/// The selection of a refused Unity run, as a message suffix (the first 20 lines).
fn plan_note(plan: &[String]) -> String {
    if plan.is_empty() {
        return String::new();
    }
    let shown: Vec<&str> = plan.iter().take(20).map(String::as_str).collect();
    let more = plan.len().saturating_sub(shown.len());
    let tail = if more > 0 {
        format!("; and {more} more")
    } else {
        String::new()
    };
    format!("; selection: {}{tail}", shown.join("; "))
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
            // frob:ticket 01M44YQXBGJW1VKDF64YJ5RTJ6
            Self::UnityProviderMissing { .. } => {
                let message = self.to_string();
                gob_cli::Refusal::new(
                    "E-TESTS-UNITY-PROVIDER",
                    gob_cli::RefusalClass::GuardNeedsAction,
                    message,
                )
                .with_remedy(
                    "run these tests from the Unity Test Runner (EditMode and PlayMode tabs) until the unity provider lands, or select only .csproj tests",
                )
                .into()
            }
            other => CliError::internal(other),
        }
    }
}

/// The result type of this crate.
pub type Result<T> = std::result::Result<T, TestsError>;
