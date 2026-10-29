//! Per-product presentation of the generated config page and schema.
// frob:ticket 01M43MPG53JR8TP0E15394FZ5T

/// How one product's config reference and schema are presented; registered by the product's crate.
///
/// A product with config tables but no entry still gets a page and a schema at default paths.
#[derive(Debug, Clone, Copy)]
pub struct ProductEntry {
    /// Product name, matching `#[config(product = ...)]` on its tables.
    pub product: &'static str,
    /// Title of the config file in the schema (`crunk.toml`).
    pub title: &'static str,
    /// Markdown placed after the page heading, before the first table section.
    pub intro: &'static str,
    /// True when top-level keys outside the product's own tables are allowed in the schema.
    pub open_top_level: bool,
    /// Top-level tables the file must contain.
    pub required_tables: &'static [&'static str],
}

inventory::collect!(ProductEntry);

/// The registered presentation entry of `product`, if its crate submitted one.
pub fn product_entry(product: &str) -> Option<&'static ProductEntry> {
    inventory::iter::<ProductEntry>
        .into_iter()
        .find(|e| e.product == product)
}
