//! The JavaScript/TypeScript scanner (also JSX and TSX): imports, `require`, destructuring and
//! member chains over the tree-sitter-javascript and tree-sitter-typescript trees.

// frob:ticket 01M5XMR67K19SFAWNTDJKKJPTT

use tree_sitter::Node;

use super::catalogue::{ArgInfo, Args};
use super::engine::{Binding, FileScan, Lit, State, SymPath, kids};

/// Global-object spellings stripped from the head of a path (`globalThis.console` is `console`).
const GLOBAL_HEADS: &[&str] = &["globalThis", "window", "self", "global"];

/// Heads whose aliases are always kept (`const r = require`, `const e = eval`, `const get = Reflect.get`).
const DYNAMIC_HEADS: &[&str] = &["require", "eval", "Function", "Reflect"];

/// `vm` entry points that run code built from a string.
const VM_RUNNERS: &[&str] = &[
    "runInThisContext",
    "runInContext",
    "runInNewContext",
    "compileFunction",
    "Script",
];

/// Reflective accessors that hand back a member without naming it in a way the scanner can follow.
const REFLECTIVE: &[(&str, &str)] = &[
    ("Reflect", "getOwnPropertyDescriptor"),
    ("Object", "getOwnPropertyDescriptor"),
    ("Object", "getOwnPropertyDescriptors"),
];

/// Node kinds that introduce a function scope.
const FUNCTIONS: &[&str] = &[
    "function_declaration",
    "function_expression",
    "function",
    "generator_function",
    "generator_function_declaration",
    "arrow_function",
    "method_definition",
];

/// Scan one parsed JavaScript or TypeScript module.
pub fn scan(mut st: State<'_>, root: Node<'_>) -> FileScan {
    scope(&mut st, root);
    st.finish()
}

fn scope(st: &mut State<'_>, parent: Node<'_>) {
    let items = kids(parent);
    for c in &items {
        pre_import(st, *c);
    }
    let mut deferred = Vec::new();
    for c in items {
        visit(st, c, &mut deferred);
    }
    for f in deferred {
        run_function(st, f);
    }
}

fn pre_import(st: &mut State<'_>, n: Node<'_>) {
    match n.kind() {
        "import_statement" => do_import(st, n),
        "function_declaration" | "generator_function_declaration" | "class_declaration" => {
            if let Some(name) = n.child_by_field_name("name") {
                let name = st.txt(name).to_owned();
                st.bind(&name, Binding::Opaque);
            }
        }
        _ => {}
    }
}

fn run_function(st: &mut State<'_>, f: Node<'_>) {
    st.push();
    if (f.kind() == "function_expression" || f.kind() == "function")
        && let Some(name) = f.child_by_field_name("name")
    {
        let name = st.txt(name).to_owned();
        st.bind(&name, Binding::Opaque);
    }
    let mut d = Vec::new();
    for field in ["parameters", "parameter"] {
        if let Some(p) = f.child_by_field_name(field) {
            bind_pattern(st, p, &mut d);
        }
    }
    if let Some(body) = f.child_by_field_name("body") {
        if body.kind() == "statement_block" {
            scope(st, body);
        } else {
            visit(st, body, &mut d);
        }
    }
    for g in d {
        run_function(st, g);
    }
    st.pop();
}

/// Bind every name a pattern introduces as a local; a default value that names an output symbol
/// makes the name an alias of it (`function f(log = console.log)`).
fn bind_pattern<'t>(st: &mut State<'_>, n: Node<'t>, d: &mut Vec<Node<'t>>) {
    match n.kind() {
        "identifier" | "shorthand_property_identifier_pattern" => {
            let name = st.txt(n).to_owned();
            st.bind(&name, Binding::Opaque);
        }
        "type_annotation" | "property_identifier" | "string" | "number" => {}
        "pair_pattern" => {
            if let Some(v) = n.child_by_field_name("value") {
                bind_pattern(st, v, d);
            }
        }
        "assignment_pattern" | "object_assignment_pattern" => {
            if let (Some(l), Some(r)) = (
                n.child_by_field_name("left"),
                n.child_by_field_name("right"),
            ) {
                bind_default(st, l, r, d);
            }
        }
        "required_parameter" | "optional_parameter" => {
            match (
                n.child_by_field_name("pattern"),
                n.child_by_field_name("value"),
            ) {
                (Some(l), Some(r)) => bind_default(st, l, r, d),
                (Some(l), None) => bind_pattern(st, l, d),
                _ => {}
            }
        }
        _ => {
            for c in kids(n) {
                bind_pattern(st, c, d);
            }
        }
    }
}

