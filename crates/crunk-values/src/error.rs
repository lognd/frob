//! Typed parse errors for colors and lengths.

/// Why a CSS color literal was rejected by [`crate::Color::parse`].
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum ColorError {
    /// The text was empty or whitespace only.
    #[error("empty color text")]
    Empty,
    /// A `#` literal had a digit run that is not 3, 4, 6 or 8 digits long.
    #[error("hex color has {len} digits; expected 3, 4, 6 or 8")]
    BadHexLength {
        /// Number of hex digits after the `#`.
        len: usize,
    },
    /// An `rgb()`/`rgba()` literal was malformed.
    #[error("malformed rgb()/rgba() color")]
    BadRgb,
    /// An `hsl()`/`hsla()` literal was malformed.
    #[error("malformed hsl()/hsla() color")]
    BadHsl,
    /// The text is not a hex, rgb, hsl or named color (`var()`, gradients, `currentcolor`, ...).
    #[error("unrecognized color `{0}`")]
    Unrecognized(String),
}

/// Why a CSS length token was rejected by [`crate::Length::parse`].
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum LengthError {
    /// The text was empty or whitespace only.
    #[error("empty length text")]
    Empty,
    /// A nonzero number with no unit.
    #[error("unitless nonzero length `{0}`")]
    UnitlessNonzero(String),
    /// A number followed by a unit crunk does not know.
    #[error("unknown length unit `{unit}` in `{text}`")]
    UnknownUnit {
        /// The whole (trimmed) length text.
        text: String,
        /// The unrecognized unit suffix, lowercased.
        unit: String,
    },
    /// The text is not a length at all.
    #[error("unrecognized length `{0}`")]
    Unrecognized(String),
}
