//! READ001: A walked file could not be read, so no rule examined it.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD
// frob:ticket 01M42M1KK02KFZG39CXKAD47SZ

use gob_rules::{Out, RepoRule, rule};

use crate::host::CheckHost;

/// A walked file could not be read, so no rule examined it.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "READ001",
    slug = "unreadable-file",
    severity = Warn,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CheckHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Read001;

gob_rules::list_in_registry!(Read001, "frob");

impl<P: ?Sized + CheckHost> RepoRule<P> for Read001 {
    /// The verdict is computed by the check pipeline (tools, perf, read); see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
