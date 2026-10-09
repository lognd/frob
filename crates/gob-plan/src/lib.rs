//! Plan format, GRL compiler and executor (plugins.md section 10).
//!
//! This milestone holds the GRL lexer and parser ([`grl`]), the plan format ([`plan`]), the
//! relation [`catalog`] and the Kleene plan executor ([`exec`]).

pub mod catalog;
pub mod check;
pub mod exec;
pub mod grl;
pub mod plan;
