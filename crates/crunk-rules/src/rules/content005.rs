//! CONTENT005: a content key's text uses a glossary variant that `design/content/voice.toml` says to avoid. Off when the project has no content files or the voice file has no glossary.

// frob:ticket 01M5H5P5E98XTANP62H5TVTSC4

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::content_files::glossary_hits;
use crate::host::{CrunkHost, content_subjects, missing_content_inputs};

/// A content key's text uses a glossary variant that `design/content/voice.toml` says to avoid. Off when the project has no content files or the voice file has no glossary.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CONTENT005",
    slug = "glossary-term-avoided",
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
pub struct Content005;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Content005 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.content() else {
            return;
        };
        for hit in glossary_hits(facts) {
            let preferred = hit.preferred.as_deref().unwrap_or_default();
            let message = format!(
                "content key '{}' says '{}'; the glossary prefers '{preferred}'",
                hit.key, hit.found,
            );
            tracing::debug!(key = %hit.key, found = %hit.found, "CONTENT005: voice hit");
            out.fire_in(&hit.path, hit.offset, message);
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_content_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Content005 {
    fn subjects(&self, host: &P) -> usize {
        content_subjects(host)
    }
}
