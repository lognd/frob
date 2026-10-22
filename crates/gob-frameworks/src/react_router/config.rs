//! react-router framework mode: the `routes.ts` config built from the `route`, `index`, `layout` and
//! `prefix` helpers of `@react-router/dev/routes` (also `@remix-run/route-config`).
//!
//! The helpers map onto the route objects of the parent module: `route(path, file)` is a route with a
//! component, `index(file)` an index route, `layout(file, children)` a pathless parent with a component and
//! `prefix(path, children)` a parent with a path and no component. The module file of a route is resolved
//! against the config file; its default export is the component and its `loader` and `action` exports the
//! GET and POST handlers. Children may be an array literal or a constant (also imported) array; anything
//! else that yields routes (`...flatRoutes()`, an unresolved call) is an opaque `Unknown` route.

// frob:ticket 01M48EFBCF70PK5KGS0PDZD40N

use std::collections::BTreeSet;

use gob_ir::{NodeId, Operator, Universal};
use tracing::{debug, trace};

use super::{Base, Kid, Named, PathExpr, RouteNode, path_expr, root_base};
use crate::exports::module_candidates;
use crate::repo::Repo;
use crate::terms::{array_items, is_call, object_props, ref_name, spread_arg};
use crate::types::Status;

/// Modules the config helpers are imported from.
const PACKAGES: [&str; 2] = ["@react-router/dev/routes", "@remix-run/route-config"];

/// How deep nested and spread arrays are followed.
const DEPTH: usize = 8;

/// One of the config helpers.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Helper {
    /// `route(path, file, options?, children?)`.
    Route,
    /// `index(file, options?)`.
    Index,
    /// `layout(file, options?, children?)`.
    Layout,
    /// `prefix(path, children)`.
    Prefix,
}

/// A node of a file: the unit consumed bookkeeping is keyed by.
type Key = (String, NodeId);

/// The helper `call` in `file` invokes, if it is a call of an imported config helper.
fn helper_of(repo: &Repo<'_>, file: &str, call: NodeId) -> Option<Helper> {
    let model = repo.model(file)?;
    if !is_call(model, call) {
        return None;
    }
    let callee = ref_name(model, *model.term().children(call).first()?)?;
    let (spec, member) = repo.graph().ts_import_source(file, callee)?;
    if !PACKAGES.contains(&spec.as_str()) {
        return None;
    }
    match member.as_str() {
        "route" => Some(Helper::Route),
        "index" => Some(Helper::Index),
        "layout" => Some(Helper::Layout),
        "prefix" => Some(Helper::Prefix),
        _ => None,
    }
}

/// The value of the string argument `node`: a plain literal as written, else whatever folds to strings.
fn text(repo: &Repo<'_>, file: &str, node: NodeId) -> Option<(Vec<String>, Status)> {
    let model = repo.model(file)?;
    if let Operator::Universal(Universal::Lit { kind, lexeme }) = model.term().operator(node)
        && kind == "string"
        && let Some(inner) = lexeme
            .strip_prefix(['"', '\''])
            .and_then(|l| l.strip_suffix(['"', '\'']))
    {
        return Some((vec![inner.to_owned()], Status::Must));
    }
    repo.strings(file, node)
}

/// The arguments of the call `call`.
fn args(repo: &Repo<'_>, file: &str, call: NodeId) -> Vec<NodeId> {
    repo.model(file)
        .map(|m| m.term().children(call).iter().skip(1).copied().collect())
        .unwrap_or_default()
}

/// The routes found while reading the config files, and what they consumed.
struct Reader<'r, 'g> {
    /// The loaded sources.
    repo: &'r Repo<'g>,
    /// Calls and arrays that are part of another route's children.
    consumed: BTreeSet<Key>,
}

impl Reader<'_, '_> {
    /// The route of the helper call `call` in `file`.
    fn build(&mut self, file: &str, call: NodeId, helper: Helper, depth: usize) -> Kid {
        let repo = self.repo;
        let line = repo.line(file, call);
        let mut route = RouteNode::new(file, line);
        let a = args(repo, file, call);
        let mut rest: &[NodeId] = &a;
        if matches!(helper, Helper::Route | Helper::Prefix) {
            route.path = match a.first() {
                Some(&p) => match text(repo, file, p) {
                    Some((alts, st)) => PathExpr::Known(alts, st),
                    None => path_expr(repo, file, p),
                },
                None => PathExpr::Unknown,
            };
            rest = a.get(1..).unwrap_or_default();
        }
        if helper == Helper::Index {
            route.index = true;
        }
        if helper != Helper::Prefix {
            self.module(file, rest.first().copied(), &mut route);
            rest = rest.get(1..).unwrap_or_default();
        }
        for &arg in rest {
            let is_options = repo
                .follow(file, arg)
                .and_then(|(f, n)| repo.model(&f).map(|m| object_props(m, n).is_some()))
                .unwrap_or(false);
            if !is_options {
                route.children = self.children(file, arg, line, depth + 1);
            }
        }
        trace!(
            file,
            line,
            ?helper,
            kids = route.children.len(),
            "config route"
        );
        Kid::Route(Box::new(route))
    }

