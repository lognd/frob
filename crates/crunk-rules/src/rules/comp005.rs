//! COMP005: a component binding whose node is not in the anatomy, whose state the component does not declare, or whose token no token file defines; also an anatomy node absent from the component's solved scene subtree. Off when the project has no component files.

// frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F

use crate::component_files::TokenLookup;
use crunk_ingest::scene::SceneNode;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::component_files::ComponentFile;
use crate::host::{CrunkHost, component_subjects, missing_component_inputs};

/// A component binding that points at nothing.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COMP005",
    slug = "binding-unresolved",
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
pub struct Comp005;

/// The component files of `host`, none when it has none.
fn components<P: ?Sized + CrunkHost>(host: &P) -> &[ComponentFile] {
    host.components().map_or(&[][..], |c| &c.files[..])
}

/// The scene node with `id` in the tree under `node` (itself included), if any.
fn find_node<'a>(node: &'a SceneNode, id: &str) -> Option<&'a SceneNode> {
    if node.id == id {
        return Some(node);
    }
    node.children.iter().find_map(|c| find_node(c, id))
}

/// Whether the tree under `node` (itself included) has a node with `id`.
fn subtree_has(node: &SceneNode, id: &str) -> bool {
    find_node(node, id).is_some()
}

/// The anatomy nodes of `file`'s component missing from its scene subtree, per scene that
/// renders the component (a scene node whose id is the component name); a scene without the
/// component is not a subject.
fn absent_from_subtrees<P: ?Sized + CrunkHost>(host: &P, file: &ComponentFile) -> Vec<String> {
    let c = &file.component;
    let Some(scenes) = host.scenes() else {
        return Vec::new();
    };
    let mut absent = Vec::new();
    for scene in &scenes.files {
        let Some(subtree) = find_node(&scene.scene.root, &c.name) else {
            continue;
        };
        for node in c.anatomy.nodes.iter().filter(|n| **n != c.name) {
            tracing::debug!(scene = %scene.path, component = %c.name, %node, "COMP005: anatomy node checked against subtree");
            if !subtree_has(subtree, node) {
                absent.push(format!(
                    "anatomy node '{}' is absent from the scene subtree of '{}' in {}",
                    c.node_id(node),
                    c.name,
                    scene.path
                ));
            }
        }
    }
    absent
}

impl<P: ?Sized + CrunkHost> RepoRule<P> for Comp005 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        for file in components(host) {
            for message in absent_from_subtrees(host, file) {
                tracing::debug!(path = %file.path, "COMP005: {message}");
                out.fire_in(&file.path, file.offset_of("[anatomy]"), message);
            }
        }
        let tokens = TokenLookup::new(host.spec(), host.tokens());
        for file in components(host) {
            let c = &file.component;
            for b in &c.bindings {
                let node = c.node_id(&b.node);
                let at = file.offset_of(&format!("node = \"{}\"", b.node));
                let mut problems: Vec<String> = Vec::new();
                if b.node != c.name && !c.anatomy.nodes.contains(&b.node) {
                    problems.push(format!("is not in the anatomy of '{}'", c.name));
                }
                if let Some(state) = &b.state
                    && !file.state_ids().any(|id| id == state)
                {
                    problems.push(format!("binds in undeclared state '{state}'"));
                }
                if let Some(token) = &b.token
                    && !tokens.is_empty()
                    && !tokens.knows(token)
                {
                    problems.push(format!("binds '{}' to unknown token '{token}'", b.property));
                }
                for problem in problems {
                    tracing::debug!(path = %file.path, %node, "COMP005: {problem}");
                    out.fire_in(&file.path, at, format!("node '{node}' {problem}"));
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_component_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Comp005 {
    fn subjects(&self, host: &P) -> usize {
        component_subjects(host)
    }
}
