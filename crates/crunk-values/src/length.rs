//! CSS length parsing: px-comparable values plus the kinds that are not.

use crate::error::LengthError;
use crate::num::split_number;

/// Units that parse as a length but carry no px value (Python `_OTHER_UNIT_RE`).
const OTHER_UNITS: &[&str] = &[
    "em", "vh", "vw", "vmin", "vmax", "pt", "pc", "in", "cm", "mm", "ex", "ch", "fr", "q",
];

/// Names why a [`Length`] does or does not carry a px-comparable value.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum LengthKind {
    /// A `px` length.
    Px,
    /// A `rem` length, converted with the root font size.
    Rem,
    /// The unitless number zero.
    Zero,
    /// A percentage; no px value.
    Percent,
    /// The `auto` keyword; no px value.
    Auto,
    /// A `calc(...)` expression; no px value.
    Calc,
    /// A known unit that is not px-comparable (`em`, `vh`, `pt`, ...); no px value.
    Other,
}

impl LengthKind {
    /// The lowercase name the Python crunk uses for this kind.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Px => "px",
            Self::Rem => "rem",
            Self::Zero => "zero",
            Self::Percent => "percent",
            Self::Auto => "auto",
            Self::Calc => "calc",
            Self::Other => "other",
        }
    }
}

/// A parsed CSS length: the `raw` text, an optional px value, and its kind.
#[derive(Debug, Clone, PartialEq)]
pub struct Length {
    /// The text exactly as given (untrimmed).
    pub raw: String,
    /// The px value, present only for px, rem and zero lengths.
    pub px: Option<f64>,
    /// Why `px` is or is not present.
    pub kind: LengthKind,
}

impl Length {
    /// Parses a CSS length token; `rem` is multiplied by `root_font_size` (px).
    ///
    /// Percent, `auto`, `calc()` and other units yield `px: None` with a kind naming why.
    ///
    /// # Errors
    ///
    /// [`LengthError`] for empty text, a unitless nonzero number, an unknown unit, or text
    /// that is not a length.
    pub fn parse(text: &str, root_font_size: f64) -> Result<Self, LengthError> {
        let candidate = text.trim();
        if candidate.is_empty() {
            tracing::debug!(raw = text, "length parse reject: empty text");
            return Err(LengthError::Empty);
        }
        let lowered = candidate.to_lowercase();
        let make = |px, kind| Self {
            raw: text.to_owned(),
            px,
            kind,
        };

        if lowered == "auto" {
            return Ok(make(None, LengthKind::Auto));
        }
        if lowered.len() >= 6
            && lowered.starts_with("calc(")
            && lowered.ends_with(')')
            && !lowered.contains('\n')
        {
            return Ok(make(None, LengthKind::Calc));
        }
        let Some((value, unit)) = split_number(&lowered) else {
            tracing::debug!(raw = text, "length parse reject: unrecognized");
            return Err(LengthError::Unrecognized(candidate.to_owned()));
        };
        match unit {
            "" if value == 0.0 => Ok(make(Some(0.0), LengthKind::Zero)),
            "" => {
                tracing::debug!(raw = text, "length parse reject: unitless nonzero");
                Err(LengthError::UnitlessNonzero(candidate.to_owned()))
            }
            "px" => Ok(make(Some(value), LengthKind::Px)),
            "rem" => Ok(make(Some(value * root_font_size), LengthKind::Rem)),
            "%" => Ok(make(None, LengthKind::Percent)),
            u if OTHER_UNITS.contains(&u) => Ok(make(None, LengthKind::Other)),
            u if u.bytes().all(|b| b.is_ascii_alphabetic()) => {
                tracing::debug!(raw = text, unit = u, "length parse reject: unknown unit");
                Err(LengthError::UnknownUnit {
                    text: candidate.to_owned(),
                    unit: u.to_owned(),
                })
            }
            _ => {
                tracing::debug!(raw = text, "length parse reject: unrecognized");
                Err(LengthError::Unrecognized(candidate.to_owned()))
            }
        }
    }
}
