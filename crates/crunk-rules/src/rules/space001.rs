//! SPACE001: margin, padding, gap and inset lengths off the spacing scale (port of
//! `crunk/rules/_scales.py` `space001`; design: `crunk.md` section 6).
//!
//! The judgment is [`crate::scales`]: px and rem lengths only, relative tolerance, the nearest and
//! the two bracketing steps in the message. Divergences from the Python rule: the finding is
//! located at the length token and names the nearest step; token names follow `[tokens]` prefixes
//! (Python hard-coded `--space` in the message); the fix payload is the autofix ticket's, so
//! `fix = Manual`; waivers are the pipeline's exceptions.

// frob:ticket 01M43ATBDWVSJBXP7TEQ6DBW3W

use crunk_spec::naming::space_token;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::scales::{SPACE_PROPS, ScaleJudgment, check};
use crate::sheets::examined_sheets;

/// A margin, padding, gap or inset length that is not a step of the spacing scale.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SPACE001",
    slug = "spacing-off-scale",
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
pub struct Space001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Space001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let token = |step: f64| space_token(&spec.tokens, step);
        let judgment = ScaleJudgment {
            props: SPACE_PROPS,
            scale: &spec.scales.spacing,
            token: &token,
        };
        check(spec, styles, &judgment, out);
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Space001 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
