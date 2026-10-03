//! The `TICK` rule family: ledger integrity rules evaluated over tickets.
//!
//! Ledger rules are repo-scope and run over the ledger, not over source
//! text, so each rule is a plain function returning [`Finding`]s. `frob-check`
//! wires them in: `TICK001` and `TICK003` come from [`crate::Ledger::doctor`],
//! `TICK002` takes ticket ids that `frob-check` extracted from `frob:ticket`
//! directives (that crate is not a dependency of this one).

use gob_rules::{Finding, Rule, RuleId, Severity};

use crate::error::Result;
use crate::id::TicketId;
use crate::ledger::Ledger;
use crate::model::{Frontmatter, Ticket};

/// A ticket's frontmatter differs from the fold of its events.
///
/// `ticket.md` is a cache of the events; when it disagrees (a hosting
/// provider's merge button skipped the merge driver, or a hand edit) the
/// events win. Run `frob ticket doctor --fix` to rewrite the frontmatter.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "TICK001",
    slug = "frontmatter-differs-from-fold",
    family = "TICK",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Deterministic,
    version = 1
)]
pub struct Tick001;

/// A ticket id is referenced but absent from the base ref.
///
/// A directive or trailer that names a ticket missing from the base branch
/// fails locally and in CI; push the ledger commit or fix the id.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "TICK002",
    slug = "ticket-not-on-base",
    family = "TICK",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    must_measure = true,
    version = 1
)]
pub struct Tick002;

/// A link or parent names a ticket that does not exist.
///
/// Remove the link with `frob ticket unlink`, or restore the ticket.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "TICK003",
    slug = "dangling-link",
    family = "TICK",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Tick003;

/// A committed ledger file holds an absolute home path.
///
/// `/home/<name>/`, `/Users/<name>/`, `/root/` and `C:\Users\<name>\` in a ledger file publish the local user name and
/// directory layout of everyone who pushes. `frob ticket doctor --fix` scrubs the paths in one new commit (history is
/// never rewritten); a hand edit to `~/` or a path relative to the repository parent clears the finding too.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "TICK004",
    slug = "absolute-home-path",
    family = "TICK",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Deterministic,
    version = 1
)]
pub struct Tick004;

pub(crate) fn id_of<R: Rule>(rule: &R) -> RuleId {
    rule.meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
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
        id_of(&Tick001),
        Severity::Error,
        None,
        format!(
            "ticket {id}: frontmatter differs from the fold of its events in {}; run `frob ticket doctor --fix`",
            fields.join(", ")
        ),
        &id.to_string(),
    ))
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
                id_of(&Tick002),
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
                id_of(&Tick003),
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
