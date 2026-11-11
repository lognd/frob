//! `TODO002`: a `frob:todo` directive points at a ticket that is already done or dropped.

// frob:ticket 01M561ZF9TSJF59M2CAXW3KTP0

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::ObligationHost;
use crate::tickets::Tickets;
use crate::todo;

/// A `frob:todo` directive points at a ticket that is already done or dropped.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TODO002",
    slug = "todo-ticket-terminal",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = ObligationHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Todo002;

impl<P: ?Sized + ObligationHost> RepoRule<P> for Todo002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let inputs = host.obligations();
        let tickets = Tickets::new(inputs.ledger);
        todo::todo002(inputs.directives, &tickets, inputs.files, out);
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        let Some(view) = host.ledger_facts() else {
            return Some("the product keeps no ticket ledger".to_owned());
        };
        if view.missing.is_some() {
            // The absent ledger is reported once by TICK001, not as zero-subject verdicts.
            return Some("ledger ref is absent".to_owned());
        }
        let referenced = host
            .obligations()
            .directives
            .iter()
            .any(|d| d.namespace == "frob" && d.verb == "todo");
        // Nothing to resolve without a ledger to resolve against or a `frob:todo` to resolve.
        (!(view.configured && referenced)).then(|| "nothing to resolve against a ledger".to_owned())
    }
}

impl<P: ?Sized + ObligationHost> Measured<P> for Todo002 {
    fn subjects(&self, host: &P) -> usize {
        host.ledger_facts().map_or(0, |view| view.tickets)
    }
}
