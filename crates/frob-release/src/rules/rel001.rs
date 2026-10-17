//! `REL001`: a product release tag that `frob release cut` did not make.

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use frob_ledger::{LedgerHost, evaluation_failed};
use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::rel001::{evaluate, not_applicable, recorded_cuts, repo_of};

/// A product release tag that `frob release cut` did not create, or that no longer matches its cut.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "REL001",
    slug = "release-without-cut",
    severity = Error,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    body = relay,
    fix = Manual,
    applies = project,
    host = LedgerHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Rel001;

/// The recorded cuts of the host's ledger; an absent ledger records none and an unreadable one is the rule's failure.
#[allow(
    clippy::result_large_err,
    reason = "the Err is the finding the rule emits, built once per run"
)]
fn cuts_of<P: ?Sized + LedgerHost>(host: &P) -> Result<Vec<frob_pm::event::CutData>, Finding> {
    match host.ledger_view().open("REL001")? {
        None => Ok(Vec::new()),
        Some(ledger) => recorded_cuts(ledger).map_err(|e| evaluation_failed("REL001", e)),
    }
}

impl<P: ?Sized + LedgerHost> RelayRule<P> for Rel001 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        let Some(repo) = repo_of(host.ledger_view().root) else {
            return Vec::new();
        };
        match cuts_of(host) {
            Ok(cuts) => evaluate(&repo, &cuts).findings,
            Err(finding) => vec![finding],
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        let Some(repo) = repo_of(host.ledger_view().root) else {
            return Some("no git work tree".to_owned());
        };
        // A failed cut read is applicable so REL001 reports it.
        let cuts = cuts_of(host).ok()?;
        not_applicable(&repo, &cuts)
    }
}
