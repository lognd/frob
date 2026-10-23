//! File context shared by the TESTQ detectors: definitions, imports and callee extraction.

// frob:ticket 01M4D957J2HZ655A1H8DJ4K8YD

use std::collections::{HashMap, HashSet};

use tree_sitter::Node;

use super::lang::Lang;
use crate::syntax::{children, text};

/// One call found in a body: the path called, and whether it was a method call on a value.
#[derive(Debug, Clone)]
pub(super) struct Callee<'t> {
    /// Path segments as written (`thread`, `sleep`); a method call holds only the method name.
    pub segs: Vec<String>,
    /// A method call on an unknown receiver (`x.helper()`).
    pub method: bool,
    /// The call node (or the name token for a call inside a macro argument list).
    pub node: Node<'t>,
    /// Found inside a macro token tree, so there is no argument structure to inspect.
    pub tokens: bool,
}

/// What one walk over a body found.
#[derive(Debug, Default)]
pub(super) struct Body<'t> {
    /// An assertion macro, `assert` statement, `raise` or skip was seen directly.
    pub direct: bool,
    /// Every call, in source order.
    pub calls: Vec<Callee<'t>>,
}

/// The definitions, imports and local names of one parsed file.
pub(super) struct Ctx<'t> {
    pub lang: Lang,
    pub src: &'t str,
    /// Function and method definitions by name.
    pub defs: HashMap<String, Vec<Node<'t>>>,
    /// Imported local name to the full path it stands for.
    pub aliases: HashMap<String, Vec<String>>,
    /// Python names imported relatively (`from . import x`).
    pub relative: HashSet<String>,
    /// Glob imports: the module path and whether it was relative.
    pub wildcards: Vec<(Vec<String>, bool)>,
    /// Rust `mod x;` declarations whose body lives in another file.
    pub bodyless_mods: HashSet<String>,
    /// Types, traits, classes and inline modules defined in this file.
    pub local_types: HashSet<String>,
    /// C# `using static Xunit.Assert;`: bare calls without a local definition are assertions.
    pub assert_statics: bool,
}

/// Split `a::b::<T>::c` into its plain segments.
fn split_rust(s: &str) -> Vec<String> {
    s.split("::")
        .map(|p| p.split_whitespace().collect::<String>())
        .filter(|p| !p.is_empty() && !p.contains(['<', '>']))
        .collect()
}

fn split_dots(s: &str) -> Vec<String> {
    s.split('.')
        .map(str::trim)
        .filter(|p| !p.is_empty())
        .map(str::to_owned)
        .collect()
}

impl<'t> Ctx<'t> {
    /// Collect the file-level facts of `root`.
    pub fn build(lang: Lang, root: Node<'t>, src: &'t str) -> Self {
        let mut cx = Self {
            lang,
            src,
            defs: HashMap::new(),
            aliases: HashMap::new(),
            relative: HashSet::new(),
            wildcards: Vec::new(),
            bodyless_mods: HashSet::new(),
            local_types: HashSet::new(),
            assert_statics: false,
        };
        cx.collect(root);
        tracing::debug!(
            defs = cx.defs.len(),
            aliases = cx.aliases.len(),
            "testq file context built"
        );
        cx
    }

    fn name_of(&self, n: Node<'t>) -> Option<String> {
        n.child_by_field_name("name")
            .map(|x| text(x, self.src).to_owned())
    }