/// Bind `target = default`: an identifier whose default resolves to an output symbol aliases it.
fn bind_default<'t>(
    st: &mut State<'_>,
    target: Node<'t>,
    default: Node<'t>,
    d: &mut Vec<Node<'t>>,
) {
    if target.kind() == "object_pattern"
        && let Some(p) = path_of(st, default, false).filter(|p| explicit(st, p))
    {
        destructure(st, target, Some(&p), d);
        return;
    }
    let alias = matches!(
        target.kind(),
        "identifier" | "shorthand_property_identifier_pattern"
    )
    .then(|| path_of(st, default, false))
    .flatten()
    .filter(|p| explicit(st, p));
    if let Some(p) = alias {
        tracing::debug!(target = st.txt(target), path = %p.join("."), "parameter default aliases an output symbol");
        let name = st.txt(target).to_owned();
        st.bind(&name, Binding::Alias(p));
    } else {
        visit(st, default, d);
        bind_pattern(st, target, d);
    }
}

/// Resolve an import specifier to a symbol path (relative specifiers become project module paths).
fn module_path(st: &State<'_>, spec: &str) -> SymPath {
    let spec = spec.strip_prefix("node:").unwrap_or(spec);
    let mut out: SymPath = if spec.starts_with('.') {
        let mut base: Vec<String> = st.ctx.path.split('/').map(str::to_owned).collect();
        base.pop();
        base
    } else {
        Vec::new()
    };
    for seg in spec.split('/') {
        match seg {
            "" | "." => {}
            ".." => {
                out.pop();
            }
            s => out.push(s.to_owned()),
        }
    }
    if spec.starts_with('.') {
        if let Some(last) = out.last_mut() {
            for ext in [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"] {
                if let Some(stem) = last.strip_suffix(ext).map(str::to_owned) {
                    *last = stem;
                    break;
                }
            }
        }
        if out.last().is_some_and(|l| l == "index") {
            out.pop();
        }
    }
    out
}

fn string_text(st: &State<'_>, n: Node<'_>) -> Option<String> {
    match n.kind() {
        "string" => Some(
            kids(n)
                .into_iter()
                .filter(|c| c.kind() == "string_fragment")
                .map(|c| st.txt(c))
                .collect(),
        ),
        "template_string" if !kids(n).iter().any(|c| c.kind() == "template_substitution") => {
            let t = st.txt(n);
            Some(t.trim_matches('`').to_owned())
        }
        _ => None,
    }
}

/// The literal an expression denotes: a number, a string, a `const` bound to one, or a `+` of strings.
fn lit_of(st: &State<'_>, n: Node<'_>) -> Option<Lit> {
    match n.kind() {
        "number" => st.txt(n).replace('_', "").parse::<i64>().ok().map(Lit::Int),
        "identifier" => match st.lookup(st.txt(n)) {
            Some(Binding::Lit(l)) => Some(l.clone()),
            _ => None,
        },
        "parenthesized_expression" | "as_expression" | "satisfies_expression" => {
            lit_of(st, kids(n).into_iter().next()?)
        }
        "binary_expression" => {
            let op = n.child_by_field_name("operator")?;
            if st.txt(op) != "+" {
                return None;
            }
            let (Lit::Str(a), Lit::Str(b)) = (
                lit_of(st, n.child_by_field_name("left")?)?,
                lit_of(st, n.child_by_field_name("right")?)?,
            ) else {
                return None;
            };
            Some(Lit::Str(a + &b))
        }
        _ => string_text(st, n).map(Lit::Str),
    }
}

