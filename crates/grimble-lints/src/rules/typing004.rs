//! TYPING004: Network or file data cast to a declared type without validation.

// frob:ticket 01M4D95Q9WWPDZH86CMBMAZEDQ

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::TypingHost;

/// Network or file data cast to a declared type without validation.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TYPING004",
    slug = "unvalidated-boundary-cast",
    severity = Error,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = TypingHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Typing004;

impl<P: ?Sized + TypingHost> RepoRule<P> for Typing004 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + TypingHost> Measured<P> for Typing004 {
    fn subjects(&self, host: &P) -> usize {
        host.typing_subjects_of("TYPING004")
    }
}
