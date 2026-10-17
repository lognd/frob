//! TW004: an arbitrary Tailwind property (`[width:13px]`) that hard-codes a length or colour.
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use crunk_tailwind::UtilityValue;
use crunk_values::{Color, Length};
use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::tailwind::sites;

/// An arbitrary property utility whose whole value is a length or colour literal.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TW004",
    slug = "tailwind-arbitrary-property",
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
pub struct Tw004;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Tw004 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let root = spec.project.root_font_size;
        for site in sites(spec, styles) {
            let Some(UtilityValue::Property { value, .. }) = &site.candidate.value else {
                continue;
            };
            let text = value.replace('_', " ");
            let literal = Color::parse(&text).is_ok()
                || Length::parse(&text, root).is_ok_and(|l| l.px.is_some());
            if !literal {
                continue;
            }
            tracing::debug!(path = %site.path, class = %site.candidate.raw, "TW004: arbitrary property hard-codes a literal");
            out.fire_in(
                &site.path,
                site.offset,
                format!(
                    "`{}` hard-codes `{text}` in an arbitrary property; use a token or a scale utility",
                    site.candidate.raw
                ),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