    /// Reads the module of a route (the `file` argument `node`) into `route`: component, loader, action.
    fn module(&self, file: &str, node: Option<NodeId>, route: &mut RouteNode) {
        let repo = self.repo;
        let spec = node
            .and_then(|n| text(repo, file, n))
            .and_then(|(alts, st)| match alts.as_slice() {
                [one] if st == Status::Must => Some(one.clone()),
                _ => None,
            });
        let Some(spec) = spec else {
            debug!(file, "route module is not a static string");
            route.unknown_props = true;
            return;
        };
        let Some(module) = repo.resolve_module(file, &spec) else {
            // Not a project file: keep the path the config names.
            let named = module_candidates(file, &spec).into_iter().next();
            route.component = named.map_or(Named::None, Named::Ref);
            return;
        };
        route.component = Named::Ref(repo.default_export(&module));
        let export = |name: &str| match repo.export_targets(&module, name, 0).as_slice() {
            [(symref, _)] => Named::Ref(symref.clone()),
            [] => Named::None,
            _ => Named::Inline,
        };
        route.loader = export("loader");
        route.action = export("action");
    }

    /// The routes of the children argument `node`: an array literal or a constant array.
    fn children(&mut self, file: &str, node: NodeId, line: u32, depth: usize) -> Vec<Kid> {
        let repo = self.repo;
        let Some((f, n)) = repo.follow(file, node) else {
            return vec![Kid::Opaque(file.to_owned(), line)];
        };
        let items = repo.model(&f).and_then(|m| array_items(m, n));
        let Some(items) = items.filter(|_| depth < DEPTH) else {
            return vec![Kid::Opaque(file.to_owned(), line)];
        };
        self.consumed.insert((f.clone(), n));
        let mut out = Vec::new();
        for item in items {
            self.item(&f, item, depth, &mut out);
        }
        out
    }

    /// Adds the route(s) the array element `item` stands for to `out`.
    fn item(&mut self, file: &str, item: NodeId, depth: usize, out: &mut Vec<Kid>) {
        let repo = self.repo;
        let Some(model) = repo.model(file) else {
            return;
        };
        let line = repo.line(file, item);
        let (inner, spread) = match spread_arg(model, item) {
            Some(i) => (i, true),
            None => (item, false),
        };
        let Some((f, n)) = repo.follow(file, inner) else {
            out.push(Kid::Opaque(file.to_owned(), line));
            return;
        };
        if let Some(helper) = helper_of(repo, &f, n) {
            self.consumed.insert((f.clone(), n));
            out.push(self.build(&f, n, helper, depth));
        } else if spread
            && depth < DEPTH
            && let Some(items) = repo.model(&f).and_then(|m| array_items(m, n))
        {
            self.consumed.insert((f.clone(), n));
            for i in items {
                self.item(&f, i, depth + 1, out);
            }
        } else {
            out.push(Kid::Opaque(file.to_owned(), line));
        }
    }
}

/// The routes declared with the config helpers in `files`, each with the file it is rooted in.
pub(super) fn roots(repo: &Repo<'_>, files: &[&str]) -> Vec<(String, Base, Kid)> {
    let mut reader = Reader {
        repo,
        consumed: BTreeSet::new(),
    };
    let mut calls: Vec<(String, NodeId, Helper)> = Vec::new();
    for &file in files {
        let Some(model) = repo.model(file) else {
            continue;
        };
        for id in model.term().ids() {
            if let Some(h) = helper_of(repo, file, id) {
                calls.push((file.to_owned(), id, h));
            }
        }
    }
    if calls.is_empty() {
        return Vec::new();
    }
    // First pass: whatever is the child of a route is not a root.
    for (file, id, helper) in &calls {
        reader.build(file, *id, *helper, 0);
    }
    let mut out = Vec::new();
    // Arrays that hold helper calls and are nobody's children are route lists.
    let called: BTreeSet<Key> = calls.iter().map(|(f, n, _)| (f.clone(), *n)).collect();
    for file in calls.iter().map(|c| c.0.as_str()).collect::<BTreeSet<_>>() {
        let Some(model) = repo.model(file) else {
            continue;
        };
        for id in model.term().ids() {
            let Some(items) = array_items(model, id) else {
                continue;
            };
            let key = (file.to_owned(), id);
            let holds_routes = items.iter().any(|&i| {
                let inner = spread_arg(model, i).unwrap_or(i);
                called.contains(&(file.to_owned(), inner))
            });
            if !holds_routes || reader.consumed.contains(&key) {
                continue;
            }
            reader.consumed.insert(key);
            let mut kids = Vec::new();
            for item in items {
                reader.item(file, item, 0, &mut kids);
            }
            for kid in kids {
                out.push((file.to_owned(), root_base(repo, file, None), kid));
            }
        }
    }
    // Helper calls outside any list or parent.
    for (file, id, helper) in &calls {
        if !reader.consumed.contains(&(file.clone(), *id)) {
            let kid = reader.build(file, *id, *helper, 0);
            out.push((file.clone(), root_base(repo, file, None), kid));
        }
    }
    debug!(roots = out.len(), "react-router config roots");
    out
}
