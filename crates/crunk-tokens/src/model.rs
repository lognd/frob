//! The token model: [`TokenSet`], the tokens derived from a [`DesignSpec`], and the types every
//! exporter, `explain` and `query` read.
//!
//! The model is shaped to grow into the DTCG 2025.10 shape (docs/design/crunk.md section 2)
//! without a rewrite: a [`Tier`] (primitive, semantic, component), aliases ([`TokenValue::Alias`]),
//! composites ([`TokenValue::Composite`]), per-mode overrides ([`Token::modes`]), binding
//! [`Scope`]s and the timing and easing value types are all present, while `crunk.toml` today
//! only produces primitive color, dimension, number and font-family tokens.

// frob:ticket 01M43ARZAJ8NJ3F38157ERAKR5

use std::collections::BTreeSet;

use crunk_spec::DesignSpec;
use crunk_spec::naming::{
    color_token, font_family_stack_token, font_family_token, font_size_token, format_step,
    layer_token, radius_token, size_token, space_token,
};
use crunk_tailwind::defaults::{
    V3_BORDER_RADIUS_KEYS, V3_FONT_SIZE_KEYS, V3_SPACING_KEYS, V3_Z_INDEX_KEYS, has_key,
};
use crunk_values::Color;
use indexmap::IndexMap;
use serde::Serialize;
use thiserror::Error;

use crate::naming::{bare_name, channels_name, scale_key, var_ref};

/// Why a [`TokenSet`] could not be built.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum TokenError {
    /// Two spec entries produce the same custom property name.
    #[error("token `{name}` is declared twice: {first} and {second}")]
    Collision {
        /// The custom property name both entries produce.
        name: String,
        /// Where the first entry was declared.
        first: String,
        /// Where the second entry was declared.
        second: String,
    },
}

/// The DTCG tier a token sits in.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
#[non_exhaustive]
pub enum Tier {
    /// A raw value; everything `crunk.toml` declares today.
    Primitive,
    /// A purpose-named alias of a primitive.
    Semantic,
    /// A token scoped to one component.
    Component,
}

/// The family a token belongs to; fixes its naming prefix and Tailwind section.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize)]
#[serde(rename_all = "snake_case")]
#[non_exhaustive]
pub enum TokenKind {
    /// A `[palette]` color.
    Color,
    /// The `-rgb` alpha-channel triplet companion of a color.
    ColorChannels,
    /// A `[scales] spacing` step.
    Space,
    /// A `[scales] font_sizes` step.
    FontSize,
    /// A `[scales] radii` step.
    Radius,
    /// A `[scales] sizes` step.
    Size,
    /// A `[layers]` z-index.
    Layer,
    /// The `base` font-family stack or a `[typography.stacks]` entry.
    FontFamily,
}

/// A property kind a token may bind to (DTCG and Figma scopes); empty scopes mean unrestricted.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
#[non_exhaustive]
pub enum Scope {
    /// Fill, stroke and text colors.
    Color,
    /// Gap, margin and padding.
    Spacing,
    /// Font size.
    FontSize,
    /// Corner radius.
    Radius,
    /// Width and height.
    Size,
    /// Stacking order.
    ZIndex,
    /// Font family.
    FontFamily,
}

/// The unit of a [`TokenValue::Dimension`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
#[non_exhaustive]
pub enum Unit {
    /// CSS pixels, the only unit scales declare.
    Px,
}

/// A token's value, in the DTCG value types crunk models.
#[derive(Debug, Clone, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
#[non_exhaustive]
pub enum TokenValue {
    /// A color.
    #[serde(serialize_with = "serialize_color")]
    Color(Color),
    /// An sRGB triplet, 0 to 255 per channel (the `-rgb` companion).
    Channels {
        /// Red.
        r: u8,
        /// Green.
        g: u8,
        /// Blue.
        b: u8,
    },
    /// A length.
    Dimension {
        /// The magnitude.
        value: f64,
        /// Its unit.
        unit: Unit,
    },
    /// A bare number (a z-index).
    Number(i64),
    /// An ordered font-family stack.
    FontFamily(Vec<String>),
    /// A duration in milliseconds (DTCG `duration`).
    Duration(f64),
    /// A cubic-bezier easing: x1, y1, x2, y2 (DTCG `cubicBezier`).
    CubicBezier([f64; 4]),
    /// A reference to another token by custom property name.
    Alias(String),
    /// A composite (typography, shadow, border, transition): named sub-values.
    Composite(IndexMap<String, TokenValue>),
}

