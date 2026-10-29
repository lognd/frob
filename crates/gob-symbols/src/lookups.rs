//! Name-computed lookups in the TypeScript family and C#: `require(n)`, `import(n)`, `obj[n]`,
//! `Reflect.get(o, n)`, `Type.GetType(n)`, `asm.GetType(n)`, `t.GetMethod(n)` and kin.
//!
//! Each adapter here only parses and folds its own syntax into a gob-ir [`ConstValue`]; which
//! calls are lookups, and whether a name is a literal, is decided once by
//! [`gob_ir::name_lookup`]. A literal name resolves to the same path the direct form has; any
//! other name yields a `computed` [`PathUse`] (see `canon`), which consumers report Unresolved.
//!
//! Direct uses resolve through the import system too (ticket PKW7X2J): `import * as cp from
//! "node:child_process"`, `const { exec } = require("child_process")`, `import fs = require("fs")`
//! and the ambient globals (`fetch`, `process`, `Deno`, `globalThis.fetch`) in the TypeScript
//! family; `using` namespaces, `using static`, `using A = X.Y`, `global::` and fully qualified
//! names in C#. A name the program binds itself (a local `fs`, a class `File`) resolves to nothing.

// frob:ticket 01M6422ZFEPZJYJQDDM6CV37RW
// frob:ticket 01M642307T98S89GQ4APKW7X2J

use std::collections::BTreeMap;

use gob_ir::const_value::{ConstValue, Fragment};
use gob_ir::name_lookup::{LookupKind, Resolved, concat, literal, primitive, resolve_name};
use tree_sitter::Node;

use crate::canon::{COMPUTED, PathUse, known_prefix};

/// Ambient TypeScript-family globals a capability can hide behind when the program binds none.
const TS_GLOBALS: &[&str] = &[
    "process",
    "fetch",
    "eval",
    "Function",
    "Deno",
    "Bun",
    "XMLHttpRequest",
    "WebSocket",
    "EventSource",
    "globalThis",
    "window",
    "self",
    "global",
];

/// Roots that name the global object; they are dropped from a path.
const GLOBAL_ROOTS: &[&str] = &["globalThis", "window", "self", "global"];

/// Namespaces C# imports implicitly (`ImplicitUsings`), tried after every written `using`.
const IMPLICIT_USINGS: &[&str] = &[
    "System",
    "System.IO",
    "System.Net.Http",
    "System.Threading",
    "System.Threading.Tasks",
    "System.Collections.Generic",
    "System.Linq",
];

/// Deepest alias or constant chain followed.
const MAX_DEPTH: usize = 8;

