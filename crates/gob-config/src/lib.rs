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

mod check;
mod describe;
mod error;
mod load;
mod materialize;
mod schema;

pub use check::{Cfg001, check};
pub use describe::{
    ConfigTable, FieldDescription, TableDescription, TableEntry, all_tables, render_default,
    schema_of,
};
pub use error::ConfigError;
pub use gob_macros::ConfigTable;
pub use inventory;
pub use load::{ConfigSource, Loaded, Provenance, load, load_with};
pub use materialize::{MaterializeReport, materialize};
pub use schema::schema;
pub use serde;
pub use toml;

/// Path of the product config file under `root`: `<root>/<product>.toml`.
pub(crate) fn config_path(root: &std::path::Path, product: &str) -> std::path::PathBuf {
    root.join(format!("{product}.toml"))
}
