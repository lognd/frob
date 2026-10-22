//! COMP005: a component binding whose node is not in the anatomy, whose state the component does not declare, or whose token no token file defines. Off when the project has no component files.

// frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F

use crate::component_files::TokenLookup;
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

impl<P: ?Sized + CrunkHost> RepoRule<P> for Comp005 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
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
