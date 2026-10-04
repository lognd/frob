//! Color parsing and the contrast/distance math built on it.

use crate::error::ColorError;
use crate::named::named_color;
use crate::num::parse_number;

/// A parsed color in 0-1 sRGB channels, with the contrast/distance math on it.
///
/// Fields are public and unclamped; [`Color::parse`] always yields channels in `[0, 1]`.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Color {
    /// Red, 0-1.
    pub r: f64,
    /// Green, 0-1.
    pub g: f64,
    /// Blue, 0-1.
    pub b: f64,
    /// Alpha, 0-1 (1 is opaque).
    pub a: f64,
}

/// Clamps a channel to the `[0, 1]` range `Color` stores everything in.
fn clamp01(value: f64) -> f64 {
    value.clamp(0.0, 1.0)
}

/// Interprets a number or percent token as a 0-1 value; `scale` divides plain numbers.
fn unit_token(token: &str, scale: f64) -> Option<f64> {
    match token.strip_suffix('%') {
        Some(num) => parse_number(num).map(|v| clamp01(v / 100.0)),
        None => parse_number(token).map(|v| clamp01(v / scale)),
    }
}

/// Parses an `rgb()` channel token (0-255 number or percent) to 0-1.
fn rgb_channel(token: &str) -> Option<f64> {
    unit_token(token, 255.0)
}

/// Parses an alpha token (0-1 number or percent) to 0-1.
fn alpha_token(token: &str) -> Option<f64> {
    unit_token(token, 1.0)
}

/// Parses a `NUM%` token to a clamped 0-1 fraction.
fn percent_token(token: &str) -> Option<f64> {
    parse_number(token.strip_suffix('%')?).map(|v| clamp01(v / 100.0))
}

/// Splits the argument text of a function into its main tokens and optional alpha token.
///
/// Accepts the comma form (`a, b, c[, alpha]`) and the space form (`a b c[ / alpha]`) and
/// nothing else, mirroring the two alternatives of the Python regexes.
fn function_args(inner: &str) -> Option<(Vec<&str>, Option<&str>)> {
    if inner.contains(',') {
        if inner.contains('/') {
            return None;
        }
        let parts: Vec<&str> = inner.split(',').map(str::trim).collect();
        return match parts.len() {
            3 => Some((parts, None)),
            4 => Some((parts[..3].to_vec(), Some(parts[3]))),
            _ => None,
        };
    }
    let (main, alpha) = match inner.split_once('/') {
        Some((main, alpha)) if !alpha.contains('/') => (main, Some(alpha.trim())),
        Some(_) => return None,
        None => (inner, None),
    };
    let tokens: Vec<&str> = main.split_whitespace().collect();
    (tokens.len() == 3).then_some((tokens, alpha))
}

/// Extracts the text between `<name>(` / `<name>a(` and the closing `)`.
fn function_inner<'a>(text: &'a str, name: &str) -> Option<&'a str> {
    let rest = text.strip_prefix(name)?;
    let rest = rest.strip_prefix('a').unwrap_or(rest);
    rest.strip_prefix('(')?.strip_suffix(')')
}

/// Expands a `#rgb`/`#rgba`/`#rrggbb`/`#rrggbbaa` digit run into a color.
fn hex_to_color(digits: &str) -> Result<Color, ColorError> {
    let byte = |s: &str| f64::from(u8::from_str_radix(s, 16).unwrap_or(0)) / 255.0;
    let short = |i: usize| {
        let c = &digits[i..=i];
        byte(&format!("{c}{c}"))
    };
    match digits.len() {
        3 => Ok(Color::new(short(0), short(1), short(2), 1.0)),
        4 => Ok(Color::new(short(0), short(1), short(2), short(3))),
        6 => Ok(Color::new(
            byte(&digits[0..2]),
            byte(&digits[2..4]),
            byte(&digits[4..6]),
            1.0,
        )),
        8 => Ok(Color::new(
            byte(&digits[0..2]),
            byte(&digits[2..4]),
            byte(&digits[4..6]),
            byte(&digits[6..8]),
        )),
        len => {
            tracing::debug!(digits, "color parse reject: bad hex length");
            Err(ColorError::BadHexLength { len })
        }
    }
}

