//! Ledger lookups with a per-evaluation cache.

use std::cell::RefCell;
use std::collections::HashMap;

use frob_ledger::{Ledger, LedgerError};

/// What the ledger says about a ticket reference.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum Standing {
    /// The reference resolves to no ticket.
    Missing,
    /// The ticket exists and is not terminal.
    Open,
    /// The ticket is done (any outcome, dropped included); carries the outcome text.
    Terminal(String),
    /// No ledger, or the ledger failed: the question cannot be decided.
    Unknown,
}

/// Resolves ticket references through an optional ledger, remembering answers.
pub(crate) struct Tickets<'a> {
    ledger: Option<&'a Ledger>,
    cache: RefCell<HashMap<String, Standing>>,
}

impl<'a> Tickets<'a> {
    /// A resolver over `ledger`; without one every answer is [`Standing::Unknown`].
    pub(crate) fn new(ledger: Option<&'a Ledger>) -> Self {
        Self {
            ledger,
            cache: RefCell::new(HashMap::new()),
        }
    }

    /// The standing of `input` (a full ULID, `~handle` or alias).
    pub(crate) fn standing(&self, input: &str) -> Standing {
        let Some(ledger) = self.ledger else {
            return Standing::Unknown;
        };
        if let Some(hit) = self.cache.borrow().get(input) {
            return hit.clone();
        }
        let found = match ledger.resolve(input) {
            Ok(id) => match ledger.show(id) {
                Ok(view) if view.summary.category.is_terminal() => Standing::Terminal(
                    view.summary
                        .outcome
                        .map_or_else(|| "done".to_owned(), |o| o.as_str().to_owned()),
                ),
                Ok(_) => Standing::Open,
                Err(err) => {
                    tracing::warn!(ticket = input, %err, "ticket unreadable; standing unknown");
                    Standing::Unknown
                }
            },
            Err(LedgerError::NotFound { .. }) => Standing::Missing,
            Err(LedgerError::Ambiguous { .. }) => Standing::Open,
            Err(err) => {
                tracing::warn!(ticket = input, %err, "ticket lookup failed; standing unknown");
                Standing::Unknown
            }
        };
        tracing::debug!(ticket = input, standing = ?found, "ticket looked up");
        self.cache
            .borrow_mut()
            .insert(input.to_owned(), found.clone());
        found
    }
}
