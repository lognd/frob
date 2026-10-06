//! react-router routes: route objects (`createBrowserRouter([..])`, `useRoutes([..])`, also through a named
//! constant or an import) and JSX `<Route>` elements, with path strings read through `const_value`.
//!
//! Only leaf routes (no `children`) and index routes are reported; a route with children is a layout and
//! joins the layout chain of everything below it. A path that is not statically known (a parameter, a
//! computed key, a spread, an unresolved import) makes the route and everything below it `Unknown`; it is
//! reported without a pattern, never dropped. A `loader` is the GET handler and an `action` the POST handler.

// frob:ticket 01M47QKVBB5G9N1QZP3AVXTRHX

use std::collections::BTreeSet;

use gob_ir::NodeId;
use gob_ir::const_value::{ConstValue, Value};
use gob_ir::markup::{self, Child, Element};
use tracing::{debug, trace};

use crate::registry::{Detector, FrameworkEntry};
use crate::repo::Repo;
use crate::terms::{Prop, array_items, is_call, is_spread, object_props, ref_name};
use crate::types::{Detection, Discovery, Entrypoint, EntrypointKind, Method, Route, Status};

/// The registry entry of react-router.
pub(crate) const ENTRY: FrameworkEntry = FrameworkEntry {
    name: "react-router",
    detectors: &[
        Detector::Dependency("react-router"),
        Detector::Dependency("react-router-dom"),
        Detector::ConfigFile("react-router.config"),
    ],
    discover,
};

/// Packages a router API is imported from.
const PACKAGES: [&str; 3] = ["react-router", "react-router-dom", "@remix-run/router"];
/// Functions that take route objects as their first argument and, optionally, `{ basename }` as the second.
const ROUTER_FNS: [&str; 5] = [
    "createBrowserRouter",
    "createHashRouter",
    "createMemoryRouter",
    "createStaticRouter",
    "useRoutes",
];

/// How a route declares its path.
#[derive(Debug, Clone, PartialEq, Eq)]
enum PathExpr {
    /// No `path`: the route continues its parent's path.
    Absent,
    /// One or several statically known segments.
    Known(Vec<String>, Status),
    /// Not statically known.
    Unknown,
}

/// A name written as a handler or component: resolved lazily to a symref.
#[derive(Debug, Clone, PartialEq, Eq)]
enum Named {
    /// Not declared.
    None,
    /// A reference, with its resolved text.
    Ref(String),
    /// Declared inline (an arrow function or element that is no plain reference).
    Inline,
}

impl Named {
    /// The text to report, if any.
    fn text(&self) -> Option<String> {
        match self {
            Self::Ref(s) => Some(s.clone()),
            Self::None | Self::Inline => None,
        }
    }

    /// True when declared at all.
    fn is_set(&self) -> bool {
        !matches!(self, Self::None)
    }
}

/// One route as written, object or element alike.
#[derive(Debug, Clone)]
struct RouteNode {
    /// File that declares it.
    file: String,
    /// One-based line.
    line: u32,
    /// The path.
    path: PathExpr,
    /// `index` route.
    index: bool,
    /// Page or layout component.
    component: Named,
    /// The `loader`.
    loader: Named,
    /// The `action`.
    action: Named,
    /// Children, when the route has a `children` array or element children.
    children: Vec<Kid>,
    /// A spread or computed key may set any property, including `path`.
    unknown_props: bool,
    /// Conditional or mapped: may not exist.
    may: bool,
}

/// A child of a route.
#[derive(Debug, Clone)]
enum Kid {
    /// A route.
    Route(Box<RouteNode>),
    /// Something that yields routes the analysis cannot see (a spread, a call, an unresolved name).
    Opaque(String, u32),
}

/// The state inherited from the routes above.
#[derive(Debug, Clone)]
struct Base {
    /// The parent patterns; `None` when unknown.
    patterns: Option<Vec<String>>,
    /// How sure the parent path is.
    status: Status,
    /// The layouts around, outermost first.
    layouts: Vec<String>,
    /// The router `basename` alternatives every final pattern is prefixed with (`/` for none).
    basenames: Vec<String>,
}

