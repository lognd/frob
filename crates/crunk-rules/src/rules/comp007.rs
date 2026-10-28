//! COMP007: a `ready` or `completed` component with no `[[code]]` mapping, or a mapping with a blank framework, path or export. Off when the project has no component files.

// frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::component_files::ComponentFile;
use crate::host::{CrunkHost, component_subjects, missing_component_inputs};

/// A locked component without a usable code mapping.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COMP007",
    slug = "code-mapping-missing",
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
pub struct Comp007;

/// The component files of `host`, none when it has none.
fn components<P: ?Sized + CrunkHost>(host: &P) -> &[ComponentFile] {
    host.components().map_or(&[][..], |c| &c.files[..])
}

impl<P: ?Sized + CrunkHost> RepoRule<P> for Comp007 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        for file in components(host) {
            let c = &file.component;
            let at = file.offset_of("[[code]]");
            if file.is_locked() && c.code.is_empty() {
                out.fire_in(
                    &file.path,
                    file.offset_of("status"),
                    format!(
                        "component '{}' is locked but has no [[code]] mapping",
                        c.name
                    ),
                );
            }
            for (i, m) in c.code.iter().enumerate() {
                for (field, value) in [
                    ("framework", &m.framework),
                    ("path", &m.path),
                    ("export", &m.export),
                ] {
                    if value.trim().is_empty() {
                        tracing::debug!(path = %file.path, field, "COMP007: blank mapping field");
                        out.fire_in(
                            &file.path,
                            at,
                            format!(
                                "component '{}' code mapping {} has a blank {field}",
                                c.name,
                                i + 1
                            ),
                        );
                    }
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_component_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Comp007 {
    fn subjects(&self, host: &P) -> usize {
        component_subjects(host)
    }
}
