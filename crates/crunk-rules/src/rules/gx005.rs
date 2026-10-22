//! GX005: A focus attribute (data-nav-*, data-focus-wrap, data-focus-axis) that names nothing usable. Off when the project has no scene documents.

// frob:ticket 01M4CXRSYQQW9C6D7K2Q2ZC9QM

use crunk_layout::InvalidReason;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_doc_inputs, scene_doc_subjects};

/// A focus attribute (data-nav-*, data-focus-wrap, data-focus-axis) that names nothing usable.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "GX005",
    slug = "focus-nav-invalid",
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
pub struct Gx005;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Gx005 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.scene_docs() else {
            return;
        };
        for file in &facts.files {
            let graph = file.focus_graph();
            for bad in &graph.invalid {
                let what = match &bad.reason {
                    InvalidReason::UnknownTarget(id) => {
                        format!("names data-id '{id}', which no element has")
                    }
                    InvalidReason::UnfocusableTarget(id) => {
                        format!("names '{id}', which is not an enabled focusable element")
                    }
                    InvalidReason::BadWrap(v) => format!("has the value '{v}'; use wrap or clamp"),
                    InvalidReason::BadAxis(v) => {
                        format!("has the value '{v}'; use vertical or horizontal")
                    }
                };
                let message = format!(
                    "{} (line {}): {} {what}",
                    bad.label, bad.line, bad.attribute
                );
                tracing::debug!(path = %file.path, attribute = %bad.attribute, "GX005: invalid focus attribute");
                out.fire_in(&file.path, bad.offset, message);
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Gx005 {
    fn subjects(&self, host: &P) -> usize {
        scene_doc_subjects(host)
    }
}
