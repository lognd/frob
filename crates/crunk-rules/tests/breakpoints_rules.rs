//! BP001-003 against throwaway projects declaring sm/md/lg breakpoints.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

mod support;

use crunk_rules::rules::{bp001::Bp001, bp002::Bp002, bp003::Bp003};

fn css(query: &str) -> String {
    format!("{query} {{\n  .a {{\n    display: block;\n  }}\n}}\n")
}

// frob:tests crates/crunk-rules/src/rules/bp001.rs::Bp001
#[test]
fn an_undeclared_media_width_fires_bp001() {
    let host = support::project(
        "styles/base/app.css",
        &css("@media (min-width: 850px)"),
        Some("breakpoints"),
    );
    let found = support::run::<Bp001>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(found[0].message.contains("850px"), "{}", found[0].message);
}

// frob:tests crates/crunk-rules/src/rules/bp001.rs::Bp001
#[test]
fn a_declared_media_width_is_clean_for_bp001() {
    let ok = support::project(
        "styles/base/app.css",
        &css("@media (min-width: 768px)"),
        Some("breakpoints"),
    );
    assert!(support::run::<Bp001>(&ok).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/bp003.rs::Bp003
#[test]
fn a_max_width_query_fires_bp003() {
    let host = support::project(
        "styles/base/app.css",
        &css("@media (max-width: 768px)"),
        Some("breakpoints"),
    );
    assert_eq!(support::run::<Bp003>(&host).len(), 1);
}

// frob:tests crates/crunk-rules/src/rules/bp002.rs::Bp002
#[test]
fn a_responsive_flex_without_a_base_fires_bp002() {
    let bare = "export const A = () => <div className=\"md:flex\" />;";
    let host = support::project("src/a.tsx", bare, Some("breakpoints"));
    assert_eq!(support::run::<Bp002>(&host).len(), 1);
    let based = "export const A = () => <div className=\"block md:flex\" />;";
    let host = support::project("src/a.tsx", based, Some("breakpoints"));
    assert!(support::run::<Bp002>(&host).is_empty());
}