fn serialize_color<S: serde::Serializer>(color: &Color, s: S) -> Result<S::Ok, S::Error> {
    s.serialize_str(&color.to_hex())
}

impl TokenValue {
    /// The value as CSS text, or `None` for a composite (it has no single CSS value).
    pub fn css(&self) -> Option<String> {
        match self {
            Self::Color(color) => Some(color.to_hex()),
            Self::Channels { r, g, b } => Some(format!("{r} {g} {b}")),
            Self::Dimension { value, unit } => {
                Some(format!("{}{}", length_number(*value), unit.css()))
            }
            Self::Number(n) => Some(n.to_string()),
            Self::FontFamily(names) => Some(
                names
                    .iter()
                    .map(|n| quote_family(n))
                    .collect::<Vec<_>>()
                    .join(", "),
            ),
            Self::Duration(ms) => Some(format!("{}ms", length_number(*ms))),
            Self::CubicBezier([a, b, c, d]) => Some(format!(
                "cubic-bezier({}, {}, {}, {})",
                length_number(*a),
                length_number(*b),
                length_number(*c),
                length_number(*d)
            )),
            Self::Alias(target) => Some(var_ref(target)),
            Self::Composite(_) => None,
        }
    }
}

impl Unit {
    fn css(self) -> &'static str {
        match self {
            Self::Px => "px",
        }
    }
}

/// Render a magnitude: whole values drop the fraction, others print shortest-round-trip.
///
/// Rust never prints an exponent, so a magnitude below `1e-4` or above `1e16` renders
/// positionally where Python's `repr` would print one.
#[allow(
    clippy::float_cmp,
    reason = "a magnitude is whole exactly when it equals its truncation"
)]
fn length_number(value: f64) -> String {
    if value == 0.0 {
        "0".to_owned()
    } else if value == value.trunc() && value.abs() < 1e15 {
        format!("{value:.0}")
    } else {
        value.to_string()
    }
}

/// Double-quote a font family name containing whitespace; single-word names pass through.
fn quote_family(name: &str) -> String {
    if name.chars().any(char::is_whitespace) {
        format!("\"{name}\"")
    } else {
        name.to_owned()
    }
}

/// Clamp a 0-1 channel and round it to a 0-255 byte, ties to even (Python's `round`).
#[allow(
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    reason = "the value is clamped to [0, 255] before the cast"
)]
fn channel_byte(value: f64) -> u8 {
    (value.clamp(0.0, 1.0) * 255.0).round_ties_even() as u8
}

/// One design token.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Token {
    /// The custom property name, with its leading `--` (`--color-ink`).
    pub name: String,
    /// The family the token belongs to.
    pub kind: TokenKind,
    /// The spec key: the palette or layer name as written, the stack name, or the formatted
    /// scale step (`8`, `6_5`). Tailwind theme keys derive from it.
    pub key: String,
    /// Where in `crunk.toml` the token comes from, for messages (`[palette] ink`).
    pub origin: String,
    /// The token's tier.
    pub tier: Tier,
    /// The default (no-mode) value.
    pub value: TokenValue,
    /// Per-mode value overrides by mode name; empty until modes land.
    pub modes: IndexMap<String, TokenValue>,
    /// Property kinds the token may bind to; empty means unrestricted.
    pub scopes: Vec<Scope>,
    /// Free-text description, when authored.
    pub description: Option<String>,
}

