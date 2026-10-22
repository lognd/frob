//! CONTENT003: a scene references a copy key (`data-copy`, `data-copy-<attribute>`) that no content file defines. Off when the project has no scene documents.

// frob:ticket 01M4CXR96GDDX460SZZVAAWD0R

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::content_files::copy_refs;
use crate::host::{CrunkHost, missing_scene_doc_inputs, scene_doc_subjects};

/// A scene referencing a copy key no content file defines.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CONTENT003",
    slug = "content-key-undefined",
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
pub struct Content003;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Content003 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(docs) = host.scene_docs() else {
            return;
        };
        let defined = host.content();
        for file in &docs.files {
            for r in copy_refs(file) {
                if defined.is_some_and(|c| c.defines(&r.key)) {
                    continue;
                }
                let message = format!(
                    "copy key '{}' referenced by {} (line {}) is not defined in design/content/*.toml",
                    r.key,
                    file.element_label(r.offset),
                    r.line,
                );
                tracing::debug!(path = %file.path, key = %r.key, "CONTENT003: undefined key");
                out.fire_in(&file.path, r.offset, message);
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Content003 {
    fn subjects(&self, host: &P) -> usize {
        scene_doc_subjects(host)
    }
}
