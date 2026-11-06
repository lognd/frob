//! The Java scanner: `import` aliases and globs, `import static`, the implicit `java.lang`,
//! `System.out`/`System.err` print chains, `printStackTrace()`, `Paths.get("/dev/stderr")` and
//! `Runtime.getRuntime().exec`, with parameters, locals and own methods shadowing.

// frob:ticket 01M63G1MW58WP8VBQ7T6NKDAMD

use tree_sitter::Node;

use super::catalogue::{ArgInfo, Args};
use super::engine::{Binding, FileScan, State, SymPath, kids};

/// The canonical path an argument-less `printStackTrace()` resolves to (it writes to `System.err`).
const STACK_TRACE: [&str; 4] = ["java", "lang", "Throwable", "printStackTrace"];

/// Scan one parsed Java compilation unit.
pub fn scan(mut st: State<'_>, root: Node<'_>) -> FileScan {
    st.globs.push(vec!["java".to_owned(), "lang".to_owned()]);
    imports(&mut st, root);
    visit(&mut st, root);
    tracing::debug!(file = %st.ctx.path, hits = st.hits.len(), "java scan done");
    st.finish()
}

/// Bind every top-level `import` of the compilation unit.
fn imports(st: &mut State<'_>, root: Node<'_>) {
    for imp in kids(root)
        .into_iter()
        .filter(|c| c.kind() == "import_declaration")
    {
        let wildcard = kids(imp).iter().any(|c| c.kind() == "asterisk");
        let Some(name) = kids(imp)
            .into_iter()
            .find(|c| matches!(c.kind(), "scoped_identifier" | "identifier"))
        else {
            continue;
        };
        let path: SymPath = st.txt(name).split('.').map(str::to_owned).collect();
        if wildcard {
            st.note(&path);
            st.globs.push(path);
        } else if let Some(last) = path.last().cloned() {
            st.bind(&last, Binding::Alias(path));
        }
    }
}

fn visit(st: &mut State<'_>, n: Node<'_>) {
    match n.kind() {
        "line_comment"
        | "block_comment"
        | "string_literal"
        | "character_literal"
        | "import_declaration"
        | "package_declaration" => {}
        "class_declaration"
        | "interface_declaration"
        | "enum_declaration"
        | "record_declaration" => {
            st.push();
            bind_members(st, n);
            scoped(st, n);
            st.pop();
        }
        "method_declaration"
        | "constructor_declaration"
        | "lambda_expression"
        | "catch_clause"
        | "enhanced_for_statement"
        | "for_statement"
        | "block" => {
            st.push();
            bind_params(st, n);
            scoped(st, n);
            st.pop();
        }
        "variable_declarator" => {
            if let Some(v) = n.child_by_field_name("value") {
                visit(st, v);
            }
            if let Some(id) = n.child_by_field_name("name") {
                let name = st.txt(id).to_owned();
                st.bind(&name, Binding::Opaque);
            }
        }
        "method_invocation" => do_call(st, n),
        "object_creation_expression" => do_new(st, n),
        "identifier" | "field_access" | "scoped_identifier" => {
            if let Some(p) = path_of(st, n)
                && st.hit_ref(n, &p)
            {
                return;
            }
            if n.kind() != "identifier" {
                for c in kids(n) {
                    visit(st, c);
                }
            }
        }
        _ => {
            for c in kids(n) {
                visit(st, c);
            }
        }
    }
}

/// Visit the children of a scope node, skipping the declared name.
fn scoped(st: &mut State<'_>, n: Node<'_>) {
    let skip = n.child_by_field_name("name").map(|c| c.id());
    for c in kids(n) {
        if Some(c.id()) != skip {
            visit(st, c);
        }
    }
}

/// Bind the methods and fields a class declares so they shadow same-named symbols.
fn bind_members(st: &mut State<'_>, class: Node<'_>) {
    let Some(body) = class.child_by_field_name("body") else {
        return;
    };
    for m in kids(body) {
        match m.kind() {
            "method_declaration" => {
                if let Some(id) = m.child_by_field_name("name") {
                    let name = st.txt(id).to_owned();
                    st.bind(&name, Binding::Opaque);
                }
            }
            "field_declaration" => {
                for d in kids(m)
                    .into_iter()
                    .filter(|d| d.kind() == "variable_declarator")
                {
                    if let Some(id) = d.child_by_field_name("name") {
                        let name = st.txt(id).to_owned();
                        st.bind(&name, Binding::Opaque);
                    }
                }
            }
            _ => {}
        }
    }
}

