//! Error sets of the ledger, declared with `error_set` (decision D22 trial).
//!
//! Small sets group related failures; [`LedgerError`] is their union, and
//! `?` converts a subset into the union for free. Every variant renders its
//! stable `E-*` code first, and [`LedgerError::to_refusal`] maps the
//! caller-fixable ones onto [`Refusal`]s for the CLI.

use error_set::error_set;
use gob_diagnostics::{Refusal, RefusalClass};
use gob_git::GitError;

/// A ticket that matched an ambiguous handle, listed in the refusal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Candidate {
    /// Full ULID.
    pub id: String,
    /// Title at the time of lookup.
    pub title: String,
}

error_set! {
    /// A ticket document or event file could not be parsed or rendered.
    FormatError := {
        /// TOML or fence syntax is wrong, or a field fails validation.
        #[display("E-TICKET-FORMAT: {path}: {message}")]
        Malformed {
            /// Repo-relative path (or a label such as `<events>`).
            path: String,
            /// What is wrong.
            message: String,
        },
    }

    /// The events of one ticket cannot be folded into a state.
    FoldError := {
        /// No create event, two create events, a bad field value, and so on.
        #[display("E-TICKET-FOLD: ticket {ticket}: {message}")]
        Fold {
            /// Full ULID of the ticket.
            ticket: String,
            /// What is wrong.
            message: String,
        },
    }

    /// The caller asked for something the model forbids.
    InputError := {
        /// A flag or value is invalid (exit 2).
        #[display("E-TICKET-INPUT: {message}")]
        Invalid {
            /// What is wrong.
            message: String,
        },
        /// The text matches a local private-term rule (exit 2); carries the rule label and pattern hash, never the term.
        #[display("E-REDACT-PRIVATE: text matches the private-term rule `{label}` (pattern hash {hash}); nothing was written")]
        Redacted {
            /// The rule's replace label.
            label: String,
            /// Short hash of the rule's pattern.
            hash: String,
        },
        /// A link breaks a topology rule (self link, cycle, second origin, ...).
        #[display("{code}: {message}")]
        LinkRejected {
            /// Stable code, for example `E-LINK-CYCLE`.
            code: &'static str,
            /// What is wrong.
            message: String,
        },
        /// The ticket is already terminal and the request would change it.
        #[display("E-TICKET-TERMINAL: {message}")]
        Terminal {
            /// What is wrong.
            message: String,
        },
        /// A close guard refused.
        #[display("{code}: {message} (remedy: {})", remedy.as_deref().unwrap_or("none"))]
        GuardRefused {
            /// Stable code, for example `E-CLOSE-OUTCOME`.
            code: String,
            /// What is wrong.
            message: String,
            /// The exact command that fixes it.
            remedy: Option<String>,
        },
    }

    /// A ticket reference did not resolve to exactly one ticket.
    LookupError := {
        /// No ticket matches the id, handle or alias.
        #[display("E-TICKET-NOT-FOUND: no ticket matches `{input}`")]
        NotFound {
            /// What the caller typed.
            input: String,
        },
        /// More than one ticket matches the handle or alias.
        #[display("E-TICKET-AMBIGUOUS: `{input}` matches {} tickets", candidates.len())]
        Ambiguous {
            /// What the caller typed.
            input: String,
            /// Every match.
            candidates: Vec<Candidate>,
        },
    }

    /// Git, SQLite or the filesystem failed.
    StoreError := {
        /// A git read or the ledger commit failed.
        #[display("{0}")]
        Git(GitError),
        /// The SQLite index failed.
        #[display("E-LEDGER-INDEX: {0}")]
        Sql(rusqlite::Error),
        /// A filesystem operation failed.
        #[display("E-LEDGER-IO: {0}")]
        Io(std::io::Error),
        /// The ledger ref does not exist in a repository that has commits.
        #[display("E-LEDGER-REF-MISSING: ledger ref `{ref_name}` does not exist")]
        RefMissing {
            /// The configured ref.
            ref_name: String,
        },
        /// Branch mode needs a checked-out branch.
        #[display("E-LEDGER-DETACHED: ref_mode is `branch` but HEAD is detached")]
        Detached,
    }

    /// Everything the ledger can fail with.
    LedgerError := FormatError || FoldError || InputError || LookupError || StoreError
}

