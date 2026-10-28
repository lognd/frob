//! HUMAN002: a subject whose current human review rejects it. The rejection stands until an input
//! changes or a reviewer records an approval; Advisory in `crunk check`, Error at the release gate.

// frob:ticket 01M4CXSM408E7A05DWKENDB7V4

use gob_rules::{Out, RepoRule, rule};

use crate::host::CrunkHost;
use crate::review::ReviewStatus;

/// A screen state a human reviewer rejected.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "HUMAN002",
    slug = "human-review-rejected",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Human002;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Human002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.reviews() else {
            return;
        };
        for f in facts
            .findings
            .iter()
            .filter(|f| matches!(f.status, ReviewStatus::Rejected(_)))
        {
            tracing::debug!(subject = %f.subject, "HUMAN002: review rejects the subject");
            out.fire_in("crunk.toml", 0, f.message.clone());
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        host.reviews()
            .is_none()
            .then(|| "no human review facts were gathered (no valid crunk.toml)".to_owned())
    }
}