/// The string an expression denotes, when it is a literal or a `const` string.
fn lit_str(st: &State<'_>, n: Node<'_>) -> Option<String> {
    match lit_of(st, n)? {
        Lit::Str(s) => Some(s),
        Lit::Int(_) => None,
    }
}

fn do_import(st: &mut State<'_>, n: Node<'_>) {
    let Some(src) = n.child_by_field_name("source") else {
        return;
    };
    let Some(spec) = string_text(st, src) else {
        return;
    };
    let module = module_path(st, &spec);
    st.note(&module);
    for c in kids(n) {
        if c.kind() != "import_clause" {
            if c.kind() == "import_require_clause"
                && let Some(id) = kids(c).into_iter().find(|k| k.kind() == "identifier")
            {
                let name = st.txt(id).to_owned();
                let linked = st.ctx.project.link(module.clone());
                st.bind(&name, Binding::Alias(linked));
            }
            continue;
        }
        for k in kids(c) {
            match k.kind() {
                "identifier" => {
                    let name = st.txt(k).to_owned();
                    let mut p = module.clone();
                    p.push("default".to_owned());
                    let linked = st.ctx.project.link(p);
                    st.bind(&name, Binding::Alias(linked));
                }
                "namespace_import" => {
                    if let Some(id) = kids(k).into_iter().next() {
                        let name = st.txt(id).to_owned();
                        let linked = st.ctx.project.link(module.clone());
                        st.bind(&name, Binding::Alias(linked));
                    }
                }
                "named_imports" => {
                    for spec in kids(k) {
                        let Some(nm) = spec.child_by_field_name("name") else {
                            continue;
                        };
                        let orig = st.txt(nm).to_owned();
                        let local = spec
                            .child_by_field_name("alias")
                            .map_or_else(|| orig.clone(), |a| st.txt(a).to_owned());
                        let mut p = module.clone();
                        p.push(orig);
                        let linked = st.ctx.project.link(p);
                        st.bind(&local, Binding::Alias(linked));
                    }
                }
                _ => {}
            }
        }
    }
}

fn visit<'t>(st: &mut State<'_>, n: Node<'t>, d: &mut Vec<Node<'t>>) {
    let kind = n.kind();
    if FUNCTIONS.contains(&kind) {
        d.push(n);
        return;
    }
    match kind {
        "comment"
        | "import_statement"
        | "type_annotation"
        | "interface_declaration"
        | "type_alias_declaration"
        | "string"
        | "regex"
        | "debugger_statement"
        | "predefined_type"
        | "type_arguments"
        | "jsx_text" => {}
        "template_string" => {
            for c in kids(n) {
                if c.kind() == "template_substitution" {
                    for e in kids(c) {
                        visit(st, e, d);
                    }
                }
            }
        }
        "class_declaration" | "class" => {
            if let Some(name) = n.child_by_field_name("name") {
                let name = st.txt(name).to_owned();
                st.bind(&name, Binding::Opaque);
            }
            for c in kids(n) {
                visit(st, c, d);
            }
        }
        "variable_declarator" => do_declarator(st, n, d),
        "assignment_expression" => do_assign(st, n, d),
        "statement_block" => {
            st.push();
            scope(st, n);
            st.pop();
        }
        "catch_clause" => {
            st.push();
            if let Some(p) = n.child_by_field_name("parameter") {
                bind_pattern(st, p, d);
            }
            if let Some(b) = n.child_by_field_name("body") {
                scope(st, b);
            }
            st.pop();
        }
        "for_in_statement" => {
            st.push();
            if let Some(r) = n.child_by_field_name("right") {
                visit(st, r, d);
            }
            if let Some(l) = n.child_by_field_name("left") {
                bind_pattern(st, l, d);
            }
            if let Some(b) = n.child_by_field_name("body") {
                visit(st, b, d);
            }
            st.pop();
        }
        "call_expression" | "new_expression" => do_call(st, n, d),
        "with_statement" => do_with(st, n, d),
        "member_expression" | "subscript_expression" | "identifier" | "nested_identifier" => {
            if kind == "subscript_expression" {
                flag_computed(st, n);
            }
            if let Some(p) = path_of(st, n, true)
                && st.hit_ref(n, &p)
            {
                return;
            }
            if kind != "identifier" {
                for c in kids(n) {
                    visit(st, c, d);
                }
            }
        }
        "property_identifier" | "shorthand_property_identifier" => {
            if kind == "shorthand_property_identifier"
                && let Some(p) = path_of_name(st, st.txt(n))
            {
                st.hit_ref(n, &p);
            }
        }
        _ => {
            for c in kids(n) {
                visit(st, c, d);
            }
        }
    }
}

