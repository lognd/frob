//! Tailwind knowledge for crunk: default-theme key tables, the utility candidate parser and
//! (feature `runtime`, on by default) the bridge to the project's own tailwindcss through node
//! (boundaries 2.4, `crunk_tailwind`). Everything but [`runtime`] is pure data and parsing; the
//! bridge is the only place a process is spawned, always through `gob-exec`.
//!
//! # Overview
//!
//! - [`defaults`]: the v3 and v4 default key tables (spacing, radius, z-index, font size, color).
//! - [`candidate`]: [`parse_candidate`] splits one class such as `md:hover:-mt-[13px]/50` into
//!   variants, importance, negation, utility, value and alpha.
//! - [`fragment`]: [`parse_class_segments`] scans a class-list fragment whose pieces may be
//!   computed, yielding candidates for the static tokens and reporting the rest as dynamic.
//! - `runtime` (feature `runtime`): compiled utilities and the resolved theme from the project's
//!   own Tailwind, cached; `Unresolved` when node or tailwindcss is absent.

// frob:ticket 01M43ARVZPN52N6NMB7VRKZYGS

pub mod candidate;
pub mod defaults;
pub mod fragment;
#[cfg(feature = "runtime")]
pub mod runtime;
mod v3_data;

pub use candidate::{Alpha, Candidate, CandidateError, UtilityValue, Variant, parse_candidate};
pub use fragment::{ClassListParse, DynamicToken, Segment, parse_class_list, parse_class_segments};