/// `parent` joined with the path segment `seg` as react-router matches it.
fn join_path(parent: &str, seg: &str) -> String {
    let seg = seg.trim();
    let joined = if seg.starts_with('/') {
        seg.to_owned()
    } else if seg.is_empty() {
        parent.to_owned()
    } else {
        format!("{}/{seg}", parent.trim_end_matches('/'))
    };
    let trimmed = joined.trim_end_matches('/');
    if trimmed.is_empty() {
        "/".to_owned()
    } else if trimmed.starts_with('/') {
        trimmed.to_owned()
    } else {
        format!("/{trimmed}")
    }
}

/// The pattern `pat` (starting with `/`) under the router basename `base`.
fn prefixed(base: &str, pat: &str) -> String {
    match (base, pat) {
        ("/", _) => pat.to_owned(),
        (_, "/") => base.to_owned(),
        _ => format!("{}{pat}", base.trim_end_matches('/')),
    }
}

/// Finds the routes and entrypoints of one detected member.
fn discover(repo: &Repo<'_>, det: &Detection) -> Discovery {
    let mut out = Discovery::default();
    let mut router_files: BTreeSet<String> = BTreeSet::new();
    for file in repo.member_sources(&det.member) {
        let mut roots: Vec<(Base, Kid)> = Vec::new();
        object_roots(repo, file, &mut roots);
        jsx_roots(repo, file, &mut roots);
        if roots.is_empty() {
            continue;
        }
        router_files.insert(file.to_owned());
        for (base, kid) in roots {
            emit_kid(&kid, &base, det, &mut out.routes);
        }
    }
    out.entrypoints = router_files
        .into_iter()
        .map(|file| Entrypoint {
            framework: ENTRY.name,
            member: det.member.clone(),
            kind: EntrypointKind::Router,
            file,
        })
        .collect();
    debug!(
        member = det.member,
        routes = out.routes.len(),
        "react-router discovered"
    );
    out
}

/// The base a router call starts from: `/`, or its `basename` option.
fn root_base(repo: &Repo<'_>, file: &str, options: Option<NodeId>) -> Base {
    let mut base = Base {
        patterns: Some(vec!["/".to_owned()]),
        status: Status::Must,
        layouts: Vec::new(),
        basenames: vec!["/".to_owned()],
    };
    let Some(model) = repo.model(file) else {
        return base;
    };
    let Some(props) = options.and_then(|o| object_props(model, o)) else {
        return base;
    };
    for p in props {
        match p {
            Prop::Named(k, v) if k == "basename" => {
                if let Some((alts, st)) = repo.strings(file, v) {
                    base.basenames = alts.iter().map(|a| join_path("/", a)).collect();
                    base.status = st;
                } else {
                    base.patterns = None;
                    base.status = Status::Unknown;
                }
            }
            Prop::Unknown => {
                // A spread may carry a basename.
                base.patterns = None;
                base.status = Status::Unknown;
            }
            Prop::Named(..) => {}
        }
    }
    base
}

/// Route objects passed to a react-router function in `file`.
fn object_roots(repo: &Repo<'_>, file: &str, roots: &mut Vec<(Base, Kid)>) {
    let Some(model) = repo.model(file) else {
        return;
    };
    let term = model.term();
    for id in term.ids() {
        if !is_call(model, id) {
            continue;
        }
        let kids = term.children(id);
        let Some(callee) = kids.first().and_then(|&c| ref_name(model, c)) else {
            continue;
        };
        let Some((spec, member)) = repo.graph().ts_import_source(file, callee) else {
            continue;
        };
        if !PACKAGES.contains(&spec.as_str()) || !ROUTER_FNS.contains(&member.as_str()) {
            continue;
        }
        let base = root_base(repo, file, kids.get(2).copied());
        let line = repo.line(file, id);
        trace!(file, callee, line, "router call");
        match kids.get(1) {
            Some(&arg) => {
                for kid in array_kids(repo, file, arg, line) {
                    roots.push((base.clone(), kid));
                }
            }
            None => roots.push((base, Kid::Opaque(file.to_owned(), line))),
        }
    }
}

