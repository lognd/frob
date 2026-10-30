//! The C# scanner: `using` namespaces as glob prefixes, `using static`, `using X = ...` aliases,
//! `global using` (project-wide) and Unity's inherited `MonoBehaviour.print`.

// frob:ticket 01M5XMR67K19SFAWNTDJKKJPTT

use tree_sitter::Node;

use super::catalogue::{ArgInfo, Args};
use super::engine::{Binding, FileScan, State, SymPath, all_kids, kids};

/// Scan one parsed C# compilation unit.
pub fn scan(mut st: State<'_>, root: Node<'_>) -> FileScan {
    for g in &st.ctx.project.globals {
        st.globs.push(g.clone());
    }
    // `using` directives apply file-wide, wherever they appear before use.
    usings(&mut st, root);
    visit(&mut st, root);
    st.finish()
}

fn dotted(text: &str) -> SymPath {
    text.split('.')
        .map(|s| s.trim().to_owned())
        .filter(|s| !s.is_empty())
        .collect()
}

fn usings(st: &mut State<'_>, n: Node<'_>) {
    for c in kids(n) {
        match c.kind() {
            "using_directive" => do_using(st, c),
            "namespace_declaration" | "file_scoped_namespace_declaration" => {
                for k in kids(c) {
                    if k.kind() == "declaration_list" {
                        usings(st, k);
                    }
                }
            }
            _ => {}
        }
    }
}

/// Global usings declared in `root`, as canonical paths (`global using static System.Console`).
#[must_use]
pub fn global_usings(src: &str, root: Node<'_>) -> Vec<SymPath> {
    kids(root)
        .into_iter()
        .filter(|c| c.kind() == "using_directive")
        .filter(|c| {
            all_kids(*c)
                .iter()
                .any(|t| &src[t.byte_range()] == "global")
        })
        .filter(|c| !all_kids(*c).iter().any(|t| &src[t.byte_range()] == "="))
        .filter_map(|c| kids(c).last().map(|k| dotted(&src[k.byte_range()])))
        .collect()
}

fn do_using(st: &mut State<'_>, n: Node<'_>) {
    let toks: Vec<&str> = all_kids(n).into_iter().map(|t| st.txt(t)).collect();
    let is_alias = toks.contains(&"=");
    let ks = kids(n);
    if is_alias {
        if let (Some(a), Some(t)) = (ks.first(), ks.last()) {
            let alias = st.txt(*a).to_owned();
            let target = dotted(st.txt(*t));
            st.bind(&alias, Binding::Alias(target));
        }
    } else if let Some(t) = ks.last() {
        let p = dotted(st.txt(*t));
        st.note(&p);
        st.globs.push(p);
    }
}

