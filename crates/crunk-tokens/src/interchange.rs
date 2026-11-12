//! Lossless W3C DTCG token files: [`Document::parse`] reads a plain DTCG tree and
//! [`Document::to_value`] writes it back, so import then export equals the input up to key order.
//!
//! The document keeps exactly what the file declares: a group's own `$type` (never the
//! inherited one), `$description`, `$extensions`, every unknown key and every `$value` verbatim
//! (so `16` and `16.0`, a legacy `"16px"` string and a `{value, unit}` object all survive).
//! Parsing validates what a consumer relies on: names, a resolvable `$type` per token, the
//! shape of the known value types and that every `{a.b}` or `{"$ref": "#/a/b/$value"}` reference resolves without a cycle.

// frob:ticket 01M4CXQYFA9ACDVWF4R62C50FH

use std::collections::BTreeSet;
use std::fmt;
use std::path::Path;

use indexmap::IndexMap;
use serde::de::{self, Deserialize, Deserializer, MapAccess, SeqAccess, Visitor};
use serde_json::{Map, Number, Value};
use thiserror::Error;

use crate::model::{Tier, Token, TokenKind, TokenSet, TokenValue, Unit};

/// Why a DTCG file was refused.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum DtcgError {
    /// The text is not valid JSON, nests too deeply, or repeats a name inside one object.
    #[error("not a valid DTCG file: {message}")]
    Syntax {
        /// The parser's message (with line and column).
        message: String,
    },
    /// A node, name or value is malformed.
    #[error("`{path}`: {reason}")]
    Invalid {
        /// The dotted path of the offending node (empty for the root).
        path: String,
        /// What is wrong.
        reason: String,
    },
    /// A token has no `$type`, none inherited and no alias to take one from.
    #[error("`{path}`: no $type on the token, any enclosing group or its alias target")]
    MissingType {
        /// The dotted token path.
        path: String,
    },
    /// A reference names no token.
    #[error("`{path}`: reference `{target}` does not resolve to a token")]
    BrokenReference {
        /// The referencing token.
        path: String,
        /// The reference as written: the `{...}` path or the `$ref` JSON pointer.
        target: String,
    },
    /// The file could not be read or written.
    #[error("cannot {action} {path}: {message}")]
    Io {
        /// `read` or `write`.
        action: &'static str,
        /// The file, lossily as text.
        path: String,
        /// The OS error.
        message: String,
    },
    /// Two distinct token paths map to the same CSS custom property.
    #[error("`{first}` and `{second}` both map to the custom property `{property}`")]
    NameCollision {
        /// The earlier token path (file order).
        first: String,
        /// The later token path.
        second: String,
        /// The shared custom property name.
        property: String,
    },
    /// The document is valid DTCG but has no faithful [`TokenSet`] form.
    #[error("`{path}`: cannot compile to a token set: {reason}")]
    Unsupported {
        /// The dotted token path.
        path: String,
        /// What crunk's token model cannot represent.
        reason: String,
    },
    /// A chain of whole-value aliases loops back on itself.
    #[error("`{path}`: reference chain is cyclic")]
    Cycle {
        /// A token on the cycle.
        path: String,
    },
}

/// One token: its declared `$type`, verbatim `$value` and the keys around it.
#[derive(Debug, Clone, PartialEq)]
pub struct TokenNode {
    /// The `$type` declared on the token itself, if any.
    pub declared_type: Option<String>,
    /// The `$value`, verbatim.
    pub value: Value,
    /// The `$description`, if any.
    pub description: Option<String>,
    /// The `$extensions` object, if any.
    pub extensions: Option<Value>,
    /// Every other key (`$deprecated`, unknown `$` keys, vendor keys), verbatim.
    pub extra: IndexMap<String, Value>,
}

/// One group: its own metadata and children in file order.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct GroupNode {
    /// The `$type` declared on the group, inherited by descendants.
    pub declared_type: Option<String>,
    /// The `$description`, if any.
    pub description: Option<String>,
    /// The `$extensions` object, if any.
    pub extensions: Option<Value>,
    /// Every other `$` key (`$extends`, `$deprecated`, `$schema`, unknown), verbatim.
    pub extra: IndexMap<String, Value>,
    /// Child groups and tokens by name (`$root` is a token child).
    pub children: IndexMap<String, Node>,
}

