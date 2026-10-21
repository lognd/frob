//! Closing by commit keyword is a tracker edit (mirror.md 3.6).
//!
//! A code-branch commit saying `fixes #12` makes the tracker close the mirrored issue. While the
//! ledger says the ticket is still open that closure is a tracker edit of the repository-owned
//! `state` field: it is reverted (the issue is reopened) and recorded as a proposal, never fought
//! silently. When the ledger already says done the closure agrees with it and nothing is reverted.

// frob:ticket 01M4052TQSK1WXBD9280DDRNM5

use gob_time::Stamp;
use tracing::{debug, info};

use crate::adapter::{EventId, IssueRef};
use crate::proposals::Edit;
use crate::reconcile::{Reconciled, Revert};

/// The repository-owned field a closure edits.
pub const STATE_FIELD: &str = "state";
/// The state value a closed issue carries.
pub const CLOSED: &str = "closed";
/// The state value an open issue carries, written back by a revert.
pub const OPEN: &str = "open";

/// A closure of a mirrored issue by a commit's closing keyword, read from tracker history.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct KeywordClosure {
    /// The tracker's closed-event id: the proposal's idempotency key.
    pub event: EventId,
    /// Tracker user id of whoever the closure is attributed to.
    pub actor_id: u64,
}

/// Everything needed to judge one closure by commit keyword.
pub struct ClosingView<'a> {
    /// The tracker issue.
    pub issue: &'a IssueRef,
    /// Whether the ledger says the ticket is done.
    pub ledger_done: bool,
    /// The closure found in history, when the issue was closed by a commit keyword.
    pub closure: Option<&'a KeywordClosure>,
    /// The run's time, stamped on the recorded edit.
    pub now: Stamp,
}

/// Reopens and proposes a keyword closure while the ledger is open; leaves a done ticket alone.
pub fn reconcile_closing(view: &ClosingView<'_>) -> Reconciled {
    let mut out = Reconciled::default();
    let Some(closure) = view.closure else {
        return out;
    };
    if view.ledger_done {
        debug!(issue = %view.issue.0, "closing: ledger is done, keyword closure agrees");
        return out;
    }
    info!(issue = %view.issue.0, "closing: keyword closure while ledger is open, reopen and propose");
    out.reverts.push(Revert {
        field: STATE_FIELD.to_owned(),
        value: OPEN.to_owned(),
    });
    out.edits.push(Edit {
        tracker_event: closure.event.clone(),
        item: view.issue.0.clone(),
        field: STATE_FIELD.to_owned(),
        actor_id: closure.actor_id.to_string(),
        time: view.now,
        value: CLOSED.to_owned(),
    });
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run(ledger_done: bool, closure: Option<&KeywordClosure>) -> Reconciled {
        let issue = IssueRef("12".into());
        reconcile_closing(&ClosingView {
            issue: &issue,
            ledger_done,
            closure,
            now: Stamp::from_unix(1_000),
        })
    }

    fn closure() -> KeywordClosure {
        KeywordClosure {
            event: EventId("c1".into()),
            actor_id: 5,
        }
    }

    // frob:tests reconcile_closing
    #[test]
    fn keyword_closure_with_open_ledger_is_reopened_and_proposed() {
        let r = run(false, Some(&closure()));
        assert_eq!(r.reverts.len(), 1);
        assert_eq!(r.reverts[0].field, STATE_FIELD);
        assert_eq!(r.reverts[0].value, OPEN);
        assert_eq!(r.edits.len(), 1);
        assert_eq!(r.edits[0].value, CLOSED);
        assert_eq!(r.edits[0].tracker_event, EventId("c1".into()));
        assert_eq!(r.edits[0].actor_id, "5");
    }

    // frob:tests reconcile_closing
    #[test]
    fn keyword_closure_with_done_ledger_reverts_nothing() {
        assert_eq!(run(true, Some(&closure())), Reconciled::default());
    }

    // frob:tests reconcile_closing
    #[test]
    fn no_closure_is_quiet() {
        assert_eq!(run(false, None), Reconciled::default());
    }
}
