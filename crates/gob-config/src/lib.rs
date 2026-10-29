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
//! Tables are scoped to a product (`#[config(product = "crunk")]`; default `frob`). Every
//! product gets its own reference page and schema, so one product's keys never appear in
//! another's: [`frob_tables`] and [`product_tables`] select a registry, [`products`] lists
//! them, and a crate may submit a [`ProductEntry`] to set the title, intro and required
//! tables. Further struct attributes: `array` (`[[x]]` tables), `inline` (nested in a parent
//! table, not a top-level schema property) and `rest` (a dynamic-key table over one map
//! field, with an optional `schema_with` for key detail). Field attributes add `required`
//! (no default; a missing key is an error) and `rename`.
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
mod mirror;
mod product;
pub mod rules;
mod schema;
mod ui;
mod workspace;

pub use artifact::{ArtifactBody, ArtifactEntry, ArtifactFamily, all_artifacts};
pub use check::check;
pub use compute::{ComputeTable, blake3_tagged, compute_digest};
pub use describe::{
    ConfigTable, DEFAULT_PRODUCT, FieldDescription, RestDescription, TableDescription, TableEntry,
    all_tables, frob_tables, product_tables, products, render_default, schema_of,
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
pub use mirror::{DEFAULT_MIRROR_KID, MirrorTable};
pub use product::{ProductEntry, product_entry};
pub use rules::cfg001::Cfg001;
pub use schema::{SchemaOptions, product_config_schema, product_schema, schema, table_schema};
pub use schemars;
pub use serde;
pub use serde_json;
pub use toml;
pub use ui::UiTable;
pub use workspace::{nested_config_dirs, workspace_members};

/// Path of the product config file under `root`: `<root>/<product>.toml`.
pub(crate) fn config_path(root: &std::path::Path, product: &str) -> std::path::PathBuf {
    root.join(format!("{product}.toml"))
}
