//! REF001: `frob:ticket` directives that name no ticket of the ledger.

use gob_directives::frob::Ticket;
use gob_directives::{Directive, DirectiveRecord};
use gob_rules::Finding;

use crate::rules::Ref001;
use crate::tickets::{Standing, Tickets};
use crate::util::finding;

/// REF001 over the `frob:ticket` directives of one file.
pub(crate) fn ref001(directives: &[&DirectiveRecord], tickets: &Tickets<'_>) -> Vec<Finding> {
    let mut out = Vec::new();
    for d in directives
        .iter()
        .filter(|d| d.namespace == "frob" && d.verb == "ticket")
    {
        let Ok(t) = Ticket::parse_args(&d.args) else {
            continue;
        };
        match tickets.standing(&t.id) {
            Standing::Missing => out.push(finding(
                &Ref001,
                Some(d.span),
                format!(
                    "`frob:ticket {}` names no ticket in the ledger; fix the id or file the ticket",
                    t.id
                ),
                &t.id,
            )),
            Standing::Unknown => {
                tracing::debug!(ticket = %t.id, "REF001 undecided: no usable ledger");
            }
            Standing::Open | Standing::Terminal(_) => {}
        }
    }
    out
}
