//! The DTCG 2025.10 exporter: a resolver document whose base set holds every token and whose
//! `mode` modifier holds one context per mode with just that mode's overrides.
//!
//! Token names map to DTCG paths by splitting the custom property name at its first `-`
//! (`--color-ink` is `color.ink`); a name that is also a group prefix lives at `<name>.$root`.
//! Aliases are written as `{path}` references and carry their resolved `$type`. Scopes, tier
//! and description round-trip through `$extensions["com.crunk"]`.

// frob:ticket 01M4CXQXGBYXFCDTSQQVQKN1E9

use std::collections::BTreeSet;
use std::path::PathBuf;

use crunk_spec::DesignSpec;
use serde_json::{Map, Value, json};

use super::{Comparison, Exporter, Target};
use crate::model::{Token, TokenSet, TokenValue};

/// The DTCG format version crunk pins and writes.
pub const DTCG_VERSION: &str = "2025.10";

/// Renders the DTCG resolver document.
#[derive(Debug, Clone, Copy, Default)]
pub struct DtcgExporter;

/// The DTCG path of `name`, given the set of names that are group prefixes.
fn path_of(name: &str, groups: &BTreeSet<&str>) -> Vec<String> {
    let bare = name.trim_start_matches("--");
    match bare.split_once('-') {
        Some((group, rest)) => vec![group.to_owned(), rest.to_owned()],
        None if groups.contains(bare) => vec![bare.to_owned(), "$root".to_owned()],
        None => vec![bare.to_owned()],
    }
}

fn reference(name: &str, groups: &BTreeSet<&str>) -> String {
    format!("{{{}}}", path_of(name, groups).join("."))
}

fn value_json(value: &TokenValue, groups: &BTreeSet<&str>) -> Value {
    match value {
        TokenValue::Color(c) => {
            json!({"colorSpace": "srgb", "components": [c.r, c.g, c.b], "alpha": c.a, "hex": c.to_hex()})
        }
        TokenValue::Channels { r, g, b } => json!(format!("{r} {g} {b}")),
        TokenValue::Dimension { value, unit } => {
            json!({"value": value, "unit": serde_json::to_value(unit).unwrap_or(Value::Null)})
        }
        TokenValue::Number(n) => json!(n),
        TokenValue::Float(f) => json!(f),
        TokenValue::FontFamily(names) => json!(names),
        TokenValue::Duration(ms) => json!({"value": ms, "unit": "ms"}),
        TokenValue::CubicBezier(b) => json!(b),
        TokenValue::Text(t) => json!(t),
        TokenValue::Alias(target) => json!(reference(target, groups)),
        TokenValue::Composite(members) => Value::Object(
            members
                .iter()
                .map(|(k, v)| (k.clone(), value_json(v, groups)))
                .collect(),
        ),
    }
}

/// Insert `leaf` at `path` under `root`, creating groups.
fn insert(root: &mut Map<String, Value>, path: &[String], leaf: Value) {
    match path {
        [last] => {
            root.insert(last.clone(), leaf);
        }
        [head, rest @ ..] => {
            let slot = root
                .entry(head.clone())
                .or_insert_with(|| Value::Object(Map::new()));
            if let Value::Object(inner) = slot {
                insert(inner, rest, leaf);
            }
        }
        [] => {}
    }
}

fn leaf(
    token: &Token,
    value: &TokenValue,
    tokens: &TokenSet,
    groups: &BTreeSet<&str>,
    with_meta: bool,
) -> Value {
    let mut obj = Map::new();
    let ty = value.dtcg_type().or_else(|| {
        tokens
            .resolve(&token.name, None)
            .and_then(TokenValue::dtcg_type)
    });
    if let Some(ty) = ty {
        obj.insert("$type".to_owned(), json!(ty));
    }
    obj.insert("$value".to_owned(), value_json(value, groups));
    if with_meta {
        if let Some(d) = &token.description {
            obj.insert("$description".to_owned(), json!(d));
        }
        let scopes: Vec<&str> = token.scopes.iter().map(|s| s.name()).collect();
        let tier = serde_json::to_value(token.tier).unwrap_or(Value::Null);
        obj.insert(
            "$extensions".to_owned(),
            json!({"com.crunk": {"tier": tier, "scopes": scopes}}),
        );
    }
    Value::Object(obj)
}

/// The DTCG document for `tokens` as JSON.
pub fn document(tokens: &TokenSet) -> Value {
    let names: Vec<&str> = tokens
        .iter()
        .filter(|t| !matches!(t.value, TokenValue::Channels { .. }))
        .map(|t| t.name.as_str())
        .collect();
    let groups: BTreeSet<&str> = names
        .iter()
        .filter_map(|n| n.trim_start_matches("--").split_once('-').map(|(g, _)| g))
        .collect();
    let mut base = Map::new();
    for token in tokens.iter().filter(|t| names.contains(&t.name.as_str())) {
        let path = path_of(&token.name, &groups);
        insert(
            &mut base,
            &path,
            leaf(token, &token.value, tokens, &groups, true),
        );
    }
    let mut doc = Map::new();
    doc.insert("version".to_owned(), json!(DTCG_VERSION));
    doc.insert(
        "sets".to_owned(),
        json!({"base": {"sources": [Value::Object(base)]}}),
    );
    let mut order = vec![json!({"$ref": "#/sets/base"})];
    let modes = tokens.mode_names();
    if !modes.is_empty() {
        let mut contexts = Map::new();
        contexts.insert("default".to_owned(), json!([]));
        for mode in &modes {
            let mut tree = Map::new();
            for token in tokens.iter() {
                if let Some(v) = token.modes.get(*mode) {
                    let path = path_of(&token.name, &groups);
                    insert(&mut tree, &path, leaf(token, v, tokens, &groups, false));
                }
            }
            contexts.insert((*mode).to_owned(), json!([Value::Object(tree)]));
        }
        doc.insert(
            "modifiers".to_owned(),
            json!({"mode": {"default": "default", "contexts": contexts}}),
        );
        order.push(json!({"$ref": "#/modifiers/mode"}));
    }
    doc.insert("resolutionOrder".to_owned(), Value::Array(order));
    Value::Object(doc)
}

impl Exporter for DtcgExporter {
    fn target(&self) -> Target {
        Target::Dtcg
    }

    /// The pretty-printed resolver document with a trailing newline.
    fn render(&self, _spec: &DesignSpec, tokens: &TokenSet) -> String {
        let mut text = serde_json::to_string_pretty(&document(tokens)).unwrap_or_default();
        text.push('\n');
        text
    }

    fn path(&self, _spec: &DesignSpec) -> Option<PathBuf> {
        None
    }

    fn comparison(&self) -> Comparison {
        Comparison::Json
    }
}
