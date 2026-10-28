//! SLOP003: gradient abuse (research top-20 #3). Four or more gradient backgrounds fire at the
//! fourth; any `background-clip: text` (gradient text) fires at the declaration. `[decisions]
//! gradients` silences it. Advisory.

// frob:ticket 01M4CXT4Z45GR5QE71B10FRR8N

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::site_path;
use crate::slop;

/// The gradient background count at which the density fires.
const GRADIENT_LIMIT: usize = 4;

/// Four or more gradient backgrounds, or gradient text, with no gradients decision.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SLOP003",
    slug = "gradient-abuse",
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
pub struct Slop003;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Slop003 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        if slop::decided(spec, "gradients") {
            return;
        }
        let mut seen = 0usize;
        for sheet in slop::judged_sheets(styles) {
            let path = site_path(spec, &sheet.path);
            for decl in &sheet.declarations {
                let value = decl.value.to_lowercase();
                if matches!(
                    decl.prop.as_str(),
                    "background-clip" | "-webkit-background-clip"
                ) && value.contains("text")
                {
                    tracing::debug!(%path, "SLOP003: gradient text");
                    out.fire_in(
                        &path,
                        decl.span.0,
                        "gradient text (`background-clip: text`)",
                    );
                } else if matches!(decl.prop.as_str(), "background" | "background-image")
                    && value.contains("gradient(")
                {
                    seen += 1;
                    if seen == GRADIENT_LIMIT {
                        tracing::debug!(%path, seen, "SLOP003: gradient density reached");
                        out.fire_in(
                            &path,
                            decl.span.0,
                            format!("{seen} gradient backgrounds in the project; one gradient is a choice, {GRADIENT_LIMIT} is a style"),
                        );
                    }
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
