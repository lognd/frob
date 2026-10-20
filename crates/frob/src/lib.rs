//! The `frob` product: its config tables and verbs on the shared CLI root.
//!
//! [`cli`] assembles the root (`check` and `doctor` are the generic `gob-product` verbs over
//! [`FrobProduct`]); `main` only runs it. Verbs live in their own
//! modules: [`doctor`], [`init`], [`config_cmd`] (`config show`, `config
//! sync`), [`ticket`] (`ticket ...` and the hidden `merge-driver`) and the
//! built-in `schema` from `gob-cli`; the lease, worktree, evidence, tests and
//! ack, check and land verbs come from their sibling crates' `register`; [`milestone_cmd`] holds `milestone new/add/show/list`; [`cycle_cmd`] holds `cycle new/show/list/close`; [`release_cmd`] holds `release changelog`; [`agent_cmd`] holds `agent sync/status/uninstall` over the emitters in [`agent`]. Config knobs are the
//! `ConfigTable` structs in [`config`].

pub mod agent;
pub mod agent_cmd;
pub mod board_cmd;
pub mod config;
pub mod config_cmd;
pub mod cycle_cmd;
pub mod doctor;
pub mod explain_cmd;
pub mod first_run;
pub mod init;
pub mod lease_cmd;
pub mod milestone_cmd;
pub mod milestone_evidence_cmd;
pub mod mirror_cmd;
pub mod mirror_recreate_cmd;
pub(crate) mod pathtext;
mod product;
pub mod profile;
pub mod profile_cmd;
pub mod refresh_cmd;
pub mod release_cmd;
pub mod rule_cmd;
pub mod stats_cmd;
pub mod teach_cmd;
pub mod ticket;
pub mod tour_cmd;
pub mod trust_cmd;
mod workspace;

use gob_cli::Cli;

pub use product::FrobProduct;

/// Product name, also the config file stem (`frob.toml`).
pub const PRODUCT: &str = "frob";

/// The fully registered `frob` command-line root: the generic `check` and `doctor`, then frob's verbs.
pub fn cli() -> Cli {
    gob_product::cli::<FrobProduct>()
}
