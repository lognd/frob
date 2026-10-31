//! Server routes: `FastAPI` and Flask decorators, Express handlers and axum `route` calls, read from the
//! folded terms of the declaring file.

// frob:ticket 01M4GM5DE96WY2ZDRZP0ETTMMF

use std::collections::BTreeMap;

use gob_ir::{NodeId, Operator, Term, Universal};
use tracing::{debug, trace};

use super::File;
use super::read::{
    Part, Parts, adapter, is_apply, join_paths, last_segment, leaves, line_of, lit,
    normalize_server, path_of, py_parts, ref_name, rs_parts, ts_parts, unit_names, unquote,
};
use crate::types::{Method, Route, Status};

/// The verbs a decorator or router method names.
const VERBS: [&str; 7] = ["get", "post", "put", "patch", "delete", "head", "options"];

/// The method named by a lower-case verb.
fn verb(name: &str) -> Option<Method> {
    Method::from_export(&name.to_ascii_uppercase())
}

/// A route prefix: known text, or a value that could not be read.
#[derive(Debug, Clone, PartialEq, Eq)]
enum Prefix {
    Known(String),
    Opaque,
}

impl Prefix {
    /// The prefix of a string value; the empty prefix when there is none.
    fn of(parts: Parts) -> Self {
        let path = path_of(parts);
        match (path.pattern, path.status) {
            (Some(p), Status::Must) => Self::Known(p),
            _ => Self::Opaque,
        }
    }
}

fn route(f: &File<'_>, framework: &'static str, at: NodeId) -> Route {
    Route {
        framework,
        member: String::new(),
        pattern: None,
        method: Method::Any,
        handler: None,
        component: None,
        layouts: Vec::new(),
        status: Status::Unknown,
        file: f.path.to_owned(),
        line: line_of(f.text, f.term, at),
        client: false,
    }
}

/// One argument of a Python decorator call.
struct PyArg {
    name: Option<String>,
    tokens: Vec<(String, String)>,
}

/// The arguments of the decorator `attr`, split at top-level commas.
fn py_args(term: &Term, attr: NodeId) -> Vec<PyArg> {
    let toks = leaves_of_children(term, attr);
    let inner = match (toks.first(), toks.last()) {
        (Some(a), Some(b)) if a.0 == "(" && b.0 == ")" => &toks[1..toks.len() - 1],
        _ => return Vec::new(),
    };
    let mut args = Vec::new();
    let (mut cur, mut depth, mut in_str) = (Vec::new(), 0_i32, false);
    let mut push = |cur: &mut Vec<(String, String)>| {
        if cur.is_empty() {
            return;
        }
        let toks = std::mem::take(cur);
        if toks.len() > 2 && toks[0].0 == "identifier" && toks[1].0 == "=" {
            args.push(PyArg {
                name: Some(toks[0].1.clone()),
                tokens: toks[2..].to_vec(),
            });
        } else {
            args.push(PyArg {
                name: None,
                tokens: toks,
            });
        }
    };
    for t in inner {
        match t.0.as_str() {
            "string_start" => in_str = true,
            "string_end" => in_str = false,
            "(" | "[" | "{" if !in_str => depth += 1,
            ")" | "]" | "}" if !in_str => depth -= 1,
            "," if !in_str && depth == 0 => {
                push(&mut cur);
                continue;
            }
            _ => {}
        }
        cur.push(t.clone());
    }
    push(&mut cur);
    args
}

/// The literal tokens among the children of `id` (a decorator's flattened arguments).
fn leaves_of_children(term: &Term, id: NodeId) -> Vec<(String, String)> {
    term.node(id)
        .children()
        .iter()
        .filter_map(|&c| lit(term, c).map(|(k, l)| (k.to_owned(), l.to_owned())))
        .collect()
}

/// The string value of the keyword argument `key` among the `call_args` of a Python call.
fn kwarg(term: &Term, call_args: &[NodeId], key: &str) -> Option<Parts> {
    call_args.iter().find_map(|&a| {
        if adapter(term, a) != Some("keyword_argument") {
            return None;
        }
        let kids = term.node(a).children();
        let (_, name) = lit(term, *kids.first()?)?;
        if name != key {
            return None;
        }
        let value = *kids.last()?;
        Some(match lit(term, value) {
            Some(("string", s)) => Some(vec![Part::Lit(unquote(s))]),
            _ => py_parts(&leaves(term, value)),
        })
    })
}

/// Prefixes of the routers, apps and blueprints a Python file builds or includes.
#[derive(Default)]
struct Routers {
    own: BTreeMap<String, Prefix>,
    outer: BTreeMap<String, Prefix>,
}

impl Routers {
    /// The full prefix of the router variable `var`, outermost first.
    fn prefix(&self, var: &str) -> Prefix {
        let own = self
            .own
            .get(var)
            .cloned()
            .unwrap_or_else(|| Prefix::Known(String::new()));
        let outer = self
            .outer
            .get(var)
            .cloned()
            .unwrap_or_else(|| Prefix::Known(String::new()));
        match (outer, own) {
            (Prefix::Known(a), Prefix::Known(b)) => Prefix::Known(join_paths(&a, &b)),
            _ => Prefix::Opaque,
        }
    }
}

