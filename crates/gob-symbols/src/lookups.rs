//! Name-computed lookups in the TypeScript family and C#: `require(n)`, `import(n)`, `obj[n]`,
//! `Reflect.get(o, n)`, `Type.GetType(n)`, `asm.GetType(n)`, `t.GetMethod(n)` and kin.
//!
//! Each adapter here only parses and folds its own syntax into a gob-ir [`ConstValue`]; which
//! calls are lookups, and whether a name is a literal, is decided once by
//! [`gob_ir::name_lookup`]. A literal name resolves to the same path the direct form has; any
//! other name yields a `computed` [`PathUse`] (see `canon`), which consumers report Unresolved.

// frob:ticket 01M6422ZFEPZJYJQDDM6CV37RW

use std::collections::BTreeMap;

use gob_ir::const_value::{ConstValue, Fragment};
use gob_ir::name_lookup::{LookupKind, Resolved, concat, literal, primitive, resolve_name};
use tree_sitter::Node;

use crate::canon::{COMPUTED, PathUse, known_prefix};

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
        match self.binds.get(name)?.as_slice() {
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
                        for p in named(nm) {
                            match p.kind() {
                                "shorthand_property_identifier_pattern" => {
                                    let k = text(src, p).to_owned();
                                    self.bind(&k.clone(), Bind::Member(v, k));
                                }
                                "pair_pattern" => {
                                    if let (Some(k), Some(val)) = (
                                        p.child_by_field_name("key"),
                                        p.child_by_field_name("value"),
                                    ) && val.kind() == "identifier"
                                    {
                                        let key = text(src, k).to_owned();
                                        self.bind(text(src, val), Bind::Member(v, key));
                                    }
                                }
                                _ => {}
                            }
                        }
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
            | "satisfies_expression" => self.resolve(*named(e).first()?, d),
            "identifier" => match self.only(text(self.src, e))? {
                Bind::Import(p) => Some((p.clone(), false)),
                Bind::Member(v, key) => {
                    let (p, dy) = self.resolve(*v, d)?;
                    Some((format!("{p}.{key}"), dy))
                }
                Bind::Plain(v) => self.resolve(*v, d),
                Bind::Opaque => None,
            },
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

    fn emit(&mut self, e: Node<'t>, call: bool) {
        let Some((path, dynamic)) = self.resolve(e, 0) else {
            return;
        };
        let (path, computed) = known_prefix(path);
        if !dynamic || (path.is_empty() && !computed) {
            return;
        }
        tracing::debug!(line = e.start_position().row + 1, %path, computed, "lookups: name lookup");
        self.out.push(PathUse {
            offset: e.start_byte(),
            line: u32::try_from(e.start_position().row + 1).unwrap_or(u32::MAX),
            spelled: text(self.src, e).split_whitespace().collect(),
            path,
            call,
            dynamic: true,
            external_root: false,
            computed,
        });
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
        assert!(u.contains(&("node:fs.rm".to_owned(), false)), "{u:?}");
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
