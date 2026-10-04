//! The generated artifacts: the JSON Schema of `crunk.toml` and its reference page.
//!
//! Both are pure functions of the [`crate::table`] types, so a new key needs no edit here.
//! `cargo dev gen` writes them to `docs/schemas/crunk.json` and `docs/crunk/config.md`.

// frob:ticket 01M43ARX764095Q4VWABWXXV5H

use serde_json::{Map, Value};

use crate::table::RawSpec;

/// The JSON Schema (draft 2020-12) of `crunk.toml`.
pub fn schema() -> Value {
    let schema = schemars::generate::SchemaSettings::draft2020_12()
        .into_generator()
        .into_root_schema_for::<RawSpec>();
    serde_json::to_value(schema).unwrap_or_else(|_| unreachable!("a schema always serializes"))
}

/// The reference page: one section per table, one row per key with type, default and doc.
pub fn reference() -> String {
    let root = schema();
    let mut out = String::from(
        "\n# crunk.toml reference\n\n\
         Every table of `crunk.toml`. Unknown keys are errors that name the key, its line and the \
         nearest valid key. Tables owned by shared crates (`[check]`, `[perf]`, ...) are \
         documented in the frob config reference. The machine-readable form is \
         `docs/schemas/crunk.json`.\n\n\
         Path-base law: `[project] tokens_file` resolves against `css_root`; every other `*_file` \
         key (`[tailwind] tokens_file`, `[tokens] json_file`) and `[tailwind] config` resolve \
         against the project root.\n",
    );
    let Some(props) = root.get("properties").and_then(Value::as_object) else {
        return out;
    };
    for (name, prop) in props {
        section(&mut out, &root, name, prop, "");
    }
    out
}

/// The JSON type of `node`, ignoring `null` in a `["T", "null"]` list.
fn kind(node: &Value) -> Option<&str> {
    match node.get("type")? {
        Value::String(s) => Some(s),
        Value::Array(list) => list.iter().filter_map(Value::as_str).find(|t| *t != "null"),
        _ => None,
    }
}

fn deref<'a>(root: &'a Value, node: &'a Value) -> &'a Value {
    node.get("$ref")
        .and_then(Value::as_str)
        .and_then(|r| r.strip_prefix('#'))
        .and_then(|p| root.pointer(p))
        .unwrap_or(node)
}

/// The non-null variant of an `anyOf: [T, null]` node.
fn unwrap_option<'a>(root: &'a Value, node: &'a Value) -> &'a Value {
    let node = deref(root, node);
    if let Some(variants) = node.get("anyOf").and_then(Value::as_array) {
        let non_null: Vec<&Value> = variants
            .iter()
            .filter(|v| v.get("type").and_then(Value::as_str) != Some("null"))
            .collect();
        if let [only] = non_null.as_slice() {
            return deref(root, only);
        }
    }
    node
}

fn is_table(node: &Value) -> bool {
    node.get("properties").is_some_and(Value::is_object) && kind(node) == Some("object")
}

fn array_item_table<'a>(root: &'a Value, node: &'a Value) -> Option<&'a Value> {
    (kind(node) == Some("array"))
        .then(|| node.get("items"))
        .flatten()
        .map(|items| unwrap_option(root, items))
        .filter(|items| is_table(items))
}

fn section(out: &mut String, root: &Value, name: &str, prop: &Value, parent: &str) {
    let node = unwrap_option(root, prop);
    let dotted = if parent.is_empty() {
        name.to_owned()
    } else {
        format!("{parent}.{name}")
    };
    let (heading, table) = if let Some(item) = array_item_table(root, node) {
        (format!("[[{dotted}]]"), item)
    } else if is_table(node) {
        (format!("[{dotted}]"), node)
    } else {
        return;
    };
    out.push_str(&format!("\n## `{heading}`\n\n"));
    let doc = table
        .get("description")
        .or_else(|| node.get("description"))
        .or_else(|| prop.get("description"))
        .and_then(Value::as_str)
        .unwrap_or_default();
    if !doc.trim().is_empty() {
        out.push_str(&format!("{}\n\n", doc.trim()));
    }
    let required: Vec<&str> = table
        .get("required")
        .and_then(Value::as_array)
        .map(|r| r.iter().filter_map(Value::as_str).collect())
        .unwrap_or_default();
    out.push_str("| Key | Type | Required | Default | Doc |\n|---|---|---|---|---|\n");
    let empty = Map::new();
    let fields = table
        .get("properties")
        .and_then(Value::as_object)
        .unwrap_or(&empty);
    let mut nested = Vec::new();
    for (key, field) in fields {
        let inner = unwrap_option(root, field);
        let doc = inner
            .get("description")
            .or_else(|| field.get("description"))
            .and_then(Value::as_str)
            .unwrap_or_default();
        let default = field
            .get("default")
            .or_else(|| inner.get("default"))
            .map_or_else(|| "-".to_owned(), Value::to_string);
        out.push_str(&format!(
            "| `{key}` | {} | {} | `{}` | {} |\n",
            type_text(root, field),
            if required.contains(&key.as_str()) {
                "yes"
            } else {
                "no"
            },
            cell(&default),
            cell(doc)
        ));
        if is_table(inner) || array_item_table(root, inner).is_some() {
            nested.push((key.clone(), field.clone()));
        }
    }
    if let Some(extra) = table.get("additionalProperties").filter(|v| v.is_object()) {
        let doc = extra
            .get("description")
            .and_then(Value::as_str)
            .unwrap_or("user-named entry");
        out.push_str(&format!(
            "| any other key | {} | no | - | {} |\n",
            type_text(root, extra),
            cell(doc)
        ));
    }
    for (key, field) in nested {
        section(out, root, &key, &field, &dotted);
    }
}

/// First paragraph of `text` as one table-cell line.
fn cell(text: &str) -> String {
    text.trim()
        .split("\n\n")
        .next()
        .unwrap_or_default()
        .trim()
        .replace('|', "\\|")
        .replace(['\r', '\n'], " ")
}

fn type_text(root: &Value, node: &Value) -> String {
    let node = unwrap_option(root, node);
    if let Some(values) = node.get("enum").and_then(Value::as_array) {
        return values
            .iter()
            .map(|v| format!("`{}`", v.as_str().unwrap_or_default()))
            .collect::<Vec<_>>()
            .join(" or ");
    }
    if let Some(variants) = node.get("oneOf").and_then(Value::as_array) {
        let names: Vec<String> = variants
            .iter()
            .filter_map(|v| v.get("const").and_then(Value::as_str))
            .map(|c| format!("`{c}`"))
            .collect();
        if names.len() == variants.len() {
            return names.join(" or ");
        }
        let kinds: Vec<String> = variants
            .iter()
            .filter_map(|v| v.pointer("/properties/kind/const").and_then(Value::as_str))
            .map(|c| format!("`{c}`"))
            .collect();
        if kinds.len() == variants.len() {
            return format!("table with `kind` = {}", kinds.join(" or "));
        }
        return "see schema".to_owned();
    }
    match kind(node) {
        Some("array") => {
            let item = node
                .get("items")
                .map_or_else(|| "any".to_owned(), |i| type_text(root, i));
            format!("array of {item}")
        }
        Some("object") => "table".to_owned(),
        Some(other) => other.to_owned(),
        None => "any".to_owned(),
    }
}
