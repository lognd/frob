//! Product scoping and the rest, required, array and inline forms of the derive.

// frob:ticket 01M43MPG53JR8TP0E15394FZ5T

use std::collections::BTreeMap;

use gob_config::{
    ConfigTable, SchemaOptions, TableDescription, frob_tables, product_schema, product_tables,
    products,
};

/// A table of the `acme` product with a required key.
#[derive(Debug, ConfigTable)]
#[config(table = "site", product = "acme")]
struct Site {
    /// Where the site is served from.
    #[config(required)]
    root: String,
    /// Optional title.
    title: Option<String>,
    /// Retry count.
    #[config(default = 3)]
    retries: u32,
}

/// Named colors: any key, one value shape.
#[derive(Debug, ConfigTable)]
#[config(table = "palette", product = "acme", rest)]
struct Palette {
    /// A CSS color literal per name.
    entries: BTreeMap<String, String>,
}

/// One `[[page]]` entry.
#[derive(Debug, ConfigTable)]
#[config(table = "page", product = "acme", array)]
#[allow(dead_code)]
struct Page {
    /// Page id.
    #[config(required)]
    id: String,
}

/// A table nested in the site table.
#[derive(Debug, ConfigTable)]
#[config(table = "site.theme", product = "acme", inline)]
#[allow(dead_code)]
struct Theme {
    /// Theme name.
    #[config(default = "plain".to_owned())]
    name: String,
}

fn acme() -> Vec<TableDescription> {
    let mut tables: Vec<_> = product_tables("acme").collect();
    tables.sort_by(|a, b| a.table.cmp(&b.table));
    tables
}

// frob:tests crates/gob-config/src/describe.rs::product_tables
#[test]
fn product_tables_are_isolated_from_the_frob_registry() {
    let names: Vec<String> = acme().into_iter().map(|t| t.table).collect();
    assert_eq!(names, ["page", "palette", "site", "site.theme"]);
    assert!(frob_tables().all(|t| t.product == "frob"));
    assert!(frob_tables().all(|t| t.table != "site" && t.table != "palette"));
    assert!(products().contains(&"acme".to_owned()));
}

// frob:tests crates/gob-config/src/describe.rs::frob_tables
#[test]
fn required_key_is_an_error_when_missing_and_blocks_default() {
    let ok: Site = toml::from_str("root = \"/srv\"").unwrap();
    assert_eq!(ok.root, "/srv");
    assert_eq!(ok.retries, 3);
    assert_eq!(ok.title, None);
    let err = toml::from_str::<Site>("title = \"x\"")
        .unwrap_err()
        .to_string();
    assert!(err.contains("missing field `root`"), "{err}");
    let err = toml::from_str::<Site>("root = \"a\"\nbogus = 1")
        .unwrap_err()
        .to_string();
    assert!(err.contains("unknown field `bogus`"), "{err}");
}

// frob:tests crates/gob-config/src/schema.rs::product_schema
#[test]
fn rest_table_accepts_any_key_and_schema_marks_required() {
    let p: Palette = toml::from_str("ink = \"#000\"\npaper = \"#fff\"").unwrap();
    assert_eq!(p.entries.len(), 2);
    assert_eq!(p.entries["ink"], "#000");
    let tables = acme();
    let refs: Vec<&TableDescription> = tables.iter().collect();
    let options = SchemaOptions {
        title: Some("acme.toml".to_owned()),
        open_top_level: false,
        required_tables: vec!["site".to_owned()],
    };
    let schema = product_schema(&refs, &options);
    assert_eq!(schema["title"], "acme.toml");
    assert_eq!(schema["required"], serde_json::json!(["site"]));
    let props = &schema["properties"];
    assert_eq!(props["site"]["required"], serde_json::json!(["root"]));
    assert_eq!(props["site"]["additionalProperties"], false);
    assert_eq!(props["palette"]["additionalProperties"]["type"], "string");
    assert_eq!(props["page"]["type"], "array");
    assert!(props.get("theme").is_none());
    assert!(Theme::describe().inline);
    assert!(Page::describe().array);
}
