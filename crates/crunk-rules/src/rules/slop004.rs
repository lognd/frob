//! SLOP004: coloured glow shadows (research top-20 #4). A `box-shadow` layer whose colour has
//! saturation above 0.3 and lightness between 0.2 and 0.9, with a blur of 15px or more, is a glow;
//! two or more glows in the project fire at each. `[decisions] glows` silences it. Advisory.

// frob:ticket 01M4CXT4Z45GR5QE71B10FRR8N

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::site_path;
use crate::slop;

/// Two or more saturated, wide-blur box shadows with no glows decision.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SLOP004",
    slug = "coloured-glow-shadows",
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
pub struct Slop004;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Slop004 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        if slop::decided(spec, "glows") {
            return;
        }
        let mut glows: Vec<(String, usize)> = Vec::new();
        for sheet in slop::judged_sheets(styles) {
            let path = site_path(spec, &sheet.path);
            for decl in sheet.declarations.iter().filter(|d| d.prop == "box-shadow") {
                for (from, to) in layer_ranges(&decl.value, decl.span.0) {
                    let colour = decl.colors.iter().find(|c| (from..to).contains(&c.span.0));
                    let blur = decl
                        .lengths
                        .iter()
                        .filter(|l| (from..to).contains(&l.span.0))
                        .nth(2)
                        .and_then(|l| l.length.px);
                    if let (Some(colour), Some(blur)) = (colour, blur)
                        && is_glow(colour.color, blur)
                    {
                        glows.push((path.clone(), colour.span.0));
                    }
                }
            }
        }
        if glows.len() >= 2 {
            for (path, at) in glows {
                tracing::debug!(%path, "SLOP004: coloured glow");
                out.fire_in(
                    &path,
                    at,
                    "coloured glow shadow (saturated colour, blur of 15px or more)",
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

/// Byte ranges (absolute, from `base`) of the comma-separated layers of a `box-shadow` value;
/// commas inside parentheses do not split.
fn layer_ranges(value: &str, base: usize) -> Vec<(usize, usize)> {
    let mut ranges = Vec::new();
    let (mut depth, mut from) = (0usize, 0usize);
    for (i, b) in value.bytes().enumerate() {
        match b {
            b'(' => depth += 1,
            b')' => depth = depth.saturating_sub(1),
            b',' if depth == 0 => {
                ranges.push((base + from, base + i));
                from = i + 1;
            }
            _ => {}
        }
    }
    ranges.push((base + from, base + value.len()));
    ranges
}

/// True when `color` at `blur` px reads as a glow: saturated, mid lightness, wide blur.
fn is_glow(color: crunk_values::Color, blur: f64) -> bool {
    let max = color.r.max(color.g).max(color.b);
    let min = color.r.min(color.g).min(color.b);
    let lightness = f64::midpoint(max, min);
    let saturation = if (max - min).abs() < f64::EPSILON {
        0.0
    } else {
        (max - min) / (1.0 - (2.0 * lightness - 1.0).abs())
    };
    blur >= 15.0 && saturation > 0.3 && (0.2..=0.9).contains(&lightness)
}
