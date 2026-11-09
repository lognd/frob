//! RADIUS001: `border-radius` and corner longhands off the radii scale (port of
//! `crunk/rules/_scales.py` `radius001`). Same judgment as SPACE001. Warn by default. A project
//! that declares no radii has no design law to judge against: the rule is then inapplicable (the
//! Python rule returned nothing; here the skip is counted and reported).

// frob:ticket 01M54H34N0CPKAZ7TP91EYXGVV
// frob:ticket 01M43ATBDWVSJBXP7TEQ6DBW3W

use crunk_spec::naming::radius_token;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scale};
use crate::scales::{RADIUS_PROPS, ScaleJudgment, check};
use crate::sheets::examined_sheets;

/// A `border-radius` length that is not a step of the radii scale.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "RADIUS001",
    slug = "radius-off-scale",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Deterministic,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Radius001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Radius001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let token = |step: f64| radius_token(&spec.tokens, step);
        let judgment = ScaleJudgment {
            props: RADIUS_PROPS,
            scale: &spec.scales.radii,
            token: &token,
        };
        check(spec, styles, &judgment, out);
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scale(
            host,
            |spec| spec.scales.radii.is_empty(),
            "no [scales] radii are declared",
        )
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Radius001 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
