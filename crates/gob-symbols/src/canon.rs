//! Import-resolved path uses of a Rust or Python file (ticket D36SRKP).
//!
//! The call graph spells a callee as written, so `use std::fs::read_to_string as slurp;
//! slurp(..)` and `import subprocess as sp; sp.run(..)` hide the very symbol a capability
//! vocabulary names. [`path_uses`] parses one file and returns every call and every
//! function-valued reference whose first segment resolves through an import, a local alias
//! (`let f = std::fs::remove_file;`, `f = os.system`) or, in Rust, an explicit external root
//! (`std::`, `tokio::`), together with the fully qualified path it denotes. Names that a
//! parameter, a local binding or a local item shadow resolve to nothing. Only syntax-tree
//! nodes are read, so strings and comments never match. Scoping is lexical and per file; a glob
//! import and a computed attribute name are not resolved (a literal `getattr` and
//! `importlib.import_module` argument is, flagged `dynamic`).

// frob:ticket 01M5XNNHJ0ES2PB6ZKAD36SRKP

use std::collections::BTreeMap;

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use tree_sitter::Node;

/// Crates whose paths a Rust file may name without importing them first.
const EXTERNAL_ROOTS: &[&str] = &["std", "core", "alloc", "tokio", "async_std", "smol"];

/// Deepest alias chain followed (`let a = b; let b = c; ..`).
const MAX_ALIAS_DEPTH: usize = 8;

/// One call or function-valued reference with its resolved path.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PathUse {
    /// Byte offset of the reference in the file.
    pub offset: usize,
    /// One-based line of the reference.
    pub line: u32,
    /// The path as written (Rust `a::b`, Python `a.b`).
    pub spelled: String,
    /// The fully qualified path it denotes (same separator as `spelled`).
    pub path: String,
    /// True for a call, false for a function used as a value.
    pub call: bool,
    /// True when a `getattr` or `import_module` literal produced the path (an unproven use).
    pub dynamic: bool,
    /// True when the path is rooted in a well-known external crate (Rust `std::` and kin): the
    /// reference names that crate whatever local items are called.
    pub external_root: bool,
}

/// How a name in scope resolves.
#[derive(Clone, Debug, PartialEq, Eq)]
enum Binding {
    /// An alias for this fully qualified path (and whether it was reached dynamically).
    Alias(String, bool),
    /// A local item or variable: the name does not denote an import.
    Shadow,
}

/// Merges a second binding of one name: equal aliases agree, anything else is a shadow.
fn bind(map: &mut BTreeMap<String, Binding>, name: &str, b: Binding) {
    match map.get(name) {
        Some(old) if *old == b => {}
        Some(_) => {
            map.insert(name.to_owned(), Binding::Shadow);
        }
        None => {
            map.insert(name.to_owned(), b);
        }
    }
}

fn text<'a>(src: &'a str, n: Node<'_>) -> &'a str {
    &src[n.start_byte()..n.end_byte()]
}

fn line(n: Node<'_>) -> u32 {
    u32::try_from(n.start_position().row + 1).unwrap_or(u32::MAX)
}

/// Every import-resolved call and function-valued reference in `source`, in source order.
/// `language` is the adapter tag (`rust` or `python`); other languages and unparsable files
/// give nothing.
pub fn path_uses(language: &str, source: &str) -> Vec<PathUse> {
    let lang = match language {
        "rust" => Language::Rust,
        "python" => Language::Python,
        _ => return Vec::new(),
    };
    let ParseResult::Parsed(tree) = parse(lang, source, &ParseLimits::default()) else {
        tracing::debug!(language, "canon: file not parsed, no path uses");
        return Vec::new();
    };
    let mut out = match lang {
        Language::Rust => rust::scan(&tree.text, tree.root()),
        _ => python::scan(&tree.text, tree.root()),
    };
    out.sort_by_key(|u| u.offset);
    out.dedup_by(|a, b| a.offset == b.offset && a.path == b.path);
    tracing::debug!(language, uses = out.len(), "canon: path uses scanned");
    out
}