/// What one binding of a name is.
#[derive(Clone, Debug)]
enum Bind<'t> {
    /// `name = value` (a declaration with an initializer).
    Plain(Node<'t>),
    /// `{ key: name } = value` or `{ name } = value`.
    Member(Node<'t>, String),
    /// An import binding, with the path it names.
    Import(String),
    /// Any other binder (parameter, assignment, function name): the name denotes nothing known.
    Opaque,
}

struct Cx<'s, 't> {
    src: &'s str,
    /// The language tag the primitive table is keyed by (`typescript` or `csharp`).
    lang: &'static str,
    binds: BTreeMap<String, Vec<Bind<'t>>>,
    /// C# `using Ns;` namespaces.
    usings: Vec<String>,
    /// C# `using static Type;` types.
    static_usings: Vec<String>,
    out: Vec<PathUse>,
}

fn text<'a>(src: &'a str, n: Node<'_>) -> &'a str {
    &src[n.start_byte()..n.end_byte()]
}

fn named(n: Node<'_>) -> Vec<Node<'_>> {
    let mut c = n.walk();
    n.named_children(&mut c).collect()
}

/// Scans a TypeScript-family or C# tree for name-computed lookups.
pub(crate) fn scan(language: &str, src: &str, root: Node<'_>) -> Vec<PathUse> {
    let lang = if language == "csharp" {
        "csharp"
    } else {
        "typescript"
    };
    let mut cx = Cx {
        src,
        lang,
        binds: BTreeMap::new(),
        usings: Vec::new(),
        static_usings: Vec::new(),
        out: Vec::new(),
    };
    cx.collect(root);
    cx.visit(root);
    tracing::debug!(language, uses = cx.out.len(), "lookups: scanned");
    cx.out
}

impl<'t> Cx<'_, 't> {
    fn csharp(&self) -> bool {
        self.lang == "csharp"
    }

    fn bind(&mut self, name: &str, b: Bind<'t>) {
        self.binds.entry(name.to_owned()).or_default().push(b);
    }

    /// The one binding of `name`, when it has exactly one and it is informative.
    fn only(&self, name: &str) -> Option<&Bind<'t>> {
        let all = self.binds.get(name)?;
        // the same module imported again in another scope still names that module
        if let [Bind::Import(first), rest @ ..] = all.as_slice()
            && rest
                .iter()
                .all(|b| matches!(b, Bind::Import(p) if p == first))
        {
            return all.first();
        }
        match all.as_slice() {
            [b @ (Bind::Plain(_) | Bind::Member(..) | Bind::Import(_))] => Some(b),
            _ => None,
        }
    }

    /// True when the program binds `name` itself (so it is not the ambient builtin).
    fn user_bound(&self, name: &str) -> bool {
        self.binds.contains_key(name)
    }

    fn collect(&mut self, n: Node<'t>) {
        let src = self.src;
        match n.kind() {
            "variable_declarator" => {
                let name = n.child_by_field_name("name");
                let value = if self.csharp() {
                    named(n)
                        .into_iter()
                        .find(|c| Some(c.id()) != name.map(|x| x.id()))
                } else {
                    n.child_by_field_name("value")
                };
                match (name, value) {
                    (Some(nm), Some(v)) if nm.kind() == "identifier" => {
                        self.bind(text(src, nm), Bind::Plain(v));
                    }
                    (Some(nm), Some(v)) if nm.kind() == "object_pattern" => {
                        self.bind_object_pattern(nm, v);
                    }
                    (Some(nm), _) => {
                        let mut names = Vec::new();
                        idents(src, nm, &mut names);
                        for x in names {
                            self.bind(&x, Bind::Opaque);
                        }
                    }
                    _ => {}
                }
            }
            "import_statement" => self.collect_import(n),
            "import_require_clause" => self.collect_import_require(n),
            "using_directive" => self.collect_using(n),
            "assignment_expression"
            | "augmented_assignment_expression"
            | "for_in_statement"
            | "for_statement" => {
                if let Some(l) = n.child_by_field_name("left") {
                    let mut names = Vec::new();
                    idents(src, l, &mut names);
                    for x in names {
                        self.bind(&x, Bind::Opaque);
                    }
                }
            }
            "required_parameter" | "optional_parameter" | "parameter" => {
                let target = n
                    .child_by_field_name("pattern")
                    .or_else(|| n.child_by_field_name("name"));
                if let Some(t) = target {
                    let mut names = Vec::new();
                    idents(src, t, &mut names);
                    for x in names {
                        self.bind(&x, Bind::Opaque);
                    }
                }
            }
            "arrow_function" | "catch_clause" => {
                if let Some(t) = n
                    .child_by_field_name("parameter")
                    .or_else(|| n.child_by_field_name("parameters"))
                {
                    let mut names = Vec::new();
                    idents(src, t, &mut names);
                    for x in names {
                        self.bind(&x, Bind::Opaque);
                    }
                }
            }
            "function_declaration"
            | "generator_function_declaration"
            | "class_declaration"
            | "foreach_statement" => {
                if let Some(nm) = n
                    .child_by_field_name("name")
                    .or_else(|| n.child_by_field_name("left"))
                    && nm.kind() == "identifier"
                {
                    self.bind(text(src, nm), Bind::Opaque);
                }
            }
            _ => {}
        }
        for k in named(n) {
            self.collect(k);
        }
    }

    /// Binds each name of `const { a, k: b } = v` as a member of `v`.
    fn bind_object_pattern(&mut self, pattern: Node<'t>, v: Node<'t>) {
        let src = self.src;
        for p in named(pattern) {
            match p.kind() {
                "shorthand_property_identifier_pattern" => {
                    let k = text(src, p).to_owned();
                    self.bind(&k.clone(), Bind::Member(v, k));
                }
                "pair_pattern" => {
                    if let (Some(k), Some(val)) =
                        (p.child_by_field_name("key"), p.child_by_field_name("value"))
                        && val.kind() == "identifier"
                    {
                        let key = text(src, k).to_owned();
                        self.bind(text(src, val), Bind::Member(v, key));
                    }
                }
                _ => {}
            }
        }
    }

    fn collect_import(&mut self, n: Node<'t>) {
        let src = self.src;
        let Some(source) = n.child_by_field_name("source") else {
            return;
        };
        let Resolved::Literal(module) = resolve_name(&self.fold(source, 0)) else {
            return;
        };
        for clause in named(n).into_iter().filter(|c| c.kind() == "import_clause") {
            for part in named(clause) {
                match part.kind() {
                    "identifier" => self.bind(text(src, part), Bind::Import(module.clone())),
                    "namespace_import" => {
                        for id in named(part) {
                            self.bind(text(src, id), Bind::Import(module.clone()));
                        }
                    }
                    "named_imports" => {
                        for spec in named(part) {
                            let (Some(nm), local) = (
                                spec.child_by_field_name("name"),
                                spec.child_by_field_name("alias"),
                            ) else {
                                continue;
                            };
                            let member = text(src, nm).trim_matches(['"', '\'']).to_owned();
                            let local =
                                local.map_or_else(|| member.clone(), |a| text(src, a).to_owned());
                            self.bind(&local, Bind::Import(format!("{module}.{member}")));
                        }
                    }
                    _ => {}
                }
            }
        }
    }

    /// `import fs = require("fs")`.
    fn collect_import_require(&mut self, n: Node<'t>) {
        let (Some(id), Some(source)) = (
            named(n).into_iter().find(|c| c.kind() == "identifier"),
            n.child_by_field_name("source"),
        ) else {
            return;
        };
        if let Resolved::Literal(module) = resolve_name(&self.fold(source, 0)) {
            let local = text(self.src, id).to_owned();
            self.bind(&local, Bind::Import(module));
        }
    }

    /// C# `using Ns;`, `using static T;`, `using A = X.Y;` (and their `global` forms).
    fn collect_using(&mut self, n: Node<'t>) {
        let alias = n.child_by_field_name("name");
        let Some(target) = named(n)
            .into_iter()
            .rev()
            .find(|c| alias.is_none_or(|a| a.id() != c.id()))
        else {
            return;
        };
        let spelled: String = text(self.src, target).split_whitespace().collect();
        let target = spelled
            .strip_prefix("global::")
            .unwrap_or(&spelled)
            .to_owned();
        if let Some(a) = alias {
            let local = text(self.src, a).to_owned();
            self.bind(&local, Bind::Import(target));
        } else if text(self.src, n)
            .split_whitespace()
            .take(3)
            .any(|w| w == "static")
        {
            self.static_usings.push(target);
        } else {
            self.usings.push(target);
        }
    }

    // ---- folding names to static values ------------------------------------------------------

    /// The static value of a name expression, as a gob-ir constant.
    fn fold(&self, n: Node<'t>, depth: usize) -> ConstValue {
        if depth > MAX_DEPTH {
            return ConstValue::Unknown;
        }
        let d = depth + 1;
        match n.kind() {
            "parenthesized_expression"
            | "as_expression"
            | "non_null_expression"
            | "satisfies_expression" => named(n)
                .first()
                .map_or(ConstValue::Unknown, |c| self.fold(*c, d)),
            "binary_expression" => {
                let plus = n
                    .child_by_field_name("operator")
                    .is_some_and(|o| text(self.src, o) == "+");
                match (
                    plus,
                    n.child_by_field_name("left"),
                    n.child_by_field_name("right"),
                ) {
                    (true, Some(l), Some(r)) => concat(&self.fold(l, d), &self.fold(r, d)),
                    _ => ConstValue::Unknown,
                }
            }
            "identifier" => match self.only(text(self.src, n)) {
                Some(Bind::Plain(v)) => self.fold(*v, d),
                _ => ConstValue::Unknown,
            },
            "string" | "template_string" => self.fold_ts_string(n),
            "string_literal"
            | "verbatim_string_literal"
            | "interpolated_string_expression"
            | "raw_string_literal" => self.fold_cs_string(n),
            _ => ConstValue::Unknown,
        }
    }

    fn fold_ts_string(&self, n: Node<'_>) -> ConstValue {
        let mut s = String::new();
        for p in named(n) {
            match p.kind() {
                "string_fragment" => s.push_str(text(self.src, p)),
                _ => return ConstValue::Fragments(vec![Fragment::Unknown]),
            }
        }
        literal(s)
    }

    fn fold_cs_string(&self, n: Node<'_>) -> ConstValue {
        let t = text(self.src, n);
        let partial = || ConstValue::Fragments(vec![Fragment::Unknown]);
        if let Some(body) = t.strip_prefix("@\"").and_then(|r| r.strip_suffix('"')) {
            return literal(body.replace("\"\"", "\""));
        }
        if let Some(body) = t.strip_prefix("$\"").and_then(|r| r.strip_suffix('"')) {
            return if body.contains(['{', '\\']) {
                partial()
            } else {
                literal(body)
            };
        }
        match t.strip_prefix('"').and_then(|r| r.strip_suffix('"')) {
            Some(body) if !body.contains('\\') && n.kind() == "string_literal" => literal(body),
            _ => partial(),
        }
    }

    /// The name argument `arg` as a path segment: its literal, or [`COMPUTED`].
    fn name_of(&self, arg: Node<'t>) -> String {
        match resolve_name(&self.fold(arg, 0)) {
            Resolved::Literal(s) => s,
            Resolved::Unresolved(gap) => {
                tracing::debug!(?gap, "lookups: computed lookup name");
                COMPUTED.to_owned()
            }
        }
    }

    // ---- resolving expressions to paths ------------------------------------------------------

    /// True when `name`, unbound by the program, denotes an ambient global or type.
    fn ambient(&self, name: &str) -> bool {
        if self.csharp() {
            name.chars().next().is_some_and(char::is_uppercase)
        } else {
            TS_GLOBALS.contains(&name)
        }
    }

    /// The call arguments of a call-like node, unwrapping C# `argument` nodes.
    fn args(call: Node<'t>) -> Vec<Node<'t>> {
        let Some(a) = call.child_by_field_name("arguments") else {
            return Vec::new();
        };
        named(a)
            .into_iter()
            .filter_map(|x| {
                if x.kind() == "argument" {
                    named(x).last().copied()
                } else {
                    Some(x)
                }
            })
            .collect()
    }

    /// The dotted path an expression denotes and whether a lookup primitive produced it.
    fn resolve(&self, e: Node<'t>, depth: usize) -> Option<(String, bool)> {
        if depth > MAX_DEPTH {
            return None;
        }
        let d = depth + 1;
        match e.kind() {
            "parenthesized_expression"
            | "await_expression"
            | "as_expression"
            | "non_null_expression"
            | "satisfies_expression"
            | "generic_name" => self.resolve(*named(e).first()?, d),
            "identifier" => {
                let name = text(self.src, e);
                match self.only(name) {
                    Some(Bind::Import(p)) => Some((p.clone(), false)),
                    Some(Bind::Member(v, key)) => {
                        let (p, dy) = self.resolve(*v, d)?;
                        Some((format!("{p}.{key}"), dy))
                    }
                    Some(Bind::Plain(v)) => self.resolve(*v, d),
                    None if !self.user_bound(name) && self.ambient(name) => {
                        Some((name.to_owned(), false))
                    }
                    Some(Bind::Opaque) | None => None,
                }
            }
            // a value built by `new T(..)` is a `T`: its methods resolve as `T.method`
            "new_expression" => self.resolve(e.child_by_field_name("constructor")?, d),
            "object_creation_expression" => self.resolve(e.child_by_field_name("type")?, d),
            "qualified_name" => {
                let (p, dy) = self.resolve(e.child_by_field_name("qualifier")?, d)?;
                Some((
                    format!("{p}.{}", text(self.src, e.child_by_field_name("name")?)),
                    dy,
                ))
            }
            "alias_qualified_name" => {
                let alias = text(self.src, e.child_by_field_name("alias")?);
                let name = e.child_by_field_name("name")?;
                (alias == "global").then(|| (text(self.src, name).to_owned(), false))
            }
            "member_expression" => {
                let (p, dy) = self.resolve(e.child_by_field_name("object")?, d)?;
                Some((
                    format!("{p}.{}", text(self.src, e.child_by_field_name("property")?)),
                    dy,
                ))
            }
            "member_access_expression" => {
                let (p, dy) = self.resolve(e.child_by_field_name("expression")?, d)?;
                Some((
                    format!("{p}.{}", text(self.src, e.child_by_field_name("name")?)),
                    dy,
                ))
            }
            "subscript_expression" => {
                let index = e.child_by_field_name("index")?;
                if index.kind() == "number" {
                    return None;
                }
                let (p, _) = self.resolve(e.child_by_field_name("object")?, d)?;
                Some((format!("{p}.{}", self.name_of(index)), true))
            }
            "typeof_expression" => {
                let t = e.child_by_field_name("type")?;
                Some((text(self.src, t).split_whitespace().collect(), false))
            }
            "call_expression" => self.resolve_ts_call(e, d),
            "invocation_expression" => self.resolve_cs_call(e, d),
            _ => None,
        }
    }

    /// `require(n)`, `import(n)` and `Reflect.get(o, n)`.
    fn resolve_ts_call(&self, call: Node<'t>, d: usize) -> Option<(String, bool)> {
        let f = call.child_by_field_name("function")?;
        let callee = match f.kind() {
            "identifier" if self.user_bound(text(self.src, f)) => return None,
            "import" | "identifier" | "member_expression" => {
                text(self.src, f).split_whitespace().collect::<String>()
            }
            _ => return None,
        };
        let prim = primitive(self.lang, &callee)?;
        let args = Self::args(call);
        let name = self.name_of(*args.get(prim.name_arg)?);
        match (prim.kind, prim.object_arg) {
            (LookupKind::Attribute, Some(o)) => {
                let (p, _) = self.resolve(*args.get(o)?, d)?;
                Some((format!("{p}.{name}"), true))
            }
            _ => Some((name, true)),
        }
    }

    /// `Type.GetType(n)`, `Assembly.Load(n)` and the reflection methods `t.GetMethod(n)`.
    fn resolve_cs_call(&self, call: Node<'t>, d: usize) -> Option<(String, bool)> {
        let f = call.child_by_field_name("function")?;
        let spelled: String = text(self.src, f).split_whitespace().collect();
        let short = spelled
            .strip_prefix("System.Reflection.")
            .or_else(|| spelled.strip_prefix("System."))
            .unwrap_or(&spelled);
        let args = Self::args(call);
        let (prim, receiver) = match primitive(self.lang, short) {
            Some(p) => (p, None),
            None if f.kind() == "member_access_expression" => {
                let member = text(self.src, f.child_by_field_name("name")?);
                (
                    primitive(self.lang, &format!(".{member}"))?,
                    f.child_by_field_name("expression"),
                )
            }
            None => return None,
        };
        let name = self.name_of(*args.get(prim.name_arg)?);
        match (prim.kind, receiver) {
            (LookupKind::Attribute, Some(r)) => {
                let (p, _) = self.resolve(r, d)?;
                Some((format!("{p}.{name}"), true))
            }
            (LookupKind::Attribute, None) => None,
            _ => Some((name, true)),
        }
    }

    // ---- emitting ----------------------------------------------------------------------------

    /// The paths a resolved `path` may name: itself, and for C# every namespace it may sit in.
    fn candidates(&self, path: &str) -> Vec<String> {
        if !self.csharp() || path.is_empty() {
            return vec![path.to_owned()];
        }
        let mut out = vec![path.to_owned()];
        if path.starts_with("System.") || path.starts_with("Microsoft.") {
            return out;
        }
        for ns in self
            .usings
            .iter()
            .map(String::as_str)
            .chain(IMPLICIT_USINGS.iter().copied())
        {
            out.push(format!("{ns}.{path}"));
        }
        // `using static System.IO.File; ReadAllText(p)`
        for ty in &self.static_usings {
            out.push(format!("{ty}.{path}"));
        }
        out.dedup();
        out
    }

    fn emit(&mut self, e: Node<'t>, call: bool) {
        let Some((path, dynamic)) = self.resolve(e, 0) else {
            return;
        };
        let (path, computed) = known_prefix(path);
        let path = normalize(path, self.csharp());
        if path.is_empty() && !computed {
            return;
        }
        tracing::debug!(line = e.start_position().row + 1, %path, computed, dynamic, "lookups: resolved use");
        let external_root = self.csharp() && path.starts_with("System.");
        for path in self.candidates(&path) {
            self.out.push(PathUse {
                offset: e.start_byte(),
                line: u32::try_from(e.start_position().row + 1).unwrap_or(u32::MAX),
                spelled: text(self.src, e).split_whitespace().collect(),
                path,
                call,
                dynamic,
                external_root,
                computed,
            });
        }
    }

    fn visit(&mut self, n: Node<'t>) {
        // a bound name called directly: `const { exec } = require("m"); exec(x)`
        if n.kind() == "identifier"
            && n.parent().is_some_and(|p| {
                matches!(p.kind(), "call_expression" | "invocation_expression")
                    && p.child_by_field_name("function").map(|f| f.id()) == Some(n.id())
            })
        {
            self.emit(n, true);
        }
        // `new T(..)` / `new ns.T(..)`: the constructed type is the callee
        match n.kind() {
            "new_expression" => {
                if let Some(c) = n.child_by_field_name("constructor") {
                    self.emit(c, true);
                }
            }
            "object_creation_expression" => {
                if let Some(t) = n.child_by_field_name("type") {
                    self.emit(t, true);
                }
            }
            _ => {}
        }
        let lookup_form = matches!(
            n.kind(),
            "call_expression"
                | "invocation_expression"
                | "subscript_expression"
                | "member_expression"
                | "member_access_expression"
        );
        if lookup_form && let Some(parent) = n.parent() {
            let id = n.id();
            let is_callee = matches!(parent.kind(), "call_expression" | "invocation_expression")
                && parent.child_by_field_name("function").map(|f| f.id()) == Some(id);
            let is_object = matches!(
                parent.kind(),
                "member_expression" | "subscript_expression" | "member_access_expression"
            ) && parent
                .child_by_field_name("object")
                .or_else(|| parent.child_by_field_name("expression"))
                .map(|o| o.id())
                == Some(id);
            if is_callee {
                self.emit(n, true);
            } else if !is_object {
                self.emit(n, false);
            }
        } else if lookup_form {
            self.emit(n, false);
        }
        for k in named(n) {
            self.visit(k);
        }
    }
}

/// A resolved path with the `node:` scheme and any global-object root dropped (`globalThis.fetch`
/// names `fetch`).
fn normalize(path: String, csharp: bool) -> String {
    if csharp {
        return path;
    }
    let path = path.strip_prefix("node:").unwrap_or(&path);
    match path.split_once('.') {
        Some((root, rest)) if GLOBAL_ROOTS.contains(&root) => rest.to_owned(),
        _ => path.to_owned(),
    }
}

/// The identifiers bound by a pattern or parameter node.
fn idents(src: &str, n: Node<'_>, out: &mut Vec<String>) {
    match n.kind() {
        "identifier" | "shorthand_property_identifier_pattern" => {
            out.push(text(src, n).to_owned());
        }
        _ => {
            for c in named(n) {
                idents(src, c, out);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use crate::canon::path_uses;

    fn uses(lang: &str, src: &str) -> Vec<(String, bool)> {
        path_uses(lang, src)
            .into_iter()
            .map(|u| (u.path, u.computed))
            .collect()
    }

    fn has(u: &[(String, bool)], p: &str) -> bool {
        u.iter().any(|(x, _)| x == p)
    }

    // frob:tests crates/gob-symbols/src/lookups.rs::scan
    #[test]
    fn typescript_imports_resolve_to_module_paths() {
        for (src, want) in [
            (
                "import * as cp from \"child_process\"; cp.exec(x);",
                "child_process.exec",
            ),
            (
                "import { exec } from \"child_process\"; exec(x);",
                "child_process.exec",
            ),
            (
                "import { exec as r } from \"node:child_process\"; r(x);",
                "child_process.exec",
            ),
            ("import fs = require(\"fs\"); fs.rmSync(p);", "fs.rmSync"),
            (
                "const { exec } = require('child_process'); exec(x);",
                "child_process.exec",
            ),
            ("globalThis.fetch(u);", "fetch"),
            ("const h = process.env.HOME;", "process.env.HOME"),
            ("new WebSocket(u);", "WebSocket"),
        ] {
            assert!(
                has(&uses("typescript", src), want),
                "{src}: {:?}",
                uses("typescript", src)
            );
        }
    }

    // frob:tests crates/gob-symbols/src/lookups.rs::scan
    #[test]
    fn typescript_local_names_shadow_ambient_ones() {
        for src in [
            "function fetch(u) { return u; } fetch(1);",
            "const fs = { readFile(p) { return p; } }; fs.readFile(p);",
            "function f(fs) { fs.readFile(p); }",
        ] {
            let u = uses("typescript", src);
            assert!(!has(&u, "fetch") && !has(&u, "fs.readFile"), "{src}: {u:?}");
        }
    }

    // frob:tests crates/gob-symbols/src/lookups.rs::scan
    #[test]
    fn csharp_usings_resolve_to_qualified_paths() {
        for (src, want) in [
            (
                "using System.Diagnostics; class C { void M(string x) { Process.Start(x); } }",
                "System.Diagnostics.Process.Start",
            ),
            (
                "using P = System.Diagnostics.Process; class C { void M(string x) { P.Start(x); } }",
                "System.Diagnostics.Process.Start",
            ),
            (
                "using static System.IO.File; class C { string M(string p) { return ReadAllText(p); } }",
                "System.IO.File.ReadAllText",
            ),
            (
                "class C { void M(string x) { global::System.Diagnostics.Process.Start(x); } }",
                "System.Diagnostics.Process.Start",
            ),
            (
                "using System.Net.Http; class C { object M() { return new HttpClient(); } }",
                "System.Net.Http.HttpClient",
            ),
        ] {
            assert!(
                has(&uses("csharp", src), want),
                "{src}: {:?}",
                uses("csharp", src)
            );
        }
    }

    // frob:tests crates/gob-symbols/src/lookups.rs::scan
    #[test]
    fn javascript_literal_lookups_resolve_to_the_module() {
        let u = uses(
            "javascript",
            "const cp = require('child_process'); cp.exec(x);",
        );
        assert!(
            u.contains(&("child_process.exec".to_owned(), false)),
            "{u:?}"
        );
        let u = uses("javascript", "const fs = require('fs'); fs['readFile'](p);");
        assert!(u.contains(&("fs.readFile".to_owned(), false)), "{u:?}");
        let u = uses("typescript", "const m = await import('node:fs'); m.rm(p);");
        assert!(u.contains(&("fs.rm".to_owned(), false)), "{u:?}");
    }

    // frob:tests crates/gob-symbols/src/lookups.rs::scan
    #[test]
    fn javascript_computed_lookups_are_flagged_not_dropped() {
        let u = uses("javascript", "function f(n) { return require(n); }");
        assert!(u.contains(&(String::new(), true)), "{u:?}");
        let u = uses(
            "javascript",
            "const fs = require('fs'); function f(k) { fs[k](1); }",
        );
        assert!(u.contains(&("fs".to_owned(), true)), "{u:?}");
    }

    // frob:tests crates/gob-symbols/src/lookups.rs::scan
    #[test]
    fn javascript_constant_names_fold_and_shadowing_blocks() {
        let u = uses("javascript", "const k = 'child' + '_process'; require(k);");
        assert!(u.contains(&("child_process".to_owned(), false)), "{u:?}");
        let u = uses(
            "javascript",
            "function require(x) { return x; } require(n);",
        );
        assert!(u.is_empty(), "{u:?}");
        let u = uses(
            "javascript",
            "const t = `fs`; require(t); require(`a${b}`);",
        );
        assert!(u.contains(&("fs".to_owned(), false)), "{u:?}");
        assert!(u.contains(&(String::new(), true)), "{u:?}");
    }

    // frob:tests crates/gob-symbols/src/lookups.rs::scan
    #[test]
    fn csharp_literal_and_computed_type_lookups() {
        let lit = uses(
            "csharp",
            "class C { void M() { var t = Type.GetType(\"System.Diagnostics.Process\"); } }",
        );
        assert!(
            lit.contains(&("System.Diagnostics.Process".to_owned(), false)),
            "{lit:?}"
        );
        let m = uses(
            "csharp",
            "class C { void M(string n) { var t = Type.GetType(n); } }",
        );
        assert!(m.contains(&(String::new(), true)), "{m:?}");
        let meth = uses(
            "csharp",
            "class C { void M() { Type.GetType(\"A.B\").GetMethod(\"Run\"); } }",
        );
        assert!(meth.contains(&("A.B.Run".to_owned(), false)), "{meth:?}");
    }
}
