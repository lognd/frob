//! The `pack.toml` manifest model and its validation, shared by frob, grimble
//! and crunk (plugins.md sections 2 and 10, security.md 2.1 and 2.6).
//!
//! Manifests come from untrusted repositories and external packs, so loading
//! is total: every table is closed (`deny_unknown_fields`), every size is
//! bounded, and no input panics. Failures are [`PackError`] values:
//! PACK005 for a malformed manifest (file, key and line named) and PACK004
//! for two packs owning one family or one name.
//!
//! ```
//! let text = r#"
//! [pack]
//! name = "py-safety"
//! version = "1.2.0"
//! families = ["PYS"]
//! needs = { grimble = ">=2.0", u = "1" }
//!
//! [provides]
//! atoms = "atoms.toml"
//! rules = ["rules/*.grl"]
//!
//! [effects]
//! "#;
//! let m = gob_packs::Manifest::parse("pack.toml", text).unwrap();
//! assert_eq!(m.pack.name, "py-safety");
//! assert!(m.effects.is_empty());
//! ```

mod error;
mod limits;
mod manifest;
mod validate;

pub use error::{PackCode, PackError};
pub use limits::{MAX_MANIFEST_BYTES, Owner};
pub use manifest::{Manifest, PackTable, Provides, check_unique, load};
