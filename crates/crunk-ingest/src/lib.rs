//! CSS ingest for crunk: [`ProjectStyles`], the located, judgment-free facts of a project's
//! stylesheets, plus bucket placement and the organization inventory `map` reads.
//!
//! [`ingest_tree`] walks `[project] css_root` (ignore files honored), parses each `.css` file
//! with the shared CSS adapter into declarations (with per-token color, length and `var()`
//! spans), selectors, custom properties, `crunk:waive` waivers and `@media` queries, places it
//! in a bucket per `[org]`, and finds the `.css` files outside `css_root` that nothing governs.
//! Parsed contents are cached by content digest ([`gob_cache`]), so an unchanged tree is read
//! from the cache on the second run.
//!
//! # Overview
//!
//! - [`model`]: [`ProjectStyles`], [`Stylesheet`], [`Declaration`] and the located facts.
//! - [`walk`]: [`ingest_tree`], [`ingest_paths`], [`bucket_for`] and [`IngestStats`].
//! - [`parse`]: [`parse_css_source`], one file's text to its [`ParsedCss`].
//! - [`glob`]: the `fnmatch` semantics `[org] entry`, `[org] ignore` and `[jsx] globs` use.
//!
//! # Known divergences from the Python crunk
//!
//! - Spans are byte offsets (Python: code points); they are equal on ASCII text.
//! - The walk honors ignore files (`.gitignore`): a git-ignored `.css` under `css_root` is not
//!   ingested, and one outside it is not "ungoverned". Python walked everything.
//! - Rules nested in rules (CSS nesting) and `@container`, `@scope` and `@starting-style`
//!   blocks are ingested; Python dropped their declarations silently.
//! - A named file outside `css_root` is skipped; Python raised. A malformed `crunk:waive`
//!   comment becomes a diagnostic; Python ignored it.
//! - Parse errors read `css syntax error at line N`; Python carried tinycss2's messages.
//! - The Tailwind theme is ingested by [`tailwind`] (the project's own Tailwind first, static
//!   readers as the fallback), JSX and TS sources by [`jsx`]; each lists its own divergences.

// frob:ticket 01M43ARY91XZ35DN9SCHRHS033

mod error;
mod facts;
pub mod glob;
pub mod jsx;
mod lex;
pub mod model;
pub mod parse;
pub mod tailwind;
pub mod waive;
pub mod walk;

pub use error::IngestError;
pub use facts::{ValueFacts, channel_triplet, value_facts};
pub use jsx::{ParsedJsx, parse_jsx_source};
pub use model::{
    Bucket, ClassSelector, CustomProp, Declaration, DynamicClass, LocatedColor, LocatedLength,
    LocatedMediaQuery, LocatedUtility, LocatedVarRef, ParseDiagnostic, ProjectStyles, Span,
    Stylesheet, Waiver,
};
pub use parse::{FoldFailure, ParsedCss, parse_css_source};
pub use waive::Waive;
pub use walk::{INGEST_VERSION, IngestStats, Ingested, bucket_for, ingest_paths, ingest_tree};
