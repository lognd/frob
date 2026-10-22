//! COMP004: a component binding that carries a literal value instead of a token, binds nothing, or has a blank property. Off when the project has no component files.

// frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::component_files::ComponentFile;
use crate::host::{CrunkHost, component_subjects, missing_component_inputs};

/// A component binding that is not a token reference.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COMP004",
    slug = "literal-unbound",
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
pub struct Comp004;

/// The component files of `host`, none when it has none.
fn components<P: ?Sized + CrunkHost>(host: &P) -> &[ComponentFile] {
    host.components().map_or(&[][..], |c| &c.files[..])
}

impl<P: ?Sized + CrunkHost> RepoRule<P> for Comp004 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        for file in components(host) {
            let c = &file.component;
            for b in &c.bindings {
                let node = c.node_id(&b.node);
                let problem = match (&b.token, &b.value) {
                    (Some(_), None) if !b.property.trim().is_empty() => continue,
                    (Some(_), None) => "has a blank property".to_owned(),
                    (None, Some(v)) => format!(
                        "binds '{}' to the literal '{v}'; bind a token instead",
                        b.property
                    ),
                    (Some(t), Some(v)) => {
                        format!(
                            "binds '{}' to both token '{t}' and the literal '{v}'",
                            b.property
                        )
                    }
                    (None, None) => format!("binds '{}' to nothing", b.property),
                };
                let at = match &b.value {
                    Some(v) => file.offset_of(&format!("\"{v}\"")),
                    None => file.offset_of(&format!("node = \"{}\"", b.node)),
                };
                tracing::debug!(path = %file.path, %node, "COMP004: {problem}");
                out.fire_in(&file.path, at, format!("node '{node}' {problem}"));
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_component_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Comp004 {
    fn subjects(&self, host: &P) -> usize {
        component_subjects(host)
    }
}
