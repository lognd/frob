//! COMP009: a component whose status is `ready` or `completed` but whose recorded `content_hash` is missing or no longer matches its content and the token values it binds. Off when the project has no component files.

// frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F

use crate::component_files::{TokenLookup, component_hash};
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::component_files::ComponentFile;
use crate::host::{CrunkHost, component_subjects, missing_component_inputs};

/// A locked component whose content hash is missing or stale.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COMP009",
    slug = "component-hash-stale",
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
pub struct Comp009;

/// The component files of `host`, none when it has none.
fn components<P: ?Sized + CrunkHost>(host: &P) -> &[ComponentFile] {
    host.components().map_or(&[][..], |c| &c.files[..])
}

impl<P: ?Sized + CrunkHost> RepoRule<P> for Comp009 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let tokens = TokenLookup::new(host.spec(), host.tokens());
        for file in components(host) {
            let c = &file.component;
            if !file.is_locked() {
                continue;
            }
            let want = component_hash(c, &tokens);
            let message = match c.content_hash.as_deref() {
                None => format!(
                    "component '{}' is locked but records no content_hash (expected {want})",
                    c.name
                ),
                Some(have) if have != want => format!(
                    "component '{}' or a token it binds changed since its content_hash was recorded (recorded {have}, now {want}); set status to `changed` or record the new hash",
                    c.name
                ),
                Some(_) => continue,
            };
            tracing::debug!(path = %file.path, "COMP009: hash missing or stale");
            out.fire_in(&file.path, file.offset_of("status"), message);
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_component_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Comp009 {
    fn subjects(&self, host: &P) -> usize {
        component_subjects(host)
    }
}