/// A group or a token.
#[derive(Debug, Clone, PartialEq)]
pub enum Node {
    /// A node with child nodes.
    Group(GroupNode),
    /// A node holding a `$value`.
    Token(TokenNode),
}

/// A parsed DTCG file; the root is a [`GroupNode`].
#[derive(Debug, Clone, PartialEq, Default)]
pub struct Document {
    /// The root group.
    pub root: GroupNode,
}

/// Counts of what a [`Document`] holds, for reports.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Summary {
    /// Tokens, `$root` tokens included.
    pub tokens: usize,
    /// Groups, the root excluded.
    pub groups: usize,
    /// Tokens whose whole value is a `{...}` reference.
    pub aliases: usize,
}

/// The JSON as the strict reader sees it: objects keep order and refuse duplicate names.
enum Raw {
    Object(IndexMap<String, Raw>),
    Array(Vec<Raw>),
    Leaf(Value),
}

impl Raw {
    fn into_value(self) -> Value {
        match self {
            Self::Object(m) => Value::Object(
                m.into_iter()
                    .map(|(k, v)| (k, v.into_value()))
                    .collect::<Map<_, _>>(),
            ),
            Self::Array(a) => Value::Array(a.into_iter().map(Self::into_value).collect()),
            Self::Leaf(v) => v,
        }
    }
}

struct RawVisitor;

impl<'de> Visitor<'de> for RawVisitor {
    type Value = Raw;

    fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("any JSON value")
    }

    fn visit_bool<E: de::Error>(self, v: bool) -> Result<Raw, E> {
        Ok(Raw::Leaf(Value::Bool(v)))
    }

    fn visit_i64<E: de::Error>(self, v: i64) -> Result<Raw, E> {
        Ok(Raw::Leaf(Value::from(v)))
    }

    fn visit_u64<E: de::Error>(self, v: u64) -> Result<Raw, E> {
        Ok(Raw::Leaf(Value::from(v)))
    }

    fn visit_f64<E: de::Error>(self, v: f64) -> Result<Raw, E> {
        Number::from_f64(v)
            .map(|n| Raw::Leaf(Value::Number(n)))
            .ok_or_else(|| E::custom("number is not finite"))
    }

    fn visit_str<E: de::Error>(self, v: &str) -> Result<Raw, E> {
        Ok(Raw::Leaf(Value::String(v.to_owned())))
    }

    fn visit_unit<E: de::Error>(self) -> Result<Raw, E> {
        Ok(Raw::Leaf(Value::Null))
    }

    fn visit_seq<A: SeqAccess<'de>>(self, mut seq: A) -> Result<Raw, A::Error> {
        let mut items = Vec::new();
        while let Some(item) = seq.next_element::<Raw>()? {
            items.push(item);
        }
        Ok(Raw::Array(items))
    }

    fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Raw, A::Error> {
        let mut out = IndexMap::new();
        while let Some(key) = map.next_key::<String>()? {
            if out.contains_key(&key) {
                return Err(de::Error::custom(format!("duplicate name `{key}`")));
            }
            let value = map.next_value::<Raw>()?;
            out.insert(key, value);
        }
        Ok(Raw::Object(out))
    }
}

impl<'de> Deserialize<'de> for Raw {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        d.deserialize_any(RawVisitor)
    }
}

fn io_error(action: &'static str, path: &Path, e: &std::io::Error) -> DtcgError {
    tracing::warn!(path = %path.to_string_lossy(), error = %e, "dtcg: {action} failed");
    DtcgError::Io {
        action,
        path: path.to_string_lossy().into_owned(),
        message: e.to_string(),
    }
}

fn invalid(path: &[String], reason: impl Into<String>) -> DtcgError {
    DtcgError::Invalid {
        path: path.join("."),
        reason: reason.into(),
    }
}

