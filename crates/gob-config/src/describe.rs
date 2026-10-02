//! Table and field descriptions plus the inventory of tables.

use schemars::JsonSchema;
use schemars::SchemaGenerator;
use serde::Serialize;
use serde::de::DeserializeOwned;

/// A config table; implemented by `#[derive(ConfigTable)]`.
pub trait ConfigTable: Default + DeserializeOwned {
    /// Dotted table path in the product file, e.g. `tickets.lease`.
    const TABLE: &'static str;

    /// Documentation, defaults and schema of every field of this table.
    fn describe() -> TableDescription;
}

/// Static description of one config table, used by docs, schema and materialize.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TableDescription {
    /// Dotted table path.
    pub table: String,
    /// Struct-level doc comment.
    pub doc: String,
    /// Whether enforcement knobs of this table are materialized and checked.
    pub materialize: bool,
    /// Fields in declaration order.
    pub fields: Vec<FieldDescription>,
}

/// Static description of one config key.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FieldDescription {
    /// Key name in the TOML table.
    pub key: String,
    /// Field doc comment.
    pub doc: String,
    /// Default rendered as an inline TOML value.
    pub default_toml: String,
    /// True when the knob must be written to the file (CFG001 flags its absence).
    pub enforcement: bool,
    /// Rust type as written.
    pub type_name: String,
    /// JSON Schema of the value type.
    pub schema: serde_json::Value,
}

/// An inventory record of one table, submitted by `#[derive(ConfigTable)]`.
pub struct TableEntry {
    describe: fn() -> TableDescription,
}

impl TableEntry {
    /// Wrap a table's `describe` function for registration.
    pub const fn new(describe: fn() -> TableDescription) -> Self {
        Self { describe }
    }
}

inventory::collect!(TableEntry);

/// Every `ConfigTable` linked into the binary, in registration order.
pub fn all_tables() -> impl Iterator<Item = TableDescription> {
    inventory::iter::<TableEntry>
        .into_iter()
        .map(|e| (e.describe)())
}

/// Render a default value as an inline TOML value (used by the derive).
///
/// # Panics
///
/// Panics when `value` is not representable as a TOML value; a declared
/// default that cannot be written to a file is a programmer bug.
pub fn render_default<T: Serialize>(value: &T) -> String {
    let rendered = toml::Value::try_from(value)
        .unwrap_or_else(|e| panic!("config default is not representable as TOML: {e}"));
    rendered.to_string()
}

/// JSON Schema of `T` as a plain JSON value (used by the derive).
pub fn schema_of<T: JsonSchema>() -> serde_json::Value {
    SchemaGenerator::default().subschema_for::<T>().to_value()
}
