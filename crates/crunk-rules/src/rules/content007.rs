//! CONTENT007: a content key one locale defines is missing from another locale. Off when the project has no content files.

// frob:ticket 01M5H5P5R4J2XAE0QABN6MVYC8

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::content_files::locale_gaps;
use crate::host::{CrunkHost, content_subjects, missing_content_inputs};

/// A content key missing from one locale that another locale defines.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CONTENT007",
    slug = "content-locale-gap",
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
pub struct Content007;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Content007 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.content() else {
            return;
        };
        for gap in locale_gaps(facts) {
            let Some(file) = facts.files.iter().find(|f| f.path == gap.path) else {
                continue;
            };
            let message = format!(
                "content key '{}' is defined for locale '{}' but missing from locale '{}'",
                gap.key, gap.defined_in, gap.locale,
            );
            tracing::debug!(key = %gap.key, locale = %gap.locale, "CONTENT007: key missing from locale");
            out.fire_in(&file.path, 0, message);
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_content_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Content007 {
    fn subjects(&self, host: &P) -> usize {
        content_subjects(host)
    }
}
