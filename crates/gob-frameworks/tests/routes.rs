//! Framework detection and route discovery over the monorepo fixture (D96, language-engines.md section 4).

// frob:ticket 01M47QKVBB5G9N1QZP3AVXTRHX

use std::path::{Path, PathBuf};

use gob_frameworks::{
    Analysis, Detector, Discovery, EntrypointKind, FrameworkEntry, Status, analyze, detect_with,
};
use gob_symbols::{SymbolGraph, extract_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn fixture(name: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures")
        .join(name)
}

fn collect(root: &Path, dir: &Path, out: &mut Vec<FileEntry>) {
    let mut entries: Vec<_> = std::fs::read_dir(dir)
        .expect("read dir")
        .flatten()
        .collect();
    entries.sort_by_key(std::fs::DirEntry::path);
    for e in entries {
        let p = e.path();
        if p.is_dir() {
            collect(root, &p, out);
        } else {
            let rel = gob_path::Shown::with_home(p.strip_prefix(root).expect("under root"), None)
                .to_string()
                .replace('\\', "/");
            let bytes = std::fs::read(&p).expect("read");
            out.push(FileEntry {
                language: LanguageHint::from_path(&rel),
                path: rel,
                size: bytes.len() as u64,
                digest: Digest::of(&bytes),
            });
        }
    }
}

fn run(name: &str) -> Analysis {
    let root = fixture(name);
    let mut files = Vec::new();
    collect(&root, &root, &mut files);
    let graph = SymbolGraph::from_files(
        files
            .iter()
            .map(|f| {
                let text = std::fs::read_to_string(root.join(&f.path)).expect("text");
                extract_file(f, &text)
            })
            .collect(),
    );
    analyze(&root, &files, &graph)
}

/// The rendered routes of one framework.
fn routes_of(a: &Analysis, framework: &str) -> Vec<String> {
    a.routes
        .iter()
        .filter(|r| r.framework == framework)
        .map(ToString::to_string)
        .collect()
}

#[test]
// frob:tests crates/gob-frameworks/src/registry.rs::detect
fn detection_finds_frameworks_in_members_below_the_root() {
    let a = run("monorepo");
    let found: Vec<(&str, &str)> = a
        .detections
        .iter()
        .map(|d| (d.framework, d.member.as_str()))
        .collect();
    assert_eq!(
        found,
        [
            ("nextjs", "apps/web/package.json"),
            ("react-router", "apps/spa/package.json"),
        ],
        "the root manifest and apps/api declare no framework"
    );
    assert_eq!(a.detections[0].evidence, ["dependency next"]);
    assert!(a.problems.is_empty(), "{:?}", a.problems);
}

#[test]
// frob:tests crates/gob-frameworks/src/nextjs.rs::ENTRY
fn a_nextjs_fixture_produces_the_expected_routes() {
    let a = run("monorepo");
    let web = "apps/web";
    let expected = [
        format!(
            "GET ? [Unknown] {web}/app/feed/(.)photo/page.tsx:1 component={web}/app/feed/(.)photo/page.tsx::Photo layouts={web}/app/layout.tsx::RootLayout"
        ),
        format!(
            "GET / [Must] {web}/app/page.tsx:1 component={web}/app/page.tsx::Home layouts={web}/app/layout.tsx::RootLayout"
        ),
        format!(
            "GET / [Must] {web}/pages/index.tsx:1 component={web}/pages/index.tsx::Index layouts={web}/pages/_app.tsx::App"
        ),
        format!(
            "GET /about [Must] {web}/pages/about.tsx:1 component={web}/pages/about.tsx::About layouts={web}/pages/_app.tsx::App"
        ),
        format!(
            "ANY /api/health [Must] {web}/pages/api/health.ts:1 handler={web}/pages/api/health.ts::handler"
        ),
        format!(
            "GET /api/orders [Must] {web}/app/api/orders/route.ts:1 handler={web}/app/api/orders/route.ts::GET"
        ),
        format!(
            "POST /api/orders [Must] {web}/app/api/orders/route.ts:1 handler={web}/app/api/orders/route.ts::POST"
        ),
        format!(
            "GET /docs/:slug* [Must] {web}/app/docs/[[...slug]]/page.tsx:1 component={web}/app/docs/[[...slug]]/page.tsx::Docs layouts={web}/app/layout.tsx::RootLayout"
        ),
        format!(
            "GET /products/:id [Must] {web}/app/(shop)/products/[id]/page.tsx:1 component={web}/app/(shop)/products/[id]/page.tsx::Product layouts={web}/app/layout.tsx::RootLayout>{web}/app/(shop)/layout.tsx::ShopLayout client"
        ),
    ];
    assert_eq!(routes_of(&a, "nextjs"), expected);
    let middleware: Vec<_> = a
        .entrypoints
        .iter()
        .filter(|e| e.kind == EntrypointKind::Middleware)
        .map(|e| e.file.as_str())
        .collect();
    assert_eq!(middleware, ["apps/web/middleware.ts"]);
}

#[test]
// frob:tests crates/gob-frameworks/src/react_router.rs::ENTRY
fn a_react_router_fixture_produces_the_expected_routes() {
    let a = run("monorepo");
    let p = "apps/spa/src/pages.tsx";
    let expected = [
        format!("GET ? [Unknown] apps/spa/src/router.tsx:20 layouts={p}::Shell"),
        format!("GET ? [Unknown] apps/spa/src/app.tsx:15 component={p}::Dyn layouts={p}::Shell"),
        format!(
            "GET ? [Unknown] apps/spa/src/router.tsx:18 component={p}::Hidden layouts={p}::Shell"
        ),
        format!("GET / [Must] apps/spa/src/app.tsx:11 component={p}::Home layouts={p}::Shell"),
        format!(
            "GET /about [Must] apps/spa/src/app.tsx:12 component={p}::About layouts={p}::Shell"
        ),
        format!(
            "GET /app [Must] apps/spa/src/router.tsx:15 component={p}::Home layouts={p}::Shell"
        ),
        format!(
            "GET /app/admin/settings [Must] apps/spa/src/router.tsx:17 component={p}::Settings layouts={p}::Shell"
        ),
        format!(
            "GET /app/beta [May] apps/spa/src/router.tsx:19 component={p}::Settings layouts={p}::Shell"
        ),
        format!(
            "GET /app/gamma [May] apps/spa/src/router.tsx:19 component={p}::Settings layouts={p}::Shell"
        ),
        format!(
            "GET /app/users [Must] apps/spa/src/router.tsx:16 handler={p}::userLoader component={p}::Users layouts={p}::Shell"
        ),
        format!(
            "POST /app/users [Must] apps/spa/src/router.tsx:16 handler={p}::userAction component={p}::Users layouts={p}::Shell"
        ),
        format!("GET /beta [May] apps/spa/src/app.tsx:14 component={p}::About layouts={p}::Shell"),
        format!(
            "GET /users/:id [Must] apps/spa/src/app.tsx:13 component={p}::User layouts={p}::Shell"
        ),
    ];
    assert_eq!(routes_of(&a, "react-router"), expected);
    let routers: Vec<_> = a
        .entrypoints
        .iter()
        .filter(|e| e.framework == "react-router")
        .map(|e| e.file.as_str())
        .collect();
    assert_eq!(routers, ["apps/spa/src/app.tsx", "apps/spa/src/router.tsx"]);
}

#[test]
// frob:tests crates/gob-frameworks/src/types.rs::Route
fn a_route_with_an_unknown_path_is_reported_unknown_not_omitted() {
    let a = run("monorepo");
    let unknown: Vec<(&str, u32)> = a
        .routes
        .iter()
        .filter(|r| r.pattern.is_none())
        .inspect(|r| assert_eq!(r.status, Status::Unknown, "{r}"))
        .map(|r| (r.file.as_str(), r.line))
        .collect();
    assert_eq!(
        unknown,
        [
            ("apps/web/app/feed/(.)photo/page.tsx", 1),
            ("apps/spa/src/router.tsx", 20),
            ("apps/spa/src/app.tsx", 15),
            ("apps/spa/src/router.tsx", 18),
        ],
        "an intercepting route, a spread of a dynamic list, and two runtime paths"
    );
}

#[test]
// frob:tests crates/gob-frameworks/src/registry.rs::detect_with
fn detectors_cover_config_files_and_directories_per_member() {
    static ENTRY: FrameworkEntry = FrameworkEntry {
        name: "fixture-fw",
        detectors: &[
            Detector::ConfigFile("fw.config"),
            Detector::Directory("routes"),
        ],
        discover: |_, _| Discovery::default(),
    };
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    for (path, text) in [
        ("package.json", "{}"),
        ("svc/package.json", "{}"),
        ("svc/fw.config.mjs", ""),
        ("other/package.json", "{}"),
        ("other/routes/a.ts", ""),
        ("plain/package.json", "{}"),
        ("plain/src/a.ts", ""),
        ("bad/package.json", "{ not json"),
    ] {
        let full = root.join(path);
        std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
        std::fs::write(full, text).expect("write");
    }
    let mut files = Vec::new();
    collect(root, root, &mut files);
    let (found, problems) = detect_with(&[&ENTRY], root, &files);
    let got: Vec<(&str, &[String])> = found
        .iter()
        .map(|d| (d.member.as_str(), d.evidence.as_slice()))
        .collect();
    assert_eq!(
        got,
        [
            ("other/package.json", &["directory routes".to_owned()][..]),
            ("svc/package.json", &["config fw.config.mjs".to_owned()][..]),
        ]
    );
    assert_eq!(problems.len(), 1);
    assert_eq!(problems[0].path, "bad/package.json");
}

#[test]
// frob:tests crates/gob-frameworks/src/lib.rs::analyze
fn a_repository_without_frameworks_yields_nothing() {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(
        dir.path().join("package.json"),
        r#"{"dependencies":{"left-pad":"1"}}"#,
    )
    .expect("write");
    let mut files = Vec::new();
    collect(dir.path(), dir.path(), &mut files);
    let graph = SymbolGraph::from_files(Vec::new());
    let a = analyze(dir.path(), &files, &graph);
    assert_eq!(a, Analysis::default());
}

/// The rendered routes of `framework` whose line mentions `needle`.
fn routes_with(a: &Analysis, framework: &str, needle: &str) -> Vec<String> {
    routes_of(a, framework)
        .into_iter()
        .filter(|r| r.contains(needle))
        .collect()
}

#[test]
// frob:tests crates/gob-frameworks/src/nextjs.rs::handlers_of
fn reexported_next_route_handlers_are_reported_per_method_at_must() {
    let a = run("frameworks");
    let nx = "apps/nx/app/api";
    assert_eq!(
        routes_with(&a, "nextjs", "/api/items ["),
        [
            format!(
                "GET /api/items [Must] {nx}/items/route.ts:1 handler={nx}/items/handlers.ts::GET"
            ),
            format!(
                "POST /api/items [Must] {nx}/items/route.ts:1 handler={nx}/items/handlers.ts::POST"
            ),
            format!(
                "DELETE /api/items [Must] {nx}/items/route.ts:1 handler={nx}/items/handlers.ts::remove"
            ),
        ],
        "named and aliased re-exports resolve to the handler in the source module"
    );
    assert_eq!(
        routes_with(&a, "nextjs", "/api/alias ["),
        [
            format!(
                "GET /api/alias [Must] {nx}/alias/route.ts:1 handler={nx}/alias/route.ts::list"
            ),
            format!(
                "HEAD /api/alias [Must] {nx}/alias/route.ts:1 handler={nx}/alias/route.ts::list"
            ),
        ],
        "one local function exported as two methods"
    );
    assert_eq!(
        routes_with(&a, "nextjs", "/api/star ["),
        [
            format!(
                "GET /api/star [Must] {nx}/star/route.ts:1 handler={nx}/items/handlers.ts::GET"
            ),
            format!(
                "POST /api/star [Must] {nx}/star/route.ts:1 handler={nx}/items/handlers.ts::POST"
            ),
        ],
        "export * contributes the methods the source module exports"
    );
    assert_eq!(
        routes_with(&a, "nextjs", "/api/ext ["),
        [format!("GET /api/ext [Must] {nx}/ext/route.ts:1")],
        "a method re-exported from a package is a Must method without a handler"
    );
}

#[test]
// frob:tests crates/gob-frameworks/src/repo.rs::default_export
fn a_page_default_export_through_a_list_or_reexport_names_the_component() {
    let a = run("frameworks");
    let app = "apps/nx/app";
    for (route, component) in [
        ("/about", "about/about-page.tsx::AboutPage"),
        ("/team", "team/team-page.tsx::TeamPage"),
        ("/blog", "blog/blog-impl.tsx::BlogImpl"),
        ("/local", "local/page.tsx::Local"),
    ] {
        let got = routes_with(&a, "nextjs", &format!("GET {route} "));
        assert_eq!(got.len(), 1, "{route}: {got:?}");
        assert!(
            got[0].contains(&format!("component={app}/{component}")),
            "{route}: {}",
            got[0]
        );
    }
}

#[test]
// frob:tests crates/gob-frameworks/src/react_router/config.rs::roots
fn a_routes_ts_config_produces_the_expected_routes() {
    let a = run("frameworks");
    let rr = "apps/rr/app";
    let page = |file: &str, name: &str| format!("component={rr}/routes/{file}.tsx::{name}");
    let expected = [
        format!("GET ? [Unknown] {rr}/routes.ts:21"),
        format!(
            "GET ? [Unknown] {rr}/routes.ts:20 {}",
            page("dyn", "DynPage")
        ),
        format!(
            "GET / [Must] {rr}/routes.ts:13 {}",
            page("home", "HomePage")
        ),
        format!(
            "GET /about [Must] {rr}/routes.ts:14 {}",
            page("about", "AboutPage")
        ),
        format!(
            "GET /admin [Must] {rr}/admin-routes.ts:4 {}",
            page("admin-home", "AdminHomePage")
        ),
        format!(
            "GET /admin/users/:id [Must] {rr}/admin-routes.ts:5 handler={rr}/routes/user.tsx::loader {}",
            page("user", "UserPage")
        ),
        format!(
            "POST /admin/users/:id [Must] {rr}/admin-routes.ts:5 handler={rr}/routes/user.tsx::action {}",
            page("user", "UserPage")
        ),
        format!(
            "GET /dash [Must] {rr}/routes.ts:16 {} layouts={rr}/routes/shell.tsx::ShellPage",
            page("dash", "DashPage")
        ),
        format!(
            "GET /shop/cart [Must] {rr}/routes.ts:6 {}",
            page("cart", "CartPage")
        ),
        format!(
            "GET /shop/checkout [Must] {rr}/routes.ts:7 {}",
            page("checkout", "CheckoutPage")
        ),
    ];
    assert_eq!(routes_of(&a, "react-router"), expected);
    assert!(
        a.entrypoints
            .iter()
            .any(|e| e.kind == EntrypointKind::Router && e.file == format!("{rr}/routes.ts")),
        "the config file is a router entrypoint"
    );
}

#[test]
// frob:tests crates/gob-frameworks/src/lib.rs::analyze
fn the_framework_fixture_detects_next_and_react_router_apps() {
    let a = run("frameworks");
    let found: Vec<(&str, &str)> = a
        .detections
        .iter()
        .map(|d| (d.framework, d.member.as_str()))
        .collect();
    assert_eq!(
        found,
        [
            ("nextjs", "apps/nx/package.json"),
            ("react-router", "apps/rr/package.json"),
        ]
    );
    assert!(a.problems.is_empty(), "{:?}", a.problems);
}