/// A Tailwind `theme` section a token can map into.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize)]
#[serde(rename_all = "camelCase")]
pub enum ThemeSection {
    /// `colors`.
    Colors,
    /// `spacing`.
    Spacing,
    /// `fontSize`.
    FontSize,
    /// `borderRadius`.
    BorderRadius,
    /// `zIndex`.
    ZIndex,
    /// `width`.
    Width,
    /// `height`.
    Height,
    /// `minWidth`.
    MinWidth,
    /// `minHeight`.
    MinHeight,
    /// `maxWidth`.
    MaxWidth,
    /// `maxHeight`.
    MaxHeight,
}

/// Every [`ThemeSection`] in the order a merged theme mapping applies them (later wins).
pub const THEME_SECTIONS: [ThemeSection; 11] = [
    ThemeSection::Colors,
    ThemeSection::Spacing,
    ThemeSection::FontSize,
    ThemeSection::BorderRadius,
    ThemeSection::ZIndex,
    ThemeSection::Width,
    ThemeSection::Height,
    ThemeSection::MinWidth,
    ThemeSection::MinHeight,
    ThemeSection::MaxWidth,
    ThemeSection::MaxHeight,
];

impl ThemeSection {
    /// The Tailwind `theme` key (`borderRadius`).
    pub fn name(self) -> &'static str {
        match self {
            Self::Colors => "colors",
            Self::Spacing => "spacing",
            Self::FontSize => "fontSize",
            Self::BorderRadius => "borderRadius",
            Self::ZIndex => "zIndex",
            Self::Width => "width",
            Self::Height => "height",
            Self::MinWidth => "minWidth",
            Self::MinHeight => "minHeight",
            Self::MaxWidth => "maxWidth",
            Self::MaxHeight => "maxHeight",
        }
    }

    /// The token family this section is built from.
    pub fn kind(self) -> TokenKind {
        match self {
            Self::Colors => TokenKind::Color,
            Self::Spacing => TokenKind::Space,
            Self::FontSize => TokenKind::FontSize,
            Self::BorderRadius => TokenKind::Radius,
            Self::ZIndex => TokenKind::Layer,
            Self::Width
            | Self::Height
            | Self::MinWidth
            | Self::MinHeight
            | Self::MaxWidth
            | Self::MaxHeight => TokenKind::Size,
        }
    }

    /// Tailwind v3's default keys of this section that a bare scale key would redefine.
    ///
    /// The sizing sections derive from Tailwind's spacing scale, so they collide with its
    /// spacing keys. Colors have no scale-step collision (palette names are authored).
    fn default_keys(self) -> &'static [&'static str] {
        match self {
            Self::Colors => &[],
            Self::Spacing
            | Self::Width
            | Self::Height
            | Self::MinWidth
            | Self::MinHeight
            | Self::MaxWidth
            | Self::MaxHeight => V3_SPACING_KEYS,
            Self::FontSize => V3_FONT_SIZE_KEYS,
            Self::BorderRadius => V3_BORDER_RADIUS_KEYS,
            Self::ZIndex => V3_Z_INDEX_KEYS,
        }
    }
}

/// A token key that, un-namespaced, would silently redefine a Tailwind default theme key.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct ThemeCollision {
    /// The colliding token's custom property name.
    pub token: String,
    /// The theme section it maps into.
    pub section: ThemeSection,
    /// The theme key shared with Tailwind's defaults.
    pub key: String,
}

impl Token {
    /// The Tailwind theme key of this token in `section`, or `None` when it does not map there.
    ///
    /// Palette and layer names are never namespaced; scale steps are keyed by their full token
    /// name when `namespaced`, else by the bare step.
    pub fn theme_key(&self, section: ThemeSection, namespaced: bool) -> Option<String> {
        if self.kind != section.kind() {
            return None;
        }
        Some(match self.kind {
            TokenKind::Color | TokenKind::Layer => self.key.clone(),
            _ => scale_key(&self.key, &self.name, namespaced),
        })
    }

