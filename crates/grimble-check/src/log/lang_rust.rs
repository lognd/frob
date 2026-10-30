//! The Rust scanner: `use` trees, macro token trees and path expressions over tree-sitter-rust.

// frob:ticket 01M5XMR67K19SFAWNTDJKKJPTT

use tree_sitter::Node;

use super::catalogue::{ArgInfo, Args};
use super::engine::{Binding, FileScan, State, SymPath, all_kids, kids};

/// Scan one parsed Rust file.
pub fn scan(mut st: State<'_>, root: Node<'_>) -> FileScan {
    scope(&mut st, root);
    st.finish()
}

/// Canonicalise a path: drop `crate`/`self`/`super` heads and map `core`/`alloc` to `std`.
fn canon(mut p: SymPath) -> SymPath {
    while p.len() > 1 && matches!(p[0].as_str(), "crate" | "self" | "super") {
        p.remove(0);
    }
    if let Some(h) = p.first_mut()
        && (h == "core" || h == "alloc")
    {
        "std".clone_into(h);
    }
    p
}

/// Visit the items of one scope: `use` declarations first (they are order independent).
fn scope(st: &mut State<'_>, parent: Node<'_>) {
    let items = kids(parent);
    for c in &items {
        if c.kind() == "use_declaration"
            && let Some(a) = c.child_by_field_name("argument")
        {
            do_use(st, a, &[]);
        }
    }
    for c in items {
        if c.kind() != "use_declaration" {
            visit(st, c);
        }
    }
}

fn segs(st: &State<'_>, n: Node<'_>) -> SymPath {
    st.txt(n)
        .split("::")
        .map(|s| s.trim().to_owned())
        .filter(|s| !s.is_empty())
        .collect()
}

fn bind_use(st: &mut State<'_>, name: &str, path: SymPath) {
    if name == "_" {
        return;
    }
    let linked = st.ctx.project.link(canon(path));
    st.bind(name, Binding::Alias(linked));
}

fn do_use(st: &mut State<'_>, n: Node<'_>, prefix: &[String]) {
    match n.kind() {
        "identifier" | "scoped_identifier" | "self" | "crate" | "super" => {
            let mut full: SymPath = prefix.to_vec();
            full.extend(segs(st, n));
            let name = if full.last().is_some_and(|l| l == "self") && full.len() > 1 {
                full.pop();
                full.last().cloned()
            } else {
                full.last().cloned()
            };
            if let Some(name) = name {
                bind_use(st, &name, full);
            }
        }
        "use_as_clause" => {
            let (Some(p), Some(a)) = (
                n.child_by_field_name("path"),
                n.child_by_field_name("alias"),
            ) else {
                return;
            };
            let mut full: SymPath = prefix.to_vec();
            full.extend(segs(st, p));
            let alias = st.txt(a).to_owned();
            bind_use(st, &alias, full);
        }
        "scoped_use_list" => {
            let mut pre: SymPath = prefix.to_vec();
            if let Some(p) = n.child_by_field_name("path") {
                pre.extend(segs(st, p));
            }
            if let Some(l) = n.child_by_field_name("list") {
                for c in kids(l) {
                    do_use(st, c, &pre);
                }
            }
        }
        "use_list" => {
            for c in kids(n) {
                do_use(st, c, prefix);
            }
        }
        "use_wildcard" => {
            let mut full: SymPath = prefix.to_vec();
            if let Some(p) = kids(n).into_iter().next() {
                full.extend(segs(st, p));
            }
            let full = canon(full);
            st.note(&full);
            st.globs.push(full);
        }
        _ => {}
    }
}

/// Bind every plain identifier of a pattern as a local value.
fn bind_pattern(st: &mut State<'_>, n: Node<'_>) {
    match n.kind() {
        "identifier" => {
            let name = st.txt(n).to_owned();
            st.bind(&name, Binding::Opaque);
        }
        "scoped_identifier" | "string_literal" | "integer_literal" => {}
        _ => {
            for c in kids(n) {
                bind_pattern(st, c);
            }
        }
    }
}