mod rust {
    use super::{
        BTreeMap, Binding, EXTERNAL_ROOTS, MAX_ALIAS_DEPTH, Node, PathUse, bind, line, text,
    };

    /// Scans a Rust syntax tree.
    pub(super) fn scan(src: &str, root: Node<'_>) -> Vec<PathUse> {
        let mut cx = Cx {
            src,
            items: BTreeMap::new(),
            out: Vec::new(),
        };
        cx.visit(root);
        cx.out
    }

    struct Cx<'s> {
        src: &'s str,
        /// Item-level bindings per container node id.
        items: BTreeMap<usize, BTreeMap<String, Binding>>,
        out: Vec<PathUse>,
    }

    fn is_path(n: Node<'_>) -> bool {
        matches!(n.kind(), "identifier" | "scoped_identifier")
    }

    /// The names a pattern binds (every identifier inside it).
    fn pattern_names(src: &str, p: Node<'_>, out: &mut Vec<String>) {
        if p.kind() == "identifier" {
            out.push(text(src, p).to_owned());
            return;
        }
        let mut c = p.walk();
        for ch in p.named_children(&mut c) {
            pattern_names(src, ch, out);
        }
    }

    /// The bindings a `use` tree introduces: `(local name, fully qualified path)`.
    fn use_bindings(src: &str, n: Node<'_>, prefix: &str, out: &mut Vec<(String, String)>) {
        let join = |tail: &str| {
            if prefix.is_empty() {
                tail.to_owned()
            } else {
                format!("{prefix}::{tail}")
            }
        };
        let clean = |s: &str| s.split_whitespace().collect::<String>();
        match n.kind() {
            "identifier" | "scoped_identifier" => {
                let full = join(clean(text(src, n)).trim_start_matches("::"));
                let local = full.rsplit("::").next().unwrap_or(&full).to_owned();
                out.push((local, full));
            }
            "self" => {
                if let Some(local) = prefix.rsplit("::").next() {
                    out.push((local.to_owned(), prefix.to_owned()));
                }
            }
            "use_as_clause" => {
                let (Some(path), Some(alias)) = (
                    n.child_by_field_name("path"),
                    n.child_by_field_name("alias"),
                ) else {
                    return;
                };
                let full = join(clean(text(src, path)).trim_start_matches("::"));
                if path.kind() == "self" {
                    out.push((text(src, alias).to_owned(), prefix.to_owned()));
                } else {
                    out.push((text(src, alias).to_owned(), full));
                }
            }
            "scoped_use_list" => {
                let base = n.child_by_field_name("path").map_or_else(
                    || prefix.to_owned(),
                    |p| join(clean(text(src, p)).trim_start_matches("::")),
                );
                if let Some(list) = n.child_by_field_name("list") {
                    use_bindings(src, list, &base, out);
                }
            }
            "use_list" => {
                let mut c = n.walk();
                for ch in n.named_children(&mut c) {
                    use_bindings(src, ch, prefix, out);
                }
            }
            // A glob names nothing locally.
            _ => {}
        }
    }

    /// Item-level bindings of a `source_file`, `declaration_list` or `block`.
    fn container_items(src: &str, container: Node<'_>) -> BTreeMap<String, Binding> {
        let mut map = BTreeMap::new();
        let mut c = container.walk();
        for ch in container.named_children(&mut c) {
            match ch.kind() {
                "use_declaration" => {
                    let Some(arg) = ch.child_by_field_name("argument") else {
                        continue;
                    };
                    let mut found = Vec::new();
                    use_bindings(src, arg, "", &mut found);
                    for (local, full) in found {
                        bind(&mut map, &local, Binding::Alias(full, false));
                    }
                }
                "function_item"
                | "struct_item"
                | "enum_item"
                | "union_item"
                | "const_item"
                | "static_item"
                | "type_item"
                | "trait_item"
                | "mod_item"
                | "function_signature_item"
                | "foreign_mod_item" => {
                    if let Some(name) = ch.child_by_field_name("name") {
                        bind(&mut map, text(src, name), Binding::Shadow);
                    }
                }
                _ => {}
            }
        }
        map
    }

    impl Cx<'_> {
        fn items_of(&mut self, container: Node<'_>) -> &BTreeMap<String, Binding> {
            let src = self.src;
            self.items
                .entry(container.id())
                .or_insert_with(|| container_items(src, container))
        }

        /// How `name` resolves at `at`, walking the enclosing scopes outwards.
        fn lookup(&mut self, name: &str, at: Node<'_>, depth: usize) -> Option<Binding> {
            let mut child = at;
            while let Some(a) = child.parent() {
                match a.kind() {
                    "block" => {
                        // later `let`s of this block do not apply; earlier ones, nearest first
                        let mut c = a.walk();
                        let before: Vec<Node<'_>> = a
                            .named_children(&mut c)
                            .take_while(|s| s.end_byte() <= child.start_byte())
                            .collect();
                        for s in before.into_iter().rev() {
                            if s.kind() != "let_declaration" {
                                continue;
                            }
                            let Some(pat) = s.child_by_field_name("pattern") else {
                                continue;
                            };
                            let mut names = Vec::new();
                            pattern_names(self.src, pat, &mut names);
                            if !names.iter().any(|n| n == name) {
                                continue;
                            }
                            let simple = names.len() == 1
                                && matches!(pat.kind(), "identifier" | "mut_pattern");
                            let aliased = simple
                                .then(|| s.child_by_field_name("value"))
                                .flatten()
                                .and_then(|v| self.resolve_expr(v, s, depth + 1));
                            return Some(match aliased {
                                Some((p, _)) => Binding::Alias(p, false),
                                None => Binding::Shadow,
                            });
                        }
                        if let Some(b) = self.items_of(a).get(name) {
                            return Some(b.clone());
                        }
                    }
                    "source_file" | "declaration_list" => {
                        if let Some(b) = self.items_of(a).get(name) {
                            return Some(b.clone());
                        }
                    }
                    "function_item" | "closure_expression" => {
                        if let Some(params) = a
                            .child_by_field_name("parameters")
                            .filter(|p| p.end_byte() <= child.start_byte() || p.id() == child.id())
                        {
                            let mut names = Vec::new();
                            pattern_names(self.src, params, &mut names);
                            if names.iter().any(|n| n == name) {
                                return Some(Binding::Shadow);
                            }
                        }
                    }
                    "for_expression" | "match_arm" | "if_expression" | "while_expression" => {
                        let mut pats = Vec::new();
                        if let Some(p) = a.child_by_field_name("pattern") {
                            pats.push(p);
                        }
                        if let Some(cond) = a.child_by_field_name("condition") {
                            pats.push(cond);
                        }
                        let mut names = Vec::new();
                        for p in pats.into_iter().filter(|p| p.id() != child.id()) {
                            pattern_names(self.src, p, &mut names);
                        }
                        if names.iter().any(|n| n == name) {
                            return Some(Binding::Shadow);
                        }
                    }
                    _ => {}
                }
                child = a;
            }
            None
        }

        /// The qualified path of the written path `spelled` at `at`: `(path, via_alias)`, or
        /// `None` when its first segment is shadowed or names this crate.
        fn canonical(
            &mut self,
            spelled: &str,
            at: Node<'_>,
            depth: usize,
        ) -> Option<(String, bool)> {
            if depth > MAX_ALIAS_DEPTH {
                return None;
            }
            let spelled = spelled.trim_start_matches("::");
            let (first, rest) = match spelled.split_once("::") {
                Some((f, r)) => (f, Some(r)),
                None => (spelled, None),
            };
            if matches!(first, "crate" | "self" | "super" | "Self") {
                return None;
            }
            match self.lookup(first, at, depth) {
                Some(Binding::Shadow) => None,
                Some(Binding::Alias(p, _)) => {
                    let head = p.trim_start_matches("::");
                    if matches!(head.split("::").next(), Some("crate" | "self" | "super")) {
                        return None;
                    }
                    Some((
                        rest.map_or_else(|| head.to_owned(), |r| format!("{head}::{r}")),
                        true,
                    ))
                }
                None => Some((spelled.to_owned(), false)),
            }
        }

        /// An expression that is a plain path (possibly with turbofish) resolved at `at`.
        fn resolve_expr(
            &mut self,
            e: Node<'_>,
            at: Node<'_>,
            depth: usize,
        ) -> Option<(String, bool)> {
            let e = if e.kind() == "generic_function" {
                e.child_by_field_name("function")?
            } else {
                e
            };
            if !is_path(e) {
                return None;
            }
            let spelled: String = text(self.src, e).split_whitespace().collect();
            if spelled.contains('<') {
                return None;
            }
            self.canonical(&spelled, at, depth)
        }

        fn emit(&mut self, e: Node<'_>, call: bool) {
            let e = if e.kind() == "generic_function" {
                match e.child_by_field_name("function") {
                    Some(f) => f,
                    None => return,
                }
            } else {
                e
            };
            if !is_path(e) {
                return;
            }
            let spelled: String = text(self.src, e).split_whitespace().collect();
            let Some((path, aliased)) = self.resolve_expr(e, e, 0) else {
                return;
            };
            let root = path.split("::").next().unwrap_or("");
            let external_root = path.contains("::") && EXTERNAL_ROOTS.contains(&root);
            if !aliased && !external_root {
                return;
            }
            self.out.push(PathUse {
                offset: e.start_byte(),
                line: line(e),
                spelled,
                path,
                call,
                dynamic: false,
                external_root,
            });
        }

        fn visit(&mut self, n: Node<'_>) {
            match n.kind() {
                "call_expression" => {
                    if let Some(f) = n.child_by_field_name("function") {
                        self.emit(f, true);
                    }
                }
                "arguments"
                | "array_expression"
                | "tuple_expression"
                | "return_expression"
                | "reference_expression"
                | "parenthesized_expression"
                | "type_cast_expression"
                | "block" => {
                    let mut c = n.walk();
                    let kids: Vec<_> = n.named_children(&mut c).collect();
                    for k in kids {
                        if matches!(k.kind(), "identifier" | "scoped_identifier") {
                            self.emit(k, false);
                        }
                    }
                }
                "let_declaration"
                | "assignment_expression"
                | "field_initializer"
                | "match_arm"
                | "closure_expression" => {
                    let field = match n.kind() {
                        "assignment_expression" => "right",
                        "closure_expression" => "body",
                        _ => "value",
                    };
                    if let Some(v) = n.child_by_field_name(field)
                        && matches!(v.kind(), "identifier" | "scoped_identifier")
                    {
                        self.emit(v, false);
                    }
                }
                _ => {}
            }
            let mut c = n.walk();
            let kids: Vec<_> = n.children(&mut c).collect();
            for k in kids {
                // macro bodies are token trees; their calls stay with the call graph
                if matches!(
                    k.kind(),
                    "use_declaration" | "attribute_item" | "token_tree"
                ) {
                    continue;
                }
                self.visit(k);
            }
        }
    }
}

