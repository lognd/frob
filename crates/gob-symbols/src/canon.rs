//! Import-resolved path uses of a Rust or Python file (ticket D36SRKP).
//!
//! The call graph spells a callee as written, so `use std::fs::read_to_string as slurp;
//! slurp(..)` and `import subprocess as sp; sp.run(..)` hide the very symbol a capability
//! vocabulary names. [`path_uses`] parses one file and returns every call and every
//! function-valued reference whose first segment resolves through an import, a local alias
//! (`let f = std::fs::remove_file;`, `f = os.system`) or, in Rust, an explicit external root
//! (`std::`, `tokio::`), together with the fully qualified path it denotes. Names that a
//! parameter, a local binding or a local item shadow resolve to nothing. Only syntax-tree
//! nodes are read, so strings and comments never match. Scoping is lexical and per file; a Rust glob
//! import and a computed attribute name are not resolved (a literal `getattr` and
//! `importlib.import_module` argument is, flagged `dynamic`). A Python name that no scope binds
//! while `from m import *` is in force (ticket G68NRS1) is emitted bare, with the candidate
//! modules in [`PathUse::wildcards`] for the consumer to resolve; [`python_all`] reads a module's
//! literal `__all__`.

// frob:ticket 01M5XNNHJ0ES2PB6ZKAD36SRKP
// frob:ticket 01M6422Z8JGE789ZHW4G68NRS1
// frob:ticket 01M64230AR8DHJZY9QQS3EC85S

use std::collections::BTreeMap;

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use tree_sitter::Node;

/// Crates whose paths a Rust file may name without importing them first.
const EXTERNAL_ROOTS: &[&str] = &[
    "std",
    "core",
    "alloc",
    "tokio",
    "async_std",
    "smol",
    // native interop (ticket S3EC85S): the crates a foreign call goes through, and the synthetic
    // `extern` root a function declared in an `extern` block resolves to
    "libc",
    "libloading",
    "windows_sys",
    "winapi",
    EXTERN_ROOT,
];

/// The synthetic root of a function or static declared in an `extern "C" { .. }` block.
const EXTERN_ROOT: &str = "extern";

/// Deepest alias chain followed (`let a = b; let b = c; ..`).
const MAX_ALIAS_DEPTH: usize = 8;

/// One call or function-valued reference with its resolved path.
#[derive(Clone, Debug, PartialEq, Eq)]
#[allow(
    clippy::struct_excessive_bools,
    reason = "independent facts of one resolved use, read together by consumers"
)]
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
    /// True when the lookup's name is not a single literal (`getattr(os, n)`, `__import__(n)`):
    /// `path` is then only the known prefix (empty when nothing is known) and the use may reach
    /// anything under it. Always `dynamic`; a consumer reports it Unresolved, never certain.
    pub computed: bool,
    /// Modules whose `from m import *` could have bound the leading name of `path` (ticket
    /// G68NRS1), as written (`os`, `.helpers`). Empty for every ordinary use. When set, `path` is
    /// the bare dotted name as written (`getenv`, `environ.get`), not a qualified path: the name
    /// is bound by no import, parameter or assignment in scope, so one of these modules supplies
    /// it, and the consumer decides which (several modules are ambiguous, never proven).
    pub wildcards: Vec<String>,
    /// True when the leading name has several possible bindings in one scope (an import rebound
    /// after a definition, a `try`/`except ImportError` fallback, a conditional shadow; ticket
    /// 01M6422ZN7HKF98JDAP7XKRQQ2): one `PathUse` is emitted per possible origin, each unproven,
    /// and a consumer must not let a same-named repository item hide them.
    pub maybe: bool,
}

/// The path segment standing for a lookup name that is not a single literal.
pub(crate) const COMPUTED: &str = "?";

/// Splits a path at its first [`COMPUTED`] segment: the known prefix and whether there was one.
pub(crate) fn known_prefix(path: String) -> (String, bool) {
    let segments: Vec<&str> = path.split('.').collect();
    match segments.iter().position(|s| *s == COMPUTED) {
        Some(i) => (segments[..i].join("."), true),
        None => (path, false),
    }
}

/// How a name in scope resolves.
#[derive(Clone, Debug, PartialEq, Eq)]
enum Binding {
    /// An alias for this fully qualified path (and whether it was reached dynamically).
    Alias(String, bool),
    /// A local item or variable: the name does not denote an import.
    Shadow,
    /// Several bindings of one scope disagree: the name may denote any of these origins (sorted,
    /// distinct) and, when the flag is set, also a local item or variable.
    Maybe(Vec<String>, bool),
}

impl Binding {
    /// The possible origins and whether a local item may also supply the name.
    fn parts(&self) -> (Vec<String>, bool) {
        match self {
            Binding::Alias(p, _) => (vec![p.clone()], false),
            Binding::Shadow => (Vec::new(), true),
            Binding::Maybe(o, s) => (o.clone(), *s),
        }
    }
}

