//! The `crunk` product: its verbs on the shared goblin CLI root.
//!
//! [`cli`] assembles the root; `main` only runs it. Verbs live in their own modules:
//! [`check`] (the `gob.sibling/1` document) and [`doctor`]; the built-in `schema` verb comes
//! from `gob-cli`. Every verb but `doctor` refuses with `E-NO-CONFIG` (exit 3) when no
//! `crunk.toml` exists ([`workspace::require_config`]). No frob crate is linked (the boundary
//! test in `tests/boundary.rs`).

// frob:ticket 01M43ARVS24254G85TMFYH8FGQ

pub mod check;
pub mod doctor;
pub mod workspace;

use gob_cli::Cli;

/// Product name, also the config file stem (`crunk.toml`).
pub const PRODUCT: &str = crunk_check::PRODUCT;

/// The fully registered `crunk` command-line root.
pub fn cli() -> Cli {
    Cli::new(PRODUCT, env!("CARGO_PKG_VERSION"))
        .with_guard(workspace::require_config)
        .register::<check::Check>()
        .register::<doctor::Doctor>()
}
