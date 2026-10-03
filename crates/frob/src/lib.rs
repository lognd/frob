//! The `frob` product: its config tables and verbs on the shared CLI root.
//!
//! [`cli`] assembles the root; `main` only runs it. Verbs live in their own
//! modules: [`doctor`], [`init`], [`config_cmd`] (`config show`, `config
//! sync`), [`ticket`] (`ticket ...` and the hidden `merge-driver`) and the
//! built-in `schema` from `gob-cli`; the lease, worktree, evidence, tests and
//! ack, check and land verbs come from their sibling crates' `register`; [`milestone_cmd`] holds `milestone new/add/show/list`; [`cycle_cmd`] holds `cycle new/show/list/close`; [`release_cmd`] holds `release changelog`. Config knobs are the
//! `ConfigTable` structs in [`config`].

pub mod config;
pub mod config_cmd;
pub mod cycle_cmd;
pub mod doctor;
pub mod first_run;
pub mod init;
pub mod lease_cmd;
pub mod milestone_cmd;
pub mod milestone_evidence_cmd;
pub mod release_cmd;
pub mod ticket;
mod workspace;

use gob_cli::Cli;

/// Product name, also the config file stem (`frob.toml`).
pub const PRODUCT: &str = "frob";

/// The fully registered `frob` command-line root.
pub fn cli() -> Cli {
    let cli = ticket::register(
        Cli::new(PRODUCT, env!("CARGO_PKG_VERSION"))
            .register::<doctor::Doctor>()
            .register::<init::Init>()
            .register::<config_cmd::ConfigShow>()
            .register::<config_cmd::ConfigSync>()
            .register::<lease_cmd::LeaseWiden>(),
    );
    let cli = milestone_cmd::register(cli);
    let cli = cycle_cmd::register(cli);
    let cli = release_cmd::register(cli);
    let cli = frob_lease::register(cli);
    let cli = frob_worktree::register(cli);
    let cli = frob_evidence::register(cli);
    let cli = frob_tests::register(cli);
    let cli = frob_ack::register(cli);
    let cli = frob_check::register(cli);
    frob_land::register(cli).with_guard(first_run::require_config)
}