    fn collect(&mut self, n: Node<'t>) {
        match (self.lang, n.kind()) {
            (Lang::Rust, "function_item")
            | (Lang::Python, "function_definition")
            | (Lang::Script, "function_declaration" | "method_definition")
            | (Lang::CSharp, "method_declaration" | "local_function_statement") => {
                if let Some(name) = self.name_of(n) {
                    self.defs.entry(name).or_default().push(n);
                }
            }
            (Lang::Rust, "use_declaration") => {
                if let Some(arg) = n.child_by_field_name("argument") {
                    self.use_tree(arg, &[]);
                }
            }
            (Lang::Rust, "mod_item") => {
                if let Some(name) = self.name_of(n) {
                    if n.child_by_field_name("body").is_none() {
                        self.bodyless_mods.insert(name);
                    } else {
                        self.local_types.insert(name);
                    }
                }
            }
            (
                Lang::Rust,
                "struct_item" | "enum_item" | "trait_item" | "union_item" | "type_item",
            )
            | (Lang::Python, "class_definition")
            | (Lang::Script, "class_declaration")
            | (
                Lang::CSharp,
                "class_declaration"
                | "struct_declaration"
                | "record_declaration"
                | "interface_declaration"
                | "enum_declaration",
            ) => {
                if let Some(name) = self.name_of(n) {
                    self.local_types.insert(name);
                }
            }
            (Lang::Script, "variable_declarator") => self.js_declarator(n),
            (Lang::Script, "import_statement") => self.js_import(n),
            (Lang::CSharp, "using_directive") => self.cs_using(n),
            (Lang::Python, "import_statement") => self.py_import(n),
            (Lang::Python, "import_from_statement") => self.py_from(n),
            _ => {}
        }
        for c in children(n) {
            self.collect(c);
        }
    }

    fn use_tree(&mut self, n: Node<'t>, prefix: &[String]) {
        let full = |segs: Vec<String>| {
            let mut p = prefix.to_vec();
            p.extend(segs);
            p
        };
        match n.kind() {
            "identifier" => {
                let name = text(n, self.src).to_owned();
                self.aliases.insert(name.clone(), full(vec![name]));
            }
            "self" => {
                if let Some(last) = prefix.last() {
                    self.aliases.insert(last.clone(), prefix.to_vec());
                }
            }
            "scoped_identifier" => {
                let segs = full(split_rust(text(n, self.src)));
                if let Some(last) = segs.last() {
                    self.aliases.insert(last.clone(), segs.clone());
                }
            }
            "use_as_clause" => {
                let path = n.child_by_field_name("path");
                let alias = n.child_by_field_name("alias");
                if let (Some(p), Some(a)) = (path, alias) {
                    let segs = full(split_rust(text(p, self.src)));
                    self.aliases.insert(text(a, self.src).to_owned(), segs);
                }
            }
            "scoped_use_list" => {
                let np = n
                    .child_by_field_name("path")
                    .map_or_else(|| prefix.to_vec(), |p| full(split_rust(text(p, self.src))));
                if let Some(list) = n.child_by_field_name("list") {
                    for c in children(list).into_iter().filter(Node::is_named) {
                        self.use_tree(c, &np);
                    }
                }
            }
            "use_list" => {
                for c in children(n).into_iter().filter(Node::is_named) {
                    self.use_tree(c, prefix);
                }
            }
            "use_wildcard" => {
                let t = text(n, self.src).trim_end_matches('*');
                let segs = full(split_rust(t));
                self.wildcards.push((segs, false));
            }
            _ => {}
        }
    }

    fn py_import(&mut self, n: Node<'t>) {
        for c in children(n).into_iter().filter(Node::is_named) {
            match c.kind() {
                "dotted_name" => {
                    let segs = split_dots(text(c, self.src));
                    if let Some(first) = segs.first() {
                        self.aliases.insert(first.clone(), vec![first.clone()]);
                    }
                }
                "aliased_import" => self.py_aliased(c, &[], false),
                _ => {}
            }
        }
    }

    fn py_aliased(&mut self, c: Node<'t>, module: &[String], rel: bool) {
        let name = c.child_by_field_name("name");
        let alias = c.child_by_field_name("alias");
        if let (Some(nm), Some(al)) = (name, alias) {
            let mut segs = module.to_vec();
            segs.extend(split_dots(text(nm, self.src)));
            let local = text(al, self.src).to_owned();
            if rel {
                self.relative.insert(local.clone());
            }
            self.aliases.insert(local, segs);
        }
    }

