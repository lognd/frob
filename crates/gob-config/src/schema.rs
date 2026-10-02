//! JSON Schema export for all config tables.

use serde_json::{Map, Value, json};

use crate::describe::{FieldDescription, TableDescription};

/// A JSON Schema document with one property per table (nested by dotted path).
pub fn schema(tables: &[&TableDescription]) -> Value {
    let mut root = Map::new();
    for desc in tables {
        let mut node = table_node(desc);
        let segs: Vec<&str> = desc.table.split('.').collect();
        let (last, parents) = segs
            .split_last()
            .unwrap_or_else(|| unreachable!("split yields at least one segment"));
        let mut props = &mut root;
        for seg in parents {
            let entry = props
                .entry((*seg).to_owned())
                .or_insert_with(|| json!({"type": "object", "properties": {}}));
            props = entry
                .get_mut("properties")
                .and_then(Value::as_object_mut)
                .unwrap_or_else(|| unreachable!("parent nodes are built with properties"));
        }
        // Keep nested children already inserted under this table's node.
        if let (Some(Value::Object(existing)), Some(Value::Object(new_props))) =
            (props.remove(*last), node.get_mut("properties"))
            && let Some(Value::Object(old_props)) = existing.get("properties")
        {
            for (k, v) in old_props {
                new_props.entry(k.clone()).or_insert_with(|| v.clone());
            }
        }
        props.insert((*last).to_owned(), node);
    }
    json!({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": root,
        "additionalProperties": false,
    })
}

fn table_node(desc: &TableDescription) -> Value {
    let props: Map<String, Value> = desc
        .fields
        .iter()
        .map(|f| (f.key.clone(), field_node(f)))
        .collect();
    let mut node = json!({
        "type": "object",
        "properties": props,
        "additionalProperties": false,
    });
    if !desc.doc.is_empty() {
        node["description"] = Value::String(desc.doc.clone());
    }
    node
}

fn field_node(f: &FieldDescription) -> Value {
    let mut node = f.schema.clone();
    if let Value::Object(map) = &mut node {
        if !f.doc.is_empty() {
            map.insert("description".to_owned(), Value::String(f.doc.clone()));
        }
        if let Some(default) = toml_to_json(&f.default_toml) {
            map.insert("default".to_owned(), default);
        }
    }
    node
}

/// Parse an inline TOML value (wrapped in a key) and convert it to JSON.
fn toml_to_json(inline: &str) -> Option<Value> {
    let table: toml::Table = format!("v = {inline}").parse().ok()?;
    serde_json::to_value(table.get("v")?).ok()
}
