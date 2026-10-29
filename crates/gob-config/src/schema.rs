//! JSON Schema export for all config tables.
// frob:ticket 01M4DGHT8H530QHR7VJPHFBHDJ

use serde_json::{Map, Value, json};

use crate::describe::{FieldDescription, RestDescription, TableDescription, product_tables};
use crate::product::product_entry;

/// Key under which schemars (draft 2020-12) stores shared definitions.
const DEFS: &str = "$defs";

/// A JSON Schema document with one property per table (nested by dotted path).
///
/// Every `$ref` a field carries resolves against the root `$defs` object, which merges the
/// definitions each field's schema brought along.
pub fn schema(tables: &[&TableDescription]) -> Value {
    product_schema(tables, &SchemaOptions::default())
}

/// How a product's schema root is presented.
#[derive(Debug, Clone, Default)]
pub struct SchemaOptions {
    /// Schema title (the config file name), when set.
    pub title: Option<String>,
    /// Allow top-level keys outside the listed tables (tables owned by shared crates).
    pub open_top_level: bool,
    /// Top-level tables the file must contain.
    pub required_tables: Vec<String>,
}

/// The config schema of `product`, presented per its registered [`crate::ProductEntry`].
pub fn product_config_schema(product: &str) -> Value {
    let mut tables: Vec<TableDescription> = product_tables(product).collect();
    tables.sort_by(|a, b| a.table.cmp(&b.table));
    let refs: Vec<&TableDescription> = tables.iter().collect();
    let options = product_entry(product).map_or_else(SchemaOptions::default, |e| SchemaOptions {
        title: Some(e.title.to_owned()),
        open_top_level: e.open_top_level,
        required_tables: e.required_tables.iter().map(|t| (*t).to_owned()).collect(),
    });
    product_schema(&refs, &options)
}

/// A JSON Schema document for one product's `tables`, presented per `options`.
pub fn product_schema(tables: &[&TableDescription], options: &SchemaOptions) -> Value {
    let mut root = Map::new();
    let mut defs = Map::new();
    for desc in tables.iter().filter(|d| !d.inline) {
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
        "additionalProperties": options.open_top_level,
    });
    if let Some(title) = &options.title {
        doc["title"] = Value::String(title.clone());
    }
    if !options.required_tables.is_empty() {
        doc["required"] = json!(options.required_tables);
    }
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

/// The schema of one table as a self-contained node: definitions its fields carry ride along
/// under `$defs` (used by the derive to make a nested table usable as a field type).
pub fn table_schema(desc: &TableDescription) -> Value {
    let mut defs = Map::new();
    let mut node = object_node(desc, &mut defs);
    if let (Value::Object(map), false) = (&mut node, defs.is_empty()) {
        map.insert(DEFS.to_owned(), Value::Object(defs));
    }
    node
}

/// The node for a table placed by path: an array wrapper for `[[x]]` tables.
fn table_node(desc: &TableDescription, defs: &mut Map<String, Value>) -> Value {
    let mut node = object_node(desc, defs);
    if desc.array {
        let description = node.as_object_mut().and_then(|m| m.remove("description"));
        let mut wrapped = json!({"type": "array", "items": node});
        if let Some(d) = description {
            wrapped["description"] = d;
        }
        return wrapped;
    }
    node
}

#[allow(clippy::option_if_let_else)]
fn object_node(desc: &TableDescription, defs: &mut Map<String, Value>) -> Value {
    let mut node = match &desc.rest {
        Some(rest) => rest_node(rest, defs),
        None => fields_node(desc, defs),
    };
    if !desc.doc.is_empty() {
        node["description"] = Value::String(desc.doc.clone());
    }
    node
}

/// A table of declared fields: closed properties plus the required list.
fn fields_node(desc: &TableDescription, defs: &mut Map<String, Value>) -> Value {
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
    let required: Vec<&str> = desc
        .fields
        .iter()
        .filter(|f| f.required)
        .map(|f| f.key.as_str())
        .collect();
    if !required.is_empty() {
        node["required"] = json!(required);
    }
    node
}

/// A dynamic-key table: the override schema when given, else any key with one value shape.
fn rest_node(rest: &RestDescription, defs: &mut Map<String, Value>) -> Value {
    let mut node = match &rest.table_schema {
        Some(full) => full.clone(),
        None => json!({"type": "object", "additionalProperties": rest.value_schema.clone()}),
    };
    hoist_defs(&mut node, defs);
    if let Some(Value::Object(map)) = node.get_mut("additionalProperties")
        && let Some(Value::Object(carried)) = map.remove(DEFS)
    {
        merge_defs(defs, carried);
    }
    node
}

/// Move a node's own `$defs` into `defs`.
fn hoist_defs(node: &mut Value, defs: &mut Map<String, Value>) {
    if let Value::Object(map) = node
        && let Some(Value::Object(carried)) = map.remove(DEFS)
    {
        merge_defs(defs, carried);
    }
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