/// Merges a second binding of one name: equal aliases agree, two shadows stay a shadow and any
/// other mix keeps every possible origin as [`Binding::Maybe`].
fn bind(map: &mut BTreeMap<String, Binding>, name: &str, b: Binding) {
    let merged = match map.get(name) {
        None => b,
        Some(old) if *old == b => return,
        Some(old) => {
            let (mut origins, mut shadowed) = old.parts();
            let (more, s2) = b.parts();
            origins.extend(more);
            origins.sort();
            origins.dedup();
            shadowed |= s2;
            if origins.is_empty() {
                Binding::Shadow
            } else if origins.len() == 1 && !shadowed {
                Binding::Alias(origins.remove(0), false)
            } else {
                Binding::Maybe(origins, shadowed)
            }
        }
    };
    map.insert(name.to_owned(), merged);
}

fn text<'a>(src: &'a str, n: Node<'_>) -> &'a str {
    &src[n.start_byte()..n.end_byte()]
}

fn line(n: Node<'_>) -> u32 {
    u32::try_from(n.start_position().row + 1).unwrap_or(u32::MAX)
}

/// What a Python module-level name may denote (ticket 01M6422ZN7HKF98JDAP7XKRQQ2).
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct PythonBinding {
    /// Every qualified path an import or alias binds the name to (relative modules keep dots).
    pub origins: Vec<String>,
    /// True when a definition or plain assignment in the module may also supply the name.
    pub local: bool,
}

/// The module-level names of a Python module and the modules of its `from m import *`.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct PythonModule {
    /// Module-level binding of each name, however many conditional branches bind it.
    pub names: BTreeMap<String, PythonBinding>,
    /// Modules of every wildcard import, as written.
    pub stars: Vec<String>,
}

/// Reads the module-level bindings of a Python source, or `None` when it does not parse. This
/// lets a consumer follow a re-export (`from subprocess import run as r`) across repository
/// modules (ticket 01M6422ZN7HKF98JDAP7XKRQQ2).
pub fn python_module(source: &str) -> Option<PythonModule> {
    let ParseResult::Parsed(tree) = parse(Language::Python, source, &ParseLimits::default()) else {
        return None;
    };
    let (map, stars) = python::module_bindings(&tree.text, tree.root());
    let names = map
        .iter()
        .map(|(k, b)| {
            let (origins, local) = b.parts();
            (k.clone(), PythonBinding { origins, local })
        })
        .collect();
    Some(PythonModule { names, stars })
}

/// The names a Python module exports through a literal top-level `__all__` (list or tuple of
/// strings, also `+=` extensions), or `None` when there is none or it is not statically known
/// (ticket G68NRS1): the caller then treats every public name as exported.
pub fn python_all(source: &str) -> Option<std::collections::BTreeSet<String>> {
    let ParseResult::Parsed(tree) = parse(Language::Python, source, &ParseLimits::default()) else {
        return None;
    };
    let src: &str = &tree.text;
    let root = tree.root();
    let mut names = std::collections::BTreeSet::new();
    let mut seen = false;
    let mut c = root.walk();
    for stmt in root.named_children(&mut c) {
        if stmt.kind() != "expression_statement" {
            continue;
        }
        let mut c2 = stmt.walk();
        for e in stmt.named_children(&mut c2) {
            if !matches!(e.kind(), "assignment" | "augmented_assignment") {
                continue;
            }
            let (Some(left), Some(right)) = (
                e.child_by_field_name("left"),
                e.child_by_field_name("right"),
            ) else {
                continue;
            };
            if left.kind() != "identifier" || src[left.byte_range()] != *"__all__" {
                continue;
            }
            seen = true;
            if !matches!(right.kind(), "list" | "tuple") {
                tracing::debug!("canon: __all__ is not a literal list");
                return None;
            }
            let mut c3 = right.walk();
            for item in right.named_children(&mut c3) {
                if item.kind() != "string" {
                    return None;
                }
                let raw = &src[item.byte_range()];
                let body = raw.trim_start_matches(|ch: char| ch.is_ascii_alphabetic());
                let q = body.chars().next().filter(|q| *q == '"' || *q == '\'')?;
                names.insert(body.trim_matches(q).to_owned());
            }
        }
    }
    seen.then_some(names)
}

/// Every import-resolved call and function-valued reference in `source`, in source order.
/// `language` is the adapter tag (`rust`, `python`, or a `typescript`/`csharp` family tag, where
/// only name-computed lookups are reported); other languages and unparsable files give nothing.
pub fn path_uses(language: &str, source: &str) -> Vec<PathUse> {
    let lang = match language {
        "rust" => Language::Rust,
        "python" => Language::Python,
        "typescript" => Language::TypeScript,
        "tsx" => Language::Tsx,
        "javascript" => Language::JavaScript,
        "jsx" => Language::Jsx,
        "csharp" => Language::CSharp,
        _ => return Vec::new(),
    };
    let ParseResult::Parsed(tree) = parse(lang, source, &ParseLimits::default()) else {
        tracing::debug!(language, "canon: file not parsed, no path uses");
        return Vec::new();
    };
    let mut out = match lang {
        Language::Rust => rust::scan(&tree.text, tree.root()),
        Language::Python => python::scan(&tree.text, tree.root()),
        _ => crate::lookups::scan(language, &tree.text, tree.root()),
    };
    out.sort_by_key(|u| u.offset);
    out.dedup_by(|a, b| a.offset == b.offset && a.path == b.path);
    tracing::debug!(language, uses = out.len(), "canon: path uses scanned");
    out
}

