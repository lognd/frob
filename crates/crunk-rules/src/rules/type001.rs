//! TYPE001: `font-size` lengths off the font-size scale (port of `crunk/rules/_scales.py`
//! `type001`). Same judgment and divergences as SPACE001, over `[scales] font_sizes`.

// frob:ticket 01M43ATBDWVSJBXP7TEQ6DBW3W

use crunk_spec::naming::font_size_token;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::scales::{FONT_SIZE_PROPS, ScaleJudgment, check};
use crate::sheets::examined_sheets;

/// A `font-size` length that is not a step of the font-size scale.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TYPE001",
    slug = "font-size-off-scale",
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
pub struct Type001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Type001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let token = |step: f64| font_size_token(&spec.tokens, step);
        let judgment = ScaleJudgment {
            props: FONT_SIZE_PROPS,
            scale: &spec.scales.font_sizes,
            token: &token,
        };
        check(spec, styles, &judgment, out);
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Type001 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
