//! The Python scanner: import and alias resolution over the tree-sitter-python tree.

// frob:ticket 01M5XMR67K19SFAWNTDJKKJPTT

use tree_sitter::Node;

use super::catalogue::{ArgInfo, Args};
use super::engine::{Binding, FileScan, State, SymPath, kids};

/// Roots whose `getattr(<root>, <non-literal>)` is reported as an unresolved dynamic form.
const DYNAMIC_ROOTS: &[&str] = &["sys", "builtins", "os", "subprocess"];

/// Scan one parsed Python module.
pub fn scan(mut st: State<'_>, root: Node<'_>) -> FileScan {
    stmts(&mut st, root);
    st.finish()
}

/// Visit the statements under `parent` as one scope, running deferred function bodies last.
fn stmts(st: &mut State<'_>, parent: Node<'_>) {
    let mut deferred = Vec::new();
    for c in kids(parent) {
        visit(st, c, &mut deferred);
    }
    for f in deferred {
        run_function(st, f);
    }
}

fn run_function(st: &mut State<'_>, f: Node<'_>) {
    st.push();
    if let Some(params) = f.child_by_field_name("parameters") {
        for p in kids(params) {
            bind_param(st, p);
        }
    }
    if let Some(body) = f.child_by_field_name("body") {
        stmts(st, body);
    }
    st.pop();
}

fn bind_param(st: &mut State<'_>, p: Node<'_>) {
    match p.kind() {
        "identifier" => {
            let name = st.name(p).into_owned();
            st.bind(&name, Binding::Opaque);
        }
        "default_parameter" | "typed_default_parameter" => {
            if let Some(n) = p.child_by_field_name("name") {
                bind_param(st, n);
            }
        }
        _ => {
            if let Some(first) = kids(p).into_iter().next() {
                bind_param(st, first);
            }
        }
    }
}

/// Bind every identifier of an assignment/loop/with target as a local value.
fn bind_targets(st: &mut State<'_>, n: Node<'_>) {
    match n.kind() {
        "identifier" => {
            let name = st.name(n).into_owned();
            st.bind(&name, Binding::Opaque);
        }
        "attribute" | "subscript" => {}
        _ => {
            for c in kids(n) {
                bind_targets(st, c);
            }
        }
    }
}

