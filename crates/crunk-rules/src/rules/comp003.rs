//! COMP003: a component that declares no states, or a state with a blank or repeated id. Off when the project has no component files.

// frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F

use gob_rules::{Measured, Out, RepoRule, rule};
use std::collections::HashSet;

use crate::component_files::ComponentFile;
use crate::host::{CrunkHost, component_subjects, missing_component_inputs};

/// A component state list that is empty, blank or repeated.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COMP003",
    slug = "states-invalid",
    severity = Warn,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Comp003;

/// The component files of `host`, none when it has none.
fn components<P: ?Sized + CrunkHost>(host: &P) -> &[ComponentFile] {
    host.components().map_or(&[][..], |c| &c.files[..])
}

impl<P: ?Sized + CrunkHost> RepoRule<P> for Comp003 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        for file in components(host) {
            let c = &file.component;
            if c.states.is_empty() {
                out.fire_in(
                    &file.path,
                    file.offset_of("name"),
                    format!(
                        "component '{}' (node '{}') declares no states",
                        c.name, c.name
                    ),
                );
                continue;
            }
            let mut seen: HashSet<&str> = HashSet::new();
            for state in &c.states {
                let problem = if state.id.trim().is_empty() {
                    "has a state with a blank id".to_owned()
                } else if !seen.insert(state.id.as_str()) {
                    format!("declares state '{}' more than once", state.id)
                } else {
                    continue;
                };
                tracing::debug!(path = %file.path, state = %state.id, "COMP003: {problem}");
                out.fire_in(
                    &file.path,
                    file.offset_of(&format!("id = \"{}\"", state.id)),
                    format!("component '{}' {problem}", c.name),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_component_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Comp003 {
    fn subjects(&self, host: &P) -> usize {
        component_subjects(host)
    }
}
