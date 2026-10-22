//! The one source of language and capability facts (D107, rule-authoring.md section 3).
//!
//! A leaf crate: [`Lang`] (a closed enum, with the pseudo-languages `opaque-text` and `binary`),
//! [`Fidelity`], [`Capability`], [`Precision`] and the const [`MATRIX`]. Every adapter's
//! `capabilities()` and `fidelity()` read their row, so the generated languages page and rule
//! applicability cannot disagree. Const helpers let `#[rule]` expansions assert against the matrix
//! at compile time.

// frob:ticket 01M48R002DA5FKCXDP8HQ6B02X

/// The digest scheme number the universal model computes and `frob.lock` records; the one definition every crate re-exports.
// frob:ticket 01M4M52WDAB9VH3PJ2VDF2JFRY
pub const DIGEST_SCHEME: u32 = 2;

mod capability;
mod lang;
mod matrix;

pub use capability::{Capability, Fidelity, Precision};
pub use lang::Lang;
pub use matrix::{
    MATRIX, Row, UNJUSTIFIED, fidelity_ceiling, is_justified, lang_fidelity, precision, provides,
    row, universal_satisfiable,
};
