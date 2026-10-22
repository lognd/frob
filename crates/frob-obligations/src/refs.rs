//! REF001: `frob:ticket` and `frob:todo` directives (ULIDs or v1 aliases) that name no ticket of the ledger.

use gob_directives::frob::{Ticket, Todo};
use gob_directives::{Directive, DirectiveRecord, Dsl002, is_v1_alias};
use gob_rules::{Applicability, Finding, Fix, FixKind, TextEdit};

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
        .filter(|(_, id)| {
            is_v1_alias(id)
                || !matches!(tickets.standing(id), Standing::Open | Standing::Terminal(_))
        })
        .map(
            |(file, id)| match tickets.canonical(&id).filter(|_| is_v1_alias(&id)) {
                // DSL002 rewrites an alias to its ULID, so the file depends on what the alias resolves to.
                Some(ulid) => (file, format!("{id}=>{ulid}")),
                None => (file, id),
            },
        )
        .collect();
    out.sort();
    out.dedup();
    tracing::debug!(
        unsettled = out.len(),
        "ticket references outside open/terminal standing"
    );
    out
}

/// DSL002 over the `frob:ticket` and `frob:todo` directives that write a v1 alias (`T-0042`).
///
/// An alias the ledger resolves to exactly one ticket carries a Machine fix rewriting it to the full
/// ULID; an alias it resolves to several tickets is reported without one. An alias it does not know is
/// left to REF001, and without a ledger nothing is decided.
// frob:ticket 01M4FG41QM8F4BG9CTMJSMN4BH
pub(crate) fn dsl002_aliases(
    directives: &[&DirectiveRecord],
    tickets: &Tickets<'_>,
) -> Vec<Finding> {
    let mut out = Vec::new();
    for d in directives {
        let Some(id) = referenced_id(d).filter(|id| is_v1_alias(id)) else {
            continue;
        };
        let Some(token) = d.args.positional.first() else {
            continue;
        };
        match tickets.standing(&id) {
            Standing::Missing | Standing::Unknown => continue,
            Standing::Open | Standing::Terminal(_) => {}
        }
        let (message, fix) = match tickets.canonical(&id) {
            Some(ulid) => (
                format!(
                    "`frob:{} {id}` carries a v1 alias; only full 26-char ULIDs persist (D24), `--fix` rewrites it to `{ulid}`",
                    d.verb
                ),
                Some(Fix {
                    kind: FixKind::Deterministic,
                    applicability: Applicability::Machine,
                    title: format!("replace `{id}` with the ticket ULID"),
                    edits: vec![TextEdit {
                        file: d.span.file,
                        range: token.range,
                        replacement: ulid,
                    }],
                }),
            ),
            None => (
                format!(
                    "`frob:{} {id}` carries a v1 alias that names several tickets; replace it with the full ULID of the right one",
                    d.verb
                ),
                None,
            ),
        };
        let mut f = finding(&Dsl002, Some(d.span), message, &id);
        f.fix = fix;
        out.push(f);
    }
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
