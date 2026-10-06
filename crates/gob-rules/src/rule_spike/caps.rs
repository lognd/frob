//! The capability matrix of the spike: a re-export of the real `gob-caps` crate (~HQ6B02X).
//!
//! The path stays because the `#[rule]` compile errors name it; the vocabulary and the const
//! matrix now live in `gob-caps`, the one source every adapter also reads.

pub use gob_caps::*;
