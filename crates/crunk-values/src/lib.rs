//! Pure CSS value math for crunk: colors, lengths, WCAG contrast and palette distance.
//!
//! Every function is pure (no I/O, no global state) and returns a typed error rather than
//! panicking, so the API is safe to expose as built-in functions elsewhere. Behaviour is a
//! port of the Python crunk `crunk.values` package, pinned by reference vectors.
//!
//! # Overview
//!
//! - [`Color`]: 0-1 sRGB channels plus alpha; [`Color::parse`], [`Color::distance`],
//!   [`Color::contrast_ratio`], [`Color::to_hex`].
//! - [`Length`] / [`LengthKind`]: [`Length::parse`] with a root font size for `rem`.
//! - [`NAMED_COLORS`] / [`named_color`]: the CSS named-color table.
//! - [`ColorError`] / [`LengthError`]: why a literal was rejected.
//!
//! ```
//! use crunk_values::{Color, Length};
//!
//! let black = Color::parse("#000").unwrap();
//! let white = Color::parse("white").unwrap();
//! assert!((black.contrast_ratio(white) - 21.0).abs() < 1e-9);
//!
//! let gap = Length::parse("2rem", 20.0).unwrap();
//! assert_eq!(gap.px, Some(40.0));
//! ```
//!
//! # Known divergences from the Python crunk
//!
//! Digits are ASCII only (Python's `\d` also accepts other Unicode digits). Rejections are
//! typed errors instead of `Nothing`.

mod color;
mod error;
mod length;
mod named;
mod num;

pub use color::Color;
pub use error::{ColorError, LengthError};
pub use length::{Length, LengthKind};
pub use named::{NAMED_COLORS, named_color};
