//! Terminal presentation (docs/design/output.md): palette, capability detection and the
//! `Presenter` implementations with the stage bar and throbber.
//!
//! - [`Capabilities`]: a pure function of an injected [`EnvSnapshot`] and [`StreamFacts`].
//! - [`Palette`]: semantic [`Role`] styles; [`Palette::plain`] is what a no-colour stream gets.
//! - [`Presenter`]: [`Quiet`], [`Plain`] and [`Live`], chosen by [`select`] / [`build`].
//!
//! Every byte goes through an injected writer; nothing here touches stdout or stderr directly,
//! reads the wall clock, or prints with the `println` family.

mod caps;
mod error;
mod palette;
mod presenter;
mod stage;
mod widget;

pub use caps::{Capabilities, EnvSnapshot, StreamCaps, StreamFacts};
pub use error::PresentError;
pub use palette::{Glyphs, Palette, Role};
pub use presenter::{Kind, Live, Plain, Presenter, Quiet, build, select};
pub use stage::{Outcome, ProfileReport, StageId, StageTiming};
pub use widget::{bar, fmt_elapsed, status_line};