/// Report `obj[expr]` when `obj` is an output object and `expr` is not a literal or `const` string.
fn flag_computed(st: &mut State<'_>, n: Node<'_>) {
    let (Some(o), Some(idx)) = (
        n.child_by_field_name("object"),
        n.child_by_field_name("index"),
    ) else {
        return;
    };
    if lit_str(st, idx).is_some() {
        return;
    }
    if path_of(st, o, true).is_some_and(|p| st.group.any_atom(&p)) {
        st.unres(n, "computed member name on an output object");
    }
}

/// `with (obj) { .. }`: names unbound in the body resolve through `obj` when it is an output
/// object; a `with` over an object the scanner cannot resolve is reported as unresolved.
fn do_with<'t>(st: &mut State<'_>, n: Node<'t>, d: &mut Vec<Node<'t>>) {
    let object = n.child_by_field_name("object");
    let body = n.child_by_field_name("body");
    let op = object.and_then(|o| path_of(st, o, true));
    match op {
        Some(p) if st.group.any_atom(&p) => {
            tracing::debug!(path = %p.join("."), "with-block over an output object");
            st.withs.push(p);
            if let Some(b) = body {
                visit(st, b, d);
            }
            st.withs.pop();
        }
        other => {
            if other.is_none() {
                st.unres(n, "with-block over an object that cannot be resolved");
            }
            if let Some(o) = object {
                visit(st, o, d);
            }
            if let Some(b) = body {
                visit(st, b, d);
            }
        }
    }
}

/// `base.key` with global-object heads stripped and project re-exports followed.
fn extend(st: &State<'_>, base: &[String], key: String) -> SymPath {
    let mut p = base.to_vec();
    p.push(key);
    while p.len() > 1 && GLOBAL_HEADS.contains(&p[0].as_str()) {
        p.remove(0);
    }
    st.ctx.project.link(p)
}

fn path_of_name(st: &State<'_>, name: &str) -> Option<SymPath> {
    match st.lookup(name) {
        Some(Binding::Alias(p)) => Some(p.clone()),
        Some(Binding::Opaque | Binding::Lit(_)) => None,
        None => Some(vec![name.to_owned()]),
    }
}

fn do_declarator<'t>(st: &mut State<'_>, n: Node<'t>, d: &mut Vec<Node<'t>>) {
    let name = n.child_by_field_name("name");
    let value = n.child_by_field_name("value");
    let Some(name) = name else { return };
    let vpath = value.and_then(|v| path_of(st, v, false));
    match name.kind() {
        "identifier" => {
            let id = st.txt(name).to_owned();
            let is_const = n.parent().is_some_and(|p| {
                p.kind() == "lexical_declaration" && st.txt(p).starts_with("const")
            });
            let lit = value.filter(|_| is_const).and_then(|v| lit_of(st, v));
            match (value, vpath) {
                (Some(_), Some(p)) if explicit(st, &p) => st.bind(&id, Binding::Alias(p)),
                (Some(v), _) if is_create_require(st, v) => {
                    st.bind(&id, Binding::Alias(vec!["require".to_owned()]));
                }
                (v, _) => {
                    if let Some(v) = v {
                        visit(st, v, d);
                    }
                    st.bind(&id, lit.map_or(Binding::Opaque, Binding::Lit));
                }
            }
        }
        "object_pattern" => {
            if vpath.is_none()
                && let Some(v) = value
            {
                visit(st, v, d);
            }
            destructure(st, name, vpath.as_deref(), d);
        }
        _ => {
            if let Some(v) = value {
                visit(st, v, d);
            }
            bind_pattern(st, name, d);
        }
    }
}

