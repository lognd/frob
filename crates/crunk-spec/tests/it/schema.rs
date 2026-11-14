//! The JSON Schema generated from the table types, and the product scoping of crunk's tables.

// frob:ticket 01M43MPG53JR8TP0E15394FZ5T

use crunk_spec::schema::{PRODUCT, schema};

// frob:tests crates/crunk-spec/src/schema.rs::schema
#[test]
fn schema_describes_every_table_and_rejects_unknown_keys() {
    let schema = schema();
    assert_eq!(
        schema["$schema"],
        "https://json-schema.org/draft/2020-12/schema"
    );
    assert_eq!(schema["title"], "crunk.toml");
    let props = schema["properties"].as_object().unwrap();
    for table in crunk_spec::OWN_TABLES {
        assert!(props.contains_key(*table), "schema lacks [{table}]");
    }
    let project = &props["project"];
    assert_eq!(project["additionalProperties"], false);
    assert_eq!(
        project["required"],
        serde_json::json!(["css_root", "tokens_file", "root_font_size"])
    );
    assert!(project["properties"]["css_root"]["description"].is_string());
    let lint = &props["lint"];
    assert!(lint["properties"]["COLOR001"]["enum"].is_array());
    assert_eq!(lint["additionalProperties"], false);
    assert_eq!(lint["properties"]["fix_tolerance"]["default"], 0.15);
    assert_eq!(
        schema["required"],
        serde_json::json!(["project", "palette", "scales", "typography", "org"])
    );
}

// frob:tests crates/crunk-spec/src/schema.rs::schema
#[test]
fn crunk_tables_are_scoped_to_the_crunk_product() {
    let crunk: Vec<String> = gob_config::product_tables(PRODUCT)
        .map(|t| t.table.clone())
        .collect();
    for table in [
        "project", "palette", "lint", "platform", "session", "mock_set",
    ] {
        assert!(crunk.iter().any(|t| t == table), "crunk lacks {table}");
    }
    let frob: Vec<String> = gob_config::frob_tables().map(|t| t.table.clone()).collect();
    for table in &crunk {
        assert!(
            !frob.contains(table),
            "{table} leaked into the frob product"
        );
    }
    assert!(gob_config::products().contains(&PRODUCT.to_owned()));
}
