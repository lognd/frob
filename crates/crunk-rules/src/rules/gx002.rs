//! GX002: A focusable element in a scene that the pad cannot reach from the default selection. Off when the project has no scene documents.

// frob:ticket 01M4CXRSYQQW9C6D7K2Q2ZC9QM

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_doc_inputs, scene_doc_subjects};
use crate::scene_docs::focus_findings;

/// A focusable element in a scene that the pad cannot reach from the default selection.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "GX002",
    slug = "focus-unreachable",
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
pub struct Gx002;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Gx002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        // frob:ticket 01M5HA924E3PTBVH6J8EBXP7XW
        let findings = focus_findings(
            host,
            "GX002",
            |g| g.unreachable(),
            |node| {
                format!(
                    "{} (line {}) cannot be reached by the pad from the default selection: give a neighbour a data-nav-* move to it, or put it in document order inside a focus group",
                    node.label, node.line
                )
            },
            |a| a.unreachable_scenes(),
            |name| {
                format!(
                    "scene '{name}' cannot be reached by the pad: no flow transition leads to it from an entry scene; add a flow edge into this screen"
                )
            },
        );
        for (path, offset, message) in findings {
            out.fire_in(&path, offset, message);
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Gx002 {
    fn subjects(&self, host: &P) -> usize {
        scene_doc_subjects(host)
    }
}
