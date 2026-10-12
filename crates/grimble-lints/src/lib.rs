//! Syntactic detectors behind grimble's universal lint rules.
//!
//! [`err::scan`] finds swallowed errors (`ERR001` empty handler, `ERR002` discarded fallible
//! result, `ERR003` catch-all that neither rethrows nor logs) in Rust, Python, TypeScript and C#
//! from the tree-sitter parse of one file. It only reports sites; mapping a site to a severity
//! (an [`err::Certainty::Unknown`] site is Unresolved, never Warn) belongs to the rule that
//! consumes it.
//!
//! [`res::scan`] finds acquire calls with no paired release in scope (`performance.mark`,
//! `Map.set`, `setTimeout`, `addEventListener`, ...) in TypeScript and JavaScript from a table of
//! acquire/release pairs ([`res::PAIRS`]); a new pair is a data change.

// frob:ticket 01M4D956T20WN96P7A3K4B9CKF

pub mod err;
pub mod res;
