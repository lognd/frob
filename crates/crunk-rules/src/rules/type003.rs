//! TYPE003: a numeric `font-weight` outside the declared weights (port of
//! `crunk/rules/_typography.py` `type003`). `normal` and `bold` resolve to 400 and 700; the
//! relative and inherited keywords carry no fixed weight and are exempt. Warn by default.

// frob:ticket 01M43ATBDWVSJBXP7TEQ6DBW3W

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::{examined_sheets, site_path};
use crate::typography::{Weight, weight_of};

/// A `font-weight` that is not one of the declared weights.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TYPE003",
    slug = "font-weight-off-scale",
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
pub struct Type003;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Type003 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let mut declared = spec.typography.weights.clone();
        declared.sort_unstable();
        for sheet in &styles.sheets {
            let path = site_path(spec, &sheet.path);
            for decl in sheet
                .declarations
                .iter()
                .filter(|d| d.prop == "font-weight")
            {
                let weight = match weight_of(&decl.value) {
                    Weight::Numeric(weight) => weight,
                    Weight::Exempt => continue,
                    Weight::Unparseable => {
                        tracing::debug!(%path, value = %decl.value, "TYPE003: skipping unparseable font-weight");
                        continue;
                    }
                };
                if declared.contains(&weight) {
                    continue;
                }
                out.fire_in(
                    &path,
                    decl.span.0,
                    format!("font-weight {weight} is outside declared weights {declared:?}"),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Type003 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
