//! The `grimble` product: its verbs on the shared goblin CLI root.
//!
//! [`cli`] assembles the root; `main` only runs it. Verbs live in their own modules:
//! [`check`] (the `gob.sibling/1` document), [`ack`] (`grimble.lock`), [`init`], [`doctor`], [`fmt_cmd`] and
//! [`exceptions`]; the built-in `schema` verb comes from `gob-cli`. The `[compute]`,
//! `[packs]`, `[check]` and `[perf]` config tables register through `grimble-check` and
//! `gob-check`. No frob crate is linked (the boundary test in `tests/boundary.rs`).

pub mod ack;
pub mod check;
pub mod doctor;
pub mod exceptions;
pub mod fmt_cmd;
pub mod init;
mod workspace;

use gob_cli::Cli;

/// Product name, also the config file stem (`grimble.toml`).
pub const PRODUCT: &str = "grimble";

/// The fully registered `grimble` command-line root.
pub fn cli() -> Cli {
    Cli::new(PRODUCT, env!("CARGO_PKG_VERSION"))
        .register::<check::Check>()
        .register::<ack::Ack>()
        .register::<init::Init>()
        .register::<doctor::Doctor>()
        .register::<fmt_cmd::Fmt>()
        .register::<exceptions::ExceptionsList>()
}
