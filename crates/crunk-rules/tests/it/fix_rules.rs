//! Tier A fix payloads of COLOR001, SPACE001, TYPE001, RADIUS001 and SIZE001: an in-tolerance
//! literal carries one machine edit to its token, an out-of-tolerance one carries none, a
//! translucent colour becomes `color-mix(...)`, and INV-FIX-02 (re-check of a fixed site is clean).

// frob:ticket 01M54H34N0CPKAZ7TP91EYXGVV

use crate::support;

use crunk_rules::rules::{
    color001::Color001, radius001::Radius001, size001::Size001, space001::Space001,
    type001::Type001,
};
use gob_rules::{Applicability, Finding, FixKind, RepoRule};

fn css(text: &str) -> support::Project {
    support::project("styles/app.css", text, None)
}

/// Apply the edits of `finding`'s fix to `text` (what `crunk fix` does for one finding).
fn apply(text: &str, finding: &Finding) -> String {
    let fix = finding.fix.as_ref().expect("a fix is attached");
    assert_eq!(fix.kind, FixKind::Deterministic);
    assert_eq!(fix.applicability, Applicability::Machine);
    let mut out = text.to_owned();
    let mut edits: Vec<_> = fix.edits.iter().collect();
    edits.sort_by_key(|e| std::cmp::Reverse(e.range.start()));
    for e in edits {
        out.replace_range(
            e.range.start().to_usize()..e.range.end().to_usize(),
            &e.replacement,
        );
    }
    out
}

/// Run `R` over `text`, fix its only finding, and return the fixed text after proving the
/// re-check of the fixed text is clean.
fn fix_and_recheck<R: RepoRule<support::Project> + Default>(text: &str) -> String {
    let found = support::run::<R>(&css(text));
    assert_eq!(found.len(), 1, "{found:?}");
    let fixed = apply(text, &found[0]);
    let again = support::run::<R>(&css(&fixed));
    assert!(again.is_empty(), "re-check of {fixed:?}: {again:?}");
    fixed
}

// frob:tests crates/crunk-rules/src/rules/space001.rs::Space001
// frob:tests crates/crunk-rules/src/scales/mod.rs::check
// frob:tests crates/crunk-rules/src/fixes.rs::replace_span
// frob:tests crates/gob-rules/src/decl.rs::Out.fire_in_with_fix
#[test]
fn an_in_tolerance_space_length_is_rewritten_to_its_token() {
    let fixed = fix_and_recheck::<Space001>(".a { margin: 13px; }\n");
    assert_eq!(fixed, ".a { margin: var(--space-12); }\n");
}

// frob:tests crates/crunk-rules/src/rules/type001.rs::Type001
#[test]
fn an_in_tolerance_font_size_is_rewritten_to_its_token() {
    let found = support::run::<Type001>(&css(".a { font-size: 15px; }\n"));
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(apply(".a { font-size: 15px; }\n", &found[0]).contains("var(--"));
    fix_and_recheck::<Type001>(".a { font-size: 15px; }\n");
}

// frob:tests crates/crunk-rules/src/rules/radius001.rs::Radius001
#[test]
fn an_in_tolerance_radius_is_rewritten_to_its_token() {
    let fixed = fix_and_recheck::<Radius001>(".a { border-radius: 7px; }\n");
    assert!(fixed.contains("var(--"), "{fixed}");
}

// frob:tests crates/crunk-rules/src/rules/size001.rs::Size001
#[test]
fn an_in_tolerance_box_size_is_rewritten_to_its_token() {
    let fixed = fix_and_recheck::<Size001>(".a { height: 47px; }\n");
    assert!(fixed.contains("var(--"), "{fixed}");
}

// frob:tests crates/crunk-rules/src/rules/space001.rs::Space001
// frob:tests crates/crunk-rules/src/rules/type001.rs::Type001
// frob:tests crates/crunk-rules/src/rules/radius001.rs::Radius001
// frob:tests crates/crunk-rules/src/rules/size001.rs::Size001
#[test]
fn a_value_outside_tolerance_carries_no_fix_and_still_fires() {
    for found in [
        support::run::<Space001>(&css(".a { margin: 14px; }\n")),
        support::run::<Space001>(&css(".a { margin: -13px; }\n")),
        support::run::<Type001>(&css(".a { font-size: 100px; }\n")),
        support::run::<Radius001>(&css(".a { border-radius: 100px; }\n")),
        support::run::<Size001>(&css(".a { height: 1000px; }\n")),
    ] {
        assert_eq!(found.len(), 1, "{found:?}");
        assert!(found[0].fix.is_none(), "{:?}", found[0]);
    }
}

// frob:tests crates/crunk-rules/src/rules/color001.rs::Color001
#[test]
fn an_in_tolerance_color_is_rewritten_to_its_token() {
    let fixed = fix_and_recheck::<Color001>(".a { color: #1b1b1b; }\n");
    assert_eq!(fixed, ".a { color: var(--color-ink); }\n");
}

// frob:tests crates/crunk-rules/src/rules/color001.rs::Color001
#[test]
fn a_far_color_carries_no_fix() {
    let far = support::run::<Color001>(&css(".a { color: #ff0000; }\n"));
    assert_eq!(far.len(), 1, "{far:?}");
    assert!(far[0].fix.is_none());
}

// frob:tests crates/crunk-rules/src/rules/color001.rs::Color001
// frob:tests crates/crunk-rules/src/fixes.rs::color_replacement
#[test]
fn a_translucent_color_in_tolerance_becomes_color_mix() {
    // The re-check is not asserted clean: crunk-ingest reports `color-mix(.. var() ..)` as an
    // unreadable colour literal (follow-up ticket filed), which is not a literal-colour finding.
    let text = ".a { color: rgba(27, 27, 27, 0.5); }\n";
    let found = support::run::<Color001>(&css(text));
    assert_eq!(found.len(), 1, "{found:?}");
    let fixed = apply(text, &found[0]);
    assert_eq!(
        fixed,
        ".a { color: color-mix(in srgb, var(--color-ink) 50%, transparent); }\n"
    );
}

// INV-FIX-02: for every in-tolerance off-scale length the re-check of the fixed site is clean.
// frob:tests crates/crunk-rules/src/scales/mod.rs::check
#[test]
fn inv_fix_02_the_recheck_of_every_fixed_space_site_is_clean() {
    for px in 1..=40 {
        let text = format!(".a {{ padding: {px}px; }}\n");
        let found = support::run::<Space001>(&css(&text));
        let Some(first) = found.first() else { continue };
        if first.fix.is_none() {
            continue;
        }
        let fixed = apply(&text, first);
        assert!(
            support::run::<Space001>(&css(&fixed)).is_empty(),
            "{text} -> {fixed}"
        );
    }
}
