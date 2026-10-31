//! Terminal presentation (docs/design/output.md): palette, capability detection and the
//! `Presenter` implementations with the stage bar and throbber.
//!
//! - [`Capabilities`]: a pure function of an injected [`EnvSnapshot`] and [`StreamFacts`].
//! - [`Palette`]: semantic [`Role`] styles; [`Palette::plain`] is what a no-colour stream gets.
//! - [`Presenter`]: [`Quiet`], [`Plain`] and [`Live`], chosen by [`select`] / [`build`].
//!
//! Every byte goes through an injected writer; nothing here touches stdout or stderr directly,
//! reads the wall clock, or prints with the `println` family.

mod error;
pub mod events;
mod presenter;
mod stage;
mod widget;

pub use error::PresentError;
pub use gob_term::{Capabilities, EnvSnapshot, Glyphs, Palette, Role, StreamCaps, StreamFacts};
pub use presenter::{Kind, Live, Plain, Presenter, Quiet, build, select};
pub use stage::{
    Outcome, ProfileReport, ProfileRow, ProfileView, SLOW_SHARE, StageId, StageTiming,
};
pub use widget::{bar, fmt_elapsed, status_line};
