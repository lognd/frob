//! GX004: A scene with no, a dead or more than one default selection. Off when the project has no scene documents.

// frob:ticket 01M4CXRSYQQW9C6D7K2Q2ZC9QM

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_doc_inputs, scene_doc_subjects};

/// A scene with no, a dead or more than one default selection.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "GX004",
    slug = "focus-default",
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
pub struct Gx004;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Gx004 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.scene_docs() else {
            return;
        };
        for file in &facts.files {
            let graph = file.focus_graph();
            for &i in &graph.dead_defaults {
                let el = &file.doc.elements[i];
                let message = format!(
                    "data-focus-default is on {} (line {}), which is not focusable or is disabled: move it to an enabled control",
                    file.element_label(el.offset),
                    el.line
                );
                tracing::debug!(path = %file.path, "GX004: default on a dead element");
                out.fire_in(&file.path, el.offset, message);
            }
            if graph.nodes.is_empty() {
                continue;
            }
            if graph.defaults.is_empty() {
                let first = &graph.nodes[0];
                let message = format!(
                    "the scene marks no data-focus-default: mark the control selected on open (the pad would start on {}, line {})",
                    first.label, first.line
                );
                tracing::debug!(path = %file.path, "GX004: no default selection");
                out.fire_in(&file.path, first.offset, message);
            }
            for &n in graph.defaults.iter().skip(1) {
                let node = &graph.nodes[n];
                let message = format!(
                    "{} (line {}) is a second data-focus-default: a scene selects exactly one control on open",
                    node.label, node.line
                );
                tracing::debug!(path = %file.path, node = %node.label, "GX004: multiple defaults");
                out.fire_in(&file.path, node.offset, message);
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Gx004 {
    fn subjects(&self, host: &P) -> usize {
        scene_doc_subjects(host)
    }
}