/// Parses lowercase `rgb()`/`rgba()` text, comma or space syntax, numbers or percentages.
fn parse_rgb(text: &str) -> Result<Color, ColorError> {
    let bad = || {
        tracing::debug!(text, "color parse reject: bad rgb()");
        ColorError::BadRgb
    };
    let inner = function_inner(text, "rgb").ok_or_else(bad)?;
    let (main, alpha) = function_args(inner).ok_or_else(bad)?;
    let chans: Option<Vec<f64>> = main.iter().map(|t| rgb_channel(t)).collect();
    let chans = chans.ok_or_else(bad)?;
    let a = match alpha {
        Some(t) => alpha_token(t).ok_or_else(bad)?,
        None => 1.0,
    };
    Ok(Color::new(chans[0], chans[1], chans[2], a))
}

/// One channel of the HSL hue wheel; helper for [`hsl_to_rgb`].
fn hue_to_rgb(p: f64, q: f64, mut t: f64) -> f64 {
    if t < 0.0 {
        t += 1.0;
    }
    if t > 1.0 {
        t -= 1.0;
    }
    if t < 1.0 / 6.0 {
        p + (q - p) * 6.0 * t
    } else if t < 0.5 {
        q
    } else if t < 2.0 / 3.0 {
        p + (q - p) * (2.0 / 3.0 - t) * 6.0
    } else {
        p
    }
}

/// Standard HSL to RGB conversion (inputs and outputs 0-1, hue in turns).
fn hsl_to_rgb(h: f64, s: f64, light: f64) -> (f64, f64, f64) {
    if s == 0.0 {
        return (light, light, light);
    }
    let q = if light < 0.5 {
        light * (1.0 + s)
    } else {
        light + s - light * s
    };
    let p = 2.0 * light - q;
    (
        hue_to_rgb(p, q, h + 1.0 / 3.0),
        hue_to_rgb(p, q, h),
        hue_to_rgb(p, q, h - 1.0 / 3.0),
    )
}

/// Parses lowercase `hsl()`/`hsla()` text, comma or space syntax, degrees plus percents.
fn parse_hsl(text: &str) -> Result<Color, ColorError> {
    let bad = || {
        tracing::debug!(text, "color parse reject: bad hsl()");
        ColorError::BadHsl
    };
    let inner = function_inner(text, "hsl").ok_or_else(bad)?;
    let (main, alpha) = function_args(inner).ok_or_else(bad)?;
    let hue_text = main[0].strip_suffix("deg").unwrap_or(main[0]);
    let hue = parse_number(hue_text).ok_or_else(bad)?.rem_euclid(360.0) / 360.0;
    let sat = percent_token(main[1]).ok_or_else(bad)?;
    let light = percent_token(main[2]).ok_or_else(bad)?;
    let a = match alpha {
        Some(t) => alpha_token(t).ok_or_else(bad)?,
        None => 1.0,
    };
    let (r, g, b) = hsl_to_rgb(hue, sat, light);
    Ok(Color::new(r, g, b, a))
}

/// WCAG linearization of one sRGB channel; the one home other math shares.
fn srgb_to_linear(c: f64) -> f64 {
    if c <= 0.03928 {
        c / 12.92
    } else {
        ((c + 0.055) / 1.055).powf(2.4)
    }
}

/// Rounds a 0-1 channel to a 0-255 byte, half to even like Python's `round`.
fn to_byte(channel: f64) -> u8 {
    // Clamped to [0, 255] and rounded, so the cast cannot truncate or wrap.
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    let byte = (clamp01(channel) * 255.0).round_ties_even() as u8;
    byte
}

