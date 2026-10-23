//! SYS003: Bindings contradict each other or an operand does not resolve.
//!
//! The end-owner kind (a flow end whose code another node owns) reports once per flow clause:
//! one wrong-owner unit keeps its per-unit message, several give one finding with the count,
//! the owners and a sample of at most three units. The per-unit rows stay in `check --json`.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// Bindings contradict each other or an operand does not resolve.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SYS003",
    slug = "sys-binding-conflict",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = BindHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Sys003;

impl<P: ?Sized + BindHost> RepoRule<P> for Sys003 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