/// The routes of the array expression `node` of `file`, following a name to its constant.
fn array_kids(repo: &Repo<'_>, file: &str, node: NodeId, line: u32) -> Vec<Kid> {
    let Some((f, n)) = repo.follow(file, node) else {
        return vec![Kid::Opaque(file.to_owned(), line)];
    };
    let Some(items) = repo.model(&f).and_then(|m| array_items(m, n)) else {
        return vec![Kid::Opaque(f, repo.line(file, node))];
    };
    items.into_iter().map(|i| kid_of(repo, &f, i)).collect()
}

/// One element of a route array.
fn kid_of(repo: &Repo<'_>, file: &str, node: NodeId) -> Kid {
    let Some(model) = repo.model(file) else {
        return Kid::Opaque(file.to_owned(), 1);
    };
    if !is_spread(model, node)
        && let Some((f, n)) = repo.follow(file, node)
        && let Some(m) = repo.model(&f)
        && let Some(props) = object_props(m, n)
    {
        return Kid::Route(Box::new(object_route(repo, &f, n, props)));
    }
    Kid::Opaque(file.to_owned(), repo.line(file, node))
}

/// The path expression of the value `node`.
fn path_expr(repo: &Repo<'_>, file: &str, node: NodeId) -> PathExpr {
    match repo.strings(file, node) {
        Some((alts, st)) => PathExpr::Known(alts, st),
        None => PathExpr::Unknown,
    }
}

/// A handler or component written as the reference `node`.
fn named_ref(repo: &Repo<'_>, file: &str, node: NodeId) -> Named {
    match repo.model(file).and_then(|m| ref_name(m, node)) {
        Some(name) => Named::Ref(repo.name_ref(file, name)),
        None => Named::Inline,
    }
}

/// True when the value `node` is not statically `false`.
fn truthy(repo: &Repo<'_>, file: &str, node: NodeId) -> bool {
    !matches!(
        repo.evaluate(file, node).value,
        ConstValue::Known(Value::Bool(false) | Value::Null)
    )
}

/// A route object with the entries `props`.
fn object_route(repo: &Repo<'_>, file: &str, node: NodeId, props: Vec<Prop>) -> RouteNode {
    let mut route = RouteNode::new(file, repo.line(file, node));
    let Some(model) = repo.model(file) else {
        return route;
    };
    for p in props {
        let Prop::Named(key, value) = p else {
            route.unknown_props = true;
            continue;
        };
        match key.as_str() {
            "path" => route.path = path_expr(repo, file, value),
            "index" => route.index = truthy(repo, file, value),
            "element" => {
                route.component = match markup::element(model, value).and_then(|e| e.tag) {
                    Some(tag) => Named::Ref(repo.name_ref(file, &tag)),
                    None => Named::Inline,
                }
            }
            "Component" => route.component = named_ref(repo, file, value),
            "loader" => route.loader = named_ref(repo, file, value),
            "action" => route.action = named_ref(repo, file, value),
            "children" => {
                route.children = array_kids(repo, file, value, route.line);
            }
            _ => {}
        }
    }
    route
}

impl RouteNode {
    /// An empty route at `file:line`.
    fn new(file: &str, line: u32) -> Self {
        Self {
            file: file.to_owned(),
            line,
            path: PathExpr::Absent,
            index: false,
            component: Named::None,
            loader: Named::None,
            action: Named::None,
            children: Vec::new(),
            unknown_props: false,
            may: false,
        }
    }
}

