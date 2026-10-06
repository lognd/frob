//! The consumer-side view of the `gob.sibling/1` document: the typed reader lives in
//! `gob_check::sibling` (one owner of the contract); only the ticket-bound exception view is frob's.

use frob_obligations::SiblingException;
pub(super) use gob_check::sibling::{Doc, DocException, DocFinding, DocSuppressed, Envelope, Sev};

/// The ticket-bound view of `e`, with the findings it parked, or `None` without a ticket.
pub(super) fn bound(
    e: &DocException,
    product: &str,
    suppressed: &[DocSuppressed],
) -> Option<SiblingException> {
    let ticket = e.ticket.clone()?;
    let parks = suppressed
        .iter()
        .filter(|s| s.exception == e.id)
        .map(|s| {
            format!(
                "{} {}",
                s.finding.rule,
                s.finding
                    .fingerprint
                    .get(..12)
                    .unwrap_or(&s.finding.fingerprint)
            )
        })
        .collect();
    Some(SiblingException {
        product: product.to_owned(),
        id: e.id.clone(),
        kind: e.kind.clone(),
        rule: e.rule.clone(),
        file: e.file.clone(),
        line: e.line,
        ticket,
        parks,
    })
}
