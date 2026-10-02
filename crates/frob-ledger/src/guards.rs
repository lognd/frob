//! Hook traits other crates implement: close guards and lease checks.

use crate::index::Summary;
use crate::model::{Outcome, Ticket};

/// What a close guard sees when a ticket would reach `done`.
#[derive(Debug)]
pub struct CloseContext<'a> {
    /// The ticket as it stands now.
    pub ticket: &'a Ticket,
    /// Its human handle (with `~`), for remedies.
    pub handle: &'a str,
    /// The outcome the caller asked for, if any.
    pub outcome: Option<Outcome>,
}

/// Why a guard refused: a stable code, a message and the exact fixing command.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GuardFailure {
    /// Stable code such as `E-CLOSE-OUTCOME`.
    pub code: String,
    /// What is missing.
    pub message: String,
    /// The command that fixes it, when there is one.
    pub remedy: Option<String>,
}

/// A named predicate evaluated when a ticket would reach `done` (tickets.md section 3).
///
/// `frob-evidence` (T-0020) adds the evidence guard; the default set is
/// [`OutcomeGuard`] only.
pub trait CloseGuard {
    /// The guard's name as selected in `[tickets.guards]`.
    fn name(&self) -> &'static str;

    /// Allow the close or explain why not.
    ///
    /// # Errors
    ///
    /// A [`GuardFailure`] when the ticket may not reach `done` yet.
    fn check(&self, cx: &CloseContext<'_>) -> Result<(), GuardFailure>;
}

/// The default guard: a terminal ticket must carry an outcome.
#[derive(Debug, Clone, Copy, Default)]
pub struct OutcomeGuard;

impl CloseGuard for OutcomeGuard {
    fn name(&self) -> &'static str {
        "has_outcome"
    }

    fn check(&self, cx: &CloseContext<'_>) -> Result<(), GuardFailure> {
        if cx.outcome.is_some() {
            return Ok(());
        }
        Err(GuardFailure {
            code: "E-CLOSE-OUTCOME".to_owned(),
            message: format!(
                "closing {} needs an outcome ({})",
                cx.handle,
                Outcome::NAMES.join(", ")
            ),
            remedy: Some(format!("frob ticket close {} --outcome done", cx.handle)),
        })
    }
}

/// The guards `close` evaluates when the caller passes none.
pub fn default_close_guards() -> Vec<Box<dyn CloseGuard>> {
    vec![Box::new(OutcomeGuard)]
}

/// Whether a ticket's scope is free of other leases; `doable` consults it.
///
/// `frob-lease` (T-0019) implements the real check; [`NoLeases`] passes everything.
pub trait LeaseCheck {
    /// True when no other holder's lease overlaps this ticket's scope.
    fn is_free(&self, ticket: &Summary, scope: &[String]) -> bool;
}

/// The default lease check: every ticket is free.
#[derive(Debug, Clone, Copy, Default)]
pub struct NoLeases;

impl LeaseCheck for NoLeases {
    fn is_free(&self, _ticket: &Summary, _scope: &[String]) -> bool {
        true
    }
}