/// True when `tag` written in `file` is react-router's `Route`.
fn is_route_tag(repo: &Repo<'_>, file: &str, tag: &str) -> bool {
    repo.graph()
        .ts_import_source(file, tag)
        .is_some_and(|(spec, member)| PACKAGES.contains(&spec.as_str()) && member == "Route")
}

/// The `<Route>` elements at or below `node` (an expression child), not descending into a found route.
fn routes_in(repo: &Repo<'_>, file: &str, node: NodeId) -> Vec<Element> {
    let Some(model) = repo.model(file) else {
        return Vec::new();
    };
    let found: Vec<Element> = std::iter::once(node)
        .chain(model.term().descendants(node))
        .filter_map(|n| markup::element(model, n))
        .filter(|e| {
            e.tag
                .as_deref()
                .is_some_and(|t| is_route_tag(repo, file, t))
        })
        .collect();
    let inner: BTreeSet<NodeId> = found
        .iter()
        .flat_map(|e| model.term().descendants(e.node))
        .collect();
    found
        .into_iter()
        .filter(|e| !inner.contains(&e.node))
        .collect()
}

/// The `<Route>` children of `el`: direct element children, and routes inside expression children (a
/// conditional or a mapped list, so they may not exist).
fn route_children(repo: &Repo<'_>, file: &str, el: &Element) -> Vec<(Element, bool)> {
    let Some(model) = repo.model(file) else {
        return Vec::new();
    };
    let mut out = Vec::new();
    for c in &el.children {
        match c {
            Child::Element(n) => {
                if let Some(e) = markup::element(model, *n)
                    && e.tag
                        .as_deref()
                        .is_some_and(|t| is_route_tag(repo, file, t))
                {
                    out.push((e, false));
                }
            }
            Child::Expr(n) => out.extend(routes_in(repo, file, *n).into_iter().map(|e| (e, true))),
            Child::Text(_) => {}
        }
    }
    out
}

/// The route of the `<Route>` element `el`.
fn element_route(repo: &Repo<'_>, file: &str, el: &Element, may: bool) -> RouteNode {
    let mut route = RouteNode::new(file, repo.line(file, el.node));
    route.may = may;
    let Some(model) = repo.model(file) else {
        return route;
    };
    for a in &el.attributes {
        let Some(name) = a.name.as_deref() else {
            route.unknown_props = true;
            continue;
        };
        let value = a.value;
        match (name, value) {
            ("index", None) => route.index = true,
            ("index", Some(v)) => route.index = truthy(repo, file, v),
            ("path", Some(v)) => route.path = path_expr(repo, file, v),
            ("path", None) => route.path = PathExpr::Unknown,
            ("element", Some(v)) => {
                route.component = match markup::element(model, v).and_then(|e| e.tag) {
                    Some(tag) => Named::Ref(repo.name_ref(file, &tag)),
                    None => Named::Inline,
                }
            }
            ("Component", Some(v)) => route.component = named_ref(repo, file, v),
            ("loader", Some(v)) => route.loader = named_ref(repo, file, v),
            ("action", Some(v)) => route.action = named_ref(repo, file, v),
            _ => {}
        }
    }
    let kids = route_children(repo, file, el);
    route.children = kids
        .into_iter()
        .map(|(e, may)| Kid::Route(Box::new(element_route(repo, file, &e, may))))
        .collect();
    route
}

/// The `<Route>` trees of `file` that are not nested in another route.
fn jsx_roots(repo: &Repo<'_>, file: &str, roots: &mut Vec<(Base, Kid)>) {
    let Some(model) = repo.model(file) else {
        return;
    };
    let all: Vec<Element> = markup::elements(model)
        .into_iter()
        .filter(|e| {
            e.tag
                .as_deref()
                .is_some_and(|t| is_route_tag(repo, file, t))
        })
        .collect();
    let mut nested: BTreeSet<NodeId> = BTreeSet::new();
    for e in &all {
        for (child, _) in route_children(repo, file, e) {
            nested.insert(child.node);
        }
    }
    for e in all.iter().filter(|e| !nested.contains(&e.node)) {
        roots.push((
            root_base(repo, file, None),
            Kid::Route(Box::new(element_route(repo, file, e, false))),
        ));
    }
}

