//! Deterministic text measurement for the solver over bundled fonts (design crunk.md section 3, D113).
//! Shaping is parley, chosen by the text-shaping spike; no system font lookup ever happens.

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C

mod error;
mod fonts;
mod measure;
mod style;

pub use error::TextError;
pub use fonts::{FALLBACK_FONT, bundled_fonts};
pub use measure::{TextMeasurer, measure_for_taffy};
pub use style::{AvailableWidth, MeasureNote, Measured, TextStyle};
