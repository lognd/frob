//! The `frob` product: its config tables and verbs on the shared CLI root.
//!
//! [`cli`] assembles the root; `main` only runs it. Verbs live in their own
//! modules: [`doctor`], [`init`], [`config_cmd`] (`config show`, `config
//! sync`), [`ticket`] (`ticket ...` and the hidden `merge-driver`) and the
//! built-in `schema` from `gob-cli`. Config knobs are the
//! `ConfigTable` structs in [`config`].

pub mod config;
pub mod config_cmd;
pub mod doctor;
pub mod init;
pub mod ticket;
mod workspace;

use gob_cli::Cli;

/// Product name, also the config file stem (`frob.toml`).
pub const PRODUCT: &str = "frob";

/// The fully registered `frob` command-line root.
pub fn cli() -> Cli {
    ticket::register(
        Cli::new(PRODUCT, env!("CARGO_PKG_VERSION"))
            .register::<doctor::Doctor>()
            .register::<init::Init>()
            .register::<config_cmd::ConfigShow>()
            .register::<config_cmd::ConfigSync>(),
    )
}