/// A `$type`, `$description`-style string field.
fn string_field(
    obj: &mut IndexMap<String, Raw>,
    key: &str,
    path: &[String],
) -> Result<Option<String>, DtcgError> {
    match obj.shift_remove(key) {
        None => Ok(None),
        Some(Raw::Leaf(Value::String(s))) => Ok(Some(s)),
        Some(_) => Err(invalid(path, format!("{key} must be a string"))),
    }
}

fn extensions_field(
    obj: &mut IndexMap<String, Raw>,
    path: &[String],
) -> Result<Option<Value>, DtcgError> {
    match obj.shift_remove("$extensions") {
        None => Ok(None),
        Some(raw @ Raw::Object(_)) => Ok(Some(raw.into_value())),
        Some(_) => Err(invalid(path, "$extensions must be an object")),
    }
}

fn check_name(name: &str, path: &[String]) -> Result<(), DtcgError> {
    if name.is_empty() || name.contains(['.', '{', '}']) {
        return Err(invalid(
            path,
            "a name may not be empty or contain `.`, `{` or `}`",
        ));
    }
    Ok(())
}

fn parse_group(
    mut obj: IndexMap<String, Raw>,
    path: &mut Vec<String>,
) -> Result<GroupNode, DtcgError> {
    let declared_type = string_field(&mut obj, "$type", path)?;
    let description = string_field(&mut obj, "$description", path)?;
    let extensions = extensions_field(&mut obj, path)?;
    let mut group = GroupNode {
        declared_type,
        description,
        extensions,
        ..GroupNode::default()
    };
    for (name, raw) in obj {
        if name.starts_with('$') && name != "$root" {
            group.extra.insert(name, raw.into_value());
            continue;
        }
        path.push(name.clone());
        if name != "$root" {
            check_name(&name, path)?;
        }
        let node = parse_node(raw, path)?;
        path.pop();
        group.children.insert(name, node);
    }
    Ok(group)
}

fn parse_token(mut obj: IndexMap<String, Raw>, path: &[String]) -> Result<TokenNode, DtcgError> {
    let declared_type = string_field(&mut obj, "$type", path)?;
    let description = string_field(&mut obj, "$description", path)?;
    let extensions = extensions_field(&mut obj, path)?;
    let value = obj
        .shift_remove("$value")
        .map_or(Value::Null, Raw::into_value);
    let extra = obj.into_iter().map(|(k, v)| (k, v.into_value())).collect();
    Ok(TokenNode {
        declared_type,
        value,
        description,
        extensions,
        extra,
    })
}

fn parse_node(raw: Raw, path: &mut Vec<String>) -> Result<Node, DtcgError> {
    let Raw::Object(obj) = raw else {
        return Err(invalid(path, "a group or token must be a JSON object"));
    };
    if obj.contains_key("$value") {
        parse_token(obj, path).map(Node::Token)
    } else {
        parse_group(obj, path).map(Node::Group)
    }
}

/// A whole-value reference: the dotted token path it names and the text as written.
struct Reference {
    /// The dotted path looked up in the document (the raw text when a pointer is malformed).
    target: String,
    /// The reference as written (`a.b` for `{a.b}`, the pointer for a `$ref`).
    written: String,
}

/// Decode a `#/a/b/$value` JSON pointer (RFC 6901, `~0` and `~1` escapes) to a dotted path.
fn pointer_target(pointer: &str) -> Option<String> {
    let rest = pointer.strip_prefix("#/")?;
    let rest = rest.strip_suffix("/$value").unwrap_or(rest);
    let parts: Vec<String> = rest
        .split('/')
        .map(|p| p.replace("~1", "/").replace("~0", "~"))
        .collect();
    (parts.iter().all(|p| !p.is_empty() && !p.contains('.'))).then(|| parts.join("."))
}

