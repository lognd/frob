//! JSON Schema export for all config tables.
// frob:ticket 01M4DGHT8H530QHR7VJPHFBHDJ

use serde_json::{Map, Value, json};

use crate::describe::{FieldDescription, TableDescription};

/// Key under which schemars (draft 2020-12) stores shared definitions.
const DEFS: &str = "$defs";

/// A JSON Schema document with one property per table (nested by dotted path).
///
/// Every `$ref` a field carries resolves against the root `$defs` object, which merges the
/// definitions each field's schema brought along.
pub fn schema(tables: &[&TableDescription]) -> Value {
    let mut root = Map::new();
    let mut defs = Map::new();
    for desc in tables {
        let mut node = table_node(desc, &mut defs);
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
    let mut doc = json!({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": root,
        "additionalProperties": false,
    });
    let dangling = dangling_refs(&doc, &defs);
    if !dangling.is_empty() {
        tracing::warn!(?dangling, "schema has $ref links with no $defs entry");
    }
    tracing::debug!(defs = defs.len(), "schema assembled");
    if !defs.is_empty() {
        doc[DEFS] = Value::Object(defs);
    }
    doc
}

/// Every `#/$defs/NAME` target referenced under `node` (and inside `defs`) that `defs` lacks.
fn dangling_refs(node: &Value, defs: &Map<String, Value>) -> Vec<String> {
    let mut out = Vec::new();
    collect_dangling(node, defs, &mut out);
    for def in defs.values() {
        collect_dangling(def, defs, &mut out);
    }
    out.sort();
    out.dedup();
    out
}

fn collect_dangling(node: &Value, defs: &Map<String, Value>, out: &mut Vec<String>) {
    match node {
        Value::Object(map) => {
            if let Some(name) = map
                .get("$ref")
                .and_then(Value::as_str)
                .and_then(|r| r.strip_prefix("#/$defs/"))
                && !defs.contains_key(name)
            {
                out.push(name.to_owned());
            }
            map.values().for_each(|v| collect_dangling(v, defs, out));
        }
        Value::Array(items) => items.iter().for_each(|v| collect_dangling(v, defs, out)),
        _ => {}
    }
}

/// Merge `incoming` definitions into `defs`; on a name clash with a different body the first
/// one wins (and the clash is logged), since `$ref` links address definitions by name only.
fn merge_defs(defs: &mut Map<String, Value>, incoming: Map<String, Value>) {
    for (name, def) in incoming {
        match defs.get(&name) {
            Some(existing) if *existing != def => {
                tracing::warn!(%name, "conflicting $defs entries share a name; keeping the first");
            }
            Some(_) => {}
            None => {
                defs.insert(name, def);
            }
        }
    }
}

fn table_node(desc: &TableDescription, defs: &mut Map<String, Value>) -> Value {
    let props: Map<String, Value> = desc
        .fields
        .iter()
        .map(|f| (f.key.clone(), field_node(f, defs)))
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

fn field_node(f: &FieldDescription, defs: &mut Map<String, Value>) -> Value {
    let mut node = f.schema.clone();
    if let Value::Object(map) = &mut node {
        if let Some(Value::Object(carried)) = map.remove(DEFS) {
            merge_defs(defs, carried);
        }
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
