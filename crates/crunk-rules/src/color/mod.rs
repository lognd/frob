//! Colour judgments shared by COLOR001 and the rules that follow it: palette conformance and the
//! nearest palette entry (port of `crunk/rules/_color.py`).
//!
//! A literal conforms when its `to_hex()` matches a palette entry, or when it is translucent and
//! its `rgb_hex()` matches an opaque palette entry (a translucent variant of an opaque palette
//! colour is not a new colour).

// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

use std::collections::BTreeSet;

use crunk_values::Color;

pub mod defs;

/// A mode's palette with the hex sets conformance needs, kept with the entries for nearest lookups.
#[derive(Debug)]
pub struct Palette<'a> {
    entries: Vec<(&'a str, Color)>,
    exact: BTreeSet<String>,
    opaque_rgb: BTreeSet<String>,
}

impl<'a> Palette<'a> {
    /// The palette over `entries`, `(name, colour)` in declaration order.
    pub fn new(entries: Vec<(&'a str, Color)>) -> Self {
        Self {
            exact: entries.iter().map(|(_, c)| c.to_hex()).collect(),
            opaque_rgb: entries
                .iter()
                .filter(|(_, c)| c.is_opaque())
                .map(|(_, c)| c.rgb_hex())
                .collect(),
            entries,
        }
    }

    /// True when `color` needs no violation (exact hex, or translucent over an opaque entry).
    pub fn conforms(&self, color: Color) -> bool {
        self.exact.contains(&color.to_hex())
            || (!color.is_opaque() && self.opaque_rgb.contains(&color.rgb_hex()))
    }

    /// The closest palette entry by [`Color::distance`] and that distance, first on ties; `None`
    /// for an empty palette.
    pub fn nearest(&self, color: Color) -> Option<(&'a str, f64)> {
        self.entries
            .iter()
            .map(|(n, c)| (*n, color.distance(*c)))
            .fold(None, |best: Option<(&str, f64)>, cur| match best {
                Some(b) if b.1 <= cur.1 => Some(b),
                _ => Some(cur),
            })
    }
}

/// The COLOR001 message, alpha-aware: a translucent literal names the rgb distance and says the
/// fix preserves alpha. `within_tolerance` states whether the nearest entry is close enough to
/// replace automatically (`[lint] color_tolerance`).
pub fn off_palette_message(
    color: Color,
    token: &str,
    distance: f64,
    within_tolerance: bool,
) -> String {
    let hexed = color.to_hex();
    let mut message = if color.is_opaque() {
        format!("color {hexed} is not a palette color; nearest is {token} (distance {distance:.2})")
    } else {
        format!(
            "color {hexed} is not a palette color; nearest is {token} (rgb distance {distance:.2}); the fix preserves alpha"
        )
    };
    if !within_tolerance {
        message.push_str("; beyond color_tolerance, so no automatic replacement");
    }
    message
}
