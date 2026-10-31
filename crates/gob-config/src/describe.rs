//! Table and field descriptions plus the inventory of tables.
// frob:ticket 01M43MPG53JR8TP0E15394FZ5T

use schemars::JsonSchema;
use schemars::SchemaGenerator;
use serde::Serialize;
use serde::de::DeserializeOwned;

/// The product a table belongs to when `#[config(product = ...)]` is absent.
pub const DEFAULT_PRODUCT: &str = "frob";

/// A config table; implemented by `#[derive(ConfigTable)]`.
pub trait ConfigTable: DeserializeOwned {
    /// Dotted table path in the product file, e.g. `tickets.lease`.
    const TABLE: &'static str;

    /// The product whose config file holds this table (`frob` unless the derive names another).
    const PRODUCT: &'static str = DEFAULT_PRODUCT;

    /// Documentation, defaults and schema of every field of this table.
    fn describe() -> TableDescription;
}

/// Static description of one config table, used by docs, schema and materialize.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TableDescription {
    /// Dotted table path.
    pub table: String,
    /// Product whose config file holds the table; docs and schemas are emitted per product.
    pub product: String,
    /// True for an array of tables (`[[platform]]`): the schema node is `{type: array, items}`.
    pub array: bool,
    /// True when the schema is only reachable through a parent field's type (not placed by path).
    pub inline: bool,
    /// Present for a dynamic-key table, whose keys are data rather than declared fields.
    pub rest: Option<RestDescription>,
    /// Struct-level doc comment.
    pub doc: String,
    /// Whether enforcement knobs of this table are materialized and checked.
    pub materialize: bool,
    /// Fields in declaration order.
    pub fields: Vec<FieldDescription>,
}

/// Description of a dynamic-key table (palette, lint, breakpoints): any key, one value shape.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RestDescription {
    /// Doc comment of the entries field.
    pub doc: String,
    /// Rust type of the entries as written.
    pub type_name: String,
    /// JSON Schema of one entry value.
    pub value_schema: serde_json::Value,
    /// Full replacement schema of the table, when keys have detail a uniform value cannot give.
    pub table_schema: Option<serde_json::Value>,
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
    /// True when the key has no default and must be written (a missing key is an error).
    pub required: bool,
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

/// Every `ConfigTable` of every product linked into the binary, in registration order.
pub fn all_tables() -> impl Iterator<Item = TableDescription> {
    inventory::iter::<TableEntry>
        .into_iter()
        .map(|e| (e.describe)())
}

/// The tables of one product, in registration order.
pub fn product_tables(product: &str) -> impl Iterator<Item = TableDescription> {
    let product = product.to_owned();
    all_tables().filter(move |t| t.product == product)
}

/// The tables of the default (`frob`) product: what `frob.toml` and the shared crates register.
pub fn frob_tables() -> impl Iterator<Item = TableDescription> {
    product_tables(DEFAULT_PRODUCT)
}

/// Every product that registered a table, sorted and deduplicated.
pub fn products() -> Vec<String> {
    let mut all: Vec<String> = all_tables().map(|t| t.product).collect();
    all.sort();
    all.dedup();
    all
}

/// Render a default value as an inline TOML value (used by the derive).
///
/// An absent value (`None`, JSON null) renders as the empty string: there is nothing to write.
///
/// # Panics
///
/// Panics when `value` is not representable as a TOML value; a declared
/// default that cannot be written to a file is a programmer bug.
pub fn render_default<T: Serialize>(value: &T) -> String {
    if matches!(serde_json::to_value(value), Ok(serde_json::Value::Null)) {
        return String::new();
    }
    let rendered = toml::Value::try_from(value)
        .unwrap_or_else(|e| panic!("config default is not representable as TOML: {e}"));
    rendered.to_string()
}

/// JSON Schema of `T` as a plain JSON value (used by the derive).
///
/// The generator's shared definitions ride along under a `$defs` key of the returned object so
/// the `$ref` links in it stay resolvable; `schema` lifts them into the document root.
pub fn schema_of<T: JsonSchema>() -> serde_json::Value {
    let mut generator = SchemaGenerator::default();
    let mut node = generator.subschema_for::<T>().to_value();
    let defs = generator.take_definitions(true);
    if let (serde_json::Value::Object(map), false) = (&mut node, defs.is_empty()) {
        map.insert("$defs".to_owned(), serde_json::Value::Object(defs));
    }
    node
}
