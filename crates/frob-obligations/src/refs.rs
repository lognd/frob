//! REF001: `frob:ticket` and `frob:todo` directives (ULIDs or v1 aliases) that name no ticket of the ledger.

use gob_directives::frob::{Ticket, Todo};
use gob_directives::{Directive, DirectiveRecord};
use gob_rules::Finding;

use crate::rules::Ref001;
use crate::tickets::{Standing, Tickets};
use crate::util::finding;

/// REF001 over the `frob:ticket` and `frob:todo` directives of one file.
pub(crate) fn ref001(directives: &[&DirectiveRecord], tickets: &Tickets<'_>) -> Vec<Finding> {
    let mut out = Vec::new();
    for d in directives
        .iter()
        .filter(|d| d.namespace == "frob" && matches!(d.verb.as_str(), "ticket" | "todo"))
    {
        let id = if d.verb == "ticket" {
            Ticket::parse_args(&d.args).map(|t| t.id)
        } else {
            Todo::parse_args(&d.args).map(|t| t.id)
        };
        let Ok(id) = id else {
            continue;
        };
        let t = Ticket { id };
        match tickets.standing(&t.id) {
            Standing::Missing => out.push(finding(
                &Ref001,
                Some(d.span),
                format!(
                    "`frob:{} {}` names no ticket or v1 alias in the ledger; fix the id or file the ticket",
                    d.verb, t.id
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
