//! Tailwind knowledge for crunk: default-theme key tables and the utility candidate parser
//! (boundaries 2.4, `crunk_tailwind`). Pure data and parsing; no process is spawned here (the
//! node runtime bridge is a separate ticket).
//!
//! # Overview
//!
//! - [`defaults`]: the v3 and v4 default key tables (spacing, radius, z-index, font size, color).
//! - [`candidate`]: [`parse_candidate`] splits one class such as `md:hover:-mt-[13px]/50` into
//!   variants, importance, negation, utility, value and alpha.
//! - [`fragment`]: [`parse_class_segments`] scans a class-list fragment whose pieces may be
//!   computed, yielding candidates for the static tokens and reporting the rest as dynamic.

// frob:ticket 01M43ARVZPN52N6NMB7VRKZYGS

pub mod candidate;
pub mod defaults;
pub mod fragment;
mod v3_data;

pub use candidate::{Alpha, Candidate, CandidateError, UtilityValue, Variant, parse_candidate};
pub use fragment::{ClassListParse, DynamicToken, Segment, parse_class_list, parse_class_segments};
