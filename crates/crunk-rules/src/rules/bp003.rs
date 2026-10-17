//! BP003: a `width`/`min-width` declaration wider than the smallest declared breakpoint.
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use gob_rules::{Out, RepoRule, rule};

use crunk_values::LengthKind;

use crate::host::{CrunkHost, missing_inputs};
use crate::org::line_offset;
use crate::sheets::site_path;

/// A fixed `width`/`min-width` in px or rem exceeding the smallest breakpoint: guaranteed mobile overflow.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "BP003",
    slug = "fixed-width-exceeds-mobile",
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
pub struct Bp003;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Bp003 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let Some((name, smallest)) = spec.breakpoints.points.iter().min_by_key(|(_, v)| **v) else {
            return;
        };
        let smallest = f64::from(i32::try_from(*smallest).unwrap_or(i32::MAX));
        for sheet in &styles.sheets {
            let path = site_path(spec, &sheet.path);
            for decl in &sheet.declarations {
                if !matches!(decl.prop.as_str(), "width" | "min-width") {
                    continue;
                }
                for located in &decl.lengths {
                    let length = &located.length;
                    let (LengthKind::Px | LengthKind::Rem, Some(px)) = (length.kind, length.px)
                    else {
                        continue;
                    };
                    if px.abs() <= smallest {
                        continue;
                    }
                    tracing::debug!(%path, prop = %decl.prop, px, "BP003: width exceeds smallest breakpoint");
                    out.fire_in(
                        &path,
                        line_offset(&sheet.source, decl.line),
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
        missing_inputs(host).or_else(|| {
            host.spec()
                .is_some_and(|s| s.breakpoints.points.is_empty())
                .then(|| "no [breakpoints] declared".to_owned())
        })
    }
}