    fn py_from(&mut self, n: Node<'t>) {
        let module_node = n.child_by_field_name("module_name");
        let rel = module_node.is_some_and(|m| m.kind() == "relative_import");
        let module = module_node
            .map(|m| split_dots(text(m, self.src)))
            .unwrap_or_default();
        let mut cur = n.walk();
        let names: Vec<Node<'t>> = n.children_by_field_name("name", &mut cur).collect();
        for c in names {
            match c.kind() {
                "dotted_name" => {
                    let local = text(c, self.src).to_owned();
                    let mut segs = module.clone();
                    segs.push(local.clone());
                    if rel {
                        self.relative.insert(local.clone());
                    }
                    self.aliases.insert(local, segs);
                }
                "aliased_import" => self.py_aliased(c, &module, rel),
                _ => {}
            }
        }
        if children(n).iter().any(|c| c.kind() == "wildcard_import") {
            self.wildcards.push((module, rel));
        }
    }

    /// Bind `local` to the module `source` (and `member` of it, when given).
    fn js_bind(&mut self, local: String, source: &str, member: Option<String>) {
        let mut segs = module_segs(source);
        segs.extend(member);
        if support_path(source) {
            self.relative.insert(local.clone());
        }
        self.aliases.insert(local, segs);
    }

    fn js_import(&mut self, n: Node<'t>) {
        let Some(source) = n.child_by_field_name("source") else {
            return;
        };
        let source = unquote(text(source, self.src)).to_owned();
        for clause in children(n)
            .into_iter()
            .filter(|c| c.kind() == "import_clause")
        {
            for c in children(clause).into_iter().filter(Node::is_named) {
                match c.kind() {
                    "identifier" => self.js_bind(text(c, self.src).to_owned(), &source, None),
                    "namespace_import" => {
                        if let Some(id) = children(c).into_iter().find(|x| x.kind() == "identifier")
                        {
                            self.js_bind(text(id, self.src).to_owned(), &source, None);
                        }
                    }
                    "named_imports" => {
                        for spec in children(c)
                            .into_iter()
                            .filter(|x| x.kind() == "import_specifier")
                        {
                            let name = spec.child_by_field_name("name");
                            let alias = spec.child_by_field_name("alias").or(name);
                            if let (Some(nm), Some(al)) = (name, alias) {
                                let member = text(nm, self.src).to_owned();
                                self.js_bind(text(al, self.src).to_owned(), &source, Some(member));
                            }
                        }
                    }
                    _ => {}
                }
            }
        }
    }

    /// A `const x = () => ...` definition, or a `const x = require('m')` import.
    fn js_declarator(&mut self, n: Node<'t>) {
        let (Some(name), Some(value)) = (
            n.child_by_field_name("name"),
            n.child_by_field_name("value"),
        ) else {
            return;
        };
        match value.kind() {
            "arrow_function" | "function_expression" | "function"
                if name.kind() == "identifier" =>
            {
                self.defs
                    .entry(text(name, self.src).to_owned())
                    .or_default()
                    .push(value);
            }
            "call_expression" => {
                let is_require = value
                    .child_by_field_name("function")
                    .is_some_and(|f| text(f, self.src) == "require");
                let arg = value
                    .child_by_field_name("arguments")
                    .and_then(|a| children(a).into_iter().find(|c| c.kind() == "string"));
                let (true, Some(arg)) = (is_require, arg) else {
                    return;
                };
                let source = unquote(text(arg, self.src)).to_owned();
                match name.kind() {
                    "identifier" => self.js_bind(text(name, self.src).to_owned(), &source, None),
                    "object_pattern" => {
                        for p in children(name).into_iter().filter(Node::is_named) {
                            match p.kind() {
                                "shorthand_property_identifier_pattern" => {
                                    let id = text(p, self.src).to_owned();
                                    self.js_bind(id.clone(), &source, Some(id));
                                }
                                "pair_pattern" => {
                                    let key = p.child_by_field_name("key");
                                    let val = p.child_by_field_name("value");
                                    if let (Some(k), Some(v)) = (key, val) {
                                        let member = text(k, self.src).to_owned();
                                        self.js_bind(
                                            text(v, self.src).to_owned(),
                                            &source,
                                            Some(member),
                                        );
                                    }
                                }
                                _ => {}
                            }
                        }
                    }
                    _ => {}
                }
            }
            _ => {}
        }
    }

