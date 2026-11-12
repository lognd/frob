//! COMP002: a component whose variant matrix does not render every combination of its enum axis props (each combination is enumerated and resolved to a cell) exactly once, or names an unknown axis or value. Off when the project has no component files.

// frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F

use crunk_spec::component_file::PropKind;
use gob_rules::{Measured, Out, RepoRule, rule};
use std::collections::BTreeSet;

use crate::component_files::ComponentFile;
use crate::host::{CrunkHost, component_subjects, missing_component_inputs};

/// A component variant matrix with holes, repeats or unknown cells.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COMP002",
    slug = "variants-incomplete",
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
pub struct Comp002;

/// Cap on unrendered combinations named in one finding.
const MAX_NAMED: usize = 8;

/// Every combination of the axes' values in axis order, each as its value list; the variant
/// matrix is "rendered" combination by combination against these.
fn combinations<'a>(axes: &[&'a crunk_spec::component_file::Prop]) -> Vec<Vec<&'a str>> {
    axes.iter().fold(vec![Vec::new()], |acc, axis| {
        let distinct: BTreeSet<&str> = axis.values.iter().map(String::as_str).collect();
        acc.iter()
            .flat_map(|prefix| {
                distinct.iter().map(move |v| {
                    let mut next = prefix.clone();
                    next.push(*v);
                    next
                })
            })
            .collect()
    })
}

/// The component files of `host`, none when it has none.
fn components<P: ?Sized + CrunkHost>(host: &P) -> &[ComponentFile] {
    host.components().map_or(&[][..], |c| &c.files[..])
}

impl<P: ?Sized + CrunkHost> RepoRule<P> for Comp002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        for file in components(host) {
            let c = &file.component;
            let axes: Vec<_> = c
                .props
                .iter()
                .filter(|p| p.axis && p.kind == PropKind::Enum && !p.values.is_empty())
                .collect();
            let at = file.offset_of("[[variants]]");
            if axes.is_empty() {
                if !c.variants.is_empty() {
                    out.fire_in(
                        &file.path,
                        at,
                        format!(
                            "component '{}' declares variants but no enum prop is an `axis`",
                            c.name
                        ),
                    );
                }
                continue;
            }
            let mut covered: BTreeSet<Vec<&str>> = BTreeSet::new();
            for (i, variant) in c.variants.iter().enumerate() {
                let mut cell: Vec<&str> = Vec::new();
                let mut valid = true;
                for key in variant.axes.keys() {
                    if !axes.iter().any(|a| a.name == *key) {
                        valid = false;
                        out.fire_in(
                            &file.path,
                            at,
                            format!(
                                "component '{}' variant {} names unknown axis '{key}'",
                                c.name,
                                i + 1
                            ),
                        );
                    }
                }
                for axis in &axes {
                    match variant.axes.get(&axis.name) {
                        None => {
                            valid = false;
                            out.fire_in(
                                &file.path,
                                at,
                                format!(
                                    "component '{}' variant {} sets no value for axis '{}'",
                                    c.name,
                                    i + 1,
                                    axis.name
                                ),
                            );
                        }
                        Some(v) if !axis.values.contains(v) => {
                            valid = false;
                            out.fire_in(
                                &file.path,
                                at,
                                format!("component '{}' variant {} gives axis '{}' the unknown value '{v}'", c.name, i + 1, axis.name),
                            );
                        }
                        Some(v) => cell.push(v.as_str()),
                    }
                }
                if valid && !covered.insert(cell.clone()) {
                    out.fire_in(
                        &file.path,
                        at,
                        format!(
                            "component '{}' variant {} repeats the cell {}",
                            c.name,
                            i + 1,
                            cell.join("/")
                        ),
                    );
                }
            }
            let all = combinations(&axes);
            let unrendered: Vec<String> = all
                .iter()
                .filter(|combo| !covered.contains(*combo))
                .map(|combo| combo.join("/"))
                .collect();
            tracing::debug!(path = %file.path, combinations = all.len(), unrendered = unrendered.len(), "COMP002: rendered every variant combination");
            if !unrendered.is_empty() {
                let named = unrendered
                    .iter()
                    .take(MAX_NAMED)
                    .cloned()
                    .collect::<Vec<_>>()
                    .join(", ");
                let more = unrendered.len().saturating_sub(MAX_NAMED);
                let tail = if more > 0 {
                    format!(" and {more} more")
                } else {
                    String::new()
                };
                out.fire_in(
                    &file.path,
                    at,
                    format!(
                        "component '{}' covers {} of {} variant combinations; no cell renders {named}{tail}",
                        c.name,
                        all.len() - unrendered.len(),
                        all.len()
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_component_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Comp002 {
    fn subjects(&self, host: &P) -> usize {
        component_subjects(host)
    }
}
