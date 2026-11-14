//! CONTENT004: a content key is defined in more than one `design/content/*.toml` file. Off when the project has no content files.

// frob:ticket 01M5H5P5KF5WHTPQVJ4WM2DDBN

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::content_files::duplicate_keys;
use crate::host::{CrunkHost, content_subjects, missing_content_inputs};

/// A content key defined in more than one content file.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CONTENT004",
    slug = "content-key-duplicate",
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
pub struct Content004;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Content004 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.content() else {
            return;
        };
        for (key, paths) in duplicate_keys(facts) {
            let Some(first) = facts.files.iter().find(|f| f.path == paths[0]) else {
                continue;
            };
            let message = format!(
                "content key '{key}' is defined in {} files: {}",
                paths.len(),
                paths.join(", "),
            );
            tracing::debug!(key = %key, files = paths.len(), "CONTENT004: duplicate key");
            out.fire_in(&first.path, first.offset_of_key(&key), message);
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_content_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Content004 {
    fn subjects(&self, host: &P) -> usize {
        content_subjects(host)
    }
}
