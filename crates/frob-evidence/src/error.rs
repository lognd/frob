//! The error type of the evidence crate and its mapping to CLI refusals.

use gob_cli::{CliError, Refusal, RefusalClass};

/// Everything evidence capture, storage and lookup can fail with.
#[derive(Debug, thiserror::Error)]
pub enum EvidenceError {
    /// The `command` provider was asked to run a tool outside `[evidence] allowed_tools`.
    #[error("E-EVIDENCE-TOOL: `{tool}` is not in [evidence] allowed_tools")]
    ToolNotAllowed {
        /// The rejected program name.
        tool: String,
    },
    /// The `command` or `nextest` reference was empty or could not be split.
    #[error("E-EVIDENCE-REF: {0}")]
    BadReference(String),
    /// A nextest or pytest filter matched no test, so there is nothing to measure.
    #[error(
        "E-EVIDENCE-NO-TESTS: the test filter `{filter}` matched no tests; nothing was recorded"
    )]
    NoTestsMatched {
        /// The filter arguments as given in `--ref`.
        filter: String,
    },
    /// An attestation was attempted without a person at a terminal.
    #[error("E-ATTEST-NOT-HUMAN: an attestation is a person's statement; refused because {}", .reasons.join("; "))]
    NotHuman {
        /// Why presence failed: a stream is not a terminal, or an agent marker is set.
        reasons: Vec<String>,
    },
    /// The attesting identity is not listed in `[evidence] attesters`.
    #[error("{}", not_attester_message(.identity.as_ref(), .listed))]
    NotAttester {
        /// The identity found (git `user.email`), when there is one.
        identity: Option<String>,
        /// The identities `[evidence] attesters` lists.
        listed: Vec<String>,
    },
    /// The statement is empty.
    #[error("E-ATTEST-STATEMENT: an attestation needs a non-empty --statement")]
    EmptyStatement,
    /// A statement or fact holds a non-ASCII character; ledger text must be ASCII.
    #[error(
        "E-ATTEST-NON-ASCII: the {what} has a non-ASCII character at position {position} (1-based), {escape}; retype it in ASCII, nothing was recorded"
    )]
    NonAscii {
        /// `statement` or `fact`.
        what: &'static str,
        /// 1-based character position of the first offender.
        position: usize,
        /// The offender as `\u{XXXX}`.
        escape: String,
    },
    /// A fact is not a URL, a commit id or a ticket id.
    #[error(
        "E-ATTEST-FACT: `{fact}` is not an https/http URL, a commit id (7 to 40 hex digits) or a ticket handle or ULID"
    )]
    BadFact {
        /// The fact as given.
        fact: String,
    },
    /// A commit or ticket named by a fact does not exist.
    #[error(
        "E-ATTEST-FACT-MISSING: {kind} `{fact}` does not exist in this repository; nothing was recorded"
    )]
    MissingFact {
        /// `commit` or `ticket`.
        kind: &'static str,
        /// The fact as given.
        fact: String,
    },
    /// A provider name is not one of `nextest`, `command`, `file`.
    #[error(
        "E-EVIDENCE-PROVIDER: `{0}` is not a provider; expected nextest, command, file or attestation"
    )]
    BadProvider(String),
    /// An acceptance index is zero or beyond the ticket's criteria.
    #[error("E-EVIDENCE-ACCEPTS: {0}")]
    BadAccepts(String),
    /// The evidence index of `fetch` does not exist.
    #[error("E-EVIDENCE-INDEX: {0}")]
    BadIndex(String),
    /// The working directory is not inside a git work tree.
    #[error("E-NOT-A-REPO: {0} is not inside a git work tree")]
    NotARepo(String),
    /// A configured knob is unusable.
    #[error("E-EVIDENCE-CONFIG: {0}")]
    Config(String),
    /// A process could not be started or supervised.
    #[error(transparent)]
    Exec(#[from] gob_exec::ExecError),
    /// The ledger refused or failed.
    #[error(transparent)]
    Ledger(#[from] frob_ledger::LedgerError),
    /// A git read or write failed.
    #[error(transparent)]
    Git(#[from] gob_git::GitError),
    /// A file could not be read or written.
    #[error("E-EVIDENCE-IO: {path}: {source}")]
    Io {
        /// The path involved.
        path: String,
        /// The OS error.
        #[source]
        source: std::io::Error,
    },
    /// An evidence event file is not in the expected shape.
    #[error("E-EVIDENCE-FORMAT: {0}")]
    Malformed(String),
}

impl EvidenceError {
    /// Wrap an I/O failure with the path it concerns.
    pub fn io(path: impl AsRef<std::path::Path>, source: std::io::Error) -> Self {
        Self::Io {
            path: path.as_ref().display().to_string(),
            source,
        }
    }

    /// The CLI error: a refusal when the caller can fix it, else internal.
    pub fn into_cli(self) -> CliError {
        use RefusalClass::{GuardNeedsAction, UsageError};
        let refusal = match &self {
            Self::ToolNotAllowed { tool } => Some(
                Refusal::new("E-EVIDENCE-TOOL", GuardNeedsAction, self.to_string()).with_remedy(
                    format!("add \"{tool}\" to [evidence] allowed_tools in frob.toml"),
                ),
            ),
            Self::NotHuman { .. } => Some(
                Refusal::new("E-ATTEST-NOT-HUMAN", GuardNeedsAction, self.to_string())
                    .with_remedy(
                        "stop and tell the user which criterion needs an attestation; only a person at an interactive terminal can make it, and an agent never attests",
                    )
                    .requiring_human(),
            ),
            Self::NotAttester { .. } => Some(
                Refusal::new("E-ATTEST-NOT-ATTESTER", GuardNeedsAction, self.to_string())
                    .with_remedy(
                        "the repository owner must list the attesting identity under [evidence] attesters in frob.toml; an agent must not edit that list",
                    )
                    .requiring_human(),
            ),
            Self::EmptyStatement => Some(
                Refusal::new("E-ATTEST-STATEMENT", UsageError, self.to_string())
                    .with_remedy("pass the statement text with --statement"),
            ),
            Self::NonAscii { .. } => Some(
                Refusal::new("E-ATTEST-NON-ASCII", UsageError, self.to_string())
                    .with_remedy("retype the statement or fact using ASCII characters only"),
            ),
            Self::BadFact { .. } => Some(
                Refusal::new("E-ATTEST-FACT", UsageError, self.to_string())
                    .with_remedy("pass each fact as an https URL, a commit id or a ~handle"),
            ),
            Self::MissingFact { kind, .. } => Some(
                Refusal::new("E-ATTEST-FACT-MISSING", GuardNeedsAction, self.to_string())
                    .with_remedy(if *kind == "commit" {
                        "find the commit id with: git log --oneline"
                    } else {
                        "find the ticket handle with: frob ticket list"
                    }),
            ),
            Self::BadReference(_) | Self::BadProvider(_) | Self::BadAccepts(_) => {
                Some(Refusal::new(code_of(&self), UsageError, self.to_string()))
            }
            Self::NoTestsMatched { filter } => Some(
                Refusal::new("E-EVIDENCE-NO-TESTS", UsageError, self.to_string()).with_remedy(
                    format!(
                        "list the test names the filter can match with: cargo nextest list {filter} (nextest) or pytest --collect-only -q {filter} (pytest)"
                    ),
                ),
            ),
            Self::BadIndex(_) => Some(
                Refusal::new("E-EVIDENCE-INDEX", GuardNeedsAction, self.to_string())
                    .with_remedy("frob ticket evidence list <ticket>"),
            ),
            Self::NotARepo(_) => Some(
                Refusal::new("E-NOT-A-REPO", GuardNeedsAction, self.to_string())
                    .with_remedy("git init"),
            ),
            Self::Config(_) => Some(
                Refusal::new("E-EVIDENCE-CONFIG", GuardNeedsAction, self.to_string())
                    .with_remedy("fix the [evidence] table in frob.toml"),
            ),
            Self::Ledger(e) => e.to_refusal(),
            Self::Git(_) | Self::Exec(_) | Self::Io { .. } | Self::Malformed(_) => None,
        };
        match refusal {
            Some(r) => r.into(),
            None => CliError::internal(self),
        }
    }
}

fn not_attester_message(identity: Option<&String>, listed: &[String]) -> String {
    let who = identity.map_or_else(
        || "no git user.email is set".to_owned(),
        |i| format!("`{i}` is not an attester"),
    );
    let list = if listed.is_empty() {
        "[evidence] attesters is empty, so nobody may attest (frob init and frob config sync write the repository owner's git user.email there)".to_owned()
    } else {
        format!("[evidence] attesters lists {}", listed.join(", "))
    };
    format!("E-ATTEST-NOT-ATTESTER: {who}; {list}")
}

fn code_of(e: &EvidenceError) -> &'static str {
    match e {
        EvidenceError::BadReference(_) => "E-EVIDENCE-REF",
        EvidenceError::BadProvider(_) => "E-EVIDENCE-PROVIDER",
        _ => "E-EVIDENCE-ACCEPTS",
    }
}

/// The result type of this crate.
pub type Result<T> = std::result::Result<T, EvidenceError>;
