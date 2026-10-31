//! Terminal capability detection and the semantic palette, shared by every goblin's presenter.
//!
//! - [`Capabilities`]: a pure function of an injected [`EnvSnapshot`] and [`StreamFacts`].
//! - [`Palette`]: semantic [`Role`] styles; [`Palette::plain`] is what a no-colour stream gets.
//!
//! Nothing here touches stdout or stderr or reads the wall clock.

mod caps;
mod palette;

pub use caps::{Capabilities, EnvSnapshot, StreamCaps, StreamFacts};
pub use palette::{Glyphs, Palette, Role};