impl Color {
    /// Builds a color from raw channels without clamping.
    pub const fn new(r: f64, g: f64, b: f64, a: f64) -> Self {
        Self { r, g, b, a }
    }

    /// Parses hex, `rgb()`/`rgba()`, `hsl()`/`hsla()` or CSS named-color syntax.
    ///
    /// Channels are clamped to `[0, 1]`. Anything else (`var()`, gradients, `currentcolor`)
    /// is an error, never a panic.
    ///
    /// # Errors
    ///
    /// [`ColorError`] naming why the text was rejected.
    pub fn parse(text: &str) -> Result<Self, ColorError> {
        let candidate = text.trim();
        if candidate.is_empty() {
            tracing::debug!(raw = text, "color parse reject: empty text");
            return Err(ColorError::Empty);
        }
        if let Some(digits) = candidate.strip_prefix('#')
            && (3..=8).contains(&digits.len())
            && digits.bytes().all(|b| b.is_ascii_hexdigit())
        {
            return hex_to_color(digits);
        }
        let lowered = candidate.to_lowercase();
        if lowered.starts_with("rgb") {
            return parse_rgb(&lowered);
        }
        if lowered.starts_with("hsl") {
            return parse_hsl(&lowered);
        }
        if let Some([r, g, b, a]) = named_color(&lowered) {
            let ch = |v: u8| f64::from(v) / 255.0;
            return Ok(Self::new(ch(r), ch(g), ch(b), ch(a)));
        }
        tracing::debug!(raw = text, "color parse reject: unrecognized");
        Err(ColorError::Unrecognized(candidate.to_owned()))
    }

    /// Redmean-weighted sRGB distance: the stand-in for perceptual distance (alpha ignored).
    pub fn distance(self, other: Self) -> f64 {
        let (r1, g1, b1) = (self.r * 255.0, self.g * 255.0, self.b * 255.0);
        let (r2, g2, b2) = (other.r * 255.0, other.g * 255.0, other.b * 255.0);
        let mean_r = f64::midpoint(r1, r2);
        let (dr, dg, db) = (r1 - r2, g1 - g2, b1 - b2);
        let weight_r = 2.0 + mean_r / 256.0;
        let weight_b = 2.0 + (255.0 - mean_r) / 256.0;
        (weight_r * dr * dr + 4.0 * dg * dg + weight_b * db * db).sqrt()
    }

    /// WCAG 2.x relative luminance, ignoring alpha.
    pub fn relative_luminance(self) -> f64 {
        0.2126 * srgb_to_linear(self.r)
            + 0.7152 * srgb_to_linear(self.g)
            + 0.0722 * srgb_to_linear(self.b)
    }

    /// WCAG 2.x contrast ratio; symmetric, always at least 1.0 for in-range channels.
    pub fn contrast_ratio(self, other: Self) -> f64 {
        let (l1, l2) = (self.relative_luminance(), other.relative_luminance());
        (l1.max(l2) + 0.05) / (l1.min(l2) + 0.05)
    }

    /// True when alpha is fully opaque (`a >= 1.0`); the one home of that threshold.
    pub fn is_opaque(self) -> bool {
        self.a >= 1.0
    }

    /// Canonical lowercase `#rrggbb` of the RGB channels alone, alpha ignored.
    pub fn rgb_hex(self) -> String {
        format!(
            "#{:02x}{:02x}{:02x}",
            to_byte(self.r),
            to_byte(self.g),
            to_byte(self.b)
        )
    }

    /// Canonical lowercase `#rrggbb`, or `#rrggbbaa` when alpha is not opaque.
    pub fn to_hex(self) -> String {
        if self.is_opaque() {
            self.rgb_hex()
        } else {
            format!("{}{:02x}", self.rgb_hex(), to_byte(self.a))
        }
    }
}
