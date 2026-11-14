//! CONTENT006: a content key's text uses a word or phrase that the `banned` list of `design/content/voice.toml` forbids. Off when the project has no content files or the voice file bans nothing.

// frob:ticket 01M5H5P5E98XTANP62H5TVTSC4

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::content_files::banned_hits;
use crate::host::{CrunkHost, content_subjects, missing_content_inputs};

/// A content key's text uses a word or phrase that the `banned` list of `design/content/voice.toml` forbids. Off when the project has no content files or the voice file bans nothing.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CONTENT006",
    slug = "tone-banned-word",
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
pub struct Content006;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Content006 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.content() else {
            return;
        };
        for hit in banned_hits(facts) {
            let message = format!(
                "content key '{}' uses '{}', which the voice file bans",
                hit.key, hit.found,
            );
            tracing::debug!(key = %hit.key, found = %hit.found, "CONTENT006: voice hit");
            out.fire_in(&hit.path, hit.offset, message);
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_content_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Content006 {
    fn subjects(&self, host: &P) -> usize {
        content_subjects(host)
    }
}
