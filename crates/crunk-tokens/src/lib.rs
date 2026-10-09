//! The crunk design-token model: the [`TokenSet`] derived from a `crunk_spec::DesignSpec`,
//! token naming and the Tailwind theme mapping inputs.
//!
//! One model feeds every exporter (CSS, JSON, Tailwind), `crunk explain` and `crunk query`;
//! rendering files and drift checks live in [`export`], not in the model.
//!
//! ```
//! use std::path::Path;
//! use crunk_tokens::TokenSet;
//!
//! let spec = crunk_spec::parse_spec(
//!     crunk_spec::presets::DEFAULT,
//!     Path::new("crunk.toml"),
//!     Path::new("/proj"),
//! )
//! .unwrap();
//! let tokens = TokenSet::from_spec(&spec).unwrap();
//! assert!(tokens.get("--color-ink").is_some());
//! ```

pub mod export;
pub mod model;
pub mod naming;

pub use model::{
    Scope, THEME_SECTIONS, ThemeCollision, ThemeSection, Tier, Token, TokenError, TokenKind,
    TokenSet, TokenValue, Unit,
};