/// The target of a value that is wholly one reference: `{a.b}` or `{"$ref": "#/a/b/$value"}`.
fn whole_reference(value: &Value) -> Option<Reference> {
    if let Value::Object(map) = value {
        let (1, Some(Value::String(pointer))) = (map.len(), map.get("$ref")) else {
            return None;
        };
        let target = pointer_target(pointer).unwrap_or_else(|| pointer.clone());
        return Some(Reference {
            target,
            written: pointer.clone(),
        });
    }
    let inner = value.as_str()?.strip_prefix('{')?.strip_suffix('}')?;
    (!inner.is_empty() && !inner.contains(['{', '}'])).then(|| Reference {
        target: inner.to_owned(),
        written: inner.to_owned(),
    })
}

/// Every whole-value reference nested anywhere in `value`.
fn references(value: &Value, out: &mut Vec<Reference>) {
    if let Some(reference) = whole_reference(value) {
        out.push(reference);
        return;
    }
    match value {
        Value::Array(items) => items.iter().for_each(|v| references(v, out)),
        Value::Object(map) => map.values().for_each(|v| references(v, out)),
        _ => {}
    }
}

fn is_number(value: &Value) -> bool {
    value.is_number()
}

/// Reject a `$value` whose shape cannot be the known `$type`; aliases pass through.
fn check_shape(ty: &str, value: &Value, path: &[String]) -> Result<(), DtcgError> {
    if whole_reference(value).is_some() {
        return Ok(());
    }
    let ok = match ty {
        "number" => is_number(value),
        "cubicBezier" => value.as_array().is_some_and(|a| {
            a.len() == 4
                && a.iter()
                    .all(|v| is_number(v) || whole_reference(v).is_some())
        }),
        "dimension" | "duration" => {
            value.is_string()
                || value
                    .get("value")
                    .is_some_and(|v| is_number(v) || v.is_string())
        }
        "color" => value.is_string() || value.is_object(),
        "fontFamily" => {
            value.is_string()
                || value
                    .as_array()
                    .is_some_and(|a| a.iter().all(Value::is_string))
        }
        "typography" | "shadow" | "border" | "transition" | "gradient" | "strokeStyle" => {
            value.is_object() || value.is_array() || value.is_string()
        }
        _ => true,
    };
    if ok {
        Ok(())
    } else {
        Err(invalid(
            path,
            format!("$value does not have the shape of $type `{ty}`"),
        ))
    }
}

impl Document {
    /// Parse and validate DTCG `text`.
    ///
    /// # Errors
    ///
    /// [`DtcgError::Syntax`] for bad JSON or a repeated name, [`DtcgError::Invalid`] for a
    /// malformed node, [`DtcgError::MissingType`], [`DtcgError::BrokenReference`] or
    /// [`DtcgError::Cycle`] when types or references do not resolve.
    pub fn parse(text: &str) -> Result<Self, DtcgError> {
        let raw: Raw = serde_json::from_str(text).map_err(|e| {
            tracing::info!(error = %e, "dtcg: text did not parse");
            DtcgError::Syntax {
                message: e.to_string(),
            }
        })?;
        let Raw::Object(obj) = raw else {
            return Err(invalid(&[], "the top level must be a JSON object"));
        };
        let root = parse_group(obj, &mut Vec::new())?;
        let doc = Self { root };
        doc.validate()?;
        tracing::debug!(summary = ?doc.summary(), "dtcg: document parsed");
        Ok(doc)
    }

    /// Read and validate the DTCG file at `path`.
    ///
    /// # Errors
    ///
    /// [`DtcgError::Io`] when unreadable, otherwise as [`Document::parse`].
    pub fn read(path: &Path) -> Result<Self, DtcgError> {
        let text = std::fs::read_to_string(path).map_err(|e| io_error("read", path, &e))?;
        tracing::debug!(path = %path.to_string_lossy(), bytes = text.len(), "dtcg: file read");
        Self::parse(&text)
    }

