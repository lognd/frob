//! The JavaScript/TypeScript scanner (also JSX and TSX): imports, `require`, destructuring and
//! member chains over the tree-sitter-javascript and tree-sitter-typescript trees.

// frob:ticket 01M5XMR67K19SFAWNTDJKKJPTT

use tree_sitter::Node;

use super::catalogue::{ArgInfo, Args};
use super::engine::{Binding, FileScan, State, SymPath, kids};

/// Global-object spellings stripped from the head of a path (`globalThis.console` is `console`).
const GLOBAL_HEADS: &[&str] = &["globalThis", "window", "self", "global"];

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
    for field in ["parameters", "parameter"] {
        if let Some(p) = f.child_by_field_name(field) {
            bind_pattern(st, p);
        }
    }
    if let Some(body) = f.child_by_field_name("body") {
        if body.kind() == "statement_block" {
            scope(st, body);
        } else {
            let mut d = Vec::new();
            visit(st, body, &mut d);
            for g in d {
                run_function(st, g);
            }
        }
    }
    st.pop();
}

fn bind_pattern(st: &mut State<'_>, n: Node<'_>) {
    match n.kind() {
        "identifier" | "shorthand_property_identifier_pattern" => {
            let name = st.txt(n).to_owned();
            st.bind(&name, Binding::Opaque);
        }
        "type_annotation" | "property_identifier" | "string" | "number" => {}
        "pair_pattern" => {
            if let Some(v) = n.child_by_field_name("value") {
                bind_pattern(st, v);
            }
        }
        _ => {
            for c in kids(n) {
                bind_pattern(st, c);
            }
        }
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
                bind_pattern(st, p);
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
                bind_pattern(st, l);
            }
            if let Some(b) = n.child_by_field_name("body") {
                visit(st, b, d);
            }
            st.pop();
        }
        "call_expression" | "new_expression" => do_call(st, n, d),
        "member_expression" | "subscript_expression" | "identifier" | "nested_identifier" => {
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

fn path_of_name(st: &State<'_>, name: &str) -> Option<SymPath> {
    match st.lookup(name) {
        Some(Binding::Alias(p)) => Some(p.clone()),
        Some(Binding::Opaque) => None,
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
            match (value, vpath) {
                (Some(_), Some(p)) if explicit(st, &p) => st.bind(&id, Binding::Alias(p)),
                (v, _) => {
                    if let Some(v) = v {
                        visit(st, v, d);
                    }
                    st.bind(&id, Binding::Opaque);
                }
            }
        }
        "object_pattern" => {
            let base = vpath;
            if base.is_none()
                && let Some(v) = value
            {
                visit(st, v, d);
            }
            for prop in kids(name) {
                let (key, local) = match prop.kind() {
                    "shorthand_property_identifier_pattern" => {
                        (st.txt(prop).to_owned(), st.txt(prop).to_owned())
                    }
                    "pair_pattern" => {
                        let k = prop
                            .child_by_field_name("key")
                            .map(|k| st.txt(k).to_owned());
                        let v = prop.child_by_field_name("value");
                        match (k, v) {
                            (Some(k), Some(v)) if v.kind() == "identifier" => {
                                (k, st.txt(v).to_owned())
                            }
                            _ => {
                                if let Some(v) = prop.child_by_field_name("value") {
                                    bind_pattern(st, v);
                                }
                                continue;
                            }
                        }
                    }
                    _ => {
                        bind_pattern(st, prop);
                        continue;
                    }
                };
                match &base {
                    Some(b) => {
                        let mut p = b.clone();
                        p.push(key);
                        let linked = st.ctx.project.link(p);
                        st.bind(&local, Binding::Alias(linked));
                    }
                    None => st.bind(&local, Binding::Opaque),
                }
            }
        }
        _ => {
            if let Some(v) = value {
                visit(st, v, d);
            }
            bind_pattern(st, name);
        }
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
    let cp = path_of(st, f, true);
    let args = arg_node.map_or_else(Args::default, |a| args_of(st, a));
    let hit = cp.as_ref().is_some_and(|p| st.hit_call(n, p, &args));
    let (saved_suppress, saved_chain) = (st.suppress, st.in_chain);
    if hit {
        st.in_chain = true;
        visit(st, f, d);
        st.suppress = true;
    } else {
        visit(st, f, d);
    }
    st.in_chain = false;
    if let Some(a) = arg_node {
        for c in kids(a) {
            visit(st, c, d);
        }
    }
    st.suppress = saved_suppress;
    st.in_chain = saved_chain;
}

fn args_of(st: &mut State<'_>, a: Node<'_>) -> Args {
    let pos = kids(a)
        .into_iter()
        .filter(|c| c.kind() != "comment")
        .map(|c| ArgInfo {
            int: (c.kind() == "number")
                .then(|| st.txt(c).parse::<i64>().ok())
                .flatten(),
            text: string_text(st, c),
            path: path_of(st, c, true),
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
                Some(Binding::Opaque) => None,
                None => {
                    if GLOBAL_HEADS.contains(&name) {
                        return Some(vec![name.to_owned()]);
                    }
                    Some(vec![name.to_owned()])
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
            let key = string_text(st, idx)?;
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
        "call_expression" => {
            let f = n.child_by_field_name("function")?;
            let a = n
                .child_by_field_name("arguments")
                .map(kids)
                .unwrap_or_default();
            if f.kind() == "import" || (f.kind() == "identifier" && st.txt(f) == "require") {
                let spec = string_text(st, *a.first()?)?;
                if f.kind() == "identifier" && st.lookup("require").is_some() {
                    return None;
                }
                return Some(st.ctx.project.link(module_path(st, &spec)));
            }
            let mut p = path_of(st, f, value_calls)?;
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
