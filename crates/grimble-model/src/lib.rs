//! The .grmb language: lexer, parser, formatter, U adapter and the MDL rules.
#![allow(missing_docs)]

pub mod ast;
pub mod directive;
pub mod fmt;
pub mod fold;
pub mod keywords;
pub mod lex;
pub mod parse;
pub mod span;
pub mod text;

pub use span::{Diagnostic, Span};
