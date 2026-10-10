//! BP003: a px-comparable `width` or `min-width` larger than the smallest declared breakpoint, a
//! guaranteed overflow on a narrower viewport (port of `crunk/rules/_breakpoints.py` `bp003`).
//! `max-width` and lengths that are not px-comparable are exempt. Off when no breakpoints are
//! declared.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use crunk_values::LengthKind;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CrunkHost;
use crate::sheets::{examined_sheets, site_path};

/// A fixed width wider than the smallest declared breakpoint.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "BP003",
    slug = "fixed-width-exceeds-breakpoint",
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
pub struct Bp003;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Bp003 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let Some((name, &smallest)) = spec.breakpoints.points.iter().min_by_key(|(_, px)| **px)
        else {
            return;
        };
        #[allow(clippy::cast_precision_loss, reason = "breakpoints are small integers")]
        let limit = smallest as f64;
        for sheet in &styles.sheets {
            let path = site_path(spec, &sheet.path);
            let decls = sheet
                .declarations
                .iter()
                .filter(|d| d.prop == "width" || d.prop == "min-width");
            for decl in decls {
                for located in &decl.lengths {
                    let length = &located.length;
                    let comparable = matches!(length.kind, LengthKind::Px | LengthKind::Rem);
                    let Some(px) = length.px.filter(|_| comparable) else {
                        continue;
                    };
                    if px.abs() <= limit {
                        continue;
                    }
                    tracing::debug!(%path, line = decl.line, raw = %length.raw, "BP003: wide fixed width");
                    out.fire_in(
                        &path,
                        located.span.0,
                        format!(
                            "{}: {} exceeds the smallest declared breakpoint {name}={smallest}px -- guaranteed mobile overflow",
                            decl.prop, length.raw
                        ),
                    );
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        crate::breakpoints::off_reason(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Bp003 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