mod python {
    use super::{BTreeMap, Binding, MAX_ALIAS_DEPTH, Node, PathUse, bind, line, text};

    /// Scans a Python syntax tree.
    pub(super) fn scan(src: &str, root: Node<'_>) -> Vec<PathUse> {
        let mut cx = Cx {
            src,
            scopes: Vec::new(),
            out: Vec::new(),
        };
        // two passes so a later alias can see an earlier one (`a = os.system; b = a`)
        cx.scopes.push(Scope {
            map: BTreeMap::new(),
            class: false,
        });
        for _ in 0..2 {
            let map = cx.collect(root, &[]);
            if let Some(s) = cx.scopes.last_mut() {
                s.map = map;
            }
        }
        cx.visit(root);
        cx.out
    }

    struct Scope {
        map: BTreeMap<String, Binding>,
        /// A class body: invisible to the functions nested in it.
        class: bool,
    }

    struct Cx<'s> {
        src: &'s str,
        scopes: Vec<Scope>,
        out: Vec<PathUse>,
    }

    /// The identifiers bound by an assignment target or parameter list.
    fn names_in(src: &str, n: Node<'_>, out: &mut Vec<String>) {
        match n.kind() {
            "identifier" => out.push(text(src, n).to_owned()),
            "attribute" | "subscript" => {}
            "default_parameter" | "typed_default_parameter" => {
                if let Some(nm) = n.child_by_field_name("name") {
                    names_in(src, nm, out);
                }
            }
            "typed_parameter" | "list_splat_pattern" | "dictionary_splat_pattern" => {
                let mut c = n.walk();
                if let Some(first) = n.named_children(&mut c).next() {
                    names_in(src, first, out);
                }
            }
            _ => {
                let mut c = n.walk();
                for ch in n.named_children(&mut c) {
                    names_in(src, ch, out);
                }
            }
        }
    }

    /// Binds the names of an `import a.b [as x]` statement.
    fn collect_import(src: &str, n: Node<'_>, map: &mut BTreeMap<String, Binding>) {
        let mut c = n.walk();
        for ch in n.children_by_field_name("name", &mut c) {
            if ch.kind() == "aliased_import" {
                if let (Some(nm), Some(al)) = (
                    ch.child_by_field_name("name"),
                    ch.child_by_field_name("alias"),
                ) {
                    let full = Binding::Alias(text(src, nm).to_owned(), false);
                    bind(map, text(src, al), full);
                }
            } else {
                let full = text(src, ch);
                let head = full.split('.').next().unwrap_or(full);
                bind(map, head, Binding::Alias(head.to_owned(), false));
            }
        }
    }

    /// Binds the names of a `from m import n [as x]` statement (relative modules shadow).
    fn collect_import_from(src: &str, n: Node<'_>, map: &mut BTreeMap<String, Binding>) {
        let module = n
            .child_by_field_name("module_name")
            .map(|m| text(src, m).to_owned())
            .unwrap_or_default();
        let relative = module.starts_with('.');
        let mut c = n.walk();
        for ch in n.children_by_field_name("name", &mut c) {
            let (local, member) = if ch.kind() == "aliased_import" {
                let (Some(nm), Some(al)) = (
                    ch.child_by_field_name("name"),
                    ch.child_by_field_name("alias"),
                ) else {
                    continue;
                };
                (text(src, al).to_owned(), text(src, nm).to_owned())
            } else {
                (text(src, ch).to_owned(), text(src, ch).to_owned())
            };
            let b = if relative {
                Binding::Shadow
            } else {
                Binding::Alias(format!("{module}.{member}"), false)
            };
            bind(map, &local, b);
        }
    }

    impl Cx<'_> {
        /// The bindings made directly in `scope`'s statements, `params` first. Nested
        /// functions, classes and lambdas only bind their own name.
        fn collect(&mut self, scope: Node<'_>, params: &[String]) -> BTreeMap<String, Binding> {
            let mut map = BTreeMap::new();
            for p in params {
                bind(&mut map, p, Binding::Shadow);
            }
            self.collect_into(scope, &mut map, true);
            map
        }

        fn collect_into(&mut self, n: Node<'_>, map: &mut BTreeMap<String, Binding>, top: bool) {
            let src = self.src;
            let shadow = |names: Vec<String>, map: &mut BTreeMap<String, Binding>| {
                for nm in names {
                    bind(map, &nm, Binding::Shadow);
                }
            };
            match n.kind() {
                "function_definition" | "class_definition" if !top => {
                    if let Some(nm) = n.child_by_field_name("name") {
                        bind(map, text(src, nm), Binding::Shadow);
                    }
                    return;
                }
                "lambda" if !top => return,
                "import_statement" => {
                    collect_import(src, n, map);
                    return;
                }
                "import_from_statement" => {
                    collect_import_from(src, n, map);
                    return;
                }
                "assignment" => {
                    if let Some(left) = n.child_by_field_name("left") {
                        let right = n.child_by_field_name("right");
                        if left.kind() == "identifier" {
                            let name = text(src, left).to_owned();
                            let aliased = right.and_then(|r| self.resolve(r, 0));
                            match aliased {
                                Some((p, d)) => bind(map, &name, Binding::Alias(p, d)),
                                None => bind(map, &name, Binding::Shadow),
                            }
                        } else {
                            let mut names = Vec::new();
                            names_in(src, left, &mut names);
                            shadow(names, map);
                        }
                    }
                }
                "augmented_assignment" | "for_statement" | "for_in_clause" => {
                    if let Some(left) = n.child_by_field_name("left") {
                        let mut names = Vec::new();
                        names_in(src, left, &mut names);
                        shadow(names, map);
                    }
                }
                "named_expression" => {
                    if let Some(nm) = n.child_by_field_name("name") {
                        let mut names = Vec::new();
                        names_in(src, nm, &mut names);
                        shadow(names, map);
                    }
                }
                "as_pattern" => {
                    if let Some(al) = n.child_by_field_name("alias") {
                        let mut names = Vec::new();
                        names_in(src, al, &mut names);
                        shadow(names, map);
                    }
                }
                _ => {}
            }
            let mut c = n.walk();
            let kids: Vec<_> = n.children(&mut c).collect();
            for k in kids {
                self.collect_into(k, map, false);
            }
        }

        fn lookup(&self, name: &str) -> Option<&Binding> {
            let last = self.scopes.len().checked_sub(1)?;
            for (i, s) in self.scopes.iter().enumerate().rev() {
                if s.class && i != last {
                    continue;
                }
                if let Some(b) = s.map.get(name) {
                    return Some(b);
                }
            }
            None
        }

        /// The dotted path an expression denotes, and whether a literal `getattr` or
        /// `import_module` produced it.
        fn resolve(&self, e: Node<'_>, depth: usize) -> Option<(String, bool)> {
            if depth > MAX_ALIAS_DEPTH {
                return None;
            }
            match e.kind() {
                "identifier" => match self.lookup(text(self.src, e)) {
                    Some(Binding::Alias(p, d)) => Some((p.clone(), *d)),
                    _ => None,
                },
                "parenthesized_expression" => {
                    let mut c = e.walk();
                    let inner = e.named_children(&mut c).next()?;
                    self.resolve(inner, depth + 1)
                }
                "attribute" => {
                    let obj = e.child_by_field_name("object")?;
                    let attr = e.child_by_field_name("attribute")?;
                    let (p, d) = self.resolve(obj, depth + 1)?;
                    Some((format!("{p}.{}", text(self.src, attr)), d))
                }
                "call" => self.resolve_dynamic(e, depth),
                _ => None,
            }
        }

        /// `getattr(mod, 'name')`, `importlib.import_module('m')` and `__import__('m')` with
        /// literal arguments.
        fn resolve_dynamic(&self, call: Node<'_>, depth: usize) -> Option<(String, bool)> {
            let f = call.child_by_field_name("function")?;
            let args = call.child_by_field_name("arguments")?;
            let mut c = args.walk();
            let args: Vec<Node<'_>> = args.named_children(&mut c).collect();
            let lit = |n: Node<'_>| -> Option<String> {
                if n.kind() != "string" {
                    return None;
                }
                let mut c = n.walk();
                let mut parts = n
                    .named_children(&mut c)
                    .filter(|p| !matches!(p.kind(), "string_start" | "string_end"));
                let first = parts.next()?;
                (first.kind() == "string_content" && parts.next().is_none())
                    .then(|| text(self.src, first).to_owned())
            };
            if f.kind() == "identifier" {
                let name = text(self.src, f);
                if self.lookup(name).is_some() {
                    // a user binding named like the builtin, or an import alias handled below
                    if let Some((p, _)) = self.resolve(f, depth + 1)
                        && p == "importlib.import_module"
                    {
                        return lit(*args.first()?).map(|m| (m, true));
                    }
                    return None;
                }
                return match name {
                    "getattr" if args.len() >= 2 => {
                        let (p, _) = self.resolve(args[0], depth + 1)?;
                        Some((format!("{p}.{}", lit(args[1])?), true))
                    }
                    "__import__" if !args.is_empty() => lit(args[0]).map(|m| (m, true)),
                    _ => None,
                };
            }
            let (p, _) = self.resolve(f, depth + 1)?;
            (p == "importlib.import_module")
                .then(|| lit(*args.first()?).map(|m| (m, true)))
                .flatten()
        }

        fn emit(&mut self, e: Node<'_>, call: bool) {
            let Some((path, dynamic)) = self.resolve(e, 0) else {
                return;
            };
            if !call && !dynamic && !path.contains('.') {
                return;
            }
            self.out.push(PathUse {
                offset: e.start_byte(),
                line: line(e),
                spelled: text(self.src, e).split_whitespace().collect(),
                path,
                call,
                dynamic,
                external_root: false,
            });
        }

        /// A function used as a value: an expression in an argument, assignment, return or
        /// container position.
        fn value(&mut self, v: Node<'_>) {
            if matches!(v.kind(), "identifier" | "attribute" | "call") {
                self.emit(v, false);
            }
        }

        fn visit(&mut self, n: Node<'_>) {
            let mut pushed = false;
            match n.kind() {
                "function_definition" | "lambda" => {
                    let mut names = Vec::new();
                    if let Some(p) = n.child_by_field_name("parameters") {
                        names_in(self.src, p, &mut names);
                    }
                    let body = n.child_by_field_name("body");
                    let mut map = BTreeMap::new();
                    for nm in &names {
                        bind(&mut map, nm, Binding::Shadow);
                    }
                    self.scopes.push(Scope { map, class: false });
                    pushed = true;
                    if let Some(b) = body {
                        let mut inner = BTreeMap::new();
                        self.collect_into(b, &mut inner, false);
                        if let Some(s) = self.scopes.last_mut() {
                            for (k, v) in inner {
                                bind(&mut s.map, &k, v);
                            }
                        }
                    }
                }
                "class_definition" => {
                    let mut map = BTreeMap::new();
                    if let Some(b) = n.child_by_field_name("body") {
                        self.collect_into(b, &mut map, false);
                    }
                    self.scopes.push(Scope { map, class: true });
                    pushed = true;
                }
                "call" => {
                    if let Some(f) = n.child_by_field_name("function")
                        && matches!(f.kind(), "identifier" | "attribute" | "call")
                    {
                        self.emit(f, true);
                    }
                }
                "argument_list"
                | "list"
                | "tuple"
                | "set"
                | "boolean_operator"
                | "conditional_expression"
                | "parenthesized_expression"
                | "return_statement"
                | "expression_list"
                | "await" => {
                    let mut c = n.walk();
                    let kids: Vec<_> = n.named_children(&mut c).collect();
                    for k in kids {
                        if k.kind() == "keyword_argument" {
                            if let Some(v) = k.child_by_field_name("value") {
                                self.value(v);
                            }
                        } else {
                            self.value(k);
                        }
                    }
                }
                "assignment" | "named_expression" => {
                    if let Some(r) = n
                        .child_by_field_name("right")
                        .or_else(|| n.child_by_field_name("value"))
                    {
                        self.value(r);
                    }
                }
                "pair" => {
                    if let Some(v) = n.child_by_field_name("value") {
                        self.value(v);
                    }
                }
                _ => {}
            }
            let mut c = n.walk();
            let kids: Vec<_> = n.children(&mut c).collect();
            for k in kids {
                self.visit(k);
            }
            if pushed {
                self.scopes.pop();
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn paths(lang: &str, src: &str) -> Vec<(String, bool, bool)> {
        path_uses(lang, src)
            .into_iter()
            .map(|u| (u.path, u.call, u.dynamic))
            .collect()
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn rust_use_alias_resolves_a_call() {
        let src = "use std::fs::read_to_string as slurp;\nfn f() { slurp(\"x\"); }\n";
        assert_eq!(
            paths("rust", src),
            vec![("std::fs::read_to_string".into(), true, false)]
        );
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn rust_type_alias_and_grouped_use_resolve() {
        let src = "use std::fs::{File as Fh, OpenOptions};\nfn f() { Fh::create(\"sh\"); }\n";
        assert_eq!(
            paths("rust", src),
            vec![("std::fs::File::create".into(), true, false)]
        );
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn rust_fn_value_and_let_alias_resolve() {
        let src = "fn f() {\n    let g: fn(&str) -> _ = std::fs::remove_file;\n    g(\"x\");\n    v.iter().for_each(std::fs::remove_file);\n}\n";
        let got = paths("rust", src);
        assert_eq!(got.len(), 3, "{got:?}");
        assert!(got.iter().all(|(p, _, _)| p == "std::fs::remove_file"));
        assert_eq!(got.iter().filter(|(_, c, _)| *c).count(), 1);
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn rust_function_scoped_use_is_scoped() {
        let src = "fn a() { use std::fs::read as r; r(\"x\"); }\nfn b() { r(\"y\"); }\n";
        let got = path_uses("rust", src);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].line, 1);
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn rust_shadowed_names_resolve_to_nothing() {
        let src = "use std::fs::read as slurp;\nfn a(slurp: u8) { slurp(1); }\nfn b() { let slurp = 3; slurp(1); }\nfn c() { fn slurp() {} slurp(); }\n";
        assert!(path_uses("rust", src).is_empty());
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn rust_explicit_external_root_is_kept_and_local_roots_are_dropped() {
        let src = "use crate::proc::File;\nfn f() { std::fs::File::create(\"sh\"); tokio::fs::File::create(\"sh\"); File::create(\"x\"); }\n";
        let got = path_uses("rust", src);
        assert_eq!(got.len(), 2, "{got:?}");
        assert!(got.iter().all(|u| u.external_root));
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn rust_strings_and_comments_never_match() {
        let src = "use std::fs::read as r;\nfn f() { let s = \"r(1)\"; // r(2)\n}\n";
        assert!(path_uses("rust", src).is_empty());
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn python_import_aliases_resolve() {
        let src = "import subprocess as sp\nfrom subprocess import run\nfrom os import system as s\nsp.run(['x'])\nrun(['x'])\ns('x')\n";
        let got = paths("python", src);
        assert_eq!(
            got,
            vec![
                ("subprocess.run".into(), true, false),
                ("subprocess.run".into(), true, false),
                ("os.system".into(), true, false),
            ]
        );
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn python_dynamic_dispatch_is_flagged() {
        let src = "import os, importlib\ngetattr(os, 'system')('x')\nimportlib.import_module('subprocess').run(['x'])\n__import__('os').system('x')\nf = getattr(os, 'system')\nf('y')\n";
        let got: Vec<_> = paths("python", src)
            .into_iter()
            .filter(|(p, _, _)| p != "importlib.import_module")
            .collect();
        assert!(got.iter().all(|(_, _, d)| *d), "{got:?}");
        assert_eq!(got.iter().filter(|(p, _, _)| p == "os.system").count(), 4);
        assert_eq!(
            got.iter().filter(|(p, _, _)| p == "subprocess.run").count(),
            1
        );
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn python_shadowing_strings_and_comments_do_not_match() {
        let src = "import subprocess as sp\nfrom subprocess import run\ndef f(sp):\n    sp.run(1)\ndef g():\n    run = 3\n    run(1)\ndef run2():\n    \"\"\"sp.run(1)\"\"\"\n    s = 'sp.run(1)'  # sp.run(2)\n";
        assert!(path_uses("python", src).is_empty());
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn python_function_value_and_alias_assignment_resolve() {
        let src =
            "import os\ndef f(xs):\n    h = os.system\n    h('a')\n    return map(os.system, xs)\n";
        let got = paths("python", src);
        assert_eq!(got.len(), 3, "{got:?}");
        assert!(got.iter().all(|(p, _, _)| p == "os.system"));
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn unknown_languages_give_nothing() {
        assert!(path_uses("go", "package main").is_empty());
    }
}
