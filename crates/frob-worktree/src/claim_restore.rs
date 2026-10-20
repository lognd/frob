//! `frob claim restore ~X --reason TEXT`: put evicted work back as `ticket/<handle>` (`distributed-tickets.md` section 4.7).
//!
//! The decision is [`crate::evict::restore_plan`] and the push is
//! [`crate::evict::restore`]; this module gathers their inputs (the live
//! lease, the remote claim, the parked refs), maps every refusal to a coded
//! [`WorktreeError`], and records the restore as a note on the ticket.

// frob:ticket 01M5DN9Q57S88B7DQQH8BAXZ01

use frob_ledger::TicketId;
use frob_ledger::model::CommentSubtype;
use gob_diagnostics::{Refusal, RefusalClass};

use crate::claim::{remote_claim, sync_settings};
use crate::error::WorktreeError;
use crate::evict::{RestoreOutcome, RestoreRefusal, parked_refs, restore, restore_plan};
use crate::work::Workspace;

/// Refusal code when someone re-claimed the ticket before the restore.
pub const E_RESTORE_TAKEN: &str = "E-RESTORE-TAKEN";

/// Refusal code when no parked work exists for the ticket.
pub const E_RESTORE_NOTHING: &str = "E-RESTORE-NOTHING";

/// Refusal code when the remote cannot be reached; a restore needs it online.
pub const E_RESTORE_OFFLINE: &str = "E-RESTORE-OFFLINE";

/// Marker that starts the ticket note recording a restore.
const NOTE_MARKER: &str = "claim restored";

/// What a successful restore did.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Restored {
    /// Full ULID.
    pub id: TicketId,
    /// Handle with `~`.
    pub handle: String,
    /// The `parked/<handle>-<n>` branch the work came from.
    pub parked: String,
    /// The restored branch tip.
    pub tip: String,
}

/// The refusal for a [`RestoreRefusal`] on `handle`.
fn plan_refusal(why: RestoreRefusal, handle: &str) -> WorktreeError {
    match why {
        RestoreRefusal::EmptyReason => {
            WorktreeError::Usage("claim restore needs a non-empty --reason".to_owned())
        }
        RestoreRefusal::Taken(by) => WorktreeError::Refused(
            Refusal::new(
                E_RESTORE_TAKEN,
                RefusalClass::GuardNeedsAction,
                format!("{handle} was claimed again by {by}; it is too late to restore"),
            )
            .with_remedy(format!(
                "ask {by} to hand the ticket back, or start fresh with `frob work {handle} --from <parked branch>`"
            )),
        ),
        RestoreRefusal::NothingParked => WorktreeError::Refused(
            Refusal::new(
                E_RESTORE_NOTHING,
                RefusalClass::GuardNeedsAction,
                format!("{handle} has no parked work to restore"),
            )
            .with_remedy(format!("claim it normally with `frob work {handle}`")),
        ),
    }
}

/// The refusal for an unreachable remote.
fn offline(handle: &str, why: &str) -> WorktreeError {
    WorktreeError::Refused(
        Refusal::new(
            E_RESTORE_OFFLINE,
            RefusalClass::GuardNeedsAction,
            format!("cannot restore {handle} offline: {why}"),
        )
        .with_remedy("reconnect and rerun `frob claim restore`"),
    )
}

/// The ticket note recording that `parked` was restored for `reason`.
fn note_body(parked: &str, tip: &str, reason: &str) -> String {
    format!("{NOTE_MARKER} from {parked} at {tip}: {reason}")
}

impl Workspace<'_> {
    /// Restore the newest parked work of `ticket` as `ticket/<handle>` on the remote and note it on the ticket.
    ///
    /// # Errors
    /// A usage error without a reason; [`E_RESTORE_TAKEN`], [`E_RESTORE_NOTHING`]
    /// and [`E_RESTORE_OFFLINE`] refusals; ledger, lease and git failures.
    pub fn restore_claim(&self, ticket: &str, reason: &str) -> Result<Restored, WorktreeError> {
        let id = self.ledger.resolve(ticket)?;
        let handle = self.ledger.show(id)?.summary.handle;
        let bare = handle.trim_start_matches('~');
        let repo = self.ledger.repo();
        let (remote, timeout) = sync_settings(repo);
        let other = self.leases.live_lease(id)?.map(|l| l.holder.actor);
        let present = remote_claim(repo, &remote, &format!("ticket/{bare}"), timeout)?
            .map_err(|why| offline(&handle, &why))?
            .is_some();
        let parked =
            parked_refs(repo, &remote, bare, timeout)?.map_err(|why| offline(&handle, &why))?;
        let name = restore_plan(reason, other.as_deref(), present, &parked, bare)
            .map_err(|why| plan_refusal(why, &handle))?;
        match restore(repo, bare, &name)? {
            RestoreOutcome::Restored { tip } => {
                self.ledger
                    .comment(id, CommentSubtype::Note, &note_body(&name, &tip, reason))?;
                tracing::info!(ticket = %id, parked = %name, "claim restored and noted");
                Ok(Restored {
                    id,
                    handle,
                    parked: name,
                    tip,
                })
            }
            RestoreOutcome::Taken => Err(plan_refusal(
                RestoreRefusal::Taken("another clone".to_owned()),
                &handle,
            )),
            RestoreOutcome::Offline(why) => Err(offline(&handle, &why)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob-worktree/src/claim_restore.rs::plan_refusal
    #[test]
    fn refusals_carry_their_codes() {
        let code = |why| match plan_refusal(why, "~X") {
            WorktreeError::Refused(r) => format!("{}", r.code),
            other => other.to_string(),
        };
        assert_eq!(code(RestoreRefusal::NothingParked), E_RESTORE_NOTHING);
        assert_eq!(code(RestoreRefusal::Taken("b".into())), E_RESTORE_TAKEN);
        assert!(code(RestoreRefusal::EmptyReason).starts_with("usage:"));
    }

    // frob:tests crates/frob-worktree/src/claim_restore.rs::note_body
    #[test]
    fn note_names_source_tip_and_reason() {
        assert_eq!(
            note_body("parked/X-1", "abc", "oops"),
            "claim restored from parked/X-1 at abc: oops"
        );
    }
}