    fn cs_using(&mut self, n: Node<'t>) {
        let kids = children(n);
        let target = kids
            .iter()
            .rev()
            .find(|c| matches!(c.kind(), "qualified_name" | "identifier"));
        let Some(target) = target else { return };
        let segs = split_dots(text(*target, self.src));
        if let Some(alias) = n.child_by_field_name("name") {
            self.aliases.insert(text(alias, self.src).to_owned(), segs);
            return;
        }
        let is_static = kids.iter().any(|c| c.kind() == "static");
        let last = segs.last().map(String::as_str).unwrap_or_default();
        if is_static && super::assert::CS_ASSERT_TYPES.contains(&last) {
            self.assert_statics = true;
        } else {
            self.wildcards.push((segs, false));
        }
    }

    /// `segs` with its first segment replaced by what it was imported as.
    pub fn expand(&self, segs: &[String]) -> Vec<String> {
        match segs.first().and_then(|f| self.aliases.get(f)) {
            Some(full) => full.iter().chain(&segs[1..]).cloned().collect(),
            None => segs.to_vec(),
        }
    }

    /// The callee of a call node, when its shape is a name, a path or a method call.
    pub fn callee(&self, call: Node<'t>) -> Option<Callee<'t>> {
        let mut f = call.child_by_field_name("function")?;
        let (segs, method) = match self.lang {
            Lang::Script | Lang::CSharp => {
                let segs = self.chain(f);
                let method = segs.first().is_some_and(|s| s == "?");
                (segs, method)
            }
            Lang::Rust => {
                while f.kind() == "generic_function" {
                    f = f.child_by_field_name("function")?;
                }
                match f.kind() {
                    "identifier" => (vec![text(f, self.src).to_owned()], false),
                    "scoped_identifier" => (split_rust(text(f, self.src)), false),
                    "field_expression" => {
                        let name = f.child_by_field_name("field")?;
                        (vec![text(name, self.src).to_owned()], true)
                    }
                    _ => return None,
                }
            }
            Lang::Python => match f.kind() {
                "identifier" => (vec![text(f, self.src).to_owned()], false),
                "attribute" => {
                    if let Some(s) = self.py_chain(f) {
                        (s, false)
                    } else {
                        let a = f.child_by_field_name("attribute")?;
                        (vec![text(a, self.src).to_owned()], true)
                    }
                }
                _ => return None,
            },
        };
        if segs.is_empty() {
            return None;
        }
        Some(Callee {
            segs,
            method,
            node: call,
            tokens: false,
        })
    }

    /// The dotted path a call target spells, with `?` for a part that is not a plain name.
    ///
    /// `expect(x).not.toBe` flattens to `expect.not.toBe`, `x.Should().Be` to `x.Should.Be`.
    fn chain(&self, n: Node<'t>) -> Vec<String> {
        let here = |t: &str| vec![t.to_owned()];
        match n.kind() {
            "identifier" | "this" | "super" | "this_expression" | "base_expression" => {
                here(text(n, self.src))
            }
            "generic_name" => children(n)
                .into_iter()
                .find(|c| c.kind() == "identifier")
                .map_or_else(|| here("?"), |c| here(text(c, self.src))),
            "member_expression" | "member_access_expression" => {
                let obj = n
                    .child_by_field_name("object")
                    .or_else(|| n.child_by_field_name("expression"));
                let prop = n
                    .child_by_field_name("property")
                    .or_else(|| n.child_by_field_name("name"));
                let mut segs = match obj {
                    Some(o) => self.chain(o),
                    // `base.Run()`: the keyword is an anonymous token, not a field.
                    None => here(text(n, self.src).split('.').next().unwrap_or("?").trim()),
                };
                segs.extend(prop.map_or_else(|| here("?"), |p| self.chain(p)));
                segs
            }
            "subscript_expression" | "element_access_expression" => {
                let mut segs = n
                    .child_by_field_name("object")
                    .or_else(|| n.child_by_field_name("expression"))
                    .map_or_else(|| here("?"), |o| self.chain(o));
                segs.push("?".to_owned());
                segs
            }
            "property_identifier" | "private_property_identifier" => here(text(n, self.src)),
            "call_expression" | "invocation_expression" => n
                .child_by_field_name("function")
                .map_or_else(|| here("?"), |f| self.chain(f)),
            "await_expression"
            | "parenthesized_expression"
            | "non_null_expression"
            | "as_expression"
            | "postfix_unary_expression"
            | "conditional_access_expression" => children(n)
                .into_iter()
                .find(Node::is_named)
                .map_or_else(|| here("?"), |c| self.chain(c)),
            _ => here("?"),
        }
    }

    fn py_chain(&self, n: Node<'t>) -> Option<Vec<String>> {
        let attr = text(n.child_by_field_name("attribute")?, self.src).to_owned();
        let obj = n.child_by_field_name("object")?;
        let mut base = match obj.kind() {
            "identifier" => vec![text(obj, self.src).to_owned()],
            "attribute" => self.py_chain(obj)?,
            _ => return None,
        };
        base.push(attr);
        Some(base)
    }

    /// Walk `n`, collecting calls and noting direct assertions.
    pub fn scan_body(&self, n: Node<'t>) -> Body<'t> {
        let mut b = Body::default();
        self.walk(n, &mut b);
        b
    }

    fn walk(&self, n: Node<'t>, b: &mut Body<'t>) {
        match (self.lang, n.kind()) {
            (Lang::Rust, "macro_invocation") => {
                if let Some(m) = n.child_by_field_name("macro") {
                    let name = text(m, self.src).rsplit("::").next().unwrap_or_default();
                    if super::assert::macro_asserts(name) {
                        b.direct = true;
                    }
                }
                for c in children(n) {
                    if c.kind() == "token_tree" {
                        self.tokens(c, b);
                    }
                }
                return;
            }
            (Lang::Rust | Lang::Script, "call_expression")
            | (Lang::Python, "call")
            | (Lang::CSharp, "invocation_expression") => {
                if let Some(c) = self.callee(n) {
                    b.calls.push(c);
                }
            }
            (Lang::Python, "assert_statement" | "raise_statement") => b.direct = true,
            // chai/should.js: `x.should.equal(1)` or a bare `x.should.be.true`.
            (Lang::Script, "member_expression")
                if n.child_by_field_name("property")
                    .is_some_and(|p| text(p, self.src) == "should") =>
            {
                b.direct = true;
            }
            _ => {}
        }
        for c in children(n) {
            self.walk(c, b);
        }
    }

    fn tokens(&self, tt: Node<'t>, b: &mut Body<'t>) {
        let kids = children(tt);
        for (i, k) in kids.iter().enumerate() {
            match k.kind() {
                "token_tree" => self.tokens(*k, b),
                "identifier" => {
                    let name = text(*k, self.src);
                    let next = kids.get(i + 1);
                    match next.map(Node::kind) {
                        Some("!") => {
                            if super::assert::macro_asserts(name) {
                                b.direct = true;
                            }
                        }
                        Some("token_tree")
                            if text(*next.unwrap_or(k), self.src).starts_with('(') =>
                        {
                            b.calls.push(Callee {
                                segs: vec![name.to_owned()],
                                method: i > 0 && kids[i - 1].kind() == ".",
                                node: *k,
                                tokens: true,
                            });
                        }
                        _ => {}
                    }
                }
                _ => {}
            }
        }
    }
}

/// The text of a JS string literal without its quotes.
fn unquote(s: &str) -> &str {
    s.trim_matches(['"', '\'', '`'])
}

/// The plain path components of a module specifier (`node:assert/strict` -> `assert`, `strict`).
fn module_segs(source: &str) -> Vec<String> {
    let bare = source.strip_prefix("node:").unwrap_or(source);
    bare.split(std::path::is_separator)
        .filter(|p| !p.is_empty() && *p != "." && *p != "..")
        .map(str::to_owned)
        .collect()
}

/// Directory names that mark a relative import as test support rather than the code under test.
const SUPPORT_DIRS: &[&str] = &["test", "tests", "__tests__", "__mocks__", "mocks", "e2e"];

/// True when a relative import reaches into test-support code, whose body is out of sight.
///
/// Importing the unit under test (`./add`) is not a helper: its calls are not assertions and
/// must not turn every test into Unresolved.
fn support_path(source: &str) -> bool {
    source.starts_with('.')
        && module_segs(source)
            .iter()
            .any(|s| SUPPORT_DIRS.contains(&s.as_str()) || super::assert::helper_word(s))
}
