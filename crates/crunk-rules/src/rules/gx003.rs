//! GX003: A focusable element that the pad can reach but not leave for the default selection. Off when the project has no scene documents.

// frob:ticket 01M4CXRSYQQW9C6D7K2Q2ZC9QM

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_doc_inputs, scene_doc_subjects};
use crate::scene_docs::focus_findings;

/// A focusable element that the pad can reach but not leave for the default selection.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "GX003",
    slug = "focus-trap",
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
pub struct Gx003;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Gx003 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        // frob:ticket 01M5HA924E3PTBVH6J8EBXP7XW
        let findings = focus_findings(
            host,
            "GX003",
            |g| g.traps(),
            |node| {
                format!(
                    "{} (line {}) is a focus trap: once the pad lands there no move leads back to the default selection; add a data-nav-* move out, or wrap the group",
                    node.label, node.line
                )
            },
            |a| a.stranded_scenes(),
            |name| {
                format!(
                    "scene '{name}' is a focus trap across screens: the flow leaves it only for scenes that never lead back to an entry; add a flow edge back out"
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

impl<P: ?Sized + CrunkHost> Measured<P> for Gx003 {
    fn subjects(&self, host: &P) -> usize {
        scene_doc_subjects(host)
    }
}