impl LedgerError {
    /// The CLI refusal for a caller-fixable error, or `None` for a bug or an environment fault.
    pub fn to_refusal(&self) -> Option<Refusal> {
        use RefusalClass::{GuardNeedsAction, GuardRetryByWaiting, UsageError};
        let r = match self {
            Self::Invalid { message } => Refusal::new("E-TICKET-INPUT", UsageError, message),
            Self::Redacted { label, hash } => Refusal::new(
                "E-REDACT-PRIVATE",
                UsageError,
                format!("text matches the private-term rule `{label}` (pattern hash {hash}); nothing was written"),
            )
            .with_remedy("reword the text without the private term (rules live only in local privacy.toml files)"),
            Self::LinkRejected { code, message } => Refusal::new(*code, GuardNeedsAction, message),
            Self::Terminal { message } => {
                Refusal::new("E-TICKET-TERMINAL", GuardNeedsAction, message)
                    .with_remedy("frob ticket reopen <ticket> --reason <why>")
            }
            Self::GuardRefused {
                code,
                message,
                remedy,
            } => {
                let r = Refusal::new(code, GuardNeedsAction, message);
                match remedy {
                    Some(c) => r.with_remedy(c),
                    None => r,
                }
            }
            Self::NotFound { input } => Refusal::new(
                "E-TICKET-NOT-FOUND",
                GuardNeedsAction,
                format!("no ticket matches `{input}`"),
            )
            .with_remedy("frob ticket list"),
            Self::Ambiguous { input, candidates } => {
                let listed = candidates
                    .iter()
                    .map(|c| format!("{} {}", c.id, c.title))
                    .collect::<Vec<_>>()
                    .join("; ");
                Refusal::new(
                    "E-TICKET-AMBIGUOUS",
                    GuardNeedsAction,
                    format!("`{input}` matches {} tickets: {listed}", candidates.len()),
                )
                .with_remedy(format!(
                    "frob ticket show {}",
                    candidates.first().map_or("<full-ulid>", |c| c.id.as_str())
                ))
            }
            Self::RefMissing { ref_name } => Refusal::new(
                "E-LEDGER-REF-MISSING",
                GuardNeedsAction,
                format!("ledger ref `{ref_name}` does not exist"),
            )
            .with_remedy(
                "set [tickets] ref in frob.toml to an existing branch, create the branch, or for ref_mode = \"orphan\" run `frob ticket branch init`",
            ),
            Self::Detached => Refusal::new(
                "E-LEDGER-DETACHED",
                GuardNeedsAction,
                "ref_mode is `branch` but HEAD is detached",
            )
            .with_remedy("git switch <branch>"),
            Self::Git(g) => match g {
                GitError::CasExhausted { .. } => {
                    Refusal::new("E-LEDGER-CAS", GuardRetryByWaiting, g.to_string())
                }
                GitError::LocalEdits { path } => {
                    Refusal::new(g.code(), GuardNeedsAction, g.to_string()).with_remedy(format!(
                        "git diff -- {path}, then commit it or `git restore --source=HEAD --staged --worktree -- {path}`, and retry"
                    ))
                }
                GitError::NoIdentity => Refusal::new(g.code(), GuardNeedsAction, g.to_string()),
                _ => return None,
            },
            Self::Malformed { .. } | Self::Fold { .. } | Self::Sql(_) | Self::Io(_) => return None,
        };
        Some(r)
    }

    /// Shorthand for [`LedgerError::Invalid`].
    pub fn invalid(message: impl Into<String>) -> Self {
        Self::Invalid {
            message: message.into(),
        }
    }

    /// Shorthand for [`LedgerError::Malformed`].
    pub fn malformed(path: impl Into<String>, message: impl Into<String>) -> Self {
        Self::Malformed {
            path: path.into(),
            message: message.into(),
        }
    }

    /// Shorthand for [`LedgerError::Fold`].
    pub fn fold(ticket: impl std::fmt::Display, message: impl Into<String>) -> Self {
        Self::Fold {
            ticket: ticket.to_string(),
            message: message.into(),
        }
    }
}

/// Result alias used across the crate.
pub type Result<T, E = LedgerError> = std::result::Result<T, E>;
