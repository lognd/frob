//! BP001-BP003 beyond the rule pages: messages, the helpers, and the family being off without
//! `[breakpoints]`.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

mod support;

use crunk_rules::breakpoints::{has_responsive_variant, matched_family, matches_breakpoint};
use crunk_rules::rules::{bp001::Bp001, bp002::Bp002, bp003::Bp003};
use gob_rules::RepoRule;
use indexmap::IndexMap;

fn points() -> IndexMap<String, i64> {
    [("sm", 640), ("md", 768)]
        .into_iter()
        .map(|(n, px)| (n.to_owned(), px))
        .collect()
}

fn with_bp(file: &str, text: &str) -> support::Project {
    support::project(file, text, Some("breakpoints"))
}

// frob:tests crates/crunk-rules/src/breakpoints/mod.rs::matches_breakpoint
#[test]
fn a_breakpoint_matches_exactly_or_at_minus_point_oh_two() {
    let p = points();
    assert!(matches_breakpoint(768.0, &p));
    assert!(matches_breakpoint(767.98, &p));
    assert!(!matches_breakpoint(850.0, &p));
    assert!(!matches_breakpoint(767.0, &p));
}

// frob:tests crates/crunk-rules/src/breakpoints/mod.rs::has_responsive_variant
#[test]
fn a_declared_name_or_an_arbitrary_min_variant_is_responsive() {
    let p = points();
    let v = |names: &[&str]| names.iter().map(|s| (*s).to_owned()).collect::<Vec<_>>();
    assert!(has_responsive_variant(&v(&["md"]), &p));
    assert!(has_responsive_variant(&v(&["hover", "min-[500px]"]), &p));
    assert!(!has_responsive_variant(&v(&["hover"]), &p));
    assert!(
        !has_responsive_variant(&v(&["lg"]), &p),
        "lg is not declared here"
    );
    assert!(!has_responsive_variant(&v(&["min-[]"]), &p));
}

// frob:tests crates/crunk-rules/src/breakpoints/mod.rs::matched_family
#[test]
fn bare_entries_share_the_display_group_and_dashed_entries_are_their_own() {
    let required: Vec<String> = ["flex", "hidden", "w-"].map(str::to_owned).to_vec();
    assert_eq!(matched_family("flex", &required), Some(("flex", "display")));
    assert_eq!(
        matched_family("hidden", &required),
        Some(("hidden", "display"))
    );
    assert_eq!(matched_family("w-1/2", &required), Some(("w-", "w-")));
    assert_eq!(matched_family("p-4", &required), None);
}

// frob:tests crates/crunk-rules/src/rules/bp001.rs::Bp001
#[test]
fn bp001_names_the_query_the_width_and_the_declared_points() {
    let host = with_bp(
        "styles/app.css",
        "@media (min-width: 850px) { .a { margin: 0; } }\n",
    );
    let found = support::run::<Bp001>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(
        found[0].message,
        "media query '(min-width: 850px)' uses 850.0px, which is not a declared breakpoint [640, 768, 1024]"
    );
}

// frob:tests crates/crunk-rules/src/breakpoints/mod.rs::off_reason
#[test]
fn the_family_is_off_without_breakpoints() {
    let host = support::project(
        "styles/app.css",
        "@media (min-width: 850px) { .a { margin: 0; } }\n",
        None,
    );
    for why in [
        Bp001.inapplicable(&host),
        Bp002.inapplicable(&host),
        Bp003.inapplicable(&host),
    ] {
        assert!(why.is_some_and(|w| w.contains("breakpoints")));
    }
    assert!(Bp001.inapplicable(&with_bp("styles/app.css", "")).is_none());
}

// frob:tests crates/crunk-rules/src/rules/bp002.rs::Bp002
#[test]
fn bp002_judges_each_class_list_on_its_own() {
    let src = "export const A = () => <div className=\"block md:flex\" />;\nexport const B = () => <div className=\"md:flex\" />;\n";
    let found = support::run::<Bp002>(&with_bp("src/A.tsx", src));
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0]
            .message
            .starts_with("utility 'flex' has a responsive variant in family 'flex'")
    );
}

// frob:tests crates/crunk-rules/src/rules/bp003.rs::Bp003
#[test]
fn bp003_names_the_smallest_breakpoint() {
    let found = support::run::<Bp003>(&with_bp("styles/app.css", ".a { width: 700px; }\n"));
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(
        found[0].message,
        "width: 700px exceeds the smallest declared breakpoint sm=640px -- guaranteed mobile overflow"
    );
}
