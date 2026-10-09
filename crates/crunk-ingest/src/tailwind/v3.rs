//! The static Tailwind 3 reader: the `theme` / `theme.extend` region of a JS or TS config.
//!
//! The fallback when the project's own Tailwind cannot be run. A bounded, side-effect free
//! evaluator over the tree-sitter syntax tree: object and array literals, strings, numbers,
//! template literals without substitutions, spreads, top-level `const` references, member access,
//! `as const` / `satisfies` wrappers, and relative `.json` imports (`import t from "./t.json"`,
//! `require("./t.json")`). Anything else (a function call, a plugin, an unresolvable import) is
//! left out and recorded as unresolved, never guessed.

// frob:ticket 01M43ARZ3VCNDX20C9BZZCCYHY

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use indexmap::IndexMap;
use tree_sitter::Node;

/// Deepest nesting the evaluator follows (references, spreads, members).
const MAX_DEPTH: usize = 32;

/// A statically known value.
#[derive(Debug, Clone, PartialEq)]
pub enum Val {
    /// A string.
    Str(String),
    /// A number, as written (`0`, `-1`, `0.5`).
    Num(String),
    /// A boolean.
    Bool(bool),
    /// `null`.
    Null,
    /// An array.
    Arr(Vec<Val>),
    /// An object, keys in source order (a repeated key keeps its first position, last value).
    Obj(IndexMap<String, Val>),
    /// Not statically known.
    Unknown,
}

/// One flattened theme entry: its Tailwind section, key, value and 1-based source line.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Entry {
    /// The first key under `theme` / `theme.extend` (`colors`, `spacing`, `zIndex`).
    pub section: String,
    /// The entry key (the last path segment, namespace-transparent).
    pub key: String,
    /// The value text.
    pub value: String,
    /// The line of the key.
    pub line: u32,
}

/// What the static v3 reader found.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct V3Read {
    /// Flattened entries in source order; a repeated key is kept per occurrence.
    pub entries: Vec<Entry>,
    /// Keys whose value was not statically known and were left out.
    pub unresolved: Vec<String>,
    /// Why nothing was read, when that is the case.
    pub note: Option<String>,
}

impl V3Read {
    /// The `{key: value}` theme (later entries win, the first position is kept).
    pub fn theme(&self) -> IndexMap<String, String> {
        let mut out = IndexMap::new();
        for e in &self.entries {
            out.insert(e.key.clone(), e.value.clone());
        }
        out
    }
}

struct Eval<'a> {
    src: &'a str,
    base_dir: Option<&'a Path>,
    consts: HashMap<String, Node<'a>>,
    imports: HashMap<String, String>,
}

fn text<'a>(src: &'a str, node: Node<'_>) -> &'a str {
    &src[node.start_byte()..node.end_byte()]
}

/// Read the theme of config `source`. `config_path` (when given) resolves relative `.json`
/// imports; without it only same-file constants resolve.
pub fn read_v3(source: &str, config_path: Option<&Path>) -> V3Read {
    let language = match config_path.and_then(Language::detect) {
        Some(l @ (Language::JavaScript | Language::Jsx | Language::TypeScript | Language::Tsx)) => {
            l
        }
        _ => Language::TypeScript,
    };
    let parsed = match parse(language, source, &ParseLimits::default()) {
        ParseResult::Parsed(tree) => tree,
        ParseResult::Unresolved(u) => {
            tracing::info!(reason = %u.reason, "tailwind config parse: v3 static fallback could not parse");
            return V3Read {
                note: Some(format!("config could not be parsed: {}", u.reason)),
                ..V3Read::default()
            };
        }
    };
    let root = parsed.root();
    let mut ev = Eval {
        src: source,
        base_dir: config_path.and_then(Path::parent),
        consts: HashMap::new(),
        imports: HashMap::new(),
    };
    ev.collect_top_level(root);
    let Some(config) = ev.config_expression(root) else {
        tracing::debug!("tailwind config parse: no `export default` / `module.exports` found");
        return V3Read {
            note: Some("no default export or module.exports found".to_owned()),
            ..V3Read::default()
        };
    };
    let value = ev.eval(config, 0);
    let Val::Obj(map) = &value else {
        tracing::info!("tailwind config parse: the config is not a statically evaluable object");
        return V3Read {
            note: Some("the config is not a statically evaluable object literal".to_owned()),
            ..V3Read::default()
        };
    };
    let mut out = V3Read::default();
    if let Some(theme) = map.get("theme") {
        flatten(theme, None, &mut out, &ev);
    } else {
        out.note = Some("no theme block".to_owned());
    }
    if !out.unresolved.is_empty() {
        tracing::info!(
            count = out.unresolved.len(),
            keys = %out.unresolved.join(", "),
            "tailwind config parse: v3 theme values left out as unresolved-by-tailwind"
        );
    }
    tracing::debug!(
        entries = out.entries.len(),
        "tailwind config parse: v3 static read"
    );
    out
}