mod rust {
    use super::{
        BTreeMap, Binding, EXTERN_ROOT, EXTERNAL_ROOTS, MAX_ALIAS_DEPTH, Node, PathUse, bind, line,
        text,
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

    /// The module paths a `use` argument imports every item of (`use libc::*` -> `libc`).
    fn use_globs(src: &str, n: Node<'_>, prefix: &str, out: &mut Vec<String>) {
        let join = |tail: &str| {
            if prefix.is_empty() {
                tail.to_owned()
            } else {
                format!("{prefix}::{tail}")
            }
        };
        let clean = |s: &str| s.split_whitespace().collect::<String>();
        match n.kind() {
            "use_wildcard" => {
                let mut c = n.walk();
                let base = n.named_children(&mut c).next().map_or_else(
                    || prefix.to_owned(),
                    |p| join(clean(text(src, p)).trim_start_matches("::")),
                );
                out.push(base);
            }
            "scoped_use_list" => {
                let base = n.child_by_field_name("path").map_or_else(
                    || prefix.to_owned(),
                    |p| join(clean(text(src, p)).trim_start_matches("::")),
                );
                if let Some(list) = n.child_by_field_name("list") {
                    use_globs(src, list, &base, out);
                }
            }
            "use_list" => {
                let mut c = n.walk();
                for ch in n.named_children(&mut c) {
                    use_globs(src, ch, prefix, out);
                }
            }
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
                "foreign_mod_item" => {
                    // every function and static the block declares is a foreign symbol
                    let mut cc = ch.walk();
                    let decls: Vec<_> = ch
                        .child_by_field_name("body")
                        .into_iter()
                        .flat_map(|b| b.named_children(&mut cc).collect::<Vec<_>>())
                        .collect();
                    for d in decls {
                        if matches!(d.kind(), "function_signature_item" | "static_item")
                            && let Some(name) = d.child_by_field_name("name")
                        {
                            let n = text(src, name);
                            bind(
                                &mut map,
                                n,
                                Binding::Alias(format!("{EXTERN_ROOT}::{n}"), false),
                            );
                        }
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
                | "function_signature_item" => {
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
        /// A glob import names no item locally, so every use it may bring in is unresolved: the
        /// module is recorded as a computed use under its path (ticket S3EC85S).
        fn emit_globs(&mut self, decl: Node<'_>) {
            let Some(arg) = decl.child_by_field_name("argument") else {
                return;
            };
            let mut globs = Vec::new();
            use_globs(self.src, arg, "", &mut globs);
            for full in globs {
                if full.is_empty()
                    || matches!(full.split("::").next(), Some("crate" | "self" | "super"))
                {
                    continue;
                }
                let at = decl;
                let Some((path, _)) = self.canonical(&full, at, 0) else {
                    continue;
                };
                self.out.push(PathUse {
                    offset: decl.start_byte(),
                    line: line(decl),
                    spelled: format!("{full}::*"),
                    path,
                    call: false,
                    dynamic: false,
                    external_root: true,
                    computed: true,
                    wildcards: Vec::new(),
                    maybe: false,
                });
            }
        }

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
                Some(Binding::Shadow | Binding::Maybe(..)) => None,
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
                computed: false,
                wildcards: Vec::new(),
                maybe: false,
            });
        }

        fn visit(&mut self, n: Node<'_>) {
            match n.kind() {
                "call_expression" => {
                    if let Some(f) = n.child_by_field_name("function") {
                        self.emit(f, true);
                    }
                }
                // `asm!(..)` / `global_asm!(..)`: the macro path is the callee
                "macro_invocation" => {
                    if let Some(m) = n.child_by_field_name("macro") {
                        self.emit(m, true);
                    }
                }
                // an `extern { .. }` block links native symbols whether or not it is called here
                "foreign_mod_item" => {
                    self.out.push(PathUse {
                        offset: n.start_byte(),
                        line: line(n),
                        spelled: EXTERN_ROOT.to_owned(),
                        path: format!("{EXTERN_ROOT}::block"),
                        call: false,
                        dynamic: false,
                        external_root: true,
                        computed: false,
                        wildcards: Vec::new(),
                        maybe: false,
                    });
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
                if k.kind() == "use_declaration" {
                    self.emit_globs(k);
                }
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
    use super::{
        BTreeMap, Binding, COMPUTED, Language, MAX_ALIAS_DEPTH, Node, ParseLimits, ParseResult,
        PathUse, bind, known_prefix, line, parse, text,
    };
    use crate::call_args::Folder;
    use gob_ir::name_lookup::{Resolved, resolve_name};

    /// Builtins whose lookups are modelled; an unshadowed use resolves to `builtins.<name>`.
    const BUILTINS: &[&str] = &[
        "getattr",
        "__import__",
        "vars",
        "globals",
        "locals",
        "eval",
        "exec",
        "compile",
        "open",
    ];

    /// Builtins that are themselves vocabulary callees (spelled bare, `open`): reached through an
    /// alias or `builtins.<name>` they resolve to that bare spelling (ticket 8B9HSHH).
    const CALLEE_BUILTINS: &[&str] = &["open"];

    /// Builtins that evaluate a string as code; a non-constant source is reported (ticket T78E2WZ).
    const DYNAMIC_CODE: &[&str] = &["builtins.eval", "builtins.exec", "builtins.compile"];

    /// Deepest nesting of constant sources re-scanned (`eval("eval('..')")`).
    const MAX_EVAL_DEPTH: usize = 3;

    /// NFKC-normalised text of an identifier or dotted-name node (the interpreter's spelling).
    fn ident(src: &str, n: Node<'_>) -> String {
        crate::python::nfkc(text(src, n)).into_owned()
    }

    /// A use's spelling without whitespace; a pure name chain is NFKC-normalised, strings never.
    fn spelled(src: &str, e: Node<'_>) -> String {
        let t: String = text(src, e).split_whitespace().collect();
        if crate::python::is_name_chain(e) {
            crate::python::nfkc(&t).into_owned()
        } else {
            t
        }
    }

    /// The module-level bindings of a Python syntax tree and the modules of its `from m import *`.
    pub(super) fn module_bindings(
        src: &str,
        root: Node<'_>,
    ) -> (BTreeMap<String, Binding>, Vec<String>) {
        let mut cx = Cx {
            src,
            fold: Folder::python(src, root),
            scopes: Vec::new(),
            stars: Vec::new(),
            out: Vec::new(),
            depth: 0,
        };
        cx.run(root);
        let map = cx.scopes.pop().map(|s| s.map).unwrap_or_default();
        (map, cx.stars)
    }

    /// Scans a Python syntax tree.
    pub(super) fn scan(src: &str, root: Node<'_>) -> Vec<PathUse> {
        let mut cx = Cx {
            src,
            fold: Folder::python(src, root),
            scopes: Vec::new(),
            stars: Vec::new(),
            out: Vec::new(),
            depth: 0,
        };
        cx.run(root);
        cx.out
    }

    #[derive(Clone)]
    struct Scope {
        map: BTreeMap<String, Binding>,
        /// A class body: invisible to the functions nested in it.
        class: bool,
    }

    struct Cx<'s> {
        src: &'s str,
        /// Folds a lookup's name argument (literals, `+`, module constants) to a static value.
        fold: Folder<'s>,
        scopes: Vec<Scope>,
        /// Modules of every `from m import *` in the file, as written, in source order (ticket
        /// G68NRS1). A name no scope binds may come from any of them.
        stars: Vec<String>,
        out: Vec<PathUse>,
        /// Nesting of the constant `eval` source being scanned (0 for the file itself).
        depth: usize,
    }

    /// The identifiers bound by an assignment target or parameter list.
    fn names_in(src: &str, n: Node<'_>, out: &mut Vec<String>) {
        match n.kind() {
            "identifier" => out.push(ident(src, n)),
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
                    let full = Binding::Alias(ident(src, nm), false);
                    bind(map, &ident(src, al), full);
                }
            } else {
                let full = ident(src, ch);
                let head = full.split('.').next().unwrap_or(&full);
                bind(map, head, Binding::Alias(head.to_owned(), false));
            }
        }
    }

    /// Binds the names of a `from m import n [as x]` statement.
    fn collect_import_from(src: &str, n: Node<'_>, map: &mut BTreeMap<String, Binding>) {
        let module = n
            .child_by_field_name("module_name")
            .map(|m| ident(src, m))
            .unwrap_or_default();
        let mut c = n.walk();
        for ch in n.children_by_field_name("name", &mut c) {
            let (local, member) = if ch.kind() == "aliased_import" {
                let (Some(nm), Some(al)) = (
                    ch.child_by_field_name("name"),
                    ch.child_by_field_name("alias"),
                ) else {
                    continue;
                };
                (ident(src, al), ident(src, nm))
            } else {
                (ident(src, ch), ident(src, ch))
            };
            // a relative module keeps its dots (`.helpers.r`): the consumer resolves it against the
            // repository (ticket 01M6422ZN7HKF98JDAP7XKRQQ2)
            let full = if module.ends_with('.') {
                format!("{module}{member}")
            } else {
                format!("{module}.{member}")
            };
            bind(map, &local, Binding::Alias(full, false));
        }
    }

    /// Records the module of each `from m import *` under `n` (relative modules keep their dots).
    fn collect_stars(src: &str, n: Node<'_>, out: &mut Vec<String>) {
        if n.kind() == "import_from_statement" {
            let mut c = n.walk();
            if n.children(&mut c).any(|k| k.kind() == "wildcard_import") {
                let module = n
                    .child_by_field_name("module_name")
                    .map(|m| ident(src, m))
                    .unwrap_or_default();
                tracing::debug!(module, line = line(n), "canon: wildcard import");
                out.push(module);
            }
            return;
        }
        if matches!(
            n.kind(),
            "function_definition" | "class_definition" | "lambda"
        ) {
            return; // a wildcard import is only legal at module level
        }
        let mut c = n.walk();
        let kids: Vec<_> = n.children(&mut c).collect();
        for k in kids {
            collect_stars(src, k, out);
        }
    }

    /// The dotted spelling of a name or attribute chain whose root is a plain identifier.
    fn dotted(src: &str, e: Node<'_>) -> Option<(String, String)> {
        match e.kind() {
            "identifier" => {
                let t = ident(src, e);
                Some((t.clone(), t))
            }
            "attribute" => {
                let (root, p) = dotted(src, e.child_by_field_name("object")?)?;
                let attr = ident(src, e.child_by_field_name("attribute")?);
                Some((root, format!("{p}.{attr}")))
            }
            _ => None,
        }
    }

    impl Cx<'_> {
        /// A use whose root name no scope binds while `from m import *` is in force: the bare
        /// dotted name, with the candidate modules for the consumer to resolve (ticket G68NRS1).
        fn emit_star(&mut self, e: Node<'_>, call: bool) {
            if self.stars.is_empty() {
                return;
            }
            let Some((root, path)) = dotted(self.src, e) else {
                return;
            };
            if self.lookup(&root).is_some()
                || root == "__builtins__"
                || BUILTINS.contains(&root.as_str())
            {
                return;
            }
            tracing::debug!(path, line = line(e), "canon: name from a wildcard import");
            self.out.push(PathUse {
                offset: e.start_byte(),
                line: line(e),
                spelled: spelled(self.src, e),
                path,
                call,
                dynamic: false,
                external_root: false,
                computed: false,
                wildcards: self.stars.clone(),
                maybe: false,
            });
        }

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
                        bind(map, &ident(src, nm), Binding::Shadow);
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
                            let name = ident(src, left);
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
                "identifier" => {
                    let name = ident(self.src, e);
                    let name = name.as_str();
                    match self.lookup(name) {
                        Some(Binding::Alias(p, d)) => Some((p.clone(), *d)),
                        Some(Binding::Shadow | Binding::Maybe(..)) => None,
                        None if name == "__builtins__" => Some(("builtins".to_owned(), false)),
                        None => BUILTINS
                            .contains(&name)
                            .then(|| (format!("builtins.{name}"), false)),
                    }
                }
                "parenthesized_expression" => {
                    let mut c = e.walk();
                    let inner = e.named_children(&mut c).next()?;
                    self.resolve(inner, depth + 1)
                }
                "subscript" => self.resolve_index(e, depth),
                "attribute" => {
                    let obj = e.child_by_field_name("object")?;
                    let attr = e.child_by_field_name("attribute")?;
                    let (p, d) = self.resolve(obj, depth + 1)?;
                    Some((format!("{p}.{}", ident(self.src, attr)), d))
                }
                "call" => self.resolve_dynamic(e, depth),
                _ => None,
            }
        }

        /// The name argument `arg` as a path segment: its literal value, or [`COMPUTED`] when the
        /// shared gob-ir rule says it is not a single literal.
        fn name_of(&self, arg: Node<'_>) -> String {
            match resolve_name(&self.fold.fold(arg)) {
                Resolved::Literal(s) => s,
                Resolved::Unresolved(gap) => {
                    tracing::debug!(?gap, line = line(arg), "canon: computed lookup name");
                    COMPUTED.to_owned()
                }
            }
        }

        /// `getattr(mod, name)`, `importlib.import_module(name)` and `__import__(name)`: the
        /// symbol a literal name denotes, or a [`COMPUTED`] segment for any other name.
        fn resolve_dynamic(&self, call: Node<'_>, depth: usize) -> Option<(String, bool)> {
            let f = call.child_by_field_name("function")?;
            let args = call.child_by_field_name("arguments")?;
            let mut c = args.walk();
            let args: Vec<Node<'_>> = args.named_children(&mut c).collect();
            let (p, _) = self.resolve(f, depth + 1)?;
            match p.as_str() {
                "builtins.getattr" if args.len() >= 2 => {
                    let (obj, _) = self.resolve(args[0], depth + 1)?;
                    Some((format!("{obj}.{}", self.name_of(args[1])), true))
                }
                "builtins.__import__" | "importlib.import_module" if !args.is_empty() => {
                    Some((self.name_of(args[0]), true))
                }
                _ => None,
            }
        }

        /// `sys.modules[name]`, `X.__dict__[name]`, `vars(X)[name]` and `globals()[name]` /
        /// `locals()[name]` / `vars()[name]`.
        fn resolve_index(&self, e: Node<'_>, depth: usize) -> Option<(String, bool)> {
            let obj = e.child_by_field_name("value")?;
            let name = self.name_of(e.child_by_field_name("subscript")?);
            if let Some((p, _)) = self.resolve(obj, depth + 1)
                && p == "sys.modules"
            {
                return Some((name, true));
            } else if let Some((p, _)) = self.resolve(obj, depth + 1)
                && p == "builtins"
            {
                return Some((format!("builtins.{name}"), true));
            }
            let namespace = |this: &Self| -> Option<(String, bool)> {
                if name == COMPUTED {
                    return Some((name.clone(), true));
                }
                match this.lookup(&name) {
                    Some(Binding::Alias(p, _)) => Some((p.clone(), true)),
                    None if DYNAMIC_CODE.contains(&format!("builtins.{name}").as_str()) => {
                        Some((format!("builtins.{name}"), true))
                    }
                    _ => None,
                }
            };
            match obj.kind() {
                "attribute"
                    if ident(self.src, obj.child_by_field_name("attribute")?) == "__dict__" =>
                {
                    let (p, _) = self.resolve(obj.child_by_field_name("object")?, depth + 1)?;
                    Some((format!("{p}.{name}"), true))
                }
                "call" => {
                    let (f, _) = self.resolve(obj.child_by_field_name("function")?, depth + 1)?;
                    let mut c = obj.walk();
                    let args: Vec<Node<'_>> = obj
                        .child_by_field_name("arguments")?
                        .named_children(&mut c)
                        .collect();
                    match (f.as_str(), args.len()) {
                        ("builtins.vars", 1) => {
                            let (p, _) = self.resolve(args[0], depth + 1)?;
                            Some((format!("{p}.{name}"), true))
                        }
                        ("builtins.vars" | "builtins.globals" | "builtins.locals", 0) => {
                            namespace(self)
                        }
                        _ => None,
                    }
                }
                _ => None,
            }
        }

        /// Collects the bindings of `root` (twice, so a later alias sees an earlier one) and
        /// visits it.
        fn run(&mut self, root: Node<'_>) {
            self.scopes.push(Scope {
                map: BTreeMap::new(),
                class: false,
            });
            collect_stars(self.src, root, &mut self.stars);
            for _ in 0..2 {
                let map = self.collect(root, &[]);
                if let Some(s) = self.scopes.last_mut() {
                    s.map = map;
                }
            }
            self.visit(root);
        }

        /// The source argument of the call whose function node is `f`: the first positional
        /// argument, else a `source=` / `expression=` keyword. `None` when it cannot be seen.
        fn source_arg<'t>(f: Node<'t>) -> Option<Node<'t>> {
            let call = f
                .parent()
                .filter(|p| p.kind() == "call" && p.child_by_field_name("function") == Some(f))?;
            let args = call.child_by_field_name("arguments")?;
            let mut c = args.walk();
            let kids: Vec<Node<'t>> = args
                .named_children(&mut c)
                .filter(|k| k.kind() != "comment")
                .collect();
            let first = *kids.first()?;
            if !matches!(
                first.kind(),
                "keyword_argument" | "list_splat" | "dictionary_splat"
            ) {
                return Some(first);
            }
            None
        }

        /// The keyword form of the source argument (`eval(expression=..)`).
        fn source_keyword<'t>(&self, f: Node<'t>) -> Option<Node<'t>> {
            let call = f
                .parent()
                .filter(|p| p.kind() == "call" && p.child_by_field_name("function") == Some(f))?;
            let args = call.child_by_field_name("arguments")?;
            let mut c = args.walk();
            args.named_children(&mut c)
                .filter(|k| k.kind() == "keyword_argument")
                .find(|k| {
                    k.child_by_field_name("name")
                        .is_some_and(|n| matches!(text(self.src, n), "source" | "expression"))
                })
                .and_then(|k| k.child_by_field_name("value"))
        }

        /// The uses inside the constant code string `code` evaluated at `depth`, resolved
        /// against the scopes in force at the call. `None` when it does not parse cleanly.
        fn scan_code(&self, code: &str) -> Option<Vec<PathUse>> {
            let ParseResult::Parsed(tree) = parse(Language::Python, code, &ParseLimits::default())
            else {
                return None;
            };
            let root = tree.root();
            if root.has_error() {
                return None;
            }
            let mut inner = Cx {
                src: &tree.text,
                fold: Folder::python(&tree.text, root),
                scopes: self.scopes.clone(),
                stars: self.stars.clone(),
                out: Vec::new(),
                depth: self.depth + 1,
            };
            inner.run(root);
            Some(inner.out)
        }

        /// Reports a use of a code-evaluating builtin at `e`: the uses of a constant source,
        /// or an unresolved (computed) use naming the builtin for anything else.
        fn emit_dynamic_code(&mut self, e: Node<'_>, path: &str, call: bool) {
            let spelled: String = spelled(self.src, e);
            let unresolved = |this: &mut Self, why: &str| {
                tracing::debug!(path, line = line(e), why, "canon: unresolved dynamic code");
                let (p, computed) = known_prefix(path.to_owned());
                this.out.push(PathUse {
                    offset: e.start_byte(),
                    line: line(e),
                    spelled: spelled.clone(),
                    path: if computed { p } else { path.to_owned() },
                    call,
                    dynamic: true,
                    external_root: false,
                    computed: true,
                    wildcards: Vec::new(),
                    maybe: false,
                });
            };
            if !call || path == "builtins.?" {
                return unresolved(self, "not a direct call");
            }
            let Some(arg) = Self::source_arg(e).or_else(|| self.source_keyword(e)) else {
                return unresolved(self, "no visible source argument");
            };
            let Resolved::Literal(code) = resolve_name(&self.fold.fold(arg)) else {
                return unresolved(self, "non-constant source");
            };
            if self.depth >= MAX_EVAL_DEPTH {
                return unresolved(self, "nesting too deep");
            }
            let Some(found) = self.scan_code(&code) else {
                return unresolved(self, "source does not parse");
            };
            tracing::debug!(path, uses = found.len(), "canon: constant source scanned");
            for mut u in found {
                u.offset = e.start_byte();
                u.line = line(e);
                u.dynamic = true;
                self.out.push(u);
            }
        }

        /// A use whose root name has several possible bindings in scope: one unproven use per
        /// possible origin (ticket 01M6422ZN7HKF98JDAP7XKRQQ2). False when the root is not so bound.
        fn emit_maybe(&mut self, e: Node<'_>, call: bool) -> bool {
            let Some((root, path)) = dotted(self.src, e) else {
                return false;
            };
            let Some(Binding::Maybe(origins, _)) = self.lookup(&root).cloned() else {
                return false;
            };
            let suffix = &path[root.len()..];
            for origin in origins {
                let path = format!("{origin}{suffix}");
                if !call && !path.contains('.') {
                    continue;
                }
                tracing::debug!(%path, line = line(e), "canon: name with several possible bindings");
                self.out.push(PathUse {
                    offset: e.start_byte(),
                    line: line(e),
                    spelled: spelled(self.src, e),
                    path,
                    call,
                    dynamic: false,
                    external_root: false,
                    computed: false,
                    wildcards: Vec::new(),
                    maybe: true,
                });
            }
            true
        }

        fn emit(&mut self, e: Node<'_>, call: bool) {
            let Some((path, dynamic)) = self.resolve(e, 0) else {
                if !self.emit_maybe(e, call) {
                    self.emit_star(e, call);
                }
                return;
            };
            if path == "builtins.?" || DYNAMIC_CODE.contains(&path.as_str()) {
                self.emit_dynamic_code(e, &path, call);
                return;
            }
            let path = match path.strip_prefix("builtins.") {
                Some(name) if CALLEE_BUILTINS.contains(&name) => {
                    tracing::debug!(name, line = line(e), "canon: builtin callee resolved");
                    name.to_owned()
                }
                Some(_) => return,
                None => path,
            };
            let (path, computed) = known_prefix(path);
            if !call && !dynamic && !path.contains('.') && !CALLEE_BUILTINS.contains(&path.as_str())
            {
                return;
            }
            self.out.push(PathUse {
                offset: e.start_byte(),
                line: line(e),
                spelled: spelled(self.src, e),
                path,
                call,
                dynamic,
                external_root: false,
                computed,
                wildcards: Vec::new(),
                maybe: false,
            });
        }

        /// A function used as a value: an expression in an argument, assignment, return or
        /// container position.
        fn value(&mut self, v: Node<'_>) {
            if matches!(v.kind(), "identifier" | "attribute" | "call" | "subscript") {
                self.emit(v, false);
            }
        }

        /// A name read through an index (`os.environ['X']`) or iterated (`for k in os.environ`)
        /// is a use (ticket 01M6422ZVVSTEKVMY0PR269X33).
        fn read_name(&mut self, n: Node<'_>) {
            let field = if n.kind() == "subscript" {
                "value"
            } else {
                "right"
            };
            if let Some(v) = n.child_by_field_name(field)
                && matches!(v.kind(), "identifier" | "attribute")
            {
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
                "expression_statement" => {
                    // a namespace lookup whose result is discarded (`vars(m)[n]`)
                    let mut c = n.walk();
                    if let Some(v) = n.named_children(&mut c).find(|k| k.kind() == "subscript") {
                        self.emit(v, false);
                    }
                }
                "call" => {
                    if let Some(f) = n.child_by_field_name("function")
                        && matches!(f.kind(), "identifier" | "attribute" | "call" | "subscript")
                    {
                        self.emit(f, true);
                    }
                    // a lookup whose result is discarded (`__import__(n)` as a statement)
                    if n.parent()
                        .is_some_and(|p| p.kind() == "expression_statement")
                    {
                        self.emit(n, false);
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
                "pair" | "default_parameter" | "typed_default_parameter" => {
                    if let Some(v) = n.child_by_field_name("value") {
                        self.value(v);
                    }
                }
                "subscript" | "for_statement" | "for_in_clause" => self.read_name(n),
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
    // frob:ticket 01M6422Z8JGE789ZHW4G68NRS1
    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn python_wildcard_names_carry_their_candidate_modules() {
        let u = path_uses("python", "from os import *\n\ndef f():\n    getenv('X')\n");
        let w = u.iter().find(|u| u.path == "getenv").expect("getenv use");
        assert_eq!(w.wildcards, vec!["os".to_owned()]);
        assert!(w.call && !w.dynamic);
        let u = path_uses(
            "python",
            "from os import *\nfrom .h import *\n\ndef f():\n    getenv('X')\n",
        );
        assert_eq!(u[0].wildcards, vec!["os".to_owned(), ".h".to_owned()]);
    }

    // frob:ticket 01M6422ZVVSTEKVMY0PR269X33
    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn python_indexed_and_iterated_names_are_uses() {
        let u = path_uses(
            "python",
            "import os\nfrom os import environ\n\ndef f():\n    a = os.environ['X']\n    for k in environ:\n        pass\n",
        );
        let n = u
            .iter()
            .filter(|u| u.path == "os.environ" && !u.call)
            .count();
        assert_eq!(n, 2, "{u:?}");
    }

    // frob:ticket 01M6422Z8JGE789ZHW4G68NRS1
    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn python_wildcard_ignores_bound_builtin_and_unimported_names() {
        let src = "from os import *\n\ndef getenv(x):\n    return x\n\ndef f(p):\n    getenv(1)\n    p(2)\n";
        let u = path_uses("python", src);
        assert!(
            u.iter().all(|u| u.path != "getenv" && u.path != "p"),
            "{u:?}"
        );
        let u = path_uses("python", "import os\n\ndef f():\n    os.getenv('X')\n");
        assert!(u.iter().all(|u| u.wildcards.is_empty()), "{u:?}");
    }

    // frob:ticket 01M6422Z8JGE789ZHW4G68NRS1
    // frob:tests crates/gob-symbols/src/canon.rs::python_all
    #[test]
    fn python_all_reads_literal_lists_and_gives_up_otherwise() {
        let a = python_all("__all__ = ['a', \"b\"]\n__all__ += ('c',)\n").unwrap();
        assert_eq!(a.into_iter().collect::<Vec<_>>(), ["a", "b", "c"]);
        assert!(python_all("x = 1\n").is_none());
        assert!(python_all("__all__ = make()\n").is_none());
        assert!(python_all("__all__ = [n for n in dir()]\n").is_none());
    }

    #[test]
    fn rust_extern_block_function_resolves_to_the_extern_root() {
        let src = "extern \"C\" { fn system(c: *const i8) -> i32; }\nfn f(c: *const i8) { unsafe { system(c); } }\n";
        assert!(
            paths("rust", src)
                .iter()
                .any(|(p, call, _)| p == "extern::system" && *call)
        );
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn rust_inline_asm_macro_resolves_through_its_import() {
        let src = "use std::arch::asm;\nfn f() { unsafe { asm!(\"nop\"); } }\n";
        assert!(
            paths("rust", src)
                .iter()
                .any(|(p, _, _)| p == "std::arch::asm")
        );
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn rust_glob_import_is_a_computed_use_of_its_path() {
        let uses = path_uses("rust", "use libc::*;\nfn f() {}\n");
        assert!(
            uses.iter()
                .any(|u| u.path == "libc" && u.spelled == "libc::*" && u.computed)
        );
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn rust_local_module_named_like_an_external_root_resolves_locally() {
        let src = "mod libc { pub fn system(_c: i32) {} }\nfn f() { libc::system(1); }\n";
        assert!(
            paths("rust", src)
                .iter()
                .all(|(p, _, _)| !p.starts_with("libc"))
        );
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

    // frob:ticket 01M6422ZCGB47DJWWY78B9HSHH
    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn python_alias_of_the_open_builtin_resolves_to_open() {
        for src in [
            "def f(p):\n    o = open\n    return o(p)\n",
            "import builtins\ndef f(p):\n    o = builtins.open\n    return o(p)\n",
            "def f(p, o=open):\n    return o(p)\n",
        ] {
            let got = paths("python", src);
            assert!(got.iter().any(|(p, _, _)| p == "open"), "{src}: {got:?}");
        }
        let shadowed = paths(
            "python",
            "def open(p):\n    return p\ndef f(p):\n    o = open\n    return o(p)\n",
        );
        assert!(shadowed.is_empty(), "{shadowed:?}");
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    // frob:ticket 01M6422ZN7HKF98JDAP7XKRQQ2
    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn python_rebound_and_fallback_names_keep_every_origin() {
        let rebound = "def run(x):\n    return x\n\nfrom subprocess import run\n\nrun('ls')\n";
        let u = path_uses("python", rebound);
        let m: Vec<_> = u
            .iter()
            .filter(|u| u.maybe)
            .map(|u| u.path.as_str())
            .collect();
        assert_eq!(m, vec!["subprocess.run"], "{u:?}");
        let tried = "try:\n    from subprocess import run\nexcept ImportError:\n    from shim import run\n\nrun('ls')\n";
        let u = path_uses("python", tried);
        let mut m: Vec<_> = u
            .iter()
            .filter(|u| u.maybe)
            .map(|u| u.path.as_str())
            .collect();
        m.sort_unstable();
        assert_eq!(m, vec!["shim.run", "subprocess.run"], "{u:?}");
        let same = "try:\n    from subprocess import run\nexcept ImportError:\n    from subprocess import run\n\nrun('ls')\n";
        assert!(path_uses("python", same).iter().all(|u| !u.maybe));
    }

    // frob:ticket 01M6422ZN7HKF98JDAP7XKRQQ2
    // frob:tests crates/gob-symbols/src/canon.rs::python_module
    #[test]
    fn python_module_exposes_reexports_and_local_definitions() {
        let src = "from subprocess import run as r\nfrom .a import b\nfrom . import c\nfrom m import *\n\ndef d():\n    pass\n";
        let m = python_module(src).expect("parses");
        assert_eq!(m.names["r"].origins, vec!["subprocess.run".to_owned()]);
        assert_eq!(m.names["b"].origins, vec![".a.b".to_owned()]);
        assert_eq!(m.names["c"].origins, vec![".c".to_owned()]);
        assert!(m.names["d"].local && m.names["d"].origins.is_empty());
        assert_eq!(m.stars, vec!["m".to_owned()]);
    }

    #[test]
    fn unknown_languages_give_nothing() {
        assert!(path_uses("go", "package main").is_empty());
    }
}
