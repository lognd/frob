//! CONTRAST001: a declared role pair below its contrast floor (port of `crunk/rules/_contrast.py`).
//!
//! Every `[palette.roles]` pair is measured with the WCAG 2.2 ratio in every declared mode
//! ([`crate::mode`]; one default mode today) and judged against ITS OWN floor (4.5 unless the role
//! declares the large-text or icon exception). The gate is the WCAG ratio; APCA is advisory and
//! opt-in through `contrast_model` once the spec declares it.
//!
//! The finding is spec-level: it sits at the start of `crunk.toml` (Python used line 0) and, as in
//! Python, cannot be waived, because a waiver attaches to a stylesheet declaration.

// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

use gob_rules::{Out, RepoRule, rule};

use crate::contrast::{Measured, measure_roles};
use crate::host::CrunkHost;
use crate::mode::modes;

/// The file spec-level findings are located in.
const SPEC_FILE: &str = "crunk.toml";

/// A declared role pair whose contrast ratio is below its floor.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CONTRAST001",
    slug = "role-contrast-below-floor",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Contrast001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Contrast001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(spec) = host.spec() else { return };
        for mode in modes(spec) {
            for pair in measure_roles(spec, mode)
                .into_iter()
                .filter(Measured::fails)
            {
                tracing::debug!(role = %pair.role, ratio = pair.ratio, floor = pair.floor, mode = mode.name, "CONTRAST001: below floor");
                out.fire_in(
                    SPEC_FILE,
                    0,
                    format!(
                        "role {:?} ({}/{}) contrast {:.2} is below the {:.1} floor{}",
                        pair.role,
                        pair.foreground,
                        pair.background,
                        pair.ratio,
                        pair.floor,
                        mode.suffix(),
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        host.spec()
            .is_none()
            .then(|| "no valid crunk.toml".to_owned())
    }
}
