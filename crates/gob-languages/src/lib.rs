//! Feature-gated tree-sitter grammars, bounded parsing and cached queries.
//!
//! # Version decision (audit M26)
//!
//! Checked 2026-10-02 against crates.io:
//!
//! - `tree-sitter` core: **0.27.0** (ABI 15, accepts grammars with ABI 13-15).
//! - `tree-sitter-rust` 0.24.2, `tree-sitter-md` 0.5.3 and
//!   `tree-sitter-toml-ng` 0.7.0 all depend only on `tree-sitter-language`
//!   0.1 (a stable `LanguageFn` shim), not on a specific core version, so
//!   they load under the newest core. Their dev-dependencies name older cores
//!   (0.25, 0.26, 0.24) which is irrelevant to consumers.
//! - `ast-grep-core` 0.45.3 requires `tree-sitter = "0.27.0"`, the same core,
//!   so ast-grep can later be layered on this crate without two cores in the
//!   build. Re-check this on every ast-grep or tree-sitter bump.
//!
//! The core and grammar crates are pinned with `=` so the identity strings in
//! [`grammar_identity`] cannot drift from what is compiled in.
//!
//! # Overview
//!
//! - [`Language`]: the supported languages, [`Language::detect`] by path.
//! - [`parse`]: bounded parse ([`ParseLimits`]) returning a [`ParseResult`];
//!   never panics, oversized or slow input becomes [`ParseResult::Unresolved`].
//! - [`grammar_identity`]: cache-key component for a grammar.
//! - [`grmb`]: `.grmb` detection and identity (hand-written parser, no grammar).
//! - [`compiled_query`] / [`captures`]: queries compiled once, captures
//!   reported with [`gob_text::TextRange`] spans.
//!
//! # Adding a language
//!
//! 1. Add a cargo feature `<lang>` in `Cargo.toml` (and to `default`) that
//!    enables the optional, exactly pinned grammar dependency.
//! 2. Add the grammar crate as an optional `=x.y.z` dependency.
//! 3. Add a variant to [`Language`], and to `Language::ALL`, `name`, and the
//!    extension map in `detect`.
//! 4. Add a `cfg(feature)` arm in the private grammar table
//!    (`grammar::language_fn`) and in `grammar::pin`, recording the crate name
//!    and exact version (the pin test checks it against `Cargo.toml`).
//! 5. Add a sample parse test and a query-capture test.

mod grammar;
pub mod grmb;
#[cfg(feature = "markdown")]
mod inline;
mod language;
mod parse;
mod query;

pub use grammar::grammar_identity;
#[cfg(feature = "markdown")]
pub use inline::{markdown_code_ranges, markdown_code_spans, markdown_link_destinations};
pub use language::Language;
pub use parse::{ParseLimits, ParseResult, ParsedTree, Unresolved, UnresolvedReason, parse};
pub use query::{Capture, CompiledQuery, QueryError, captures, compiled_query};