/// True for `createRequire(..)` from `module`: the result is a `require` function.
fn is_create_require(st: &mut State<'_>, v: Node<'_>) -> bool {
    v.kind() == "call_expression"
        && v.child_by_field_name("function")
            .and_then(|f| path_of(st, f, true))
            .is_some_and(|p| p == ["module", "createRequire"])
}

/// Bind the names of an object pattern as aliases of `base.<key>`, recursing through nested
/// patterns; with no resolvable `base` the names are plain locals.
fn destructure<'t>(
    st: &mut State<'_>,
    pat: Node<'t>,
    base: Option<&[String]>,
    d: &mut Vec<Node<'t>>,
) {
    for prop in kids(pat) {
        match prop.kind() {
            "shorthand_property_identifier_pattern" => {
                let k = st.txt(prop).to_owned();
                bind_member(st, &k, base.map(|b| extend(st, b, k.clone())));
            }
            "object_assignment_pattern" => {
                let (Some(left), Some(right)) = (
                    prop.child_by_field_name("left"),
                    prop.child_by_field_name("right"),
                ) else {
                    continue;
                };
                let key = st.txt(left).to_owned();
                match base {
                    Some(root) => bind_member(st, &key, Some(extend(st, root, key.clone()))),
                    None => bind_default(st, left, right, d),
                }
            }
            "pair_pattern" => {
                let (Some(key), Some(v)) = (
                    prop.child_by_field_name("key"),
                    prop.child_by_field_name("value"),
                ) else {
                    continue;
                };
                let member = pattern_key(st, key, base.is_some());
                let sub = match (base, member) {
                    (Some(b), Some(k)) => Some(extend(st, b, k)),
                    _ => None,
                };
                bind_target(st, v, sub, d);
            }
            _ => bind_pattern(st, prop, d),
        }
    }
}

/// Bind the target of one destructured member (`local`, `{ nested }`, `local = default`).
fn bind_target<'t>(st: &mut State<'_>, v: Node<'t>, sub: Option<SymPath>, d: &mut Vec<Node<'t>>) {
    match v.kind() {
        "identifier" => {
            let name = st.txt(v).to_owned();
            bind_member(st, &name, sub);
        }
        "object_pattern" => destructure(st, v, sub.as_deref(), d),
        "assignment_pattern" => {
            if let Some(l) = v.child_by_field_name("left") {
                bind_target(st, l, sub, d);
            }
        }
        _ => bind_pattern(st, v, d),
    }
}

/// Bind `name` to the member path when known, otherwise as a local.
fn bind_member(st: &mut State<'_>, name: &str, path: Option<SymPath>) {
    match path {
        Some(p) => st.bind(name, Binding::Alias(p)),
        None => st.bind(name, Binding::Opaque),
    }
}

/// The member name a pattern key denotes; a computed key that is not a literal is reported
/// as unresolved when the destructured object is itself resolvable.
fn pattern_key(st: &mut State<'_>, key: Node<'_>, based: bool) -> Option<String> {
    if key.kind() == "computed_property_name" {
        let inner = kids(key).into_iter().next()?;
        let lit = lit_str(st, inner);
        if lit.is_none() && based {
            st.unres(key, "computed destructuring key on an output object");
        }
        return lit;
    }
    match key.kind() {
        "string" => string_text(st, key),
        _ => Some(st.txt(key).to_owned()),
    }
}

/// True when `p` is worth aliasing: an atom matches it or its head is an import/binding.
fn explicit(st: &State<'_>, p: &[String]) -> bool {
    st.group.any_atom(p)
        || st
            .ctx
            .project
            .modules
            .contains_key(&p[..p.len().saturating_sub(1)].join("."))
        || st.lookup(p[0].as_str()).is_some()
        || DYNAMIC_HEADS.contains(&p[0].as_str())
}

