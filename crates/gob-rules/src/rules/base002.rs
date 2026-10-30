//! BASE002: a baseline table whose burn-down ticket is not live.

// frob:ticket 01M5XMJH35MV9Z2PFF27FDF275

use crate::baseline::{BASELINE_FILE, BaselineHost, TicketLife, dead_tables};
use crate::decl::{Measured, Out, RepoRule};
use crate::rule;

/// A baseline table whose ticket is closed or dropped without a successor.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "BASE002",
    slug = "baseline-ticket-dead",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = BaselineHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Base002;

impl<P: ?Sized + BaselineHost> RepoRule<P> for Base002 {
    /// Fail every table whose ticket is dead; report Unresolved when the ledger cannot say.
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(head) = host.baseline_head() else {
            return;
        };
        for (rule, ticket, life) in dead_tables(head, |t| host.ticket_life(t)) {
            match life {
                TicketLife::Dead => out.fire_in(
                    BASELINE_FILE,
                    0,
                    format!(
                        "baseline for {rule} names ticket {ticket}, which is closed or dropped without a successor; point it at a live burn-down ticket or fix the findings"
                    ),
                ),
                _ => out.unresolved_in(
                    BASELINE_FILE,
                    0,
                    format!("baseline for {rule}: ticket {ticket} could not be looked up"),
                ),
            }
        }
    }
}

impl<P: ?Sized + BaselineHost> Measured<P> for Base002 {
    /// Subjects are the head tables whose ticket was judged.
    fn subjects(&self, host: &P) -> usize {
        host.baseline_head().map_or(0, |b| b.rules.len())
    }
}
