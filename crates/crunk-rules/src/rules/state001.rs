//! STATE001: a screen declared `interactive` that lacks one of the states default, hover, focus-visible, active and disabled. Judges component files the same way. Off when the project has no screen or component files.

// frob:ticket 01M4CXR89ERNB60CEDG60E2DXH

use crunk_spec::table::ScreenKind;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_screen_inputs, state_subjects};

/// An interactive screen without its component states.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "STATE001",
    slug = "interactive-states-missing",
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
pub struct State001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for State001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        for file in host.screens().map_or(&[][..], |s| &s.files[..]) {
            if !file.screen.kinds.contains(&ScreenKind::Interactive) {
                continue;
            }
            let missing = file.missing_states(ScreenKind::Interactive);
            if missing.is_empty() {
                continue;
            }
            tracing::debug!(path = %file.path, ?missing, "STATE001: states missing");
            out.fire_in(
                &file.path,
                file.offset_of("kinds"),
                format!(
                    "screen '{}' is `interactive` but declares no {} state",
                    file.screen.id,
                    missing.join(", ")
                ),
            );
        }
        // frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F
        for file in host.components().map_or(&[][..], |c| &c.files[..]) {
            if !file.component.kinds.contains(&ScreenKind::Interactive) {
                continue;
            }
            let missing = file.missing_states(ScreenKind::Interactive);
            if missing.is_empty() {
                continue;
            }
            tracing::debug!(path = %file.path, ?missing, "STATE001: component states missing");
            out.fire_in(
                &file.path,
                file.offset_of("kinds"),
                format!(
                    "component '{0}' (node '{0}') is `interactive` but declares no {1} state",
                    file.component.name,
                    missing.join(", ")
                ),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_screen_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for State001 {
    fn subjects(&self, host: &P) -> usize {
        state_subjects(host)
    }
}