fn do_assign<'t>(st: &mut State<'_>, n: Node<'t>, d: &mut Vec<Node<'t>>) {
    let (Some(lhs), Some(rhs)) = (
        n.child_by_field_name("left"),
        n.child_by_field_name("right"),
    ) else {
        return;
    };
    if lhs.kind() == "identifier" {
        let id = st.txt(lhs).to_owned();
        match path_of(st, rhs, false) {
            Some(p) if explicit(st, &p) => st.bind(&id, Binding::Alias(p)),
            _ => {
                visit(st, rhs, d);
                st.bind(&id, Binding::Opaque);
            }
        }
    } else {
        visit(st, rhs, d);
        visit(st, lhs, d);
    }
}

fn do_call<'t>(st: &mut State<'_>, n: Node<'t>, d: &mut Vec<Node<'t>>) {
    let Some(f) = n
        .child_by_field_name("function")
        .or_else(|| n.child_by_field_name("constructor"))
    else {
        return;
    };
    let arg_node = n.child_by_field_name("arguments");
    let arg_nodes: Vec<Node<'t>> = arg_node
        .map(kids)
        .unwrap_or_default()
        .into_iter()
        .filter(|c| c.kind() != "comment")
        .collect();
    let mut cp = callee_path(st, f);
    let mut args = args_from(st, &arg_nodes);
    if f.kind() != "new_expression" {
        flag_dynamic(st, n, cp.as_deref(), &arg_nodes);
    }
    if cp.as_deref() == Some(&["Reflect".to_owned(), "apply".to_owned()][..])
        && let Some(target) = arg_nodes.first().and_then(|t| path_of(st, *t, true))
    {
        let list = arg_nodes
            .get(2)
            .filter(|l| l.kind() == "array_expression")
            .map(|l| kids(*l))
            .unwrap_or_default();
        args = args_from(st, &list);
        cp = Some(target);
    }
    let hit = cp.as_ref().is_some_and(|p| st.hit_call(n, p, &args));
    if !hit
        && !st.in_chain
        && cp
            .as_ref()
            .is_some_and(|p| st.group.fd_unresolved(p, &args))
    {
        st.unres(
            n,
            "raw descriptor write to an fd that is not a known integer",
        );
    }
    let (saved_suppress, saved_chain) = (st.suppress, st.in_chain);
    if hit {
        st.in_chain = true;
        visit(st, f, d);
        st.suppress = true;
    } else {
        visit(st, f, d);
    }
    st.in_chain = false;
    for c in arg_nodes {
        visit(st, c, d);
    }
    st.suppress = saved_suppress;
    st.in_chain = saved_chain;
}

/// The symbol path of a callee; `import` (dynamic import) is the pseudo-path `["import"]`.
fn callee_path(st: &mut State<'_>, f: Node<'_>) -> Option<SymPath> {
    if f.kind() == "import" {
        Some(vec!["import".to_owned()])
    } else {
        path_of(st, f, true)
    }
}

/// Report calls whose effect the scanner cannot follow: dynamic `import`/`require`, `eval`,
/// `Function`, `vm` runners, `setTimeout(string)`, and reflective member lookups.
fn flag_dynamic(st: &mut State<'_>, n: Node<'_>, cp: Option<&[String]>, arg_nodes: &[Node<'_>]) {
    let Some(cp) = cp else { return };
    let head = cp.first().map(String::as_str);
    let atomish = |st: &mut State<'_>| {
        arg_nodes
            .first()
            .and_then(|a| path_of(st, *a, true))
            .is_some_and(|p| st.group.any_atom(&p))
    };
    let what = match cp {
        [h] if h == "import" || h == "require" => {
            if arg_nodes.first().and_then(|a| lit_str(st, *a)).is_some() {
                return;
            }
            "dynamic import or require with a specifier that is not a literal"
        }
        [h] if h == "eval" || h == "Function" => "eval or Function builds code from a string",
        [h] if matches!(h.as_str(), "setTimeout" | "setInterval" | "setImmediate") => {
            if arg_nodes.first().and_then(|a| lit_str(st, *a)).is_none() {
                return;
            }
            "a timer given a code string"
        }
        [_, m] if head == Some("vm") && VM_RUNNERS.contains(&m.as_str()) => {
            "vm runs code built from a string"
        }
        [h, m] if h == "Reflect" && m == "get" => {
            if arg_nodes.get(1).and_then(|k| lit_str(st, *k)).is_some() || !atomish(st) {
                return;
            }
            "Reflect.get with a member name that is not a literal"
        }
        [h, m] if REFLECTIVE.contains(&(h.as_str(), m.as_str())) => {
            if !atomish(st) {
                return;
            }
            "a property descriptor of an output object escapes the scanner"
        }
        _ => return,
    };
    st.unres(n, what);
}