fn read_routers(f: &File<'_>) -> Routers {
    let term = f.term;
    let mut out = Routers::default();
    for id in term.ids() {
        if adapter(term, id) == Some("assignment") {
            let kids = term.node(id).children();
            let (Some(&target), Some(&value)) = (kids.first(), kids.last()) else {
                continue;
            };
            let Some(var) = ref_name(term, target) else {
                continue;
            };
            if !is_apply(term, value, "call") {
                continue;
            }
            let call = term.node(value).children();
            let Some(callee) = call.first().and_then(|&c| ref_name(term, c)) else {
                continue;
            };
            if !matches!(
                last_segment(callee),
                "APIRouter" | "Blueprint" | "`FastAPI`" | "Flask"
            ) {
                continue;
            }
            let prefix = ["prefix", "url_prefix"]
                .iter()
                .find_map(|k| kwarg(term, call, k))
                .map_or_else(|| Prefix::Known(String::new()), Prefix::of);
            trace!(var, ?prefix, "router prefix");
            out.own.insert(var.to_owned(), prefix);
        } else if is_apply(term, id, "call") {
            let call = term.node(id).children();
            let Some(callee) = call.first().and_then(|&c| ref_name(term, c)) else {
                continue;
            };
            if !(callee.ends_with(".include_router") || callee.ends_with(".register_blueprint")) {
                continue;
            }
            let Some(var) = call.get(1).and_then(|&c| ref_name(term, c)) else {
                continue;
            };
            if let Some(p) = ["prefix", "url_prefix"]
                .iter()
                .find_map(|k| kwarg(term, call, k))
            {
                out.outer.insert(var.to_owned(), Prefix::of(p));
            }
        }
    }
    out
}

/// `FastAPI` and Flask routes declared by decorators in a Python file.
pub(super) fn python_routes(f: &File<'_>) -> Vec<Route> {
    let framework = if f.text.contains("fastapi") {
        "fastapi"
    } else if f.text.contains("flask") {
        "flask"
    } else {
        return Vec::new();
    };
    let term = f.term;
    let routers = read_routers(f);
    let mut out = Vec::new();
    for id in term.ids() {
        let Operator::Universal(Universal::Attr { name }) = term.node(id).op() else {
            continue;
        };
        let Some(unit) = term.node(id).parent() else {
            continue;
        };
        if !matches!(term.node(unit).op(), Operator::Universal(Universal::Unit { kind, .. }) if kind == "function")
        {
            continue;
        }
        let Some((var, m)) = name.rsplit_once('.') else {
            continue;
        };
        if !(VERBS.contains(&m) || m == "route" || m == "api_route") {
            continue;
        }
        let args = py_args(term, id);
        let Some(path_arg) = args
            .iter()
            .find(|a| a.name.is_none() || matches!(a.name.as_deref(), Some("path" | "rule")))
        else {
            continue;
        };
        let path = path_of(py_parts(&path_arg.tokens));
        let mut methods: Vec<(Method, Status)> = Vec::new();
        if let Some(v) = verb(m) {
            methods.push((v, Status::Must));
        } else if let Some(a) = args.iter().find(|a| a.name.as_deref() == Some("methods")) {
            let names: Vec<&str> = a
                .tokens
                .iter()
                .filter(|t| t.0 == "string_content")
                .map(|t| t.1.as_str())
                .collect();
            let all_strings = a.tokens.iter().all(|t| {
                matches!(
                    t.0.as_str(),
                    "[" | "]" | "," | "(" | ")" | "string_start" | "string_content" | "string_end"
                )
            });
            if all_strings && !names.is_empty() {
                methods.extend(names.iter().map(|n| {
                    (
                        Method::from_export(&n.to_ascii_uppercase()).unwrap_or(Method::Any),
                        Status::Must,
                    )
                }));
            } else {
                methods.push((Method::Any, Status::May));
            }
        } else {
            methods.push((Method::Get, Status::Must));
        }
        let handler = term.symref_of(unit).map(ToString::to_string);
        let prefix = routers.prefix(var);
        for (method, mstatus) in methods {
            let mut r = route(f, framework, id);
            r.method = method;
            r.handler.clone_from(&handler);
            match (&prefix, &path.pattern) {
                (Prefix::Known(pre), Some(p)) => {
                    r.pattern = Some(normalize_server(&join_paths(pre, p)));
                    r.status = path.status.meet(mstatus);
                }
                _ => r.status = Status::Unknown,
            }
            debug!(file = f.path, pattern = ?r.pattern, method = r.method.as_str(), "python route");
            out.push(r);
        }
    }
    out
}

