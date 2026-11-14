//! The C and C++ scanner: calls and `std::` paths, `using` aliases and globs, stream arguments
//! (`fprintf(stderr, ..)`), the `<<` chain on `std::cout`, `#define` bodies (re-parsed), with
//! parameters, locals and own functions shadowing.

// frob:ticket 01M63G1MW58WP8VBQ7T6NKDAMD

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use tree_sitter::Node;

use super::catalogue::{ArgInfo, Args};
use super::engine::{Binding, FileScan, State, SymPath, bind_named, kids, scan_file};

/// The atom id for stream-taking stdio functions (`fprintf`, `fputs`, ...).
const STDIO_STREAM: &str = "c.stdio-stream";

/// Scan one parsed C or C++ translation unit.
pub fn scan(st: State<'_>, root: Node<'_>) -> FileScan {
    scan_file(
        st,
        root,
        "c",
        |st, n| {
            bind_named(st, n, "function_definition", &|st, f| {
                f.child_by_field_name("declarator")
                    .and_then(|d| decl_name(st, d))
            });
        },
        visit,
    )
}

/// The name a declarator declares, looking through pointers, arrays and function declarators.
fn decl_name(st: &State<'_>, n: Node<'_>) -> Option<String> {
    match n.kind() {
        "identifier" | "field_identifier" | "type_identifier" => Some(st.txt(n).to_owned()),
        "qualified_identifier" => decl_name(st, n.child_by_field_name("name")?),
        _ => {
            let inner = n
                .child_by_field_name("declarator")
                .or_else(|| kids(n).into_iter().next())?;
            decl_name(st, inner)
        }
    }
}

fn visit(st: &mut State<'_>, n: Node<'_>) {
    match n.kind() {
        "comment"
        | "string_literal"
        | "raw_string_literal"
        | "char_literal"
        | "concatenated_string"
        | "preproc_include"
        | "system_lib_string" => {
            include_note(st, n);
        }
        "preproc_def" | "preproc_function_def" => define(st, n),
        "using_declaration" => using(st, n),
        "namespace_alias_definition" => ns_alias(st, n),
        "function_definition" => {
            st.push();
            bind_params(st, n);
            if let Some(body) = n.child_by_field_name("body") {
                visit(st, body);
            }
            st.pop();
        }
        "lambda_expression" => {
            st.push();
            for c in kids(n)
                .into_iter()
                .filter(|c| c.kind() != "compound_statement")
            {
                bind_all_params(st, c);
            }
            for c in kids(n)
                .into_iter()
                .filter(|c| c.kind() == "compound_statement")
            {
                visit(st, c);
            }
            st.pop();
        }
        "compound_statement" => {
            st.push();
            for c in kids(n) {
                visit(st, c);
            }
            st.pop();
        }
        "declaration" => declaration(st, n),
        "call_expression" => do_call(st, n),
        "identifier" | "qualified_identifier" => {
            if let Some(p) = path_of(st, n) {
                st.hit_ref(n, &p);
            }
        }
        _ => {
            for c in kids(n) {
                visit(st, c);
            }
        }
    }
}

/// An `#include <dir/lib.h>` of a logging library marks logging as configured.
fn include_note(st: &mut State<'_>, n: Node<'_>) {
    if n.kind() != "system_lib_string" && n.kind() != "preproc_include" {
        return;
    }
    let raw = st.txt(n);
    let Some(start) = raw.find(['<', '"']) else {
        return;
    };
    let inner = raw[start + 1..].trim_end_matches(['>', '"', '\n', '\r', ' ']);
    if !inner.contains('/') {
        return;
    }
    let mut segs: SymPath = inner.split('/').map(str::to_owned).collect();
    if let Some(last) = segs.last_mut()
        && let Some((stem, _)) = last.split_once('.')
    {
        *last = stem.to_owned();
    }
    st.note(&segs);
}

/// A `declaration` binds the declared names after visiting their initialisers.
fn declaration(st: &mut State<'_>, n: Node<'_>) {
    for c in kids(n) {
        match c.kind() {
            "init_declarator" => {
                if let Some(v) = c.child_by_field_name("value") {
                    visit(st, v);
                }
                bind_decl(st, c);
            }
            "identifier" | "pointer_declarator" | "array_declarator" | "reference_declarator" => {
                bind_decl(st, c);
            }
            _ => visit(st, c),
        }
    }
}

fn bind_decl(st: &mut State<'_>, d: Node<'_>) {
    if let Some(name) = decl_name(st, d) {
        st.bind(&name, Binding::Opaque);
    }
}

/// Bind the parameters of a function definition.
fn bind_params(st: &mut State<'_>, f: Node<'_>) {
    if let Some(d) = f.child_by_field_name("declarator") {
        bind_all_params(st, d);
    }
}

/// Bind the name of every `parameter_declaration` below `n`.
fn bind_all_params(st: &mut State<'_>, n: Node<'_>) {
    if matches!(
        n.kind(),
        "parameter_declaration"
            | "optional_parameter_declaration"
            | "variadic_parameter_declaration"
    ) {
        if let Some(d) = n.child_by_field_name("declarator") {
            bind_decl(st, d);
        }
        return;
    }
    for c in kids(n) {
        bind_all_params(st, c);
    }
}

