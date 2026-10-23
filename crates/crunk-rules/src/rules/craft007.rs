//! CRAFT007: shadows form one elevation system. Every shadow in a project is lit by the same
//! light, so each layer's offset points the same way (within 15 degrees) and its blur grows with
//! its distance in a similar ratio (within a factor of 3). `box-shadow` and `--shadow*` or
//! `*elevation*` custom properties are read; `inset` layers, layers using `var()` and layers with
//! no offset (glows) are skipped. The first qualifying layer in source order is the reference; a
//! declaration with a layer that disagrees fires once at it. Fewer than two qualifying layers is
//! quiet. Advisory.

// frob:ticket 01M5HM3WE0PDTYAJ31B2C2A8A0

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::site_path;
use crate::slop::judged_sheets;

/// The most a layer's light angle may differ from the reference, in degrees.
const MAX_ANGLE_DEGREES: f64 = 15.0;

/// The most the blur-to-distance ratio may differ from the reference, as a factor.
const MAX_RATIO_FACTOR: f64 = 3.0;

/// The smallest ratio compared, so a hard shadow (blur 0) is not infinitely off.
const RATIO_FLOOR: f64 = 0.25;

/// One shadow layer's light direction and softness.
#[derive(Debug, Clone, Copy)]
struct Layer {
    angle: f64,
    ratio: f64,
}

/// A CSS length token in pixels (`px`, `rem` and `em` at 16, or a bare zero).
fn pixels(token: &str) -> Option<f64> {
    let token = token.to_ascii_lowercase();
    if let Some(n) = token.strip_suffix("px") {
        return n.parse().ok();
    }
    if let Some(n) = token
        .strip_suffix("rem")
        .or_else(|| token.strip_suffix("em"))
    {
        return n.parse::<f64>().ok().map(|v| v * 16.0);
    }
    (token.parse::<f64>().ok()? == 0.0).then_some(0.0)
}

/// `value` split at its top-level commas.
fn split_layers(value: &str) -> Vec<&str> {
    let mut out = Vec::new();
    let (mut depth, mut start) = (0_i32, 0);
    for (i, c) in value.char_indices() {
        match c {
            '(' => depth += 1,
            ')' => depth -= 1,
            ',' if depth == 0 => {
                out.push(&value[start..i]);
                start = i + 1;
            }
            _ => {}
        }
    }
    out.push(&value[start..]);
    out
}

/// The whitespace tokens of `layer`, keeping a parenthesised colour in one piece.
fn tokens(layer: &str) -> Vec<&str> {
    let mut out = Vec::new();
    let (mut depth, mut start) = (0_i32, None);
    for (i, c) in layer.char_indices() {
        match c {
            '(' => depth += 1,
            ')' => depth -= 1,
            _ => {}
        }
        match (c.is_whitespace() && depth == 0, start) {
            (true, Some(s)) => {
                out.push(&layer[s..i]);
                start = None;
            }
            (false, None) => start = Some(i),
            _ => {}
        }
    }
    if let Some(s) = start {
        out.push(&layer[s..]);
    }
    out
}

/// The light direction and softness of one layer, `None` when it does not qualify.
fn parse_layer(layer: &str) -> Option<Layer> {
    if layer.contains("var(") {
        return None;
    }
    let tokens = tokens(layer);
    if tokens.iter().any(|t| t.eq_ignore_ascii_case("inset")) {
        return None;
    }
    let lengths: Vec<f64> = tokens.iter().filter_map(|t| pixels(t)).collect();
    let (x, y) = (*lengths.first()?, *lengths.get(1)?);
    let blur = lengths.get(2).copied().unwrap_or(0.0);
    let distance = x.hypot(y);
    (distance > 0.0).then(|| Layer {
        angle: x.atan2(y).to_degrees(),
        ratio: (blur / distance).max(RATIO_FLOOR),
    })
}

/// Why `layer` disagrees with `reference`, `None` when it fits the system.
fn disagreement(reference: Layer, layer: Layer) -> Option<String> {
    let turn = (layer.angle - reference.angle + 540.0).rem_euclid(360.0) - 180.0;
    if turn.abs() > MAX_ANGLE_DEGREES {
        return Some(format!(
            "its light comes from {:.0} degrees off the system's",
            turn.abs()
        ));
    }
    let factor = reference.ratio.max(layer.ratio) / reference.ratio.min(layer.ratio);
    (factor > MAX_RATIO_FACTOR)
        .then(|| format!("its blur-to-distance ratio is {factor:.1}x the system's"))
}

/// A shadow lit from a different direction, or softened out of proportion, to the rest.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CRAFT007",
    slug = "elevation-system",
    severity = Advisory,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Craft007;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Craft007 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let mut reference: Option<Layer> = None;
        for sheet in judged_sheets(styles) {
            for decl in &sheet.declarations {
                let shadow = decl.prop == "box-shadow"
                    || (decl.prop.starts_with("--")
                        && (decl.prop.starts_with("--shadow") || decl.prop.contains("elevation")));
                if !shadow {
                    continue;
                }
                for layer in split_layers(&decl.value)
                    .into_iter()
                    .filter_map(parse_layer)
                {
                    let Some(base) = reference else {
                        reference = Some(layer);
                        continue;
                    };
                    if let Some(why) = disagreement(base, layer) {
                        tracing::debug!(prop = %decl.prop, "CRAFT007: shadow off the system");
                        out.fire_in(
                            &site_path(spec, &sheet.path),
                            decl.span.0,
                            format!(
                                "`{}` has a shadow layer off the elevation system: {why}; match \
                                 the light direction and blur proportion of the other shadows",
                                decl.prop
                            ),
                        );
                        break;
                    }
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