fn visit(st: &mut State<'_>, n: Node<'_>) {
    match n.kind() {
        "line_comment"
        | "block_comment"
        | "attribute_item"
        | "inner_attribute_item"
        | "string_literal"
        | "raw_string_literal"
        | "char_literal"
        | "use_declaration" => {}
        "macro_definition" => {
            if let Some(name) = n.child_by_field_name("name") {
                let name = st.txt(name).to_owned();
                st.bind(&name, Binding::Opaque);
            }
        }
        "mod_item" => {
            st.push();
            if let Some(b) = n.child_by_field_name("body") {
                scope(st, b);
            }
            st.pop();
        }
        "block" | "declaration_list" => {
            st.push();
            scope(st, n);
            st.pop();
        }
        "function_item" | "closure_expression" => {
            if n.kind() == "function_item"
                && let Some(name) = n.child_by_field_name("name")
            {
                let name = st.txt(name).to_owned();
                st.bind(&name, Binding::Opaque);
            }
            st.push();
            if let Some(p) = n.child_by_field_name("parameters") {
                bind_pattern(st, p);
            }
            if let Some(b) = n.child_by_field_name("body") {
                visit(st, b);
            }
            st.pop();
        }
        "let_declaration" => do_let(st, n),
        "for_expression" => {
            if let Some(v) = n.child_by_field_name("value") {
                visit(st, v);
            }
            st.push();
            if let Some(p) = n.child_by_field_name("pattern") {
                bind_pattern(st, p);
            }
            if let Some(b) = n.child_by_field_name("body") {
                visit(st, b);
            }
            st.pop();
        }
        "let_condition" | "match_arm" => {
            if let Some(v) = n.child_by_field_name("value") {
                visit(st, v);
            }
            if let Some(p) = n.child_by_field_name("pattern") {
                bind_pattern(st, p);
            }
            for c in kids(n) {
                if Some(c.id()) != n.child_by_field_name("pattern").map(|p| p.id())
                    && Some(c.id()) != n.child_by_field_name("value").map(|p| p.id())
                {
                    visit(st, c);
                }
            }
        }
        "macro_invocation" => do_macro(st, n),
        "call_expression" => do_call(st, n),
        "scoped_identifier"
        | "scoped_type_identifier"
        | "field_expression"
        | "identifier"
        | "type_identifier"
        | "generic_type" => {
            if let Some(p) = path_of(st, n, false, true)
                && st.hit_ref(n, &p)
            {
                return;
            }
            if matches!(n.kind(), "field_expression") {
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

fn do_let(st: &mut State<'_>, n: Node<'_>) {
    let pat = n.child_by_field_name("pattern");
    let val = n.child_by_field_name("value");
    if let Some(ty) = n.child_by_field_name("type") {
        visit(st, ty);
    }
    match (pat, val) {
        (Some(p), Some(v)) if p.kind() == "identifier" => {
            let name = st.txt(p).to_owned();
            match path_of(st, v, false, false) {
                Some(path) if st.group.any_atom(&path) => st.bind(&name, Binding::Alias(path)),
                _ => {
                    visit(st, v);
                    st.bind(&name, Binding::Opaque);
                }
            }
        }
        (p, v) => {
            if let Some(v) = v {
                visit(st, v);
            }
            if let Some(p) = p {
                bind_pattern(st, p);
            }
            if let Some(e) = n.child_by_field_name("alternative") {
                visit(st, e);
            }
        }
    }
}

fn do_macro(st: &mut State<'_>, n: Node<'_>) {
    let Some(m) = n.child_by_field_name("macro") else {
        return;
    };
    let tt = kids(n).into_iter().find(|c| c.kind() == "token_tree");
    let path = path_of(st, m, true, false);
    let hit = path
        .as_ref()
        .is_some_and(|p| st.hit_call(n, p, &Args::default()));
    let saved = st.suppress;
    if hit {
        st.suppress = true;
    }
    if let Some(t) = tt {
        tokens(st, t);
    }
    st.suppress = saved;
}

/// Scan a macro token tree for paths, calls and nested macro invocations.
fn tokens(st: &mut State<'_>, tt: Node<'_>) {
    let items = all_kids(tt);
    let mut i = 0;
    while i < items.len() {
        let c = items[i];
        match c.kind() {
            "identifier" | "scoped_identifier" => {
                let after_dot = i > 0 && items[i - 1].kind() == ".";
                let after_path = i > 0 && items[i - 1].kind() == "::";
                // Collect `a :: b :: c` runs written as separate tokens.
                let mut parts: SymPath = segs(st, c);
                let mut j = i + 1;
                while j + 1 < items.len()
                    && items[j].kind() == "::"
                    && matches!(items[j + 1].kind(), "identifier" | "scoped_identifier")
                {
                    parts.extend(segs(st, items[j + 1]));
                    j += 2;
                }
                if after_dot || after_path {
                    i = j;
                    continue;
                }
                let next = items.get(j);
                let is_macro = next.is_some_and(|x| x.kind() == "!")
                    && items.get(j + 1).is_some_and(|x| x.kind() == "token_tree");
                let resolved = resolve_parts(st, &parts, is_macro);
                if is_macro {
                    let hit = resolved
                        .as_ref()
                        .is_some_and(|p| st.hit_call(c, p, &Args::default()));
                    let saved = st.suppress;
                    if hit {
                        st.suppress = true;
                    }
                    tokens(st, items[j + 1]);
                    st.suppress = saved;
                    i = j + 2;
                    continue;
                }
                if next.is_some_and(|x| x.kind() == "token_tree") {
                    let hit = resolved
                        .as_ref()
                        .is_some_and(|p| st.hit_call(c, p, &Args::default()));
                    let saved = st.suppress;
                    if hit {
                        st.suppress = true;
                    }
                    if let Some(t) = next {
                        tokens(st, *t);
                    }
                    st.suppress = saved;
                    i = j + 1;
                    continue;
                }
                if let Some(p) = resolved {
                    st.hit_ref(c, &p);
                }
                i = j;
                continue;
            }
            "token_tree" => tokens(st, c),
            _ => {}
        }
        i += 1;
    }
}

fn resolve_parts(st: &State<'_>, parts: &[String], is_macro: bool) -> Option<SymPath> {
    let (head, rest) = parts.split_first()?;
    let mut base = match st.lookup(head) {
        Some(Binding::Alias(p)) => p.clone(),
        Some(Binding::Opaque | Binding::Lit(_)) => return None,
        None => unbound(st, head, is_macro && rest.is_empty()),
    };
    base.extend_from_slice(rest);
    Some(st.ctx.project.link(canon(base)))
}

fn unbound(st: &State<'_>, name: &str, as_macro: bool) -> SymPath {
    if as_macro {
        return vec!["std".to_owned(), name.to_owned()];
    }
    for g in &st.globs {
        let mut cand = g.clone();
        cand.push(name.to_owned());
        if st.group.any_atom(&cand) {
            return cand;
        }
    }
    vec![name.to_owned()]
}

fn do_call(st: &mut State<'_>, n: Node<'_>) {
    let Some(f) = n.child_by_field_name("function") else {
        return;
    };
    let arg_node = n.child_by_field_name("arguments");
    let cp = path_of(st, f, false, true);
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

fn args_of(st: &mut State<'_>, a: Node<'_>) -> Args {
    let pos = kids(a)
        .into_iter()
        .filter(|c| !matches!(c.kind(), "line_comment" | "block_comment"))
        .map(|c| arg_info(st, c))
        .collect();
    Args {
        pos,
        kw: Vec::new(),
    }
}

fn arg_info(st: &mut State<'_>, n: Node<'_>) -> ArgInfo {
    let int = (n.kind() == "integer_literal")
        .then(|| {
            let t: String = st.txt(n).chars().take_while(char::is_ascii_digit).collect();
            t.parse::<i64>().ok()
        })
        .flatten();
    let text = (n.kind() == "string_literal").then(|| {
        kids(n)
            .into_iter()
            .filter(|c| c.kind() == "string_content")
            .map(|c| st.txt(c))
            .collect::<String>()
    });
    ArgInfo {
        int,
        text,
        path: path_of(st, n, false, true),
    }
}

/// The symbol path an expression denotes. `value_calls` lets a call stand for its callee.
fn path_of(st: &mut State<'_>, n: Node<'_>, is_macro: bool, value_calls: bool) -> Option<SymPath> {
    match n.kind() {
        "identifier" | "type_identifier" | "crate" | "super" | "self" => {
            let parts = vec![st.txt(n).to_owned()];
            resolve_parts(st, &parts, is_macro)
        }
        "scoped_identifier" | "scoped_type_identifier" => {
            let parts = segs(st, n);
            resolve_parts(st, &parts, is_macro)
        }
        "generic_type" | "generic_function" => {
            let inner = n
                .child_by_field_name("type")
                .or_else(|| n.child_by_field_name("function"))?;
            path_of(st, inner, is_macro, value_calls)
        }
        "field_expression" => {
            let v = n.child_by_field_name("value")?;
            let f = n.child_by_field_name("field")?;
            let mut p = path_of(st, v, false, true)?;
            p.push(st.txt(f).to_owned());
            Some(p)
        }
        "call_expression" if value_calls => {
            let f = n.child_by_field_name("function")?;
            let mut p = path_of(st, f, false, true)?;
            if p.len() > 1 && p.last().is_some_and(|l| l == "new") {
                p.pop();
            }
            Some(p)
        }
        "parenthesized_expression"
        | "reference_expression"
        | "try_expression"
        | "await_expression" => path_of(st, kids(n).into_iter().next()?, false, value_calls),
        _ => None,
    }
}
