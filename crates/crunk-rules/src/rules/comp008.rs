//! COMP008: a code mapping whose listed props differ from the component's `[[props]]`. Off when the project has no component files.

// frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F

use gob_rules::{Measured, Out, RepoRule, rule};
use std::collections::BTreeSet;

use crate::component_files::ComponentFile;
use crate::host::{CrunkHost, component_subjects, missing_component_inputs};

/// A code mapping that disagrees with the spec props.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COMP008",
    slug = "code-props-mismatch",
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
pub struct Comp008;

/// The component files of `host`, none when it has none.
fn components<P: ?Sized + CrunkHost>(host: &P) -> &[ComponentFile] {
    host.components().map_or(&[][..], |c| &c.files[..])
}

impl<P: ?Sized + CrunkHost> RepoRule<P> for Comp008 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        for file in components(host) {
            let c = &file.component;
            let spec: BTreeSet<&str> = c.props.iter().map(|p| p.name.as_str()).collect();
            for m in &c.code {
                let Some(listed) = &m.props else {
                    continue;
                };
                let code: BTreeSet<&str> = listed.iter().map(String::as_str).collect();
                let extra: Vec<&str> = code.difference(&spec).copied().collect();
                let missing: Vec<&str> = spec.difference(&code).copied().collect();
                if extra.is_empty() && missing.is_empty() {
                    continue;
                }
                tracing::debug!(path = %file.path, ?extra, ?missing, "COMP008: props differ");
                let mut parts: Vec<String> = Vec::new();
                if !missing.is_empty() {
                    parts.push(format!("lacks {}", missing.join(", ")));
                }
                if !extra.is_empty() {
                    parts.push(format!("adds {}", extra.join(", ")));
                }
                out.fire_in(
                    &file.path,
                    file.offset_of("[[code]]"),
                    format!(
                        "component '{}' code '{}' ({}) {} against the spec props",
                        c.name,
                        m.export,
                        m.framework,
                        parts.join(" and ")
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_component_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Comp008 {
    fn subjects(&self, host: &P) -> usize {
        component_subjects(host)
    }
}