    /// Atomically write the rendered document to `path`, creating parent directories.
    ///
    /// # Errors
    ///
    /// [`DtcgError::Io`] when the file cannot be written.
    pub fn write(&self, path: &Path) -> Result<(), DtcgError> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).map_err(|e| io_error("write", path, &e))?;
        }
        gob_fs::write_atomic(path, self.render().as_bytes())
            .map_err(|e| io_error("write", path, &e))?;
        tracing::info!(path = %path.to_string_lossy(), "dtcg: file written");
        Ok(())
    }

    /// The document as JSON, equal to the parsed input up to key order.
    pub fn to_value(&self) -> Value {
        group_value(&self.root)
    }

    /// The pretty-printed document with a trailing newline.
    pub fn render(&self) -> String {
        let mut text = serde_json::to_string_pretty(&self.to_value()).unwrap_or_default();
        text.push('\n');
        text
    }

    /// The token at dotted `path`, if there is one.
    pub fn token(&self, path: &str) -> Option<&TokenNode> {
        match self.node(path)? {
            Node::Token(t) => Some(t),
            Node::Group(_) => None,
        }
    }

    /// The node at dotted `path` (the root for the empty path).
    fn node(&self, path: &str) -> Option<&Node> {
        let mut group = &self.root;
        let mut parts = path.split('.').peekable();
        if path.is_empty() {
            return None;
        }
        while let Some(part) = parts.next() {
            let node = group.children.get(part)?;
            if parts.peek().is_none() {
                return Some(node);
            }
            match node {
                Node::Group(g) => group = g,
                Node::Token(_) => return None,
            }
        }
        None
    }

    /// The token a reference `target` names; a group resolves to its `$root` token.
    fn target(&self, target: &str) -> Option<(String, &TokenNode)> {
        match self.node(target)? {
            Node::Token(t) => Some((target.to_owned(), t)),
            Node::Group(g) => match g.children.get("$root")? {
                Node::Token(t) => Some((format!("{target}.$root"), t)),
                Node::Group(_) => None,
            },
        }
    }

    /// The effective `$type` of the token at `path`: its own, else the nearest enclosing
    /// group's, else its alias target's.
    pub fn resolved_type(&self, path: &str) -> Option<String> {
        self.resolve_type(path, &mut BTreeSet::new())
    }

    fn resolve_type(&self, path: &str, seen: &mut BTreeSet<String>) -> Option<String> {
        if !seen.insert(path.to_owned()) {
            return None;
        }
        let token = self.token(path)?;
        if let Some(ty) = &token.declared_type {
            return Some(ty.clone());
        }
        let mut group = &self.root;
        let mut inherited = group.declared_type.clone();
        let parts: Vec<&str> = path.split('.').collect();
        for part in &parts[..parts.len() - 1] {
            let Node::Group(g) = group.children.get(*part)? else {
                break;
            };
            group = g;
            if group.declared_type.is_some() {
                inherited.clone_from(&group.declared_type);
            }
        }
        inherited.or_else(|| {
            let reference = whole_reference(&token.value)?;
            let (resolved, _) = self.target(&reference.target)?;
            self.resolve_type(&resolved, seen)
        })
    }

    /// Visit every token with its dotted path, in file order.
    pub fn tokens(&self) -> Vec<(String, &TokenNode)> {
        let mut out = Vec::new();
        collect(&self.root, &mut Vec::new(), &mut out);
        out
    }

    /// Counts of tokens, groups and aliases.
    pub fn summary(&self) -> Summary {
        let mut summary = Summary::default();
        count(&self.root, &mut summary);
        summary
    }

    /// The first pair of distinct token paths that map to one CSS custom property, if any.
    ///
    /// # Errors
    ///
    /// [`DtcgError::NameCollision`] naming both paths and the shared property.
    pub fn check_css_names(&self) -> Result<(), DtcgError> {
        let mut seen = std::collections::BTreeMap::<String, String>::new();
        for (path, _) in self.tokens() {
            let property = crate::dialect::name_of_path(&path);
            if let Some(first) = seen.get(&property) {
                tracing::warn!(%first, second = %path, %property, "dtcg: css name collision");
                return Err(DtcgError::NameCollision {
                    first: first.clone(),
                    second: path,
                    property,
                });
            }
            seen.insert(property, path);
        }
        Ok(())
    }

    /// Compile the document into a [`TokenSet`]: one token per DTCG token in file order, each
    /// holding its resolved value (references replaced by the value they name).
    ///
    /// # Errors
    ///
    /// [`DtcgError::Unsupported`] for a `$type` or value crunk's model cannot hold, or when two
    /// tokens (a group and its `$root`) compile to one custom property.
    pub fn compile(&self) -> Result<TokenSet, DtcgError> {
        let mut tokens = Vec::new();
        for (path, node) in self.tokens() {
            let unsupported = |reason: String| DtcgError::Unsupported {
                path: path.clone(),
                reason,
            };
            let ty = self
                .resolved_type(&path)
                .ok_or_else(|| DtcgError::MissingType { path: path.clone() })?;
            let value = self
                .convert(&ty, &node.value, &mut BTreeSet::new())
                .map_err(unsupported)?;
            let key = path.strip_suffix(".$root").unwrap_or(&path).to_owned();
            tokens.push(Token {
                name: crate::dialect::name_of_path(&key),
                kind: if matches!(value, TokenValue::Color(_)) {
                    TokenKind::Color
                } else {
                    TokenKind::Custom
                },
                origin: format!("dtcg {path}"),
                key,
                tier: Tier::Primitive,
                value,
                modes: IndexMap::new(),
                scopes: Vec::new(),
                description: node.description.clone(),
                deprecated: match node.extra.get("$deprecated") {
                    Some(Value::String(why)) => Some(why.clone()),
                    Some(Value::Bool(true)) => Some("deprecated".to_owned()),
                    _ => None,
                },
            });
        }
        let set = TokenSet::from_tokens(tokens).map_err(|e| {
            tracing::warn!(error = %e, "dtcg: compile collided");
            DtcgError::Unsupported {
                path: String::new(),
                reason: e.to_string(),
            }
        })?;
        tracing::debug!(count = set.len(), "dtcg: compiled to token set");
        Ok(set)
    }

    /// Convert a `$value` of DTCG type `ty` to a model value, following references.
    fn convert(
        &self,
        ty: &str,
        value: &Value,
        seen: &mut BTreeSet<String>,
    ) -> Result<TokenValue, String> {
        if let Some(Reference { target, written }) = whole_reference(value) {
            let (path, node) = self
                .target(&target)
                .ok_or_else(|| format!("reference `{written}` does not resolve"))?;
            if !seen.insert(path.clone()) {
                return Err(format!("reference `{written}` is cyclic"));
            }
            let target_ty = self.resolved_type(&path).unwrap_or_else(|| ty.to_owned());
            let out = self.convert(&target_ty, &node.value, seen);
            seen.remove(&path);
            return out;
        }
        match ty {
            "color" => color_value(value),
            "dimension" => dimension(value, "px").map(|value| TokenValue::Dimension {
                value,
                unit: Unit::Px,
            }),
            "duration" => dimension(value, "ms").map(TokenValue::Duration),
            "number" => Ok(number_value(value)?),
            "cubicBezier" => {
                let items = value
                    .as_array()
                    .ok_or("a cubicBezier is a list of 4 numbers")?;
                let mut out = [0.0; 4];
                if items.len() != 4 {
                    return Err("a cubicBezier needs exactly 4 numbers".to_owned());
                }
                for (slot, item) in out.iter_mut().zip(items) {
                    *slot = item
                        .as_f64()
                        .or_else(|| match self.convert("number", item, seen) {
                            Ok(TokenValue::Float(f)) => Some(f),
                            _ => None,
                        })
                        .ok_or("a cubicBezier member is not a number")?;
                }
                Ok(TokenValue::CubicBezier(out))
            }
            "fontFamily" => match value {
                Value::String(name) => Ok(TokenValue::FontFamily(vec![name.clone()])),
                Value::Array(names) => names
                    .iter()
                    .map(|n| {
                        n.as_str()
                            .map(str::to_owned)
                            .ok_or("a font family is not text")
                    })
                    .collect::<Result<_, _>>()
                    .map(TokenValue::FontFamily)
                    .map_err(str::to_owned),
                _ => Err("a fontFamily is text or a list of text".to_owned()),
            },
            "string" => value
                .as_str()
                .map(|s| TokenValue::Text(s.to_owned()))
                .ok_or_else(|| "a string token holds text".to_owned()),
            "typography" | "shadow" | "border" | "transition" => {
                let object = match value {
                    Value::Array(layers) if layers.len() == 1 => &layers[0],
                    other => other,
                };
                let members = object
                    .as_object()
                    .ok_or("a composite is an object (a shadow list needs exactly one layer)")?;
                let mut out = IndexMap::new();
                for (key, member) in members {
                    out.insert(key.clone(), self.member(member, seen)?);
                }
                Ok(TokenValue::Composite(out))
            }
            other => Err(format!("$type `{other}` has no token model form")),
        }
    }

    /// Convert a composite member, whose type is read from its shape.
    fn member(&self, value: &Value, seen: &mut BTreeSet<String>) -> Result<TokenValue, String> {
        if let Some(Reference { target, written }) = whole_reference(value) {
            let ty = self
                .target(&target)
                .and_then(|(path, _)| self.resolved_type(&path))
                .ok_or_else(|| format!("reference `{written}` does not resolve"))?;
            return self.convert(&ty, value, seen);
        }
        match value {
            Value::Number(_) => number_value(value),
            Value::Array(items) if items.iter().all(Value::is_number) => {
                self.convert("cubicBezier", value, seen)
            }
            Value::Array(_) => self.convert("fontFamily", value, seen),
            Value::Object(map) if map.contains_key("colorSpace") => color_value(value),
            Value::Object(map) if map.contains_key("unit") => {
                dimension(value, "px").map(|value| TokenValue::Dimension {
                    value,
                    unit: Unit::Px,
                })
            }
            Value::String(s) => Ok(color_value(value)
                .or_else(|_| {
                    dimension(value, "px").map(|value| TokenValue::Dimension {
                        value,
                        unit: Unit::Px,
                    })
                })
                .unwrap_or_else(|_| TokenValue::Text(s.clone()))),
            _ => Err("a composite member has no token model form".to_owned()),
        }
    }

    fn validate(&self) -> Result<(), DtcgError> {
        self.check_css_names()?;
        for (path, token) in self.tokens() {
            let parts: Vec<String> = path.split('.').map(str::to_owned).collect();
            let Some(ty) = self.resolved_type(&path) else {
                return Err(match whole_reference(&token.value) {
                    Some(r) if self.target(&r.target).is_some() => DtcgError::Cycle { path },
                    _ => DtcgError::MissingType { path },
                });
            };
            check_shape(&ty, &token.value, &parts)?;
            let mut refs = Vec::new();
            references(&token.value, &mut refs);
            for reference in refs {
                if self.target(&reference.target).is_none() {
                    tracing::warn!(%path, target = %reference.written, "dtcg: unresolvable reference");
                    return Err(DtcgError::BrokenReference {
                        path,
                        target: reference.written,
                    });
                }
            }
        }
        Ok(())
    }
}