/// `using std::cerr;` aliases the name; `using namespace std;` opens a glob.
fn using(st: &mut State<'_>, n: Node<'_>) {
    let text = st.txt(n).trim().trim_end_matches(';').trim();
    let Some(rest) = text.strip_prefix("using") else {
        return;
    };
    let rest = rest.trim();
    if let Some(ns) = rest.strip_prefix("namespace") {
        let path: SymPath = ns
            .trim()
            .split("::")
            .filter(|s| !s.is_empty())
            .map(|s| s.trim().to_owned())
            .collect();
        st.note(&path);
        st.globs.push(path);
    } else if rest.contains('<') || rest.contains('=') {
        // `using T = ...;` alias declarations and templates are not followed
    } else {
        let path: SymPath = rest
            .split("::")
            .filter(|s| !s.is_empty())
            .map(|s| s.trim().to_owned())
            .collect();
        if let Some(last) = path.last().cloned() {
            st.bind(&last, Binding::Alias(path));
        }
    }
}

/// `namespace fs = std::filesystem;`
fn ns_alias(st: &mut State<'_>, n: Node<'_>) {
    let text = st.txt(n).trim().trim_end_matches(';').trim();
    let Some((lhs, rhs)) = text.split_once('=') else {
        return;
    };
    let name = lhs.trim().trim_start_matches("namespace").trim().to_owned();
    let path: SymPath = rhs
        .trim()
        .split("::")
        .filter(|s| !s.is_empty())
        .map(|s| s.trim().to_owned())
        .collect();
    if !name.is_empty() && !path.is_empty() {
        st.bind(&name, Binding::Alias(path));
    }
}

/// A `#define` body is re-parsed as a statement; its hits are reported at the define.
fn define(st: &mut State<'_>, n: Node<'_>) {
    let Some(value) = n.child_by_field_name("value") else {
        return;
    };
    let body = st
        .txt(value)
        .replace("\\\r\n", " ")
        .replace("\\\n", " ")
        .replace("##", " ")
        .replace('#', " ");
    let text = format!("void grimble_macro(void) {{ {} ; }}", body.trim());
    let ParseResult::Parsed(tree) = parse(Language::Cpp, &text, &ParseLimits::default()) else {
        tracing::debug!(file = %st.ctx.path, "macro body did not parse");
        return;
    };
    let mut inner = State::new(st.group, st.ctx, &text);
    inner.frames.clone_from(&st.frames);
    inner.globs.clone_from(&st.globs);
    inner.push();
    if let Some(params) = n.child_by_field_name("parameters") {
        for p in kids(params)
            .into_iter()
            .filter(|p| p.kind() == "identifier")
        {
            let name = st.txt(p).to_owned();
            inner.bind(&name, Binding::Opaque);
        }
    }
    visit(&mut inner, tree.root());
    let scan = inner.finish_nested();
    st.logging_seen |= scan.logging_seen;
    for h in scan.hits {
        st.hits.push(super::engine::Hit {
            start: n.start_byte(),
            end: n.end_byte(),
            ..h
        });
    }
}

/// The canonical symbol path `n` denotes, if it names one.
fn path_of(st: &State<'_>, n: Node<'_>) -> Option<SymPath> {
    match n.kind() {
        "identifier" | "type_identifier" | "namespace_identifier" => st.resolve_segs(&[st.txt(n)]),
        "qualified_identifier" => {
            let t = st.txt(n);
            if t.contains(['<', '(', ' ']) {
                return None;
            }
            let segs: Vec<&str> = t.split("::").filter(|s| !s.is_empty()).collect();
            st.resolve_segs(&segs)
        }
        "template_function" => path_of(st, n.child_by_field_name("name")?),
        "parenthesized_expression" => path_of(st, kids(n).into_iter().next()?),
        _ => None,
    }
}

/// The std stream a plain identifier argument names (`stdout`, `stderr`), when not shadowed.
fn std_stream(st: &State<'_>, n: Node<'_>) -> bool {
    let t = st.txt(n);
    matches!(t, "stdout" | "stderr") && st.lookup(t).is_none()
}

/// The int an fd argument denotes: a literal, or `STDOUT_FILENO` / `STDERR_FILENO`.
fn fd_int(st: &State<'_>, n: Node<'_>) -> Option<i64> {
    match st.txt(n) {
        "STDOUT_FILENO" => Some(1),
        "STDERR_FILENO" => Some(2),
        t => t.parse::<i64>().ok(),
    }
}

fn do_call(st: &mut State<'_>, n: Node<'_>) {
    let func = n.child_by_field_name("function");
    let arg_node = n.child_by_field_name("arguments");
    let cp = func.and_then(|f| path_of(st, f));
    let arg_list = arg_node.map(kids).unwrap_or_default();
    let args = Args {
        pos: arg_list
            .iter()
            .enumerate()
            .map(|(i, a)| ArgInfo {
                int: if i == 0 { fd_int(st, *a) } else { None },
                text: None,
                path: path_of(st, *a),
                ..ArgInfo::default()
            })
            .collect(),
        kw: Vec::new(),
    };
    let hit = match &cp {
        Some(p) => {
            let is_stream_fn = st
                .group
                .atoms
                .iter()
                .any(|a| a.id == STDIO_STREAM && a.matches_path(p));
            let to_std = is_stream_fn
                && (arg_list.iter().any(|a| std_stream(st, *a))
                    || (matches!(p.last().map(String::as_str), Some("dprintf" | "vdprintf"))
                        && matches!(args.pos.first().and_then(|a| a.int), Some(1 | 2))));
            if to_std {
                st.hit_atom(n, STDIO_STREAM, p)
            } else {
                st.hit_call(n, p, &args)
            }
        }
        None => false,
    };
    st.scoped_flags(|st| {
        if hit {
            st.in_chain = true;
        }
        if cp.is_none()
            && let Some(f) = func
        {
            visit(st, f);
        }
        if hit {
            st.suppress = true;
        }
        st.in_chain = false;
        for a in arg_list {
            visit(st, a);
        }
    });
}
