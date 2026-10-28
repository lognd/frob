//! HUMAN001: a subject that needs a human review has none, or the review is stale (an input
//! changed since the ack), was recorded by someone off the allow-list, or (with `require_signed`)
//! was introduced by an unsigned commit or a key not listed for the reviewer. Advisory in
//! `crunk check`; the family's release severity makes it Error at the release gate.

// frob:ticket 01M4CXSM408E7A05DWKENDB7V4

use gob_rules::{Out, RepoRule, rule};

use crate::host::CrunkHost;
use crate::review::ReviewStatus;

/// A screen state whose human review is missing, stale or untrusted.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "HUMAN001",
    slug = "human-review-stale",
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
pub struct Human001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Human001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.reviews() else {
            return;
        };
        if let Some(why) = &facts.unreadable {
            tracing::warn!(%why, "HUMAN001: reviews cannot be judged");
            out.unresolved_in(
                "crunk.toml",
                0,
                format!("human reviews cannot be judged: {why}"),
            );
            return;
        }
        for f in facts
            .findings
            .iter()
            .filter(|f| !matches!(f.status, ReviewStatus::Current | ReviewStatus::Rejected(_)))
        {
            tracing::debug!(subject = %f.subject, "HUMAN001: review not current");
            out.fire_in("crunk.toml", 0, f.message.clone());
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        host.reviews()
            .is_none()
            .then(|| "no human review facts were gathered (no valid crunk.toml)".to_owned())
    }
}
