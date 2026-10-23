//! CRAFT005: pressing something answers. A project that styles components but never writes an
//! `:active` rule (or a Tailwind `active:` variant) gives no feedback at the moment of a press, so
//! a tap feels dead. Fires once, at the first styled sheet, when the project has UI declarations
//! and no sheet styles `active`. An empty `:active {}` block, a comment or a string does not
//! count; a project with no UI to judge stays quiet. Advisory.

// frob:ticket 01M5HM3WE0PDTYAJ31B2C2A8A0

use gob_rules::{Out, RepoRule, rule};

use crate::craft::{state_styled, ui_sheets};
use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::site_path;

/// The pseudo-class this rule requires.
const STATE: &str = "active";

/// A project with UI and no `:active` style.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CRAFT005",
    slug = "press-feedback",
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
pub struct Craft005;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Craft005 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let sheets: Vec<_> = ui_sheets(styles).collect();
        let Some(first) = sheets.first() else {
            tracing::debug!("CRAFT005: no styled UI to judge");
            return;
        };
        if sheets.iter().any(|sheet| state_styled(sheet, STATE)) {
            return;
        }
        tracing::debug!(sheets = sheets.len(), "CRAFT005: no active style");
        out.fire_in(
            &site_path(spec, &first.path),
            0,
            "no `:active` style anywhere: a press gets no feedback; add an `:active` rule (or an \
             `active:` utility) that shifts, scales or darkens the pressed control",
        );
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
