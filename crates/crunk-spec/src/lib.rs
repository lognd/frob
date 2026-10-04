//! The `crunk.toml` design spec: schema, validation with located errors, [`DesignSpec`], token
//! naming and presets.
//!
//! [`load_spec`] reads a project's `crunk.toml` into a frozen [`DesignSpec`], the design law
//! everything downstream trusts. A bad file is a [`SpecError`] carrying the key, its line and
//! column and, for an unknown key, a did-you-mean (exit code 2 via [`SpecError::exit_code`]).
//!
//! # Overview
//!
//! - [`table`]: the TOML-shaped tables; their docs and defaults are the single source of the
//!   generated `docs/schemas/crunk.json` ([`schema::schema`]) and `docs/crunk/config.md`
//!   ([`schema::reference`]).
//! - [`DesignSpec`] and its sub-models ([`model`]), with the path-base law as methods:
//!   [`DesignSpec::tokens_path`] resolves against `css_root`, while
//!   [`DesignSpec::tailwind_tokens_path`] and [`DesignSpec::json_tokens_path`] resolve against
//!   the project root.
//! - [`naming`]: every custom-property name crunk emits, from the `[tokens]` prefixes.
//! - [`presets`]: the `default` and `mono` `crunk.toml` texts for `crunk init`.
//! - [`catalog`]: the rule catalog rows and default severities `[lint]` overrides.
//!
//! ```
//! use std::path::Path;
//!
//! let text = crunk_spec::presets::DEFAULT;
//! let spec = crunk_spec::parse_spec(text, Path::new("crunk.toml"), Path::new("/proj")).unwrap();
//! assert_eq!(spec.tokens_path(), Path::new("/proj/styles/tokens.css"));
//! assert_eq!(crunk_spec::naming::color_token(&spec.tokens, "ink"), "--color-ink");
//! ```
//!
//! # Known divergences from the Python crunk
//!
//! Paths are normalized lexically (`..` and `.` collapse) and never resolved through symlinks.
//! Value types are strict: `root_font_size = "16"` is rejected where pydantic coerced it. Tables
//! owned by shared crates (`[check]`, `[perf]`, ...) are accepted and left to their owners; every
//! other unknown top-level key is an error as before. `format_step` prints a step below `1e-4`
//! positionally instead of with an exponent.

#![allow(
    clippy::result_large_err,
    reason = "SpecError carries path, location, detail and suggestion by value; it is built once per failed load, never in a loop"
)]
#![allow(
    clippy::format_push_string,
    reason = "the reference page and path renderers build text with push_str(&format!(..)) for readability"
)]

// frob:ticket 01M43ARX764095Q4VWABWXXV5H

pub mod catalog;
mod dynamic;
mod error;
mod load;
pub mod model;
pub mod naming;
pub mod presets;
pub mod schema;
pub mod table;
mod validate;

pub use catalog::{CATALOG, CONTRAST_AA_FLOOR, CatalogRow, Severity};
pub use dynamic::Dyn;
pub use error::{Location, SpecError, SpecErrorKind};
pub use load::{OWN_TABLES, load_spec, load_spec_file, parse_spec};
pub use model::{DesignSpec, normalize_join};
