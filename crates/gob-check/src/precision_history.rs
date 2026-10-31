//! Persisting the precision ledger's fixed and dismissed counts in the product's state directory.

// frob:ticket 01M4M8EJA0RAXE090V8X84157K

use std::collections::BTreeSet;
use std::path::Path;

use gob_rules::{HistoryError, PrecisionHistory, RuleId};

use crate::product::Product;
use crate::report::CheckReport;

/// Fold `report` into the history under `state_dir` and return it; failures are logged, never raised.
///
/// A run limited by `--only` or a scope is not recorded (it cannot tell fixed from not looked at).
pub(crate) fn record(
    state_dir: &Path,
    report: &CheckReport,
    unfiltered: bool,
) -> Option<PrecisionHistory> {
    let mut history = match PrecisionHistory::load(state_dir) {
        Ok(h) => h,
        Err(err) => {
            tracing::warn!(%err, "precision history unreadable; fixed and dismissed counts skipped");
            return None;
        }
    };
    if unfiltered && report.scope.is_none() {
        let evaluated: BTreeSet<String> = report.subjects_examined.keys().cloned().collect();
        history.record_run(&report.findings, &evaluated);
        if let Err(err) = history.save(state_dir) {
            tracing::warn!(%err, "precision history not written");
        }
    } else {
        tracing::debug!("filtered run; precision history read but not extended");
    }
    Some(history)
}

/// Record the dismissal of the finding `fingerprint` of `rule` for `reason`, persisted for later runs.
///
/// # Errors
///
/// [`HistoryError::Reason`] without an acceptable reason; I/O and format errors from the history file.
pub fn dismiss<P: Product>(
    product: &P,
    root: &Path,
    rule: &RuleId,
    fingerprint: &str,
    reason: &str,
) -> Result<(), HistoryError> {
    let dir = product.telemetry_dir(root);
    let mut history = PrecisionHistory::load(&dir)?;
    history.dismiss(rule, fingerprint, reason)?;
    history.save(&dir)
}
