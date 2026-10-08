//! SIZE001: `width`, `height`, `min-width`, `min-height` and `max-height` lengths off the sizes
//! scale (port of `crunk/rules/_scales.py` `size001`, r10/CR-22). `max-width` is exempt by design.
//! `[scales] sizes` falls back to `spacing` when empty, and the suggested token names follow the
//! scale in use (`--size-*` or `--space-*`). Warn by default.

// frob:ticket 01M43ATBDWVSJBXP7TEQ6DBW3W

use crunk_spec::naming::{size_token, space_token};
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::scales::{SIZE_PROPS, ScaleJudgment, check};
use crate::sheets::examined_sheets;

/// A box-size length that is not a step of the sizes scale (or of spacing when no sizes are declared).
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SIZE001",
    slug = "size-off-scale",
    severity = Warn,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Size001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Size001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let fallback = spec.scales.sizes.is_empty();
        let scale = if fallback {
            &spec.scales.spacing
        } else {
            &spec.scales.sizes
        };
        let token = |step: f64| {
            if fallback {
                space_token(&spec.tokens, step)
            } else {
                size_token(&spec.tokens, step)
            }
        };
        let judgment = ScaleJudgment {
            props: SIZE_PROPS,
            scale,
            token: &token,
        };
        check(spec, styles, &judgment, out);
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Size001 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