fn collect<'a>(
    group: &'a GroupNode,
    prefix: &mut Vec<String>,
    out: &mut Vec<(String, &'a TokenNode)>,
) {
    for (name, node) in &group.children {
        prefix.push(name.clone());
        match node {
            Node::Token(t) => out.push((prefix.join("."), t)),
            Node::Group(g) => collect(g, prefix, out),
        }
        prefix.pop();
    }
}

fn count(group: &GroupNode, summary: &mut Summary) {
    for node in group.children.values() {
        match node {
            Node::Token(t) => {
                summary.tokens += 1;
                summary.aliases += usize::from(whole_reference(&t.value).is_some());
            }
            Node::Group(g) => {
                summary.groups += 1;
                count(g, summary);
            }
        }
    }
}

fn meta(
    out: &mut Map<String, Value>,
    ty: Option<&String>,
    description: Option<&String>,
    extensions: Option<&Value>,
) {
    if let Some(ty) = ty {
        out.insert("$type".to_owned(), Value::String(ty.clone()));
    }
    if let Some(d) = description {
        out.insert("$description".to_owned(), Value::String(d.clone()));
    }
    if let Some(e) = extensions {
        out.insert("$extensions".to_owned(), e.clone());
    }
}

fn group_value(group: &GroupNode) -> Value {
    let mut out = Map::new();
    meta(
        &mut out,
        group.declared_type.as_ref(),
        group.description.as_ref(),
        group.extensions.as_ref(),
    );
    out.extend(group.extra.iter().map(|(k, v)| (k.clone(), v.clone())));
    for (name, node) in &group.children {
        let value = match node {
            Node::Group(g) => group_value(g),
            Node::Token(t) => token_value(t),
        };
        out.insert(name.clone(), value);
    }
    Value::Object(out)
}