/// Express routes: `app.get('/x', handler)` style calls in a file that imports express.
pub(super) fn express_routes(f: &File<'_>) -> Vec<Route> {
    if !f.text.contains("express") {
        return Vec::new();
    }
    let term = f.term;
    let names = unit_names(term);
    let mut out = Vec::new();
    for id in term.ids() {
        if !is_apply(term, id, "call") {
            continue;
        }
        let kids = term.node(id).children();
        let Some(callee) = kids.first().and_then(|&c| ref_name(term, c)) else {
            continue;
        };
        let Some((obj, m)) = callee.rsplit_once('.') else {
            continue;
        };
        let method = if m == "all" {
            Some(Method::Any)
        } else {
            verb(m)
        };
        let (Some(method), true, true) = (method, !obj.contains('.'), kids.len() >= 3) else {
            continue;
        };
        let parts = ts_parts(term, kids[1]);
        let looks_like_path =
            matches!(parts.as_deref(), Some([Part::Lit(s), ..]) if s.starts_with('/') || s == "*");
        if !looks_like_path {
            continue;
        }
        let path = path_of(parts);
        let mut r = route(f, "express", id);
        r.method = method;
        r.pattern = path.pattern.as_deref().map(normalize_server);
        r.status = if method == Method::Any {
            path.status.meet(Status::May)
        } else {
            path.status
        };
        r.handler = kids
            .last()
            .and_then(|&h| ref_name(term, h))
            .and_then(|n| names.get(last_segment(n)).cloned());
        debug!(file = f.path, pattern = ?r.pattern, method = r.method.as_str(), "express route");
        out.push(r);
    }
    out
}

/// The `(method, handler name)` pairs of an axum method-router expression like `post(h).get(g)`.
fn rs_methods(term: &Term, id: NodeId, out: &mut Vec<(Method, Option<String>)>) {
    let kids = term.node(id).children();
    let Some(callee) = kids.first().and_then(|&c| ref_name(term, c)) else {
        return;
    };
    let name = last_segment(callee);
    let method = if name == "any" {
        Some(Method::Any)
    } else {
        verb(name)
    };
    let Some(method) = method else {
        return;
    };
    if is_apply(term, id, "call") {
        let h = kids.get(1).and_then(|&h| ref_name(term, h));
        out.push((method, h.map(|h| last_segment(h).to_owned())));
    } else if is_apply(term, id, "method") {
        let h = kids.get(2).and_then(|&h| ref_name(term, h));
        out.push((method, h.map(|h| last_segment(h).to_owned())));
        if let Some(&recv) = kids.get(1) {
            rs_methods(term, recv, out);
        }
    }
}

/// The `.nest` prefix around the `route` call `id`, outermost first.
fn nest_prefix(term: &Term, id: NodeId) -> Prefix {
    let mut chain = Vec::new();
    let mut cur = id;
    while let Some(p) = term.node(cur).parent() {
        let kids = term.node(p).children();
        let nest = is_apply(term, p, "method")
            && kids.first().and_then(|&c| ref_name(term, c)) == Some(".nest")
            && kids.get(3) == Some(&cur);
        if nest {
            chain.push(Prefix::of(kids.get(2).and_then(|&s| rs_parts(term, s))));
        }
        cur = p;
    }
    let mut all = String::new();
    for p in chain.into_iter().rev() {
        match p {
            Prefix::Known(s) => all = join_paths(&all, &s),
            Prefix::Opaque => return Prefix::Opaque,
        }
    }
    Prefix::Known(all)
}

/// axum routes: `.route("/x", get(h).post(g))` calls, with the `.nest` prefixes of the same expression.
pub(super) fn axum_routes(f: &File<'_>) -> Vec<Route> {
    if !f.text.contains("axum") {
        return Vec::new();
    }
    let term = f.term;
    let names = unit_names(term);
    let mut out = Vec::new();
    for id in term.ids() {
        let kids = term.node(id).children();
        if !is_apply(term, id, "method")
            || kids.first().and_then(|&c| ref_name(term, c)) != Some(".route")
            || kids.len() < 4
        {
            continue;
        }
        let path = path_of(kids.get(2).and_then(|&s| rs_parts(term, s)));
        let prefix = nest_prefix(term, id);
        let mut methods = Vec::new();
        rs_methods(term, kids[3], &mut methods);
        if methods.is_empty() {
            methods.push((Method::Any, None));
        }
        let known = !methods.iter().any(|m| m.0 == Method::Any);
        for (method, handler) in methods {
            let mut r = route(f, "axum", id);
            r.method = method;
            r.handler = handler.and_then(|h| names.get(&h).cloned());
            match (&prefix, &path.pattern) {
                (Prefix::Known(pre), Some(p)) => {
                    r.pattern = Some(normalize_server(&join_paths(pre, p)));
                    r.status = if known {
                        path.status
                    } else {
                        path.status.meet(Status::May)
                    };
                }
                _ => r.status = Status::Unknown,
            }
            debug!(file = f.path, pattern = ?r.pattern, method = r.method.as_str(), "axum route");
            out.push(r);
        }
    }
    out
}
