//! The one source of language and capability facts (D107, rule-authoring.md section 3).
//!
//! A leaf crate: [`Lang`] (a closed enum, with the pseudo-languages `opaque-text` and `binary`),
//! [`Fidelity`], [`Capability`], [`Precision`] and the const [`MATRIX`]. Every adapter's
//! `capabilities()` and `fidelity()` read their row, so the generated languages page and rule
//! applicability cannot disagree. Const helpers let `#[rule]` expansions assert against the matrix
//! at compile time.

// frob:ticket 01M48R002DA5FKCXDP8HQ6B02X

mod capability;
mod lang;
mod matrix;

pub use capability::{Capability, Fidelity, Precision};
pub use lang::Lang;
pub use matrix::{MATRIX, Row, lang_fidelity, precision, provides, row, universal_satisfiable};
