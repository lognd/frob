//! Inputs and outputs of text measurement.

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C

/// The text style a measurement is taken under.
#[derive(Debug, Clone, PartialEq)]
pub struct TextStyle {
    /// Requested font family; must be bundled.
    pub font: String,
    /// Font size in px.
    pub size_px: f32,
    /// Extra advance per glyph in px.
    pub letter_spacing_px: f32,
    /// Line height as a multiple of the font size.
    pub line_height: f32,
    /// `white-space: nowrap`: never wrap (hard newlines still break).
    pub nowrap: bool,
}

impl TextStyle {
    /// A plain style: no letter spacing, 1.2 line height, wrapping allowed.
    pub fn new(font: &str, size_px: f32) -> Self {
        Self {
            font: font.to_string(),
            size_px,
            letter_spacing_px: 0.0,
            line_height: 1.2,
            nowrap: false,
        }
    }
}

/// The width constraint a measurement answers.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum AvailableWidth {
    /// Wrap at this many px (zero behaves as min-content).
    Definite(f32),
    /// The narrowest width that avoids avoidable overflow.
    MinContent,
    /// The width of the text laid out on unwrapped lines.
    MaxContent,
}

impl From<taffy::AvailableSpace> for AvailableWidth {
    fn from(a: taffy::AvailableSpace) -> Self {
        match a {
            taffy::AvailableSpace::Definite(w) => Self::Definite(w),
            taffy::AvailableSpace::MinContent => Self::MinContent,
            taffy::AvailableSpace::MaxContent => Self::MaxContent,
        }
    }
}

/// A non-fatal observation made while measuring.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MeasureNote {
    /// A glyph was absent from the requested font and came from the fallback (or is notdef).
    MissingGlyph,
}

/// The result of one measurement.
#[derive(Debug, Clone, PartialEq)]
pub struct Measured {
    /// Widest line in px.
    pub width: f32,
    /// Total height in px.
    pub height: f32,
    /// Number of lines (zero for empty text).
    pub lines: u32,
    /// Observations such as `missing_glyph`.
    pub notes: Vec<MeasureNote>,
}

impl Measured {
    /// The measurement of empty text.
    pub(crate) fn empty() -> Self {
        Self {
            width: 0.0,
            height: 0.0,
            lines: 0,
            notes: Vec::new(),
        }
    }
}
