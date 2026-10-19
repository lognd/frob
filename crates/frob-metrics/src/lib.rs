//! Delivery metrics over the ticket fold: velocity and capacity, points remaining, throughput, cycle and lead times, and cost per point.
//!
//! Everything here is a pure function over plain facts ([`TicketFact`], closed cycles and their
//! done points), so the CLI gathers inputs once and `frob stats` renders text and JSON from the
//! one [`StatsReport`] value. Every figure is a [`Figure`]: below `[pm] min_history` samples it is
//! `Unresolved` with the sample count, never a number (pm-enforcement.md, forecasts).
// frob:ticket 01M48Q2AQXY69YKK3D2DC05ZWR

pub mod cost;
pub mod figure;
pub mod fit;
pub mod percentile;
pub mod remaining;
pub mod report;
pub mod times;
pub mod velocity;

pub use figure::Figure;
pub use report::{Section, StatsInput, StatsReport, TicketFact, TicketState, compute, render_text};
