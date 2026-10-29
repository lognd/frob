//! LOG001/LOG002: direct output must go through a logging crate.
//!
//! The output atoms live as data in `docs/design/output-atoms.md` ([`catalogue`]); the per-language
//! scanners resolve imports, aliases and re-exports over tree-sitter trees ([`engine`] and the
//! `lang_*` modules) and [`pass`] turns the hits into findings.

// frob:ticket 01M5XMR67K19SFAWNTDJKKJPTT

pub mod catalogue;
pub mod engine;
pub mod lang_csharp;
pub mod lang_js;
pub mod lang_python;
pub mod lang_rust;
pub mod pass;

/// Rule id of the direct-output rule.
pub const LOG001: &str = "LOG001";

/// Rule id of the logging-crate-required rule.
pub const LOG002: &str = "LOG002";