fn visit(st: &mut State<'_>, n: Node<'_>) {
    match n.kind() {
        "comment"
        | "using_directive"
        | "string_literal"
        | "verbatim_string_literal"
        | "raw_string_literal"
        | "character_literal"
        | "string_literal_content" => {}
        "class_declaration" => {
            st.push();
            let mono = kids(n)
                .into_iter()
                .filter(|c| c.kind() == "base_list")
                .any(|b| {
                    st.txt(b)
                        .split(|c: char| !c.is_alphanumeric() && c != '_')
                        .any(|w| w == "MonoBehaviour")
                });
            if mono {
                let p: SymPath = ["UnityEngine", "MonoBehaviour", "print"]
                    .iter()
                    .map(|s| (*s).to_owned())
                    .collect();
                st.bind("print", Binding::Alias(p));
            }
            for c in kids(n) {
                visit(st, c);
            }
            st.pop();
        }
        "method_declaration"
        | "constructor_declaration"
        | "local_function_statement"
        | "lambda_expression"
        | "anonymous_method_expression" => {
            st.push();
            for c in kids(n) {
                if c.kind() == "parameter_list" || c.kind() == "parameter" {
                    bind_params(st, c);
                }
            }
            for c in kids(n) {
                visit(st, c);
            }
            st.pop();
        }
        "variable_declarator" => {
            if let Some(id) = kids(n).into_iter().find(|c| c.kind() == "identifier") {
                let name = st.txt(id).to_owned();
                for c in kids(n) {
                    if c.kind() != "identifier" {
                        visit(st, c);
                    }
                }
                st.bind(&name, Binding::Opaque);
            }
        }
        "invocation_expression" => do_call(st, n),
        "member_access_expression" | "identifier" | "qualified_name" => {
            if let Some(p) = path_of(st, n)
                && st.hit_ref(n, &p)
            {
                return;
            }
            if n.kind() == "member_access_expression" {
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

fn bind_params(st: &mut State<'_>, n: Node<'_>) {
    if n.kind() == "parameter" {
        if let Some(id) = n.child_by_field_name("name") {
            let name = st.txt(id).to_owned();
            st.bind(&name, Binding::Opaque);
        }
        return;
    }
    for c in kids(n) {
        bind_params(st, c);
    }
}

fn unbound(st: &State<'_>, name: &str) -> SymPath {
    for g in &st.globs {
        let mut cand = g.clone();
        cand.push(name.to_owned());
        if st.group.any_atom(&cand) {
            return cand;
        }
    }
    vec![name.to_owned()]
}

fn path_of(st: &State<'_>, n: Node<'_>) -> Option<SymPath> {
    match n.kind() {
        "identifier" => {
            let name = st.txt(n);
            match st.lookup(name) {
                Some(Binding::Alias(p)) => Some(p.clone()),
                Some(Binding::Opaque | Binding::Lit(_)) => None,
                None => Some(unbound(st, name)),
            }
        }
        "qualified_name" => {
            let parts = dotted(st.txt(n));
            let (head, rest) = parts.split_first()?;
            let mut base = match st.lookup(head) {
                Some(Binding::Alias(p)) => p.clone(),
                Some(Binding::Opaque | Binding::Lit(_)) => return None,
                None => unbound(st, head),
            };
            base.extend_from_slice(rest);
            Some(st.ctx.project.link(base))
        }
        "member_access_expression" => {
            let e = n.child_by_field_name("expression")?;
            let name = n.child_by_field_name("name")?;
            let mut p = path_of(st, e)?;
            p.push(st.txt(name).to_owned());
            Some(st.ctx.project.link(p))
        }
        "parenthesized_expression" => path_of(st, kids(n).into_iter().next()?),
        _ => None,
    }
}

fn do_call(st: &mut State<'_>, n: Node<'_>) {
    let Some(f) = n.child_by_field_name("function") else {
        return;
    };
    let arg_node = n.child_by_field_name("arguments");
    let cp = path_of(st, f);
    let args = arg_node.map_or_else(Args::default, |a| args_of(st, a));
    let hit = cp.as_ref().is_some_and(|p| st.hit_call(n, p, &args));
    let (saved_suppress, saved_chain) = (st.suppress, st.in_chain);
    if hit {
        st.in_chain = true;
        visit(st, f);
        st.suppress = true;
    } else {
        visit(st, f);
    }
    st.in_chain = false;
    if let Some(a) = arg_node {
        for c in kids(a) {
            visit(st, c);
        }
    }
    st.suppress = saved_suppress;
    st.in_chain = saved_chain;
}

fn args_of(st: &State<'_>, a: Node<'_>) -> Args {
    let pos = kids(a)
        .into_iter()
        .map(|arg| {
            let inner = kids(arg).into_iter().next().unwrap_or(arg);
            let t = st.txt(inner);
            ArgInfo {
                int: t.parse::<i64>().ok(),
                text: (inner.kind().contains("string_literal")).then(|| {
                    t.trim_start_matches(['@', '$'])
                        .trim_matches('"')
                        .to_owned()
                }),
                path: path_of(st, inner),
            }
        })
        .collect();
    Args {
        pos,
        kw: Vec::new(),
    }
}
