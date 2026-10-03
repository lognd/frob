//! Ticket-bound exits of a sibling product's exceptions (`exceptions.md`, decision D28).
//!
//! A sibling (grimble) carries `ticket=` opaquely; only frob owns the ledger, so
//! only frob decides whether the ticket exists (`EXC007`) or is already done
//! (`EXC003`). The sibling's own decision to park a finding stands, and the EXC
//! finding is what fails the gate, once (`sibling-contract.md` section 5).

use std::path::Path;

use frob_ledger::Ledger;
use gob_rules::Finding;
use gob_text::{FileInterner, LineCol, LineIndex, Span, TextRange};

use crate::rules::{Exc003, Exc007};
use crate::tickets::{Standing, Tickets};
use crate::util::finding;

/// One sibling exception that names a ticket, as read from the sibling document.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SiblingException {
    /// The product that wrote it (`grimble`).
    pub product: String,
    /// The exception id the sibling assigned.
    pub id: String,
    /// The kind (`accept`, `defer`, `hotfix`, `baseline`), for the message.
    pub kind: String,
    /// The excepted rule id.
    pub rule: String,
    /// Repository-relative file the exception is written in, when it has one.
    pub file: Option<String>,
    /// 1-based line of the exception, when it has one.
    pub line: Option<u32>,
    /// The `ticket=` value, verbatim.
    pub ticket: String,
    /// The suppressed findings it parks, as `RULE fingerprint` labels.
    pub parks: Vec<String>,
}

/// The span of the start of `line` in `file` under `root`, interning the path.
fn span_at(root: &Path, files: &mut FileInterner, file: &str, line: Option<u32>) -> Option<Span> {
    let text = std::fs::read_to_string(root.join(file)).ok()?;
    let index = LineIndex::new(&text).ok()?;
    let start = index.offset(LineCol {
        line: line.unwrap_or(1),
        col: 1,
    })?;
    Some(Span::new(files.intern(file), TextRange::empty(start)))
}

/// `EXC003` and `EXC007` for the ticket-bound `exceptions` of a sibling, resolved through `ledger`.
///
/// Findings are located at the exception's file and line when readable under `root`,
/// else spanless; each names the suppressed findings so the result reads against them.
/// Without a ledger the question cannot be decided and nothing is raised.
pub fn sibling_exception_findings(
    root: &Path,
    ledger: Option<&Ledger>,
    exceptions: &[SiblingException],
    files: &mut FileInterner,
) -> Vec<Finding> {
    let tickets = Tickets::new(ledger);
    let mut out = Vec::new();
    for e in exceptions {
        let standing = tickets.standing(&e.ticket);
        let parks = if e.parks.is_empty() {
            "it parks no finding".to_owned()
        } else {
            format!("it parks {}", e.parks.join(", "))
        };
        let at = |files: &mut FileInterner| {
            e.file
                .as_deref()
                .and_then(|f| span_at(root, files, f, e.line))
        };
        let anchor = format!("{}:{}:{}", e.product, e.id, e.rule);
        match standing {
            Standing::Missing => {
                tracing::info!(product = %e.product, exception = %e.id, ticket = %e.ticket, "EXC007 on sibling exception");
                let span = at(files);
                out.push(finding(
                    &Exc007,
                    span,
                    format!(
                        "{} `{} {}` names ticket {}, which does not exist; fix the id or file the ticket ({parks})",
                        e.product, e.kind, e.rule, e.ticket
                    ),
                    &anchor,
                ));
            }
            Standing::Terminal(outcome) => {
                tracing::info!(product = %e.product, exception = %e.id, ticket = %e.ticket, %outcome, "EXC003 on sibling exception");
                let span = at(files);
                out.push(finding(
                    &Exc003,
                    span,
                    format!(
                        "{} `{} {}` names ticket {}, which is already done ({outcome}); pay the debt or re-point the exception ({parks})",
                        e.product, e.kind, e.rule, e.ticket
                    ),
                    &anchor,
                ));
            }
            Standing::Open | Standing::Unknown => {
                tracing::debug!(exception = %e.id, ticket = %e.ticket, "sibling exception exit holds");
            }
        }
    }
    out
}
