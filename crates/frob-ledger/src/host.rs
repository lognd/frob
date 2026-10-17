//! The host the ledger-reading rules (`TICK`, `PM`, `REL`) judge: the open ledger and why it may be absent.

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use std::path::Path;

use gob_rules::{Finding, RequiredReason, RuleId, Severity};

use crate::ledger::Ledger;

/// What a product knows about the repository's ticket ledger, borrowed from its inputs.
#[derive(Clone, Copy)]
pub struct LedgerView<'a> {
    /// The repository root every rule reads beside the ledger (config, `changelog.d`).
    pub root: &'a Path,
    /// The open ledger, `None` when there is none or it could not be read.
    pub ledger: Option<&'a Ledger>,
    /// Why an existing ledger could not be read; the rules then report Unresolved, never zero findings.
    pub error: Option<&'a str>,
    /// Why the configured ledger ref is absent, reported once by `TICK001`.
    pub missing: Option<&'a str>,
    /// Milestone objects in the ledger (`PM001`, `PM002` and `PM034` have nothing to judge without one).
    pub milestones: usize,
    /// Tickets in the ledger, the subject count of `TICK002`.
    pub tickets: usize,
    /// Whether the repository has, or expects, a ledger (so a rule reading it has something to judge).
    pub configured: bool,
}

impl<'a> LedgerView<'a> {
    /// The open ledger, `Ok(None)` when there is none, or the required Unresolved finding for `rule` when it is unreadable.
    ///
    /// # Errors
    ///
    /// The `evaluation-failed` finding of `rule` when the ledger exists but could not be read.
    #[allow(
        clippy::result_large_err,
        reason = "the Err is the finding the rule emits, built once per run"
    )]
    pub fn open(&self, rule: &str) -> Result<Option<&'a Ledger>, Finding> {
        match self.error {
            Some(err) => {
                let finding = evaluation_failed(rule, format_args!("ledger unreadable: {err}"));
                Err(finding)
            }
            None => Ok(self.ledger),
        }
    }
}

/// A product whose snapshot holds the ticket ledger.
pub trait LedgerHost {
    /// The ledger facts of this snapshot.
    fn ledger_view(&self) -> LedgerView<'_>;

    /// The findings of the ledger doctor (read-only), computed once per snapshot; the error text when it cannot run.
    ///
    /// # Errors
    ///
    /// The doctor's failure rendered as text.
    fn doctor_findings(&self) -> Result<Vec<Finding>, String>;
}

/// The required Unresolved finding saying `rule` was not evaluated because of `error` (unknown is never a pass).
// frob:ticket 01M42MGNE7XHTT1MR5CA6C2R1C
pub fn evaluation_failed(rule: &str, error: impl std::fmt::Display) -> Finding {
    let error = error.to_string();
    tracing::warn!(rule, %error, "rule not evaluated; reporting required Unresolved");
    let id: RuleId = rule
        .parse()
        .unwrap_or_else(|e| unreachable!("rule id literal {rule}: {e}"));
    Finding::new(
        id,
        Severity::Unresolved,
        None,
        format!("evaluation-failed: {rule} was not evaluated: {error}"),
        "repository",
    )
    .with_required(RequiredReason::EvaluationFailed {
        rule: rule.to_owned(),
        error,
    })
}
