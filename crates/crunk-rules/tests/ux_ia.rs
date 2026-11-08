//! The IA checks over a throwaway project: the acceptance cases and edge cases.

// frob:ticket 01M5XCZ0XPCPA1DT2QB5VGHDZC

use std::path::Path;

use crunk_rules::ux::ia::{IaFacts, IaFinding, IaIssue, ScreenRoute, check_ia};
use crunk_spec::parse_spec;

fn facts(sitemap: Option<&str>) -> IaFacts {
    let dir = tempfile::tempdir().expect("tempdir");
    if let Some(text) = sitemap {
        let path = dir.path().join("design/ia/sitemap.toml");
        std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
        std::fs::write(path, text).expect("write");
    }
    let spec = parse_spec(
        crunk_spec::presets::DEFAULT,
        Path::new("crunk.toml"),
        dir.path(),
    )
    .expect("spec");
    IaFacts::load(&spec)
}

fn screen(id: &str, entry: &str) -> ScreenRoute {
    ScreenRoute {
        id: id.into(),
        entry: entry.into(),
    }
}

fn page(route: &str, label: &str, parent: Option<&str>) -> String {
    let parent = parent.map_or_else(String::new, |p| format!("parent = \"{p}\"\n"));
    format!("[[pages]]\nroute = \"{route}\"\nlabel = \"{label}\"\n{parent}")
}

fn issues(f: &[IaFinding]) -> Vec<IaIssue> {
    f.iter().map(|f| f.issue).collect()
}

fn run(map: &str, screens: &[ScreenRoute], code: Option<&[&str]>) -> Vec<IaFinding> {
    let code: Option<Vec<String>> = code.map(|c| c.iter().map(|s| (*s).to_owned()).collect());
    check_ia(&facts(Some(map)), screens, code.as_deref())
}

// frob:tests crates/crunk-rules/src/ux/ia.rs::check_ia
#[test]
fn ia_route_without_screen_and_screen_without_route_fire() {
    let map = format!("{}{}", page("/", "Home", None), page("/a", "A", Some("/")));
    let f = run(
        &map,
        &[screen("home", "/"), screen("lonely", "/lonely")],
        Some(&["/", "/a"]),
    );
    assert_eq!(
        issues(&f),
        [IaIssue::RouteWithoutScreen, IaIssue::ScreenWithoutRoute]
    );
    assert!(f[0].message.contains("/a") && f[0].line == Some(5), "{f:?}");
    assert!(f[1].message.contains("lonely"));
}

// frob:tests crates/crunk-rules/src/ux/ia.rs::check_ia
#[test]
fn ia_code_routes_missing_from_the_sitemap_are_named() {
    let map = page("/", "Home", None);
    let f = run(&map, &[screen("home", "/")], Some(&["/", "/hidden"]));
    assert_eq!(issues(&f), [IaIssue::CodeRouteMissing]);
    assert!(f[0].message.contains("/hidden"));
}

// frob:tests crates/crunk-rules/src/ux/ia.rs::check_ia
#[test]
fn ia_unavailable_route_discovery_is_unresolved_not_clean() {
    let f = run(&page("/", "Home", None), &[screen("home", "/")], None);
    assert_eq!(issues(&f), [IaIssue::Unresolved]);
}

// frob:tests crates/crunk-rules/src/ux/ia.rs::check_ia
#[test]
fn ia_depth_fires_once_per_deepest_path() {
    let map = format!(
        "max_depth = 1\n{}{}{}{}{}",
        page("/", "Home", None),
        page("/a", "A", Some("/")),
        page("/a/b", "B", Some("/a")),
        page("/a/b/c", "C", Some("/a/b")),
        page("/a/b/d", "D", Some("/a/b")),
    );
    let screens = ["/", "/a", "/a/b", "/a/b/c", "/a/b/d"].map(|r| screen(r, r));
    let f = run(
        &map,
        &screens,
        Some(&["/", "/a", "/a/b", "/a/b/c", "/a/b/d"]),
    );
    assert_eq!(issues(&f), [IaIssue::TooDeep, IaIssue::TooDeep], "{f:?}");
}

// frob:tests crates/crunk-rules/src/ux/ia.rs::check_ia
#[test]
fn ia_sibling_labels_differing_by_case_collide() {
    let map = format!(
        "{}{}{}",
        page("/", "Home", None),
        page("/a", "Docs", Some("/")),
        page("/b", "docs", Some("/"))
    );
    let screens = ["/", "/a", "/b"].map(|r| screen(r, r));
    let f = run(&map, &screens, Some(&["/", "/a", "/b"]));
    assert_eq!(issues(&f), [IaIssue::LabelCollision]);
}

// frob:tests crates/crunk-rules/src/ux/ia.rs::check_ia
#[test]
fn ia_a_page_unreachable_from_home_is_named() {
    let map = format!(
        "{}{}",
        page("/", "Home", None),
        page("/island", "Island", None)
    );
    let screens = ["/", "/island"].map(|r| screen(r, r));
    let f = run(&map, &screens, Some(&["/", "/island"]));
    assert_eq!(issues(&f), [IaIssue::Unreachable]);
    assert!(f[0].message.contains("/island"));
}

// frob:tests crates/crunk-rules/src/ux/ia.rs::check_ia
#[test]
fn ia_a_dynamic_route_matches_a_screen_with_the_same_param_shape() {
    let map = format!(
        "{}{}",
        page("/", "Home", None),
        page("/users/:id", "User", Some("/"))
    );
    let f = run(
        &map,
        &[screen("home", "/"), screen("user", "/users/[name]")],
        Some(&["/", "/users/{id}"]),
    );
    assert!(f.is_empty(), "{f:?}");
}

// frob:tests crates/crunk-rules/src/ux/ia.rs::check_ia
// frob:tests crates/crunk-rules/src/ux/ia.rs::IaFacts.load
#[test]
fn ia_a_parent_cycle_is_a_schema_finding_and_an_absent_sitemap_is_silent() {
    let cycle = format!(
        "{}{}",
        page("/a", "A", Some("/b")),
        page("/b", "B", Some("/a"))
    );
    let f = run(&cycle, &[], Some(&[]));
    assert_eq!(issues(&f), [IaIssue::Schema]);
    assert!(f[0].message.contains("E-IA-CYCLE"));
    assert!(check_ia(&facts(None), &[screen("x", "/x")], None).is_empty());
}
