//! The `.grmb` language: lexer, parser, formatter, U adapter (F4) and the MDL rules
//! (`docs/design/grmb-spec.md`, ticket G08).
//!
//! # Overview
//!
//! - [`lex`] and [`parse`]: a hand-written lexer and recursive-descent parser producing the
//!   typed AST of [`ast`] for every entity and clause of grmb-spec 4. It is hand-written rather
//!   than tree-sitter because a syntax error must become a `hole` that resynchronizes at the next
//!   `;` or at the `}` closing the current block, with exact byte spans, and the rest of the file
//!   must still parse; the grammar is small and LL(1).
//! - [`model`]: a model is the set of files reachable from a root through `include` (cycles are
//!   refused as MDL003), with one namespace per model and the nearest-first resolution of
//!   grmb-spec 5. No I/O happens here: the caller hands over bytes in [`ModelFiles`].
//! - [`fold`]: the U encoding of grmb-spec 9, one [`gob_ir::Term`] and scope graph per file;
//!   selectors are parsed by `gob-walk` and become `apply(kind=select)`, exceptions become
//!   `attr`, and directives in comments become `attr` nodes bound to their entity.
//!   [`adapter`] implements the gob-symbols adapter trait at F4 on top of it.
//! - [`fmt`]: `grimble fmt`, the alpha-normal printer; `parse(fmt(m))` equals `m` in U.
//! - [`rules`]: `MDL000`-`MDL017` ([`rule_defs`]) and [`check_model`], the entry point of the
//!   `grimble check` verb for the model itself.
//! - [`binding`]: the model-side inputs of the binding relation (`owns` selectors and
//!   `grimble:binds` directives); G10 joins them with code terms.
//!
//! # Conformance
//!
//! `tests/corpus` holds the grmb-spec 12 corpus; see its `README.md`.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

pub mod adapter;
pub mod ast;
pub mod binding;
pub mod directive;
pub mod dump;
pub mod fmt;
pub mod fold;
pub mod keywords;
pub mod lex;
pub mod model;
pub mod parse;
pub mod rule_defs;
pub mod rules;
pub mod span;
pub mod text;

mod atoms;

pub use adapter::GrmbAdapter;
pub use fmt::{FmtError, format_file};
pub use fold::{FoldedFile, fold_file};
pub use model::{ModelFiles, PackPin};
pub use parse::parse_file;
pub use rules::check_model;
pub use span::{Diagnostic, Span};
