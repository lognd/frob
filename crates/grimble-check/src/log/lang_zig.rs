//! The Zig scanner: `const std = @import("std")` and `const print = std.debug.print` aliases,
//! `std.debug.print`, `std.io.getStdOut().writer()` chains, `std.posix.write(1, ..)`, with
//! parameters, locals, captures and own functions shadowing.

// frob:ticket 01M6SD9NZJ8XPWYNGTB233F9ZV

use tree_sitter::Node;

use super::catalogue::{ArgInfo, Args};
use super::engine::{
    Binding, FileScan, State, SymPath, bind_named, kids, name_field, scan_file, visit_scoped,
};

/// Scan one parsed Zig source file.
pub fn scan(st: State<'_>, root: Node<'_>) -> FileScan {
    scan_file(
        st,
        root,
        "zig",
        |st, n| bind_named(st, n, "function_declaration", &name_field),
        visit,
    )
}

fn visit(st: &mut State<'_>, n: Node<'_>) {
    match n.kind() {
        "comment" | "string" | "multiline_string" | "character" => {}
        "function_declaration" => {
            st.push();
            bind_params(st, n);
            visit_scoped(st, n, visit);
            st.pop();
        }
        "block" | "for_statement" | "while_statement" | "if_statement" | "if_expression"
        | "for_expression" | "while_expression" | "switch_case" => {
            st.push();
            for c in kids(n) {
                visit(st, c);
            }
            st.pop();
        }
        "payload" => {
            for id in kids(n).into_iter().filter(|c| c.kind() == "identifier") {
                let name = st.txt(id).to_owned();
                st.bind(&name, Binding::Opaque);
            }
        }
        "variable_declaration" => declaration(st, n),
        "call_expression" => do_call(st, n),
        "identifier" | "field_expression" => {
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

/// Bind the parameters of a function declaration as opaque locals.
fn bind_params(st: &mut State<'_>, f: Node<'_>) {
    for params in kids(f).into_iter().filter(|c| c.kind() == "parameters") {
        for p in kids(params).into_iter().filter(|c| c.kind() == "parameter") {
            if let Some(id) = p.child_by_field_name("name") {
                let name = st.txt(id).to_owned();
                st.bind(&name, Binding::Opaque);
            }
        }
    }
}

/// Handle `const|var name = init;`: alias a plain path or `@import("std")`, else bind opaque.
fn declaration(st: &mut State<'_>, n: Node<'_>) {
    let named = kids(n);
    let Some(id) = named.iter().find(|c| c.kind() == "identifier").copied() else {
        for c in named {
            visit(st, c);
        }
        return;
    };
    let name = st.txt(id).to_owned();
    let ty = n.child_by_field_name("type").map(|t| t.id());
    let init = named
        .iter()
        .rev()
        .find(|c| c.id() != id.id() && Some(c.id()) != ty && c.kind() != "string")
        .copied();
    match init {
        Some(e)
            if matches!(
                e.kind(),
                "identifier" | "field_expression" | "builtin_function"
            ) =>
        {
            if let Some(p) = path_of(st, e) {
                tracing::debug!(name = %name, path = %p.join("."), "zig alias bound");
                st.bind(&name, Binding::Alias(p));
                return;
            }
            visit(st, e);
        }
        Some(e) => visit(st, e),
        None => {}
    }
    st.bind(&name, Binding::Opaque);
}

/// The canonical symbol path `n` denotes, if it names one.
fn path_of(st: &State<'_>, n: Node<'_>) -> Option<SymPath> {
    match n.kind() {
        "identifier" => st.resolve_segs(&[st.txt(n)]),
        "field_expression" => {
            let mut p = path_of(st, n.child_by_field_name("object")?)?;
            p.push(st.txt(n.child_by_field_name("member")?).to_owned());
            Some(st.ctx.project.link(p))
        }
        "call_expression" => path_of(st, n.child_by_field_name("function")?),
        "parenthesized_expression" | "dereference_expression" | "null_coercion_expression" => {
            path_of(st, kids(n).into_iter().next()?)
        }
        "builtin_function" => {
            let is_import = kids(n)
                .iter()
                .any(|c| c.kind() == "builtin_identifier" && st.txt(*c) == "@import");
            let arg = kids(n).into_iter().find(|c| c.kind() == "arguments")?;
            let lit = kids(arg).into_iter().find(|c| c.kind() == "string")?;
            (is_import && st.txt(lit) == "\"std\"").then(|| vec!["std".to_owned()])
        }
        _ => None,
    }
}

fn do_call(st: &mut State<'_>, n: Node<'_>) {
    let func = n.child_by_field_name("function");
    let arg_nodes: Vec<Node<'_>> = kids(n)
        .into_iter()
        .filter(|c| Some(c.id()) != func.map(|f| f.id()))
        .collect();
    let args = args_of(st, &arg_nodes);
    let hit = func
        .and_then(|f| path_of(st, f))
        .is_some_and(|p| st.hit_call(n, &p, &args));
    st.scoped_flags(|st| {
        if hit {
            st.in_chain = true;
        }
        if let Some(f) = func {
            visit_callee(st, f);
        }
        if hit {
            st.suppress = true;
        }
        st.in_chain = false;
        for a in arg_nodes {
            visit(st, a);
        }
    });
}

/// Visit the callee of a call: only its receiver chain, never the callee path itself as a ref.
fn visit_callee(st: &mut State<'_>, f: Node<'_>) {
    if f.kind() == "field_expression" {
        if let Some(o) = f.child_by_field_name("object") {
            visit(st, o);
        }
    } else if f.kind() != "identifier" {
        visit(st, f);
    }
}

fn args_of(st: &State<'_>, nodes: &[Node<'_>]) -> Args {
    let pos = nodes
        .iter()
        .map(|arg| {
            let t = st.txt(*arg);
            ArgInfo {
                int: t.parse::<i64>().ok(),
                text: (arg.kind() == "string").then(|| t.trim_matches('"').to_owned()),
                path: path_of(st, *arg),
                ..ArgInfo::default()
            }
        })
        .collect();
    Args {
        pos,
        kw: Vec::new(),
    }
}
