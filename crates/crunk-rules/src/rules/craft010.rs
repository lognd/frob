//! CRAFT010: motion policy present (research section 4.7, the presence twin of the MOTION and SLOP
//! rules). Deleting every transition and animation passes any motion rule vacuously, so a project
//! whose stylesheets carry no motion at all fires once ("no motion policy"), and a project that
//! has motion but no `prefers-reduced-motion` media query fires once ("no reduced-motion twin").
//! Advisory; turn it off under `[lint]` for a deliberately static design.

// frob:ticket 01M4CXT7KWGP62H0CRCDTBY8Q0

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::site_path;
use crate::slop;

/// Declaration property prefixes that make motion.
const MOTION_PROPS: [&str; 2] = ["transition", "animation"];

/// No motion declared anywhere, or motion declared with no reduced-motion twin.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CRAFT010",
    slug = "motion-policy",
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
pub struct Craft010;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Craft010 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let sheets: Vec<_> = slop::judged_sheets(styles).collect();
        let Some(first) = sheets.first() else {
            return;
        };
        let has_motion = sheets.iter().any(|s| {
            s.source.contains("@keyframes")
                || s.declarations
                    .iter()
                    .any(|d| MOTION_PROPS.iter().any(|p| d.prop.starts_with(p)))
        });
        if !has_motion {
            tracing::debug!("CRAFT010: no motion declared");
            out.fire_in(
                &site_path(spec, &first.path),
                0,
                "no motion policy: no transition or animation is declared; add purposeful motion \
                 (press, enter, state change) or switch CRAFT010 off for a static design"
                    .to_owned(),
            );
            return;
        }
        let has_twin = sheets.iter().any(|s| {
            s.media_queries
                .iter()
                .any(|m| m.prelude.contains("prefers-reduced-motion"))
        });
        if !has_twin {
            tracing::debug!("CRAFT010: motion without a reduced-motion twin");
            out.fire_in(
                &site_path(spec, &first.path),
                0,
                "no reduced-motion twin: motion is declared but no `prefers-reduced-motion` \
                 media query softens it"
                    .to_owned(),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
