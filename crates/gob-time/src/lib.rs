//! One clock, one zone (docs/design/time.md, D93): the only crate that reads the wall clock.
//!
//! - [`Stamp`]: a UTC instant, RFC 3339 with `Z`; the type of everything persisted or compared.
//! - [`Day`]: a UTC calendar day; the type of cycles, due dates and release dates.
//! - [`Shown`]: render-only local display text; the one conversion to the user's zone.
//! - [`Clock`]: `now()` and a derived `today()`; [`SystemClock`] reads the system, [`FixedClock`]
//!   returns a set instant. A verb reads its clock once ([`SystemClock::pin`]) so every date a
//!   command writes comes from one snapshot.
//!
//! Workspace `clippy.toml` forbids the wall-clock and local-zone reads everywhere else.

mod clock;
mod day;
mod shown;
mod stamp;
mod wall;

pub use clock::{Clock, FixedClock, SystemClock};
pub use day::Day;
pub use shown::Shown;
pub use stamp::Stamp;