/// Flatten `theme` / `theme.extend` objects: nesting keywords are transparent, a namespace is
/// walked but not itself a key, a string or number leaf is an entry, arrays are not theme shape.
fn flatten(value: &Val, section: Option<&str>, out: &mut V3Read, ev: &Eval<'_>) {
    let Val::Obj(map) = value else {
        return;
    };
    for (key, sub) in map {
        if section.is_none() && (key == "extend" || key == "theme") {
            flatten(sub, None, out, ev);
            continue;
        }
        match sub {
            Val::Str(s) => push(out, section, key, s.clone(), ev),
            Val::Num(n) => push(out, section, key, n.clone(), ev),
            Val::Obj(_) => flatten(sub, Some(section.unwrap_or(key)), out, ev),
            Val::Unknown => out.unresolved.push(key.clone()),
            Val::Bool(_) | Val::Null | Val::Arr(_) => {}
        }
    }
}

fn push(out: &mut V3Read, section: Option<&str>, key: &str, value: String, ev: &Eval<'_>) {
    out.entries.push(Entry {
        section: section.unwrap_or_default().to_owned(),
        key: key.to_owned(),
        value,
        line: ev.line_of_key(key),
    });
}

impl<'a> Eval<'a> {
    /// 1-based line of the first occurrence of `key` as an object key (best effort).
    fn line_of_key(&self, key: &str) -> u32 {
        for (i, line) in self.src.lines().enumerate() {
            let t = line.trim_start();
            let quoted = [format!("\"{key}\""), format!("'{key}'")];
            let bare_hit = t
                .strip_prefix(key)
                .is_some_and(|r| r.trim_start().starts_with(':'));
            let quoted_hit = quoted.iter().any(|q| {
                t.strip_prefix(q.as_str())
                    .is_some_and(|r| r.trim_start().starts_with(':'))
            });
            if bare_hit || quoted_hit {
                return u32::try_from(i + 1).unwrap_or(u32::MAX);
            }
        }
        1
    }

    /// Record top-level `const NAME = expr` declarations and imports.
    fn collect_top_level(&mut self, root: Node<'a>) {
        let mut cursor = root.walk();
        for stmt in root.named_children(&mut cursor) {
            match stmt.kind() {
                "lexical_declaration" | "variable_declaration" => {
                    let mut c = stmt.walk();
                    for decl in stmt.named_children(&mut c) {
                        if decl.kind() != "variable_declarator" {
                            continue;
                        }
                        let (Some(name), Some(value)) = (
                            decl.child_by_field_name("name"),
                            decl.child_by_field_name("value"),
                        ) else {
                            continue;
                        };
                        if name.kind() == "identifier" {
                            self.consts.insert(text(self.src, name).to_owned(), value);
                        }
                    }
                }
                "import_statement" => self.collect_import(stmt),
                _ => {}
            }
        }
    }

    fn collect_import(&mut self, stmt: Node<'a>) {
        let Some(source) = stmt.child_by_field_name("source") else {
            return;
        };
        let specifier = string_value(self.src, source);
        let mut c = stmt.walk();
        for clause in stmt.named_children(&mut c) {
            if clause.kind() != "import_clause" {
                continue;
            }
            let mut cc = clause.walk();
            for part in clause.named_children(&mut cc) {
                match part.kind() {
                    "identifier" => {
                        self.imports
                            .insert(text(self.src, part).to_owned(), specifier.clone());
                    }
                    "namespace_import" => {
                        if let Some(id) = part.named_child(0) {
                            self.imports
                                .insert(text(self.src, id).to_owned(), specifier.clone());
                        }
                    }
                    _ => {}
                }
            }
        }
    }

