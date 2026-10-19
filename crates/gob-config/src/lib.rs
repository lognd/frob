//! Layered product config (`frob.toml`, `grimble.toml`, ...) for the goblins.
//!
//! Each config table is a struct with `#[derive(ConfigTable)]`; the derive
//! generates its `Deserialize` (declared defaults fill absent keys), `Default`,
//! a [`TableDescription`] (docs, defaults, JSON schema) and an inventory entry
//! so [`all_tables`] lists every table. [`load`] reads and layers a table,
//! [`materialize`] writes every missing enforcement knob (comments preserved),
//! [`check`] reports each missing knob as `CFG001`, and [`schema`] exports a
//! JSON Schema for all tables.
//!
//! ```
//! use gob_config::ConfigTable;
//!
//! /// Ticket settings.
//! #[derive(Debug, ConfigTable)]
//! #[config(table = "tickets", materialize)]
//! struct Tickets {
//!     /// Compare-and-swap retries.
//!     #[config(default = 5, enforcement)]
//!     cas_retries: u32,
//! }
//!
//! assert_eq!(Tickets::default().cas_retries, 5);
//! assert_eq!(Tickets::describe().fields[0].default_toml, "5");
//! ```
#![expect(
    clippy::disallowed_methods,
    reason = "confinement allow list: path-to-text conversion pending migration to gob-path"
)]

extern crate self as gob_config;

mod artifact;
mod check;
mod compute;
mod describe;
mod error;
pub mod host;
mod ledger_dir;
mod load;
mod local;
mod materialize;
pub mod rules;
mod schema;
mod workspace;

pub use artifact::{ArtifactBody, ArtifactEntry, ArtifactFamily, all_artifacts};
pub use check::check;
pub use compute::{ComputeTable, blake3_tagged, compute_digest};
pub use describe::{
    ConfigTable, FieldDescription, TableDescription, TableEntry, all_tables, render_default,
    schema_of,
};
pub use error::ConfigError;
pub use gob_macros::ConfigTable;
pub use inventory;
pub use ledger_dir::{DEFAULT_LEDGER_DIR, ledger_dir};
pub use load::{
    ConfigDocument, ConfigSource, Loaded, Provenance, file_reads, load, load_str, load_with,
};
pub use local::{repo_file, user_config_dir, user_config_dir_with, user_file};
pub use materialize::{MaterializeReport, materialize};
pub use rules::cfg001::Cfg001;
pub use schema::schema;
pub use serde;
pub use toml;
pub use workspace::{nested_config_dirs, workspace_members};

/// Path of the product config file under `root`: `<root>/<product>.toml`.
pub(crate) fn config_path(root: &std::path::Path, product: &str) -> std::path::PathBuf {
    root.join(format!("{product}.toml"))
}
