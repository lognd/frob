//! REF001: `frob:ticket` and `frob:todo` directives (ULIDs or v1 aliases) that name no ticket of the ledger.

use gob_directives::frob::{Ticket, Todo};
use gob_directives::{Directive, DirectiveRecord};
use gob_rules::Finding;

use crate::legacy::Ref001;
use crate::tickets::{Standing, Tickets};
use crate::util::finding;

/// The ticket id a `frob:ticket` or `frob:todo` directive names, `None` for any other or malformed directive.
fn referenced_id(d: &DirectiveRecord) -> Option<String> {
    if d.namespace != "frob" {
        return None;
    }
    match d.verb.as_str() {
        "ticket" => Ticket::parse_args(&d.args).ok().map(|t| t.id),
        "todo" => Todo::parse_args(&d.args).ok().map(|t| t.id),
        _ => None,
    }
}

/// Every `(file, id)` reference whose standing is neither open nor terminal (missing or undecidable).
///
/// REF001 of a file depends on the ledger only through these ids: a reference to an open or
/// terminal ticket never fires, so the set (and nothing else) is the file's cache side input.
pub fn unsettled_ticket_refs(
    directives: &[DirectiveRecord],
    ledger: Option<&frob_ledger::Ledger>,
) -> Vec<(gob_text::FileId, String)> {
    let tickets = Tickets::new(ledger);
    let mut out: Vec<(gob_text::FileId, String)> = directives
        .iter()
        .filter_map(|d| referenced_id(d).map(|id| (d.span.file, id)))
        .filter(|(_, id)| !matches!(tickets.standing(id), Standing::Open | Standing::Terminal(_)))
        .collect();
    out.sort();
    out.dedup();
    tracing::debug!(
        unsettled = out.len(),
        "ticket references outside open/terminal standing"
    );
    out
}

/// REF001 over the `frob:ticket` and `frob:todo` directives of one file.
pub(crate) fn ref001(directives: &[&DirectiveRecord], tickets: &Tickets<'_>) -> Vec<Finding> {
    let mut out = Vec::new();
    for d in directives {
        let Some(id) = referenced_id(d) else {
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
