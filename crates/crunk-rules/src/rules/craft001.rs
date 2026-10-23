//! CRAFT001: a visible keyboard focus style exists. A project that styles components but never
//! writes `:focus-visible` (or a Tailwind `focus-visible:` variant) leaves keyboard users with the
//! browser default at best and nothing at worst. Fires once, at the first styled sheet, when the
//! project has UI declarations and no sheet styles `focus-visible`. Comments and strings do not
//! count, and a project with no UI to judge stays quiet. Contrast of the ring is judged elsewhere.
//! Advisory.

// frob:ticket 01M5HM3WE0PDTYAJ31B2C2A8A0

use gob_rules::{Out, RepoRule, rule};

use crate::craft::{state_styled, ui_sheets};
use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::site_path;

/// The pseudo-class this rule requires.
const STATE: &str = "focus-visible";

/// A project with UI and no `:focus-visible` style.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CRAFT001",
    slug = "focus-visible-defined",
    severity = Advisory,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Craft001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Craft001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let sheets: Vec<_> = ui_sheets(styles).collect();
        let Some(first) = sheets.first() else {
            tracing::debug!("CRAFT001: no styled UI to judge");
            return;
        };
        if sheets.iter().any(|sheet| state_styled(sheet, STATE)) {
            return;
        }
        tracing::debug!(sheets = sheets.len(), "CRAFT001: no focus-visible style");
        out.fire_in(
            &site_path(spec, &first.path),
            0,
            "no `:focus-visible` style anywhere: keyboard users get no visible focus indicator; \
             add a `:focus-visible` rule (or a `focus-visible:` utility) with an outline of at \
             least 3:1 contrast",
        );
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
