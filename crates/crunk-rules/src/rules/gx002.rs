//! GX002: A focusable element in a scene that the pad cannot reach from the default selection. Off when the project has no scene documents.

// frob:ticket 01M4CXRSYQQW9C6D7K2Q2ZC9QM

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_doc_inputs, scene_doc_subjects};

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
        let Some(facts) = host.scene_docs() else {
            return;
        };
        for file in &facts.files {
            let graph = file.focus_graph();
            for n in graph.unreachable() {
                let node = &graph.nodes[n];
                let message = format!(
                    "{} (line {}) cannot be reached by the pad from the default selection: give a neighbour a data-nav-* move to it, or put it in document order inside a focus group",
                    node.label, node.line
                );
                tracing::debug!(path = %file.path, node = %node.label, "GX002: unreachable focusable");
                out.fire_in(&file.path, node.offset, message);
            }
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
