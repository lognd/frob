//! CONTENT001: a scene writes copy inline (element text, or an alt/aria-label/title/placeholder attribute) instead of referencing a content key. Off when the project has no scene documents.

// frob:ticket 01M4CXR96GDDX460SZZVAAWD0R

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::content_files::{literal_copy, quote};
use crate::host::{CrunkHost, missing_scene_doc_inputs, scene_doc_subjects};

/// A scene carrying literal copy.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CONTENT001",
    slug = "content-literal-copy",
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
pub struct Content001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Content001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.scene_docs() else {
            return;
        };
        for file in &facts.files {
            for hit in literal_copy(file) {
                let what = match &hit.attribute {
                    Some(attr) => format!("{attr} attribute"),
                    None => "text".to_owned(),
                };
                let message = format!(
                    "literal copy \"{}\" in the {what} of {} (line {}): move it to a content key such as '{}' in design/content/*.toml and reference it with {}=\"{}\"",
                    quote(&hit.literal),
                    file.element_label(hit.offset),
                    hit.line,
                    hit.suggested_key,
                    hit.reference_attr,
                    hit.suggested_key,
                );
                tracing::debug!(path = %file.path, key = %hit.suggested_key, "CONTENT001: literal copy");
                out.fire_in(&file.path, hit.offset, message);
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Content001 {
    fn subjects(&self, host: &P) -> usize {
        scene_doc_subjects(host)
    }
}