    /// The expression a config module exports: `export default X`, `module.exports = X` or
    /// `exports.default = X`.
    fn config_expression(&self, root: Node<'a>) -> Option<Node<'a>> {
        let mut cursor = root.walk();
        for stmt in root.named_children(&mut cursor) {
            if stmt.kind() == "export_statement" {
                if let Some(value) = stmt.child_by_field_name("value") {
                    return Some(value);
                }
                continue;
            }
            if stmt.kind() != "expression_statement" {
                continue;
            }
            let Some(expr) = stmt.named_child(0) else {
                continue;
            };
            if expr.kind() != "assignment_expression" {
                continue;
            }
            let (Some(left), Some(right)) = (
                expr.child_by_field_name("left"),
                expr.child_by_field_name("right"),
            ) else {
                continue;
            };
            if matches!(text(self.src, left), "module.exports" | "exports.default") {
                return Some(right);
            }
        }
        None
    }

    fn eval(&self, node: Node<'a>, depth: usize) -> Val {
        if depth > MAX_DEPTH {
            return Val::Unknown;
        }
        match node.kind() {
            "string" => Val::Str(string_value(self.src, node)),
            "template_string" => {
                let mut c = node.walk();
                if node
                    .named_children(&mut c)
                    .any(|n| n.kind() == "template_substitution")
                {
                    return Val::Unknown;
                }
                let raw = text(self.src, node);
                Val::Str(raw.trim_matches('`').to_owned())
            }
            "number" => Val::Num(text(self.src, node).to_owned()),
            "true" => Val::Bool(true),
            "false" => Val::Bool(false),
            "null" => Val::Null,
            "unary_expression" => self.eval_unary(node, depth),
            "object" => self.eval_object(node, depth),
            "array" => self.eval_array(node, depth),
            "parenthesized_expression"
            | "as_expression"
            | "satisfies_expression"
            | "non_null_expression"
            | "type_assertion" => node
                .named_child(0)
                .map_or(Val::Unknown, |inner| self.eval(inner, depth + 1)),
            "identifier" => self.eval_identifier(text(self.src, node), depth),
            "member_expression" => self.eval_member(node, depth),
            "subscript_expression" => self.eval_subscript(node, depth),
            "call_expression" => self.eval_call(node),
            "binary_expression" => self.eval_binary(node, depth),
            _ => Val::Unknown,
        }
    }

    fn eval_unary(&self, node: Node<'a>, depth: usize) -> Val {
        let op = node
            .child_by_field_name("operator")
            .map(|o| text(self.src, o));
        let arg = node
            .child_by_field_name("argument")
            .map(|a| self.eval(a, depth + 1));
        match (op, arg) {
            (Some("-"), Some(Val::Num(n))) => Val::Num(format!("-{n}")),
            (Some("+"), Some(Val::Num(n))) => Val::Num(n),
            _ => Val::Unknown,
        }
    }

    fn eval_binary(&self, node: Node<'a>, depth: usize) -> Val {
        let (Some(l), Some(r)) = (
            node.child_by_field_name("left"),
            node.child_by_field_name("right"),
        ) else {
            return Val::Unknown;
        };
        let op = node
            .child_by_field_name("operator")
            .map(|o| text(self.src, o));
        match (op, self.eval(l, depth + 1), self.eval(r, depth + 1)) {
            (Some("+"), Val::Str(a), Val::Str(b)) => Val::Str(a + &b),
            _ => Val::Unknown,
        }
    }

    fn eval_array(&self, node: Node<'a>, depth: usize) -> Val {
        let mut out = Vec::new();
        let mut c = node.walk();
        for el in node.named_children(&mut c) {
            if el.kind() == "spread_element" {
                match el.named_child(0).map(|n| self.eval(n, depth + 1)) {
                    Some(Val::Arr(items)) => out.extend(items),
                    _ => out.push(Val::Unknown),
                }
            } else if el.kind() != "comment" {
                out.push(self.eval(el, depth + 1));
            }
        }
        Val::Arr(out)
    }

    fn eval_object(&self, node: Node<'a>, depth: usize) -> Val {
        let mut map: IndexMap<String, Val> = IndexMap::new();
        let mut c = node.walk();
        for member in node.named_children(&mut c) {
            match member.kind() {
                "pair" => {
                    let (Some(key), Some(value)) = (
                        member.child_by_field_name("key"),
                        member.child_by_field_name("value"),
                    ) else {
                        continue;
                    };
                    if let Some(name) = self.key_name(key, depth) {
                        map.insert(name, self.eval(value, depth + 1));
                    }
                }
                "shorthand_property_identifier" => {
                    let name = text(self.src, member);
                    map.insert(name.to_owned(), self.eval_identifier(name, depth));
                }
                "spread_element" => {
                    if let Some(Val::Obj(inner)) =
                        member.named_child(0).map(|n| self.eval(n, depth + 1))
                    {
                        map.extend(inner);
                    }
                }
                _ => {}
            }
        }
        Val::Obj(map)
    }

    fn key_name(&self, key: Node<'a>, depth: usize) -> Option<String> {
        match key.kind() {
            "property_identifier" | "identifier" | "number" => Some(text(self.src, key).to_owned()),
            "string" => Some(string_value(self.src, key)),
            "computed_property_name" => match self.eval(key.named_child(0)?, depth + 1) {
                Val::Str(s) | Val::Num(s) => Some(s),
                _ => None,
            },
            _ => None,
        }
    }

    fn eval_identifier(&self, name: &str, depth: usize) -> Val {
        if let Some(node) = self.consts.get(name) {
            return self.eval(*node, depth + 1);
        }
        if let Some(specifier) = self.imports.get(name) {
            return self.load_json(specifier);
        }
        Val::Unknown
    }

    fn eval_member(&self, node: Node<'a>, depth: usize) -> Val {
        let (Some(obj), Some(prop)) = (
            node.child_by_field_name("object"),
            node.child_by_field_name("property"),
        ) else {
            return Val::Unknown;
        };
        Self::member_of(self.eval(obj, depth + 1), text(self.src, prop))
    }

    fn eval_subscript(&self, node: Node<'a>, depth: usize) -> Val {
        let (Some(obj), Some(index)) = (
            node.child_by_field_name("object"),
            node.child_by_field_name("index"),
        ) else {
            return Val::Unknown;
        };
        match self.eval(index, depth + 1) {
            Val::Str(k) | Val::Num(k) => Self::member_of(self.eval(obj, depth + 1), &k),
            _ => Val::Unknown,
        }
    }

    fn member_of(value: Val, key: &str) -> Val {
        match value {
            Val::Obj(map) => map.get(key).cloned().unwrap_or(Val::Unknown),
            Val::Arr(items) => key
                .parse::<usize>()
                .ok()
                .and_then(|i| items.get(i).cloned())
                .unwrap_or(Val::Unknown),
            _ => Val::Unknown,
        }
    }

    /// Only `require("<relative>.json")` is read; every other call is not statically known.
    fn eval_call(&self, node: Node<'a>) -> Val {
        let Some(callee) = node.child_by_field_name("function") else {
            return Val::Unknown;
        };
        if text(self.src, callee) != "require" {
            return Val::Unknown;
        }
        let Some(args) = node.child_by_field_name("arguments") else {
            return Val::Unknown;
        };
        match args.named_child(0) {
            Some(arg) if arg.kind() == "string" => self.load_json(&string_value(self.src, arg)),
            _ => Val::Unknown,
        }
    }

    fn load_json(&self, specifier: &str) -> Val {
        if !(specifier.starts_with("./") || specifier.starts_with("../"))
            || !Path::new(specifier)
                .extension()
                .is_some_and(|e| e.eq_ignore_ascii_case("json"))
        {
            return Val::Unknown;
        }
        let Some(dir) = self.base_dir else {
            return Val::Unknown;
        };
        let path: PathBuf = dir.join(specifier);
        match std::fs::read_to_string(&path) {
            Ok(body) => match serde_json::from_str::<serde_json::Value>(&body) {
                Ok(json) => from_json(&json),
                Err(e) => {
                    tracing::info!(path = %path.display(), error = %e, "tailwind config: json import is not JSON");
                    Val::Unknown
                }
            },
            Err(e) => {
                tracing::info!(path = %path.display(), error = %e, "tailwind config: json import unreadable");
                Val::Unknown
            }
        }
    }
}

fn from_json(value: &serde_json::Value) -> Val {
    match value {
        serde_json::Value::String(s) => Val::Str(s.clone()),
        serde_json::Value::Number(n) => Val::Num(n.to_string()),
        serde_json::Value::Bool(b) => Val::Bool(*b),
        serde_json::Value::Null => Val::Null,
        serde_json::Value::Array(a) => Val::Arr(a.iter().map(from_json).collect()),
        serde_json::Value::Object(o) => {
            Val::Obj(o.iter().map(|(k, v)| (k.clone(), from_json(v))).collect())
        }
    }
}

/// The decoded text of a string literal node (quotes removed, simple escapes resolved).
fn string_value(src: &str, node: Node<'_>) -> String {
    let raw = text(src, node);
    let inner = raw
        .strip_prefix(['"', '\'', '`'])
        .and_then(|r| r.strip_suffix(['"', '\'', '`']))
        .unwrap_or(raw);
    let mut out = String::with_capacity(inner.len());
    let mut chars = inner.chars();
    while let Some(c) = chars.next() {
        if c != '\\' {
            out.push(c);
            continue;
        }
        match chars.next() {
            Some('n') => out.push('\n'),
            Some('t') => out.push('\t'),
            Some('r') => out.push('\r'),
            Some('0') => out.push('\0'),
            Some(other) => out.push(other),
            None => {}
        }
    }
    out
}