#[allow(
    clippy::too_many_lines,
    reason = "one match over every Python node kind"
)]
fn visit<'t>(st: &mut State<'_>, n: Node<'t>, d: &mut Vec<Node<'t>>) {
    match n.kind() {
        "comment" | "global_statement" | "nonlocal_statement" | "dotted_name" | "type"
        | "pass_statement" => {}
        "string" => {
            for c in kids(n) {
                if c.kind() == "interpolation" {
                    visit(st, c, d);
                }
            }
        }
        "import_statement" => do_import(st, n),
        "import_from_statement" => do_from(st, n),
        "function_definition" => {
            if let Some(name) = n.child_by_field_name("name") {
                let name = st.name(name).into_owned();
                st.bind(&name, Binding::Opaque);
            }
            if let Some(params) = n.child_by_field_name("parameters") {
                for p in kids(params) {
                    if let Some(v) = p.child_by_field_name("value") {
                        visit(st, v, d);
                    }
                }
            }
            d.push(n);
        }
        "class_definition" => {
            if let Some(name) = n.child_by_field_name("name") {
                let name = st.name(name).into_owned();
                st.bind(&name, Binding::Opaque);
            }
            if let Some(sup) = n.child_by_field_name("superclasses") {
                visit(st, sup, d);
            }
            st.push();
            if let Some(body) = n.child_by_field_name("body") {
                stmts(st, body);
            }
            st.pop();
        }
        "lambda" => {
            st.push();
            if let Some(params) = n.child_by_field_name("parameters") {
                for p in kids(params) {
                    bind_param(st, p);
                }
            }
            if let Some(b) = n.child_by_field_name("body") {
                visit(st, b, d);
            }
            st.pop();
        }
        "assignment" => do_assign(st, n, d),
        "for_statement" => {
            if let Some(r) = n.child_by_field_name("right") {
                visit(st, r, d);
            }
            if let Some(l) = n.child_by_field_name("left") {
                bind_targets(st, l);
            }
            for f in ["body", "alternative"] {
                if let Some(b) = n.child_by_field_name(f) {
                    visit(st, b, d);
                }
            }
        }
        "with_clause" => {
            for item in kids(n) {
                let Some(v) = item.child_by_field_name("value") else {
                    continue;
                };
                if v.kind() == "as_pattern" {
                    if let Some(e) = kids(v).into_iter().next() {
                        visit(st, e, d);
                    }
                    if let Some(a) = v.child_by_field_name("alias") {
                        bind_targets(st, a);
                    }
                } else {
                    visit(st, v, d);
                }
            }
        }
        "except_clause" => {
            for c in kids(n) {
                if c.kind() == "as_pattern" {
                    if let Some(e) = kids(c).into_iter().next() {
                        visit(st, e, d);
                    }
                    if let Some(a) = c.child_by_field_name("alias") {
                        bind_targets(st, a);
                    }
                } else {
                    visit(st, c, d);
                }
            }
        }
        "list_comprehension"
        | "set_comprehension"
        | "dictionary_comprehension"
        | "generator_expression" => {
            st.push();
            for c in kids(n) {
                if c.kind() == "for_in_clause" {
                    if let Some(r) = c.child_by_field_name("right") {
                        visit(st, r, d);
                    }
                    if let Some(l) = c.child_by_field_name("left") {
                        bind_targets(st, l);
                    }
                }
            }
            for c in kids(n) {
                if c.kind() != "for_in_clause" {
                    visit(st, c, d);
                }
            }
            st.pop();
        }
        "named_expression" => {
            if let Some(v) = n.child_by_field_name("value") {
                visit(st, v, d);
            }
            if let Some(l) = n.child_by_field_name("name") {
                bind_targets(st, l);
            }
        }
        "keyword_argument" => {
            if let Some(v) = n.child_by_field_name("value") {
                visit(st, v, d);
            }
        }
        "call" => do_call(st, n, d),
        "attribute" | "subscript" => {
            if let Some((p, _)) = path_of(st, n, true)
                && st.hit_ref(n, &p)
            {
                return;
            }
            for c in kids(n) {
                visit(st, c, d);
            }
        }
        "identifier" => {
            if let Some((p, _)) = path_of(st, n, true) {
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

fn do_assign<'t>(st: &mut State<'_>, n: Node<'t>, d: &mut Vec<Node<'t>>) {
    let left = n.child_by_field_name("left");
    let right = n.child_by_field_name("right");
    match (left, right) {
        (Some(lhs), Some(rhs)) if lhs.kind() == "identifier" => {
            let name = st.name(lhs).into_owned();
            match path_of(st, rhs, false) {
                Some((p, explicit)) if explicit || st.group.any_atom(&p) => {
                    st.bind(&name, Binding::Alias(p));
                }
                _ => {
                    visit(st, rhs, d);
                    st.bind(&name, Binding::Opaque);
                }
            }
        }
        (lhs, rhs) => {
            if let Some(rhs) = rhs {
                visit(st, rhs, d);
            }
            if let Some(lhs) = lhs {
                if matches!(lhs.kind(), "attribute" | "subscript") {
                    visit(st, lhs, d);
                } else {
                    bind_targets(st, lhs);
                }
            }
        }
    }
}

fn do_call<'t>(st: &mut State<'_>, n: Node<'t>, d: &mut Vec<Node<'t>>) {
    let Some(f) = n.child_by_field_name("function") else {
        return;
    };
    let arg_node = n.child_by_field_name("arguments");
    let cp = path_of(st, f, true).map(|(p, _)| p);
    if let (Some(p), Some(a)) = (&cp, arg_node) {
        flag_dynamic(st, n, p, a);
    }
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

/// Report `getattr(<sys|builtins|os|subprocess>, <non-literal>)` as an unresolved dynamic form.
fn flag_dynamic(st: &mut State<'_>, n: Node<'_>, callee: &[String], args: Node<'_>) {
    if callee != ["builtins", "getattr"] {
        return;
    }
    let a = kids(args);
    if a.len() < 2 || a[1].kind() == "string" {
        return;
    }
    if let Some((p, _)) = path_of(st, a[0], true)
        && p.len() == 1
        && DYNAMIC_ROOTS.contains(&p[0].as_str())
    {
        st.unres(n, "getattr on an output module with a non-literal name");
    }
}

fn args_of(st: &mut State<'_>, a: Node<'_>) -> Args {
    let mut out = Args::default();
    for c in kids(a) {
        match c.kind() {
            "keyword_argument" => {
                if let (Some(k), Some(v)) = (
                    c.child_by_field_name("name"),
                    c.child_by_field_name("value"),
                ) {
                    let key = st.name(k).into_owned();
                    let info = arg_info(st, v);
                    out.kw.push((key, info));
                }
            }
            "list_splat" | "dictionary_splat" | "comment" => {}
            _ => {
                let info = arg_info(st, c);
                out.pos.push(info);
            }
        }
    }
    out
}

fn arg_info(st: &mut State<'_>, n: Node<'_>) -> ArgInfo {
    ArgInfo {
        int: (n.kind() == "integer")
            .then(|| st.txt(n).replace('_', "").parse::<i64>().ok())
            .flatten(),
        text: string_lit(st, n),
        path: path_of(st, n, true).map(|(p, _)| p),
    }
}

/// The text of a plain (non-interpolated) string literal.
fn string_lit(st: &State<'_>, n: Node<'_>) -> Option<String> {
    if n.kind() != "string" {
        return None;
    }
    let mut out = String::new();
    for c in kids(n) {
        match c.kind() {
            "string_content" => out.push_str(st.txt(c)),
            "interpolation" => return None,
            _ => {}
        }
    }
    Some(out)
}

fn do_import(st: &mut State<'_>, n: Node<'_>) {
    for c in kids(n) {
        match c.kind() {
            "dotted_name" => {
                let segs: SymPath = st.name(c).split('.').map(str::to_owned).collect();
                let head = segs[0].clone();
                st.bind(&head, Binding::Alias(vec![head.clone()]));
                st.note(&segs);
            }
            "aliased_import" => {
                if let (Some(name), Some(alias)) = (
                    c.child_by_field_name("name"),
                    c.child_by_field_name("alias"),
                ) {
                    let segs: SymPath = st.name(name).split('.').map(str::to_owned).collect();
                    let alias = st.name(alias).into_owned();
                    let linked = st.ctx.project.link(segs);
                    st.bind(&alias, Binding::Alias(linked));
                }
            }
            _ => {}
        }
    }
}

/// The module package directory segments of the current file (`src/pkg/util.py` gives `src.pkg`).
fn package_of(path: &str) -> Vec<String> {
    let mut parts: Vec<String> = path.split('/').map(str::to_owned).collect();
    parts.pop();
    parts
}

fn do_from(st: &mut State<'_>, n: Node<'_>) {
    let Some(m) = n.child_by_field_name("module_name") else {
        return;
    };
    let mut module: SymPath = Vec::new();
    if m.kind() == "relative_import" {
        let mut dots = 0usize;
        let mut rest = String::new();
        for c in kids(m) {
            match c.kind() {
                "import_prefix" => dots = st.txt(c).len(),
                "dotted_name" => rest = st.name(c).into_owned(),
                _ => {}
            }
        }
        let mut pkg = package_of(st.ctx.path);
        for _ in 1..dots {
            pkg.pop();
        }
        module = pkg;
        module.extend(rest.split('.').filter(|s| !s.is_empty()).map(str::to_owned));
    } else {
        module.extend(st.name(m).split('.').map(str::to_owned));
    }
    st.note(&module);
    let mut names = Vec::new();
    for c in kids(n) {
        if c.id() == m.id() {
            continue;
        }
        match c.kind() {
            "dotted_name" => names.push((st.name(c).into_owned(), st.name(c).into_owned())),
            "aliased_import" => {
                if let (Some(a), Some(b)) = (
                    c.child_by_field_name("name"),
                    c.child_by_field_name("alias"),
                ) {
                    names.push((st.name(a).into_owned(), st.name(b).into_owned()));
                }
            }
            "wildcard_import" => st.globs.push(module.clone()),
            _ => {}
        }
    }
    for (name, local) in names {
        let mut p = module.clone();
        p.push(name);
        let linked = st.ctx.project.link(p);
        st.bind(&local, Binding::Alias(linked));
    }
}

/// The symbol path an expression denotes, and whether its head was explicitly bound.
///
/// `value_calls` lets a call stand for its callee path (`subprocess.Popen(..).wait`).
fn path_of(st: &mut State<'_>, n: Node<'_>, value_calls: bool) -> Option<(SymPath, bool)> {
    match n.kind() {
        "identifier" => {
            let name = st.name(n).into_owned();
            match st.lookup(&name) {
                Some(Binding::Alias(p)) => return Some((p.clone(), true)),
                Some(Binding::Opaque | Binding::Lit(_)) => return None,
                None => {}
            }
            if name == "__builtins__" {
                return Some((vec!["builtins".to_owned()], false));
            }
            for g in &st.globs {
                let mut cand = g.clone();
                cand.push(name.clone());
                if st.group.any_atom(&cand) {
                    return Some((cand, true));
                }
            }
            Some((vec!["builtins".to_owned(), name.clone()], false))
        }
        "attribute" => {
            let obj = n.child_by_field_name("object")?;
            let attr = st.name(n.child_by_field_name("attribute")?).into_owned();
            let (mut p, e) = path_of(st, obj, value_calls)?;
            if attr != "__dict__" {
                p.push(attr);
            }
            Some((st.ctx.project.link(p), e))
        }
        "subscript" => {
            let obj = n.child_by_field_name("value")?;
            let key = string_lit(st, n.child_by_field_name("subscript")?)?;
            let (mut p, e) = path_of(st, obj, value_calls)?;
            p.push(key);
            Some((p, e))
        }
        "parenthesized_expression" => path_of(st, kids(n).into_iter().next()?, value_calls),
        "call" => {
            let f = n.child_by_field_name("function")?;
            let (cp, e) = path_of(st, f, value_calls)?;
            let args = kids(n.child_by_field_name("arguments")?);
            match cp.join(".").as_str() {
                "builtins.getattr" if args.len() >= 2 => {
                    let key = string_lit(st, args[1])?;
                    let (mut p, e) = path_of(st, args[0], value_calls)?;
                    p.push(key);
                    return Some((p, e));
                }
                "builtins.vars" if args.len() == 1 => {
                    return path_of(st, args[0], value_calls);
                }
                "importlib.import_module" | "builtins.__import__" => {
                    let name = string_lit(st, *args.first()?)?;
                    let segs: SymPath = if cp[0] == "builtins" {
                        vec![name.split('.').next()?.to_owned()]
                    } else {
                        name.split('.').map(str::to_owned).collect()
                    };
                    return Some((segs, true));
                }
                "functools.partial" if !args.is_empty() => {
                    return path_of(st, args[0], value_calls);
                }
                _ => {}
            }
            value_calls.then_some((cp, e))
        }
        _ => None,
    }
}
