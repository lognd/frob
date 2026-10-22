//! COMP001: a component prop that is unnamed, repeated, an enum without values or with a default outside them, or a slot whose min exceeds its max. Off when the project has no component files.

// frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F

use crunk_spec::component_file::PropKind;
use gob_rules::{Measured, Out, RepoRule, rule};
use std::collections::HashSet;

use crate::component_files::ComponentFile;
use crate::host::{CrunkHost, component_subjects, missing_component_inputs};

/// A component prop declaration that cannot work.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COMP001",
    slug = "props-invalid",
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
pub struct Comp001;

/// The component files of `host`, none when it has none.
fn components<P: ?Sized + CrunkHost>(host: &P) -> &[ComponentFile] {
    host.components().map_or(&[][..], |c| &c.files[..])
}

impl<P: ?Sized + CrunkHost> RepoRule<P> for Comp001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        for file in components(host) {
            let c = &file.component;
            let mut seen: HashSet<&str> = HashSet::new();
            for prop in &c.props {
                let at = file.offset_of(&format!("name = \"{}\"", prop.name));
                let mut problems: Vec<String> = Vec::new();
                if prop.name.trim().is_empty() {
                    problems.push("has a blank name".to_owned());
                } else if !seen.insert(prop.name.as_str()) {
                    problems.push("is declared more than once".to_owned());
                }
                if prop.kind == PropKind::Enum {
                    if prop.values.is_empty() {
                        problems.push("is an enum with no values".to_owned());
                    }
                    let mut vals: HashSet<&str> = HashSet::new();
                    if prop.values.iter().any(|v| !vals.insert(v.as_str())) {
                        problems.push("repeats an enum value".to_owned());
                    }
                    if let Some(d) = &prop.default
                        && !prop.values.contains(d)
                    {
                        problems.push(format!("defaults to '{d}', which is not one of its values"));
                    }
                } else {
                    if !prop.values.is_empty() {
                        problems.push("lists values but is not an enum".to_owned());
                    }
                    if prop.axis {
                        problems.push("is a variant axis but not an enum".to_owned());
                    }
                }
                if let (Some(min), Some(max)) = (prop.min, prop.max)
                    && min > max
                {
                    problems.push(format!("has min {min} above max {max}"));
                }
                for problem in problems {
                    tracing::debug!(path = %file.path, prop = %prop.name, "COMP001: {problem}");
                    out.fire_in(
                        &file.path,
                        at,
                        format!("component '{}' prop '{}' {problem}", c.name, prop.name),
                    );
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_component_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Comp001 {
    fn subjects(&self, host: &P) -> usize {
        component_subjects(host)
    }
}