/// Reports `kid` and everything below it into `out`.
fn emit_kid(kid: &Kid, base: &Base, det: &Detection, out: &mut Vec<Route>) {
    match kid {
        Kid::Opaque(file, line) => out.push(Route {
            framework: ENTRY.name,
            member: det.member.clone(),
            pattern: None,
            method: Method::Get,
            handler: None,
            component: None,
            layouts: base.layouts.clone(),
            status: Status::Unknown,
            file: file.clone(),
            line: *line,
            client: false,
        }),
        Kid::Route(r) => emit_route(r, base, det, out),
    }
}

/// The patterns and status of `route` under `base`.
fn own_patterns(route: &RouteNode, base: &Base) -> (Option<Vec<String>>, Status) {
    let (patterns, status) = match (&route.path, &base.patterns) {
        (_, None) | (PathExpr::Unknown, _) => (None, Status::Unknown),
        (PathExpr::Absent, Some(_)) if route.unknown_props => (None, Status::Unknown),
        (PathExpr::Absent, Some(p)) => (Some(p.clone()), base.status),
        (PathExpr::Known(segs, st), Some(p)) => {
            let joined: BTreeSet<String> = p
                .iter()
                .flat_map(|parent| segs.iter().map(|s| join_path(parent, s)))
                .collect();
            (Some(joined.into_iter().collect()), base.status.min(*st))
        }
    };
    let status = if route.may && status > Status::May {
        Status::May
    } else {
        status
    };
    (patterns, status)
}

/// Reports `route`: a leaf as routes, a parent as a layout around its children.
fn emit_route(route: &RouteNode, base: &Base, det: &Detection, out: &mut Vec<Route>) {
    let (patterns, status) = own_patterns(route, base);
    if !route.children.is_empty() {
        let mut layouts = base.layouts.clone();
        if let Some(c) = route.component.text() {
            layouts.push(c);
        }
        let inner = Base {
            patterns,
            status,
            layouts,
            basenames: base.basenames.clone(),
        };
        for kid in &route.children {
            emit_kid(kid, &inner, det, out);
        }
        return;
    }
    let mut push = |pattern: Option<String>, method: Method, handler: Option<String>| {
        out.push(Route {
            framework: ENTRY.name,
            member: det.member.clone(),
            pattern,
            method,
            handler,
            component: route.component.text(),
            layouts: base.layouts.clone(),
            status,
            file: route.file.clone(),
            line: route.line,
            client: false,
        });
    };
    let alts: Vec<Option<String>> = match patterns {
        Some(p) => p
            .iter()
            .flat_map(|pat| base.basenames.iter().map(|b| Some(prefixed(b, pat))))
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect(),
        None => vec![None],
    };
    for pattern in alts {
        push(pattern.clone(), Method::Get, route.loader.text());
        if route.action.is_set() {
            push(pattern, Method::Post, route.action.text());
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{join_path, prefixed};

    #[test]
    // frob:tests crates/gob-frameworks/src/react_router.rs::join_path
    fn paths_join_like_the_router_matches() {
        assert_eq!(join_path("/", "users"), "/users");
        assert_eq!(join_path("/users", ":id"), "/users/:id");
        assert_eq!(join_path("/users", "/users/new"), "/users/new");
        assert_eq!(join_path("/users", ""), "/users");
        assert_eq!(join_path("/", "/"), "/");
        assert_eq!(join_path("/a/", "b/"), "/a/b");
    }

    #[test]
    // frob:tests crates/gob-frameworks/src/react_router.rs::prefixed
    fn a_basename_prefixes_every_pattern() {
        assert_eq!(prefixed("/", "/users"), "/users");
        assert_eq!(prefixed("/app", "/"), "/app");
        assert_eq!(prefixed("/app/", "/users"), "/app/users");
    }
}
