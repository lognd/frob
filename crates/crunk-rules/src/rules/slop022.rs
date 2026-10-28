//! SLOP022: uniform radius (research top-20 #22). Three or more literal px or rem `border-radius`
//! declarations (zero and percentages aside) that share one value, or that are 16px and larger in
//! more than 60 percent of cases, fire once at the first. `[decisions] radius` (a per-role radius
//! policy, or rounded by design) silences it. Advisory.

// frob:ticket 01M4CXT4Z45GR5QE71B10FRR8N

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::scales::RADIUS_PROPS;
use crate::sheets::site_path;
use crate::slop;

/// Three or more literal radii that are all one value, or mostly 16px and up, with no radius decision.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SLOP022",
    slug = "uniform-radius",
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
pub struct Slop022;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Slop022 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        if slop::decided(spec, "radius") {
            return;
        }
        let mut radii: Vec<(String, usize, f64)> = Vec::new();
        for sheet in slop::judged_sheets(styles) {
            let path = site_path(spec, &sheet.path);
            for decl in sheet
                .declarations
                .iter()
                .filter(|d| RADIUS_PROPS.contains(&d.prop.as_str()))
            {
                if !decl.var_refs.is_empty() {
                    continue;
                }
                if let Some(px) = decl.lengths.first().and_then(|l| l.length.px)
                    && px > 0.0
                {
                    radii.push((path.clone(), decl.span.0, px));
                }
            }
        }
        if radii.len() < 3 {
            return;
        }
        let first = &radii[0];
        let same = radii.iter().all(|(_, _, px)| (px - first.2).abs() < 0.01);
        let large = radii.iter().filter(|(_, _, px)| *px >= 16.0).count();
        #[allow(clippy::cast_precision_loss, reason = "a handful of declarations")]
        let mostly_large = large as f64 / radii.len() as f64 > 0.6;
        if same || mostly_large {
            tracing::debug!(
                count = radii.len(),
                same,
                mostly_large,
                "SLOP022: uniform radius"
            );
            let why = if same {
                format!("all {} radii are {}px", radii.len(), first.2)
            } else {
                format!("{large} of {} radii are 16px or larger", radii.len())
            };
            out.fire_in(
                &first.0,
                first.1,
                format!("uniform radius: {why}; declare `[decisions] radius` if it is the design"),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
