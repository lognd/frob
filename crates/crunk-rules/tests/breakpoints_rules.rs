//! BP001-003 against throwaway projects declaring sm/md/lg breakpoints, porting the Python
//! semantics: widths equal to a point (or point - 0.02), variant-gated bare utilities, and
//! fixed widths above the smallest point.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

mod support;

use crunk_rules::rules::{bp001::Bp001, bp002::Bp002, bp003::Bp003};

fn css(query: &str) -> String {
    format!("{query} {{\n  .a {{\n    display: block;\n  }}\n}}\n")
}

fn tsx(class: &str) -> String {
    format!("export const A = () => <div className=\"{class}\" />;")
}

fn bp1(query: &str) -> usize {
    let host = support::project("styles/base/app.css", &css(query), Some("breakpoints"));
    support::run::<Bp001>(&host).len()
}

fn bp2(class: &str) -> usize {
    let host = support::project("src/a.tsx", &tsx(class), Some("breakpoints"));
    support::run::<Bp002>(&host).len()
}

fn bp3(decl: &str) -> Vec<String> {
    let text = format!(".a {{\n  {decl};\n}}\n");
    let host = support::project("styles/base/app.css", &text, Some("breakpoints"));
    support::run::<Bp003>(&host)
        .into_iter()
        .map(|f| f.message)
        .collect()
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
fn declared_widths_and_the_point_minus_a_hundredth_are_clean_for_bp001() {
    assert_eq!(bp1("@media (min-width: 768px)"), 0);
    assert_eq!(bp1("@media (max-width: 768px)"), 0);
    assert_eq!(bp1("@media (min-width: 767.98px)"), 0);
    assert_eq!(bp1("@media (max-width: 767.98px)"), 0);
}

// frob:tests crates/crunk-rules/src/rules/bp001.rs::Bp001
#[test]
fn the_point_minus_one_pixel_fires_bp001() {
    assert_eq!(bp1("@media (max-width: 767px)"), 1);
    assert_eq!(bp1("@media (min-width: 767px)"), 1);
}

// frob:tests crates/crunk-rules/src/rules/bp002.rs::Bp002
#[test]
fn a_responsive_flex_without_a_base_fires_bp002() {
    assert_eq!(bp2("md:flex"), 1);
    assert_eq!(bp2("block md:flex"), 0);
}

// frob:tests crates/crunk-rules/src/rules/bp002.rs::Bp002
#[test]
fn bp002_groups_bare_display_utilities_and_matches_prefix_families() {
    assert_eq!(bp2("hidden md:flex"), 0);
    assert_eq!(bp2("md:w-1/2"), 1);
    assert_eq!(bp2("w-full md:w-1/2"), 0);
    assert_eq!(bp2("md:flex-col"), 0);
}

// frob:tests crates/crunk-rules/src/rules/bp002.rs::Bp002
#[test]
fn bp002_ignores_non_point_variants_and_judges_arbitrary_min() {
    assert_eq!(bp2("hover:flex"), 0);
    assert_eq!(bp2("min-[900px]:flex"), 1);
}

// frob:tests crates/crunk-rules/src/rules/bp003.rs::Bp003
#[test]
fn a_fixed_width_above_the_smallest_point_fires_bp003() {
    let m = bp3("width: 800px");
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(
        m[0].contains("width: 800px") && m[0].contains("sm=640px"),
        "{}",
        m[0]
    );
    assert_eq!(bp3("min-width: 50rem").len(), 1);
}

// frob:tests crates/crunk-rules/src/rules/bp003.rs::Bp003
#[test]
fn bp003_exempts_max_width_small_widths_and_other_units() {
    assert!(bp3("max-width: 800px").is_empty());
    assert!(bp3("width: 600px").is_empty());
    assert!(bp3("width: 80%").is_empty());
}
