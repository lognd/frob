//! HTTP layer: server routes and client call sites match as cross-language edges by method and path.

// frob:ticket 01M4GM5DE96WY2ZDRZP0ETTMMF

use std::path::{Path, PathBuf};

use gob_frameworks::{Analysis, ClientCall, Library, Method, Route, Status, analyze};
use gob_path::Shown;
use gob_symbols::{SymbolGraph, extract_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

/// The fixture directory `name` under `tests/fixtures/http`.
fn fixture(name: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/http")
        .join(name)
}

/// Collects the files under `dir` as walk entries relative to `root`.
fn collect(root: &Path, dir: &Path, out: &mut Vec<FileEntry>) {
    let mut names: Vec<_> = std::fs::read_dir(dir)
        .unwrap()
        .map(|e| e.unwrap().path())
        .collect();
    names.sort();
    for p in names {
        if p.is_dir() {
            collect(root, &p, out);
            continue;
        }
        let bytes = std::fs::read(&p).unwrap();
        let rel = Shown::of(p.strip_prefix(root).unwrap()).to_string();
        out.push(FileEntry {
            language: LanguageHint::from_path(&rel),
            path: rel,
            size: bytes.len() as u64,
            digest: Digest::of(&bytes),
        });
    }
}

/// Analyzes the whole `http` fixture tree.
fn run() -> Analysis {
    let root = fixture("");
    let mut files = Vec::new();
    collect(&root, &root, &mut files);
    let graph = SymbolGraph::from_files(
        files
            .iter()
            .filter_map(|f| {
                let text = std::fs::read_to_string(root.join(&f.path)).ok()?;
                Some(extract_file(f, &text))
            })
            .collect(),
    );
    analyze(&root, &files, &graph)
}

/// The call in `file` at the method and pattern.
fn call<'a>(a: &'a Analysis, file: &str, method: Method, pattern: Option<&str>) -> &'a ClientCall {
    a.calls
        .iter()
        .find(|c| c.file.ends_with(file) && c.method == method && c.pattern.as_deref() == pattern)
        .unwrap_or_else(|| panic!("no call {method:?} {pattern:?} in {file}: {:#?}", a.calls))
}

/// The route in `file` at the method and pattern.
fn route<'a>(a: &'a Analysis, file: &str, method: Method, pattern: &str) -> &'a Route {
    a.routes
        .iter()
        .find(|r| {
            r.file.ends_with(file) && r.method == method && r.pattern.as_deref() == Some(pattern)
        })
        .unwrap_or_else(|| panic!("no route {method:?} {pattern} in {file}: {:#?}", a.routes))
}

/// The edge status between a call and a route, if they are linked.
fn edge(a: &Analysis, c: &ClientCall, r: &Route) -> Option<Status> {
    a.edges
        .iter()
        .find(|e| &e.call == c && &e.route == r)
        .map(|e| e.status)
}

// frob:tests gob_frameworks::link
#[test]
fn fetch_post_matches_fastapi_route() {
    let a = run();
    let c = call(&a, "Orders.tsx", Method::Post, Some("/api/orders"));
    assert_eq!((c.library, c.status), (Library::Fetch, Status::Must));
    let r = route(&a, "orders.py", Method::Post, "/api/orders");
    assert_eq!(r.framework, "fastapi");
    assert_eq!(edge(&a, c, r), Some(Status::Must));
}

// frob:tests gob_frameworks::link
#[test]
fn dynamic_path_is_may_and_matches_param_route() {
    let a = run();
    let c = call(&a, "Orders.tsx", Method::Get, Some("/api/orders/:id"));
    assert_eq!(c.status, Status::May);
    let r = route(&a, "orders.py", Method::Get, "/api/orders/:order_id");
    assert_eq!(edge(&a, c, r), Some(Status::May));
    let post = route(&a, "orders.py", Method::Post, "/api/orders");
    assert_eq!(edge(&a, c, post), None);
}

// frob:tests gob_frameworks::analyze
#[test]
fn opaque_url_is_unknown_without_edges() {
    let a = run();
    let c = a
        .calls
        .iter()
        .find(|c| c.pattern.is_none())
        .expect("opaque call");
    assert_eq!(c.status, Status::Unknown);
    assert!(a.edges.iter().all(|e| e.call != *c));
}

// frob:tests gob_frameworks::analyze
#[test]
fn shadowed_fetch_is_not_a_client_call() {
    let a = run();
    let n = a
        .calls
        .iter()
        .filter(|c| c.library == Library::Fetch && c.pattern.as_deref() == Some("/api/orders"))
        .count();
    assert_eq!(n, 1, "{:#?}", a.calls);
}

// frob:tests gob_frameworks::analyze
#[test]
fn axios_and_ky_calls_match_flask_routes() {
    let a = run();
    let get = call(&a, "Orders.tsx", Method::Get, Some("/api/items"));
    assert_eq!(get.library, Library::Axios);
    let flask = route(&a, "flask_app.py", Method::Get, "/api/items");
    assert_eq!(edge(&a, get, flask), Some(Status::Must));
    let del = call(&a, "Orders.tsx", Method::Delete, Some("/api/items/7"));
    assert_eq!(del.library, Library::Ky);
    let drop = route(&a, "flask_app.py", Method::Delete, "/api/items/:item_id");
    assert_eq!(edge(&a, del, drop), Some(Status::Must));
}

// frob:tests gob_frameworks::link
#[test]
fn base_url_makes_the_edge_may() {
    let a = run();
    let put = call(&a, "Orders.tsx", Method::Put, Some("/api/items"));
    assert!(put.open_prefix);
    let r = route(&a, "flask_app.py", Method::Put, "/api/items");
    assert_eq!(edge(&a, put, r), Some(Status::May));
}

// frob:tests gob_frameworks::analyze
#[test]
fn express_and_axum_routes_are_extracted() {
    let a = run();
    let ex = route(&a, "server.js", Method::Get, "/api/list");
    assert_eq!(ex.framework, "express");
    assert!(ex.handler.is_some());
    let nested = route(&a, "main.rs", Method::Get, "/api/ping");
    assert_eq!(nested.framework, "axum");
    assert!(nested.handler.is_some());
    route(&a, "main.rs", Method::Post, "/api/ping");
    route(&a, "main.rs", Method::Get, "/flat");
}
