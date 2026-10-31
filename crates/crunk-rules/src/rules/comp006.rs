//! COMP006: an `interactive` component whose a11y contract lacks a role, an accessible-name source or a keyboard map, or whose minimum target is absent or under 24 CSS pixels. Off when the project has no component files.

// frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F

use crate::component_files::MIN_TARGET_PX;
use crunk_spec::table::ScreenKind;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::component_files::ComponentFile;
use crate::host::{CrunkHost, component_subjects, missing_component_inputs};

/// An interactive component without a complete a11y contract.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COMP006",
    slug = "a11y-contract-incomplete",
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
pub struct Comp006;

/// The component files of `host`, none when it has none.
fn components<P: ?Sized + CrunkHost>(host: &P) -> &[ComponentFile] {
    host.components().map_or(&[][..], |c| &c.files[..])
}

impl<P: ?Sized + CrunkHost> RepoRule<P> for Comp006 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        for file in components(host) {
            let c = &file.component;
            if !c.kinds.contains(&ScreenKind::Interactive) {
                continue;
            }
            let a = &c.a11y;
            let blank = |s: &Option<String>| s.as_deref().is_none_or(|v| v.trim().is_empty());
            let mut missing: Vec<String> = Vec::new();
            if blank(&a.role) {
                missing.push("a role".to_owned());
            }
            if blank(&a.name_source) {
                missing.push("a name source".to_owned());
            }
            if a.keyboard.is_empty() {
                missing.push("a keyboard map".to_owned());
            }
            match a.min_target {
                None => missing.push("a min_target".to_owned()),
                Some(px) if px < MIN_TARGET_PX => {
                    missing.push(format!(
                        "a min_target of at least {MIN_TARGET_PX} (has {px})"
                    ));
                }
                Some(_) => {}
            }
            if missing.is_empty() {
                continue;
            }
            tracing::debug!(path = %file.path, ?missing, "COMP006: a11y contract incomplete");
            out.fire_in(
                &file.path,
                file.offset_of("[a11y]"),
                format!(
                    "component '{0}' (node '{0}') is `interactive` but its a11y contract lacks {1}",
                    c.name,
                    missing.join(", ")
                ),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_component_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Comp006 {
    fn subjects(&self, host: &P) -> usize {
        component_subjects(host)
    }
}