fn token_value(token: &TokenNode) -> Value {
    let mut out = Map::new();
    meta(
        &mut out,
        token.declared_type.as_ref(),
        token.description.as_ref(),
        token.extensions.as_ref(),
    );
    out.extend(token.extra.iter().map(|(k, v)| (k.clone(), v.clone())));
    out.insert("$value".to_owned(), token.value.clone());
    Value::Object(out)
}

/// A JSON number as the model's integer (`16`) or fractional (`16.0`) value.
fn number_value(value: &Value) -> Result<TokenValue, String> {
    let number = value.as_number().ok_or("expected a number")?;
    if let Some(n) = number.as_i64() {
        return Ok(TokenValue::Number(n));
    }
    number
        .as_f64()
        .map(TokenValue::Float)
        .ok_or_else(|| "number out of range".to_owned())
}

/// A DTCG color: a hex or CSS string, or an sRGB `{colorSpace, components, alpha}` object.
fn color_value(value: &Value) -> Result<TokenValue, String> {
    use crunk_values::Color;
    if let Some(text) = value.as_str() {
        return Color::parse(text)
            .map(TokenValue::Color)
            .map_err(|e| format!("bad color `{text}`: {e}"));
    }
    let object = value.as_object().ok_or("a color is text or an object")?;
    let space = object
        .get("colorSpace")
        .and_then(Value::as_str)
        .unwrap_or("");
    if space != "srgb" {
        return Err(format!(
            "color space `{space}` is not supported (only srgb)"
        ));
    }
    let comps: Vec<f64> = object
        .get("components")
        .and_then(Value::as_array)
        .map(|a| a.iter().filter_map(Value::as_f64).collect())
        .unwrap_or_default();
    let [r, g, b] = comps[..] else {
        return Err("srgb components need exactly 3 numbers".to_owned());
    };
    let alpha = object.get("alpha").and_then(Value::as_f64).unwrap_or(1.0);
    Ok(TokenValue::Color(Color::new(r, g, b, alpha)))
}

/// A dimension or duration magnitude: `"16px"`, `"0.2s"`, or `{value, unit}`; durations are
/// returned in ms and dimensions in px (`default_unit` names which).
fn dimension(value: &Value, default_unit: &str) -> Result<f64, String> {
    let (magnitude, unit) = match value {
        Value::String(text) => {
            let at = text
                .find(|c: char| c.is_ascii_alphabetic())
                .unwrap_or(text.len());
            let (n, u) = text.split_at(at);
            (
                n.trim()
                    .parse::<f64>()
                    .map_err(|_| format!("cannot read `{text}`"))?,
                u.to_owned(),
            )
        }
        Value::Object(map) => {
            let n = map
                .get("value")
                .and_then(Value::as_f64)
                .ok_or("missing numeric value")?;
            let u = map
                .get("unit")
                .and_then(Value::as_str)
                .unwrap_or(default_unit);
            (n, u.to_owned())
        }
        _ => return Err("expected a string or a {value, unit} object".to_owned()),
    };
    match (default_unit, unit.as_str()) {
        ("px", "px") | ("ms", "ms") => Ok(magnitude),
        ("ms", "s") => Ok(magnitude * 1000.0),
        (_, other) => Err(format!("unit `{other}` is not supported")),
    }
}
