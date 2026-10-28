//! CRAFT006: scales present (research section 4.7, the presence twin of the TYPE, SPACE and SLOP
//! rules). Deleting a scale passes every rule that judges against it vacuously: with no type scale
//! TYPE001 has nothing to compare, with no spacing scale SPACE001 does not, and with no radius
//! policy SLOP022 and RADIUS001 cannot tell a deliberate radius from a default. Each missing scale
//! fires once at `crunk.toml`, naming the rules it silences. A radius policy is either
//! `[scales] radii` or a `[decisions] radius` entry. Advisory; turn it off under `[lint]` for a
//! design that really has no scale.

// frob:ticket 01M5HM3VTW5FAZQ3TXM8XH739S

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::slop;

/// A type scale, spacing scale or radius policy that the project does not declare.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CRAFT006",
    slug = "scales-present",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Craft006;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Craft006 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(spec) = host.spec() else {
            return;
        };
        let missing = [
            (
                spec.scales.font_sizes.is_empty(),
                "no type scale: `[scales] font_sizes` is empty, so TYPE001 judges nothing; \
                 declare the font-size ramp",
            ),
            (
                spec.scales.spacing.is_empty(),
                "no spacing scale: `[scales] spacing` is empty, so SPACE001 judges nothing; \
                 declare the spacing steps",
            ),
            (
                spec.scales.radii.is_empty() && !slop::decided(spec, "radius"),
                "no radius policy: neither `[scales] radii` nor `[decisions] radius` is declared, \
                 so SLOP022 and RADIUS001 cannot judge radii; declare one",
            ),
        ];
        for (_, message) in missing.iter().filter(|(absent, _)| *absent) {
            tracing::debug!(message, "CRAFT006: scale missing");
            out.fire_in("crunk.toml", 0, (*message).to_owned());
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
