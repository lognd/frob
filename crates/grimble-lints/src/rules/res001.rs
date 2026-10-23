//! RES001: An acquire call (timer, listener, mark, map entry, object URL) with no paired release in its scope.

// frob:ticket 01M4MGE2XKGBNJEV1AECPBVHQF

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::ResHost;

/// An acquire call (timer, listener, mark, map entry, object URL) with no paired release in its scope.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "RES001",
    slug = "unpaired-resource-acquisition",
    severity = Warn,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = ResHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Res001;

impl<P: ?Sized + ResHost> RepoRule<P> for Res001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + ResHost> Measured<P> for Res001 {
    fn subjects(&self, host: &P) -> usize {
        host.res_subjects_of("RES001")
    }
}
