//! The `TICK` check functions: ledger integrity checks evaluated over tickets.
//!
//! The rule declarations live in `src/rules/`; this module holds the plain functions returning
//! [`Finding`]s that they and the ledger doctor share. `TICK001` and `TICK003` come from
//! [`crate::Ledger::doctor`], `TICK002` takes ticket ids that `frob-check` extracted from
//! `frob:ticket` directives (that crate is not a dependency of this one).

use gob_rules::{Finding, RuleDecl, RuleId, Severity};

use crate::error::Result;
use crate::id::TicketId;
use crate::ledger::Ledger;
use crate::model::{Frontmatter, Ticket};
use crate::rules::{tick001::Tick001, tick002::Tick002, tick003::Tick003};

/// The typed id of the declared rule `R`.
pub(crate) fn id_of<R: RuleDecl>() -> RuleId {
    R::DEF
        .id
        .parse()
        .unwrap_or_else(|e| unreachable!("the rule macro validates the id: {e}"))
}

/// Names of the document fields in which `a` and `b` differ (`body` included).
pub fn differing_fields(a: &Ticket, b: &Ticket) -> Vec<String> {
    let to_map = |t: &Ticket| match serde_json::to_value(&t.front) {
        Ok(serde_json::Value::Object(m)) => m,
        _ => serde_json::Map::new(),
    };
    let (ma, mb) = (to_map(a), to_map(b));
    let mut keys: Vec<&String> = ma.keys().chain(mb.keys()).collect();
    keys.sort();
    keys.dedup();
    let mut out: Vec<String> = keys
        .into_iter()
        .filter(|k| ma.get(*k) != mb.get(*k))
        .cloned()
        .collect();
    if a.body != b.body {
        out.push("body".to_owned());
    }
    out
}

/// `TICK001`: a finding when `stored` differs from `folded`.
pub fn tick001(id: TicketId, folded: &Ticket, stored: &Ticket) -> Option<Finding> {
    let fields = differing_fields(folded, stored);
    if fields.is_empty() {
        return None;
    }
    Some(Finding::new(
        id_of::<Tick001>(),
        Severity::Error,
        None,
        format!(
            "ticket {id}: frontmatter differs from the fold of its events in {}; run `frob ticket doctor --fix`",
            fields.join(", ")
        ),
        &id.to_string(),
    ))
}

/// `TICK001`: a finding for a `ticket.md` that cannot be parsed although its events fold.
pub fn tick001_unreadable(id: TicketId, error: &str) -> Finding {
    Finding::new(
        id_of::<Tick001>(),
        Severity::Error,
        None,
        format!(
            "ticket {id}: ticket.md is unreadable ({error}); run `frob ticket doctor --fix` to re-render it from its events"
        ),
        &id.to_string(),
    )
}

/// `TICK002`: a finding for each of `ids` that has no ticket on `base_ref`.
///
/// `ids` are strings as found in tracked text; an abbreviated or malformed
/// id is reported too, since only full ULIDs are persisted (decision D24).
///
/// # Errors
///
/// Git failures other than an unresolvable `base_ref`, which counts as no tickets.
pub fn tick002(ids: &[&str], base_ref: &str, ledger: &Ledger) -> Result<Vec<Finding>> {
    let mut findings = Vec::new();
    for raw in ids {
        let present = match raw.parse::<TicketId>() {
            Ok(id) => ledger.ticket_exists_at(base_ref, &id.to_string())?,
            Err(_) => false,
        };
        if !present {
            findings.push(Finding::new(
                id_of::<Tick002>(),
                Severity::Error,
                None,
                format!("ticket `{raw}` is not present on {base_ref}; push the ledger commit or use the full ULID of an existing ticket"),
                raw,
            ));
        }
    }
    Ok(findings)
}

/// `TICK003`: a finding for each link or parent of `front` whose target `exists` rejects.
pub fn tick003(front: &Frontmatter, exists: &dyn Fn(TicketId) -> bool) -> Vec<Finding> {
    let targets = front
        .links
        .iter()
        .map(|l| (l.kind.as_str(), l.target))
        .chain(front.parent.map(|p| ("parent", p)));
    targets
        .filter(|(_, t)| !exists(*t))
        .map(|(kind, t)| {
            Finding::new(
                id_of::<Tick003>(),
                Severity::Error,
                None,
                format!(
                    "ticket {}: {kind} link points at {t}, which does not exist",
                    front.id
                ),
                &front.id.to_string(),
            )
        })
        .collect()
}