    /// The Tailwind theme value of this token in `section`: `var(--x)`, or for a color under
    /// `alpha_channels` `rgb(var(--x-rgb) / <alpha-value>)`.
    pub fn theme_value(&self, section: ThemeSection, alpha_channels: bool) -> Option<String> {
        if self.kind != section.kind() {
            return None;
        }
        if self.kind == TokenKind::Color && alpha_channels {
            return Some(format!(
                "rgb({} / <alpha-value>)",
                var_ref(&channels_name(&self.name))
            ));
        }
        Some(var_ref(&self.name))
    }
}

/// The ordered, collision-free tokens derived from one [`DesignSpec`].
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct TokenSet {
    tokens: IndexMap<String, Token>,
}

/// Incremental builder that rejects a second token with an existing name.
struct Builder {
    tokens: IndexMap<String, Token>,
}

impl Builder {
    fn push(&mut self, token: Token) -> Result<(), TokenError> {
        if let Some(existing) = self.tokens.get(&token.name) {
            tracing::debug!(
                name = %token.name,
                first = %existing.origin,
                second = %token.origin,
                "token name collision"
            );
            return Err(TokenError::Collision {
                name: token.name,
                first: existing.origin.clone(),
                second: token.origin,
            });
        }
        self.tokens.insert(token.name.clone(), token);
        Ok(())
    }

    fn primitive(
        &mut self,
        name: String,
        kind: TokenKind,
        key: String,
        origin: String,
        value: TokenValue,
    ) -> Result<(), TokenError> {
        self.push(Token {
            name,
            kind,
            key,
            origin,
            tier: Tier::Primitive,
            value,
            modes: IndexMap::new(),
            scopes: Vec::new(),
            description: None,
        })
    }

    fn scale(
        &mut self,
        kind: TokenKind,
        steps: &[f64],
        scale: &str,
        name_of: impl Fn(f64) -> String,
    ) -> Result<(), TokenError> {
        for &step in steps {
            self.primitive(
                name_of(step),
                kind,
                format_step(step),
                format!("[scales] {scale} {}", format_step(step)),
                TokenValue::Dimension {
                    value: step,
                    unit: Unit::Px,
                },
            )?;
        }
        Ok(())
    }
}

impl TokenSet {
    /// Derive the token set from `spec`, in the Python crunk's emission order: palette colors,
    /// their `-rgb` companions (when `[tailwind] alpha_channels`), spacing, font sizes, radii,
    /// sizes, layers, the `base` font stack, then the declared stacks.
    ///
    /// # Errors
    ///
    /// [`TokenError::Collision`] naming both entries when two entries produce the same custom
    /// property name (palette names that sanitize alike, a prefix-free family overlapping
    /// another, a stack called `base`).
    pub fn from_spec(spec: &DesignSpec) -> Result<Self, TokenError> {
        let cfg = &spec.tokens;
        let mut b = Builder {
            tokens: IndexMap::new(),
        };
        for (name, color) in &spec.palette {
            b.primitive(
                color_token(cfg, name),
                TokenKind::Color,
                name.clone(),
                format!("[palette] {name}"),
                TokenValue::Color(*color),
            )?;
        }
        if spec.tailwind.alpha_channels {
            for (name, color) in &spec.palette {
                b.primitive(
                    channels_name(&color_token(cfg, name)),
                    TokenKind::ColorChannels,
                    name.clone(),
                    format!("[palette] {name} (alpha channels)"),
                    TokenValue::Channels {
                        r: channel_byte(color.r),
                        g: channel_byte(color.g),
                        b: channel_byte(color.b),
                    },
                )?;
            }
        }
        b.scale(TokenKind::Space, &spec.scales.spacing, "spacing", |s| {
            space_token(cfg, s)
        })?;
        b.scale(
            TokenKind::FontSize,
            &spec.scales.font_sizes,
            "font_sizes",
            |s| font_size_token(cfg, s),
        )?;
        b.scale(TokenKind::Radius, &spec.scales.radii, "radii", |s| {
            radius_token(cfg, s)
        })?;
        b.scale(TokenKind::Size, &spec.scales.sizes, "sizes", |s| {
            size_token(cfg, s)
        })?;
        for (name, z_index) in &spec.layers {
            b.primitive(
                layer_token(cfg, name),
                TokenKind::Layer,
                name.clone(),
                format!("[layers] {name}"),
                TokenValue::Number(*z_index),
            )?;
        }
        b.primitive(
            font_family_token(cfg),
            TokenKind::FontFamily,
            "base".to_owned(),
            "[typography] families".to_owned(),
            TokenValue::FontFamily(spec.typography.families.clone()),
        )?;
        for (stack, members) in &spec.typography.stacks {
            b.primitive(
                font_family_stack_token(cfg, stack),
                TokenKind::FontFamily,
                stack.clone(),
                format!("[typography.stacks] {stack}"),
                TokenValue::FontFamily(members.clone()),
            )?;
        }
        tracing::debug!(count = b.tokens.len(), "token set built");
        Ok(Self { tokens: b.tokens })
    }

