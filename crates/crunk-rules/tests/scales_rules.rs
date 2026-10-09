//! SPACE001, TYPE001, RADIUS001 and SIZE001 beyond the rule pages: the scale judgment itself, the
//! messages, the fallbacks and the exemptions.

// frob:ticket 01M43ATBDWVSJBXP7TEQ6DBW3W

mod support;

use crunk_rules::rules::{
    radius001::Radius001, size001::Size001, space001::Space001, type001::Type001,
};
use crunk_rules::scales::off_scale;
use crunk_values::Length;
use gob_rules::{Measured, RepoRule, Severity};

fn css(text: &str) -> support::Project {
    support::project("styles/app.css", text, None)
}

fn px(text: &str) -> Length {
    Length::parse(text, 16.0).expect("a length")
}

const SCALE: [f64; 5] = [0.0, 4.0, 8.0, 12.0, 16.0];

// frob:tests crates/crunk-rules/src/scales/mod.rs::off_scale
#[test]
fn a_length_on_the_scale_or_not_px_comparable_is_not_off_scale() {
    assert!(off_scale(&px("8px"), &SCALE, 0.15).is_none());
    assert!(
        off_scale(&px("0.5rem"), &SCALE, 0.15).is_none(),
        "rem converts"
    );
    assert!(off_scale(&px("-8px"), &SCALE, 0.15).is_none(), "magnitude");
    assert!(off_scale(&px("50%"), &SCALE, 0.15).is_none());
    assert!(off_scale(&px("auto"), &SCALE, 0.15).is_none());
    assert!(off_scale(&px("2em"), &SCALE, 0.15).is_none());
    assert!(off_scale(&px("0"), &SCALE, 0.15).is_none());
}

// frob:tests crates/crunk-rules/src/scales/mod.rs::off_scale
#[test]
fn the_neighbours_the_nearest_step_and_the_tolerance_are_reported() {
    let off = off_scale(&px("13px"), &SCALE, 0.15).expect("off scale");
    assert!((off.lower - 12.0).abs() < f64::EPSILON && (off.upper - 16.0).abs() < f64::EPSILON);
    assert!((off.nearest - 12.0).abs() < f64::EPSILON);
    assert!(off.snappable, "1px is within 15 percent of 12px");
    let far = off_scale(&px("14px"), &SCALE, 0.15).expect("off scale");
    assert!(
        !far.snappable,
        "2px is not within 15 percent of 12px or 16px"
    );
    let past_top = off_scale(&px("40px"), &SCALE, 0.15).expect("off scale");
    assert!(
        (past_top.lower - 16.0).abs() < f64::EPSILON
            && (past_top.upper - 16.0).abs() < f64::EPSILON
    );
}

// frob:tests crates/crunk-rules/src/scales/mod.rs::off_scale
#[test]
fn step_zero_borrows_an_absolute_allowance_from_the_smallest_nonzero_step() {
    let near_zero = off_scale(&px("0.5px"), &SCALE, 0.15).expect("off scale");
    assert!((near_zero.nearest - 0.0).abs() < f64::EPSILON);
    assert!(near_zero.snappable, "0.5 <= 0.15 * 4");
    let farther = off_scale(&px("1px"), &SCALE, 0.15).expect("off scale");
    assert!(farther.nearest > 0.0 || !farther.snappable);
}

// frob:tests crates/crunk-rules/src/rules/space001.rs::Space001
#[test]
fn the_message_names_the_property_the_bracket_and_the_nearest_step() {
    let found = support::run::<Space001>(&css(".a { margin: 13px; }\n"));
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(
        found[0].message,
        "margin: 13px is off the scale; between var(--space-12) and var(--space-16); nearest is var(--space-12)"
    );
    assert_eq!(found[0].severity, Severity::Error);
    let far = support::run::<Space001>(&css(".a { margin: 14px; }\n"));
    assert!(
        far[0].message.contains("beyond fix_tolerance"),
        "{}",
        far[0].message
    );
}

// frob:tests crates/crunk-rules/src/rules/space001.rs::Space001
#[test]
fn every_off_scale_length_of_a_shorthand_is_its_own_finding_at_its_token() {
    let text = ".a { padding: 5px 8px 13px; }\n";
    let found = support::run::<Space001>(&css(text));
    assert_eq!(found.len(), 2, "{found:?}");
    let at: Vec<usize> = found
        .iter()
        .map(|f| f.span.expect("located").range.start().to_usize())
        .collect();
    assert_eq!(&text[at[0]..at[0] + 3], "5px");
    assert_eq!(&text[at[1]..at[1] + 4], "13px");
}

// frob:tests crates/crunk-rules/src/rules/type001.rs::Type001
#[test]
fn type001_judges_font_size_against_the_font_size_scale() {
    let found = support::run::<Type001>(&css("h1 { font-size: 27px; }\n"));
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0]
            .message
            .starts_with("font-size: 27px is off the scale; between var(--font-size-24)"),
        "{}",
        found[0].message
    );
    assert!(support::run::<Type001>(&css("h1 { font-size: 24px; margin: 13px; }\n")).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/size001.rs::Size001
#[test]
fn size001_falls_back_to_spacing_names_and_exempts_max_width() {
    let found = support::run::<Size001>(&css(".a { width: 45px; max-width: 640px; }\n"));
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].message.contains("var(--space-"),
        "{}",
        found[0].message
    );
    assert_eq!(found[0].severity, Severity::Warn);
}

// frob:tests crates/crunk-rules/src/rules/size001.rs::Size001
#[test]
fn size001_uses_the_declared_sizes_scale_and_its_token_names() {
    let spec = support::DEFAULT_SPEC.replace("[scales]", "[scales]\nsizes = [20, 40, 80]");
    let host = support::project_with_spec(
        &spec,
        "styles/app.css",
        ".a { width: 45px; height: 40px; }\n",
    );
    let found = support::run::<Size001>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].message.contains("var(--size-40)"),
        "{}",
        found[0].message
    );
}

// frob:tests crates/crunk-rules/src/rules/radius001.rs::Radius001
#[test]
fn radius001_is_inapplicable_without_declared_radii() {
    let spec = support::DEFAULT_SPEC.replace("radii = [0, 4, 8, 16]", "radii = []");
    let host = support::project_with_spec(&spec, "styles/app.css", ".a { border-radius: 6px; }\n");
    assert_eq!(
        RepoRule::<support::Project>::inapplicable(&Radius001, &host).as_deref(),
        Some("no [scales] radii are declared")
    );
    assert!(support::run::<Radius001>(&host).is_empty());
    let with = css(".a { border-radius: 6px; }\n");
    assert_eq!(
        RepoRule::<support::Project>::inapplicable(&Radius001, &with),
        None
    );
    assert_eq!(support::run::<Radius001>(&with).len(), 1);
}

// frob:tests crates/crunk-rules/src/rules/space001.rs::Space001
#[test]
fn subjects_are_the_examined_sheets() {
    let host = css(".a { margin: 12px; }\n");
    assert_eq!(Measured::<support::Project>::subjects(&Space001, &host), 1);
}
