//! CONTENT002: a content key's text is longer than its `max_chars` budget. Off when the project has no content files.

// frob:ticket 01M4CXR96GDDX460SZZVAAWD0R

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, content_subjects, missing_content_inputs};

/// A copy key whose text is longer than its `max_chars` budget.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CONTENT002",
    slug = "content-over-budget",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Content002;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Content002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.content() else {
            return;
        };
        for file in &facts.files {
            for key in &file.content.keys {
                let Some(budget) = key.max_chars else {
                    continue;
                };
                let len = key.text.chars().count();
                if len as u64 > u64::from(budget) {
                    let message = format!(
                        "copy key '{}' is {len} characters, over its budget of {budget} (by {})",
                        key.id,
                        len as u64 - u64::from(budget),
                    );
                    tracing::debug!(path = %file.path, key = %key.id, len, budget, "CONTENT002: over budget");
                    out.fire_in(&file.path, file.offset_of_key(&key.id), message);
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_content_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Content002 {
    fn subjects(&self, host: &P) -> usize {
        content_subjects(host)
    }
}
