//! TW001: an arbitrary Tailwind value (`p-[13px]`, `bg-[#2f6eec]`, `z-[999]`) off its governed scale.
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use crunk_spec::naming;
use crunk_values::{Color, Length, LengthKind};
use gob_rules::{Out, RepoRule, rule};

use crate::color::Palette;
use crate::host::{CrunkHost, missing_inputs};
use crate::layers::declared_values;
use crate::mode::Mode;
use crate::tailwind::{LENGTH_PREFIXES, off_scale, scale_and_token, sites, split_arbitrary};

/// An arbitrary-value utility whose z-index, colour or length is off the declared layers, palette or scale.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TW001",
    slug = "tailwind-arbitrary-off-scale",
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
pub struct Tw001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Tw001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let palette = Palette::new(Mode::DEFAULT.palette(spec));
        let root = spec.project.root_font_size;
        for site in sites(spec, styles) {
            let Some((prefix, inner)) = split_arbitrary(site.name) else {
                continue;
            };
            let name = site.name;
            let message = if prefix == "z" || prefix == "-z" {
                z_message(spec, name, prefix, inner)
            } else if let Ok(color) = Color::parse(inner) {
                if palette.conforms(color) {
                    None
                } else {
                    let nearest = palette.nearest(color).map_or_else(String::new, |(n, d)| {
                        format!(
                            "; nearest is {} (distance {d:.2})",
                            naming::color_token(&spec.tokens, n)
                        )
                    });
                    Some(format!(
                        "arbitrary value '{name}' is not a palette color{nearest}"
                    ))
                }
            } else if LENGTH_PREFIXES.contains(&prefix) {
                length_message(spec, name, prefix, inner, root)
            } else {
                None
            };
            if let Some(message) = message {
                tracing::debug!(path = %site.path, utility = name, "TW001: arbitrary value is off its scale");
                out.fire_in(&site.path, site.offset, message);
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

/// The finding text for an arbitrary z-index, `None` when it is a declared layer or not judged.
fn z_message(
    spec: &crunk_spec::DesignSpec,
    name: &str,
    prefix: &str,
    inner: &str,
) -> Option<String> {
    let layers = declared_values(spec);
    if layers.is_empty() {
        return None;
    }
    let mut value: i64 = inner.trim().parse().ok()?;
    if prefix == "-z" {
        value = -value;
    }
    if layers.contains(&value) {
        return None;
    }
    let mut sorted = layers.clone();
    sorted.sort_unstable();
    let nearest = spec
        .layers
        .iter()
        .min_by_key(|(_, v)| (value - **v).abs())
        .map(|(n, _)| format!("; nearest is {}", naming::layer_token(&spec.tokens, n)))
        .unwrap_or_default();
    Some(format!(
        "arbitrary value '{name}' is z-index {value}, not among declared layers {sorted:?}{nearest}"
    ))
}

/// The finding text for an arbitrary length of a governed family, `None` when it is on the scale.
fn length_message(
    spec: &crunk_spec::DesignSpec,
    name: &str,
    prefix: &str,
    inner: &str,
    root: f64,
) -> Option<String> {
    let uncomparable = || {
        Some(format!(
            "arbitrary value '{name}' uses a unit that cannot be compared to the px scale; '{prefix}' is a governed scale family"
        ))
    };
    let Ok(length) = Length::parse(inner, root) else {
        return uncomparable();
    };
    let (LengthKind::Px | LengthKind::Rem, Some(px)) = (length.kind, length.px) else {
        return uncomparable();
    };
    let choice = scale_and_token(spec, prefix);
    let off = off_scale(px, choice.steps)?;
    let token = |step: f64| (choice.token)(&spec.tokens, step);
    let nearest = token(off.nearest);
    if (off.upper - off.lower).abs() < f64::EPSILON {
        return Some(format!(
            "arbitrary value '{name}' is off the scale; beyond var({nearest}), the nearest step; nearest is {nearest}"
        ));
    }
    Some(format!(
        "arbitrary value '{name}' is off the scale; between var({}) and var({}); nearest is {nearest}",
        token(off.lower),
        token(off.upper),
    ))
}
