//! Plan format, GRL compiler and executor (plugins.md section 10).
//!
//! This milestone holds the GRL lexer and parser ([`grl`]), the plan format ([`plan`]), the
//! relation [`catalog`] and the Kleene plan executor ([`exec`]).

pub mod catalog;
pub mod check;
// frob:ticket 01M3ZX7HGX4HXKW1X8VKHW9BKW
pub mod codegen;
pub mod examples;
pub mod exec;
pub mod grl;
pub mod limits;
pub mod lower;
pub mod plan;
pub mod verbs;
// frob:ticket 01M3ZX7H8FPEAY1X1WVW1PNXXN
pub mod why;