/// Bind the parameters a method, lambda, catch or for header introduces as local values.
fn bind_params(st: &mut State<'_>, n: Node<'_>) {
    match n.kind() {
        "enhanced_for_statement" | "catch_clause" | "for_statement" | "block" => {
            if let Some(id) = n.child_by_field_name("name") {
                let name = st.txt(id).to_owned();
                st.bind(&name, Binding::Opaque);
            }
            if n.kind() == "catch_clause" {
                bind_idents(st, n, "catch_formal_parameter");
            }
        }
        "lambda_expression" => {
            if let Some(p) = n.child_by_field_name("parameters") {
                if p.kind() == "identifier" {
                    let name = st.txt(p).to_owned();
                    st.bind(&name, Binding::Opaque);
                } else {
                    bind_idents(st, p, "formal_parameter");
                    for c in kids(p).into_iter().filter(|c| c.kind() == "identifier") {
                        let name = st.txt(c).to_owned();
                        st.bind(&name, Binding::Opaque);
                    }
                }
            }
        }
        _ => {
            if let Some(p) = n.child_by_field_name("parameters") {
                bind_idents(st, p, "formal_parameter");
                bind_idents(st, p, "spread_parameter");
            }
        }
    }
}

/// Bind the `name` of every `kind` descendant of `n` as an opaque local.
fn bind_idents(st: &mut State<'_>, n: Node<'_>, kind: &str) {
    if n.kind() == kind {
        let id = n
            .child_by_field_name("name")
            .or_else(|| kids(n).into_iter().rev().find(|c| c.kind() == "identifier"));
        if let Some(id) = id {
            let name = st.txt(id).to_owned();
            st.bind(&name, Binding::Opaque);
        }
        return;
    }
    for c in kids(n) {
        bind_idents(st, c, kind);
    }
}

/// The canonical symbol path `n` denotes, if it names one.
fn path_of(st: &State<'_>, n: Node<'_>) -> Option<SymPath> {
    match n.kind() {
        "identifier" | "type_identifier" => st.resolve_segs(&[st.txt(n)]),
        "scoped_identifier" | "scoped_type_identifier" => {
            let t = st.txt(n);
            st.resolve_segs(&t.split('.').collect::<Vec<_>>())
        }
        "field_access" => {
            let mut p = path_of(st, n.child_by_field_name("object")?)?;
            p.push(st.txt(n.child_by_field_name("field")?).to_owned());
            Some(st.ctx.project.link(p))
        }
        "generic_type" | "parenthesized_expression" => path_of(st, kids(n).into_iter().next()?),
        "method_invocation" => {
            let name = st.txt(n.child_by_field_name("name")?);
            let Some(obj) = n.child_by_field_name("object") else {
                return st.resolve_segs(&[name]);
            };
            let mut p = path_of(st, obj)?;
            if name != "getRuntime" {
                p.push(name.to_owned());
            }
            Some(st.ctx.project.link(p))
        }
        "object_creation_expression" => path_of(st, n.child_by_field_name("type")?),
        _ => None,
    }
}

/// Rewrite the bare `Paths.get` spelling to the canonical `java.nio.file.Path.of`.
fn canonical(mut p: SymPath) -> SymPath {
    if p.len() >= 2 && p[p.len() - 2] == "Paths" && p[p.len() - 1] == "get" {
        let tail = p.split_off(p.len() - 2);
        drop(tail);
        p.extend(["java", "nio", "file", "Path", "of"].map(str::to_owned));
    }
    p
}

fn do_call(st: &mut State<'_>, n: Node<'_>) {
    let arg_node = n.child_by_field_name("arguments");
    let name = n.child_by_field_name("name").map_or("", |c| st.txt(c));
    let no_args = arg_node.is_none_or(|a| kids(a).is_empty());
    let cp = if name == "printStackTrace" && no_args {
        Some(STACK_TRACE.map(str::to_owned).to_vec())
    } else {
        path_of(st, n).map(canonical)
    };
    let args = arg_node.map_or_else(Args::default, |a| args_of(st, a));
    let hit = cp.as_ref().is_some_and(|p| st.hit_call(n, p, &args));
    let obj = n.child_by_field_name("object");
    visit_parts(st, obj, arg_node, hit);
}

fn do_new(st: &mut State<'_>, n: Node<'_>) {
    let arg_node = n.child_by_field_name("arguments");
    let cp = n.child_by_field_name("type").and_then(|t| path_of(st, t));
    let args = arg_node.map_or_else(Args::default, |a| args_of(st, a));
    let hit = cp.as_ref().is_some_and(|p| st.hit_call(n, p, &args));
    visit_parts(st, None, arg_node, hit);
}

/// Visit the receiver then the arguments; a hit call suppresses bare path hits in both.
fn visit_parts(st: &mut State<'_>, obj: Option<Node<'_>>, arg_node: Option<Node<'_>>, hit: bool) {
    st.scoped_flags(|st| {
        if hit {
            st.in_chain = true;
        }
        if let Some(o) = obj {
            visit(st, o);
        }
        if hit {
            st.suppress = true;
        }
        st.in_chain = false;
        if let Some(a) = arg_node {
            for c in kids(a) {
                visit(st, c);
            }
        }
    });
}

fn args_of(st: &State<'_>, a: Node<'_>) -> Args {
    let pos = kids(a)
        .into_iter()
        .map(|arg| {
            let t = st.txt(arg);
            ArgInfo {
                int: t.parse::<i64>().ok(),
                text: (arg.kind() == "string_literal").then(|| t.trim_matches('"').to_owned()),
                path: path_of(st, arg),
                ..ArgInfo::default()
            }
        })
        .collect();
    Args {
        pos,
        kw: Vec::new(),
    }
}
