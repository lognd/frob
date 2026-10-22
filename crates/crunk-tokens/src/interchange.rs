//! Lossless W3C DTCG token files: [`Document::parse`] reads a plain DTCG tree and
//! [`Document::to_value`] writes it back, so import then export equals the input up to key order.
//!
//! The document keeps exactly what the file declares: a group's own `$type` (never the
//! inherited one), `$description`, `$extensions`, every unknown key and every `$value` verbatim
//! (so `16` and `16.0`, a legacy `"16px"` string and a `{value, unit}` object all survive).
//! Parsing validates what a consumer relies on: names, a resolvable `$type` per token, the
//! shape of the known value types and that every `{a.b}` reference resolves without a cycle.

// frob:ticket 01M4CXQYFA9ACDVWF4R62C50FH

use std::collections::BTreeSet;
use std::fmt;
use std::path::Path;

use indexmap::IndexMap;
use serde::de::{self, Deserialize, Deserializer, MapAccess, SeqAccess, Visitor};
use serde_json::{Map, Number, Value};
use thiserror::Error;

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
        /// The `{...}` target path as written.
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

/// The `{a.b}` target of a string that is wholly one reference.
fn whole_reference(value: &Value) -> Option<&str> {
    let inner = value.as_str()?.strip_prefix('{')?.strip_suffix('}')?;
    (!inner.is_empty() && !inner.contains(['{', '}'])).then_some(inner)
}

/// Every whole-string reference nested anywhere in `value`.
fn references<'a>(value: &'a Value, out: &mut Vec<&'a str>) {
    match value {
        Value::String(_) => out.extend(whole_reference(value)),
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
            let target = whole_reference(&token.value)?;
            let (resolved, _) = self.target(target)?;
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

    fn validate(&self) -> Result<(), DtcgError> {
        for (path, token) in self.tokens() {
            let parts: Vec<String> = path.split('.').map(str::to_owned).collect();
            let Some(ty) = self.resolved_type(&path) else {
                return Err(match whole_reference(&token.value) {
                    Some(target) if self.target(target).is_some() => DtcgError::Cycle { path },
                    _ => DtcgError::MissingType { path },
                });
            };
            check_shape(&ty, &token.value, &parts)?;
            let mut refs = Vec::new();
            references(&token.value, &mut refs);
            for target in refs {
                if self.target(target).is_none() {
                    return Err(DtcgError::BrokenReference {
                        path,
                        target: target.to_owned(),
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
