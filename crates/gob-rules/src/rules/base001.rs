//! BASE001: a baseline table gained a key or changed its ticket against the base tip.

// frob:ticket 01M5XMJH35MV9Z2PFF27FDF275

use crate::baseline::{BASELINE_FILE, growth};
use crate::decl::{Measured, Out, RepoRule};
use crate::rule;

use super::BaselineHost;

/// A baseline table that grew or changed ticket without `frob baseline adopt`.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "BASE001",
    slug = "baseline-grew",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = BaselineHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Base001;

impl<P: ?Sized + BaselineHost> RepoRule<P> for Base001 {
    /// Fail every table of the head baseline that gained a key or changed ticket versus the base.
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(head), Some(base)) = (host.baseline_head(), host.baseline_base()) else {
            return;
        };
        for g in growth(base, head) {
            if !g.added.is_empty() {
                out.fire_in(
                    BASELINE_FILE,
                    0,
                    format!(
                        "baseline for {} grew by {} key(s) against the base tip; keys are only added by `frob baseline adopt`, fix the finding instead",
                        g.rule,
                        g.added.len()
                    ),
                );
            }
            if let Some((was, now)) = g.ticket_changed {
                out.fire_in(
                    BASELINE_FILE,
                    0,
                    format!(
                        "baseline for {} changed its ticket from {was} to {now} against the base tip",
                        g.rule
                    ),
                );
            }
        }
    }
}

impl<P: ?Sized + BaselineHost> Measured<P> for Base001 {
    /// Subjects are the head tables compared.
    fn subjects(&self, host: &P) -> usize {
        host.baseline_head().map_or(0, |b| b.rules.len())
    }
}