fn args_from(st: &mut State<'_>, nodes: &[Node<'_>]) -> Args {
    let pos = nodes
        .iter()
        .map(|c| {
            let lit = lit_of(st, *c);
            ArgInfo {
                int: match lit {
                    Some(Lit::Int(i)) => Some(i),
                    _ => None,
                },
                text: match lit {
                    Some(Lit::Str(s)) => Some(s),
                    _ => None,
                },
                path: path_of(st, *c, true),
            }
        })
        .collect();
    Args {
        pos,
        kw: Vec::new(),
    }
}

/// The symbol path an expression denotes, with global-object heads stripped.
fn path_of(st: &mut State<'_>, n: Node<'_>, value_calls: bool) -> Option<SymPath> {
    let mut p = raw_path(st, n, value_calls)?;
    while p.len() > 1 && GLOBAL_HEADS.contains(&p[0].as_str()) {
        p.remove(0);
    }
    Some(p)
}

fn raw_path(st: &mut State<'_>, n: Node<'_>, value_calls: bool) -> Option<SymPath> {
    match n.kind() {
        "identifier" => {
            let name = st.txt(n);
            match st.lookup(name) {
                Some(Binding::Alias(p)) => Some(p.clone()),
                Some(Binding::Opaque | Binding::Lit(_)) => None,
                None => {
                    let name = name.to_owned();
                    if let Some(w) = st.withs.last() {
                        let via = extend(st, w, name.clone());
                        if st.group.any_atom(&via) {
                            return Some(via);
                        }
                    }
                    Some(vec![name])
                }
            }
        }
        "member_expression" => {
            let o = n.child_by_field_name("object")?;
            let prop = n.child_by_field_name("property")?;
            let mut p = path_of(st, o, value_calls)?;
            p.push(st.txt(prop).to_owned());
            Some(st.ctx.project.link(p))
        }
        "nested_identifier" => {
            let mut p: SymPath = Vec::new();
            for c in kids(n) {
                p.push(st.txt(c).to_owned());
            }
            Some(p)
        }
        "subscript_expression" => {
            let o = n.child_by_field_name("object")?;
            let idx = n.child_by_field_name("index")?;
            let key = lit_str(st, idx)?;
            let mut p = path_of(st, o, value_calls)?;
            p.push(key);
            Some(p)
        }
        "parenthesized_expression"
        | "as_expression"
        | "satisfies_expression"
        | "non_null_expression"
        | "await_expression"
        | "type_assertion" => path_of(st, kids(n).into_iter().next()?, value_calls),
        "sequence_expression" => path_of(st, kids(n).into_iter().last()?, value_calls),
        "call_expression" => {
            let f = n.child_by_field_name("function")?;
            let a: Vec<Node<'_>> = n
                .child_by_field_name("arguments")
                .map(kids)
                .unwrap_or_default();
            let mut p = callee_path(st, f)?;
            if p == ["import"] || p == ["require"] {
                let spec = lit_str(st, *a.first()?)?;
                return Some(st.ctx.project.link(module_path(st, &spec)));
            }
            if p == ["Reflect", "get"] {
                let base = path_of(st, *a.first()?, value_calls)?;
                let key = lit_str(st, *a.get(1)?)?;
                return Some(extend(st, &base, key));
            }
            if p.last().is_some_and(|l| l == "bind") && p.len() > 1 {
                p.pop();
                return Some(p);
            }
            value_calls.then_some(p)
        }
        "new_expression" if value_calls => {
            path_of(st, n.child_by_field_name("constructor")?, value_calls)
        }
        _ => None,
    }
}
