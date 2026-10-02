//! Exception primitive data types (no directive parsing here).

use serde::{Deserialize, Serialize};

use crate::id::RuleId;

/// The four exception kinds from the exceptions design.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ExceptionKind {
    /// Does not apply here by design; permanent.
    Accept,
    /// Real debt paid by a ticket.
    Defer,
    /// Quick fix that must be revisited; hard expiry.
    Hotfix,
    /// Mass legacy findings admitted at rule introduction.
    Baseline,
}

/// A recorded exception to one rule.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Exception {
    /// Which kind of exception this is.
    pub kind: ExceptionKind,
    /// The rule excepted.
    pub rule: RuleId,
    /// Why; vetted by `check_reason`.
    pub reason: String,
    /// Ticket that pays the debt, when the kind needs one.
    pub ticket: Option<String>,
    /// Optional ISO date (`YYYY-MM-DD`) after which the exception lapses.
    pub until: Option<String>,
}