    /// The number of tokens.
    pub fn len(&self) -> usize {
        self.tokens.len()
    }

    /// Whether the set has no tokens (a valid spec always has the font-family base).
    pub fn is_empty(&self) -> bool {
        self.tokens.is_empty()
    }

    /// The token with custom property name `name` (with its leading `--`).
    pub fn get(&self, name: &str) -> Option<&Token> {
        self.tokens.get(name)
    }

    /// Every token in emission order.
    pub fn iter(&self) -> impl Iterator<Item = &Token> {
        self.tokens.values()
    }

    /// Every token of `kind` in emission order.
    pub fn of_kind(&self, kind: TokenKind) -> impl Iterator<Item = &Token> {
        self.tokens.values().filter(move |t| t.kind == kind)
    }

    /// The set of custom property names the spec defines.
    pub fn names(&self) -> BTreeSet<&str> {
        self.tokens.keys().map(String::as_str).collect()
    }

    /// The ordered `(name, css value)` pairs every CSS and JSON export renders.
    ///
    /// Composite tokens have no single CSS value and are skipped; the spec produces none.
    pub fn css_entries(&self) -> Vec<(&str, String)> {
        self.tokens
            .values()
            .filter_map(|t| t.value.css().map(|v| (t.name.as_str(), v)))
            .collect()
    }

    /// The `(key, value)` rows of one Tailwind theme `section`, in emission order.
    pub fn theme_section(
        &self,
        section: ThemeSection,
        namespaced: bool,
        alpha_channels: bool,
    ) -> Vec<(String, String)> {
        self.of_kind(section.kind())
            .filter_map(|t| {
                Some((
                    t.theme_key(section, namespaced)?,
                    t.theme_value(section, alpha_channels)?,
                ))
            })
            .collect()
    }

    /// Every section merged into one flat utility-key to value mapping, later sections winning
    /// a key collision (colors, spacing, fontSize, borderRadius, zIndex, then the sizing ones).
    pub fn theme_mapping(
        &self,
        namespaced: bool,
        alpha_channels: bool,
    ) -> IndexMap<String, String> {
        let mut map = IndexMap::new();
        for section in THEME_SECTIONS {
            map.extend(self.theme_section(section, namespaced, alpha_channels));
        }
        map
    }

    /// The keys that, un-namespaced, would redefine a Tailwind v3 default theme key.
    ///
    /// Empty when `namespaced`, which is collision-free by construction.
    pub fn default_theme_collisions(&self, namespaced: bool) -> Vec<ThemeCollision> {
        if namespaced {
            return Vec::new();
        }
        let mut out = Vec::new();
        for section in THEME_SECTIONS {
            for token in self.of_kind(section.kind()) {
                let Some(key) = token.theme_key(section, false) else {
                    continue;
                };
                if has_key(section.default_keys(), &key) {
                    out.push(ThemeCollision {
                        token: token.name.clone(),
                        section,
                        key,
                    });
                }
            }
        }
        tracing::debug!(count = out.len(), "default theme collisions");
        out
    }

    /// The flat-JSON key of every token: its name without `--`.
    pub fn json_keys(&self) -> impl Iterator<Item = &str> {
        self.tokens.keys().map(|n| bare_name(n))
    }
}
