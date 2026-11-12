//! Router route discovery: `router.tsx` fixtures parse to the paths GALLERY005 checks.

// frob:ticket 01M4YZCC0PBYFW8CSBB8ERKFXE

use crunk_gallery::router::{RouterError, parse_routes};

const OBJECT: &str = include_str!("../fixtures/router/object.tsx");
const JSX: &str = include_str!("../fixtures/router/jsx.tsx");
const DYNAMIC: &str = include_str!("../fixtures/router/dynamic_path.tsx");
const TEMPLATE: &str = include_str!("../fixtures/router/template_path.tsx");
const NONE: &str = include_str!("../fixtures/router/none.tsx");

// frob:tests parse_routes
#[test]
fn object_routes_nest_and_keep_dynamic_segments() {
    let routes = parse_routes(OBJECT).unwrap();
    assert_eq!(
        routes,
        [
            "/",
            "/about",
            "/users/:id",
            "/users/:id/edit",
            "/settings",
            "*"
        ]
    );
}

#[test]
fn jsx_routes_nest_and_survive_apostrophes() {
    let routes = parse_routes(JSX).unwrap();
    assert_eq!(
        routes,
        [
            "/",
            "/pricing",
            "/docs/:slug?",
            "/docs/:slug?/api",
            "/login"
        ]
    );
}

#[test]
fn identifier_path_is_a_typed_error() {
    let err = parse_routes(DYNAMIC).unwrap_err();
    assert!(
        matches!(err, RouterError::UnsupportedPath { line: 2, .. }),
        "{err}"
    );
    assert!(err.to_string().contains("ROUTES"));
}

#[test]
fn interpolated_template_path_is_a_typed_error() {
    let err = parse_routes(TEMPLATE).unwrap_err();
    assert!(
        matches!(err, RouterError::UnsupportedPath { line: 1, .. }),
        "{err}"
    );
}

#[test]
fn source_without_routes_is_a_typed_error() {
    assert_eq!(parse_routes(NONE), Err(RouterError::NoRoutes));
    assert_eq!(parse_routes(""), Err(RouterError::NoRoutes));
}

#[test]
fn unterminated_input_does_not_panic() {
    assert!(parse_routes("<Route path=\"/a").is_err());
    assert!(parse_routes("/* open").is_err());
    assert!(parse_routes("{ path: ").is_err());
}

#[test]
fn discovered_routes_feed_gallery005() {
    use crunk_gallery::rules::check_routes;
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../crunk-spec/tests/fixtures/valid/gallery005_routes.toml");
    let text = std::fs::read_to_string(&path).unwrap();
    let spec = crunk_spec::parse_spec(&text, &path, path.parent().unwrap()).unwrap();
    let routes = parse_routes(JSX).unwrap();
    let findings = check_routes(&spec, &routes);
    assert!(findings.iter().all(|f| f.rule == "GALLERY005"));
}
