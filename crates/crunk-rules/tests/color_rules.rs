//! COLOR001 and COLOR002 beyond the rule pages: messages, tolerance, severities, the mode loop and
//! applicability.

// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

mod support;

use crunk_rules::rules::{color001::Color001, color002::Color002};
use crunk_rules::{CrunkHost, color::Palette, host::missing_inputs, mode};
use crunk_values::Color;
use gob_rules::{RuleDecl, RuleDef, Severity};

fn css(text: &str) -> support::Project {
    support::project("styles/app.css", text, None)
}

// frob:tests crates/crunk-rules/src/rules/color001.rs::Color001
#[test]
fn a_literal_within_color_tolerance_names_the_palette_token() {
    let found = support::run::<Color001>(&css(".a { color: #1b1b1b; }\n"));
    assert_eq!(found.len(), 1, "{found:?}");
    let message = &found[0].message;
    assert!(
        message.contains("nearest is --color-ink (distance"),
        "{message}"
    );
    assert!(!message.contains("beyond color_tolerance"), "{message}");
    assert_eq!(found[0].severity, Severity::Error);
}

// frob:tests crates/crunk-rules/src/rules/color001.rs::Color001
#[test]
fn a_literal_beyond_color_tolerance_still_fires_and_says_so() {
    let found = support::run::<Color001>(&css(".a { color: #ff0000; }\n"));
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].message.contains("beyond color_tolerance"),
        "{}",
        found[0].message
    );
}

// frob:tests crates/crunk-rules/src/rules/color001.rs::Color001
#[test]
fn a_translucent_off_palette_literal_says_the_fix_preserves_alpha() {
    let found = support::run::<Color001>(&css(".a { color: rgba(10, 200, 30, 0.5); }\n"));
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].message.contains("the fix preserves alpha"),
        "{}",
        found[0].message
    );
}

// frob:tests crates/crunk-rules/src/rules/color001.rs::Color001
#[test]
fn the_finding_is_located_at_the_literal_in_its_file() {
    let text = ".a {\n  color: #1b1b1b;\n}\n";
    let host = css(text);
    let found = support::run::<Color001>(&host);
    let span = found[0].span.expect("located");
    let at = span.range.start().to_usize();
    assert_eq!(&text[at..at + 7], "#1b1b1b");
}

// frob:tests crates/crunk-rules/src/color/mod.rs::Palette
#[test]
fn conformance_is_exact_or_translucent_over_an_opaque_entry() {
    let ink = Color::parse("#1a1a1a").expect("ink");
    let palette = Palette::new(vec![("ink", ink)]);
    assert!(palette.conforms(ink));
    assert!(palette.conforms(Color::parse("rgba(26, 26, 26, 0.5)").expect("shade")));
    assert!(!palette.conforms(Color::parse("#1b1b1b").expect("near")));
    assert_eq!(palette.nearest(ink).map(|(n, _)| n), Some("ink"));
    assert!(Palette::new(Vec::new()).nearest(ink).is_none());
}

// frob:tests crates/crunk-rules/src/rules/color002.rs::Color002
#[test]
fn with_the_generated_sheet_indexed_an_undefined_reference_is_an_error() {
    let found = support::run::<Color002>(&css(".a { color: var(--color-missing); }\n"));
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].severity, Severity::Error);
    assert_eq!(
        found[0].message,
        "var(--color-missing) references an undefined token"
    );
    assert!(found[0].span.is_some(), "located at the reference");
}

// frob:tests crates/crunk-rules/src/rules/color002.rs::Color002
#[test]
fn without_the_generated_sheet_the_same_reference_is_unresolved_not_clean() {
    let host = support::project(
        "styles/app.css",
        ".a { color: var(--color-missing); }\n",
        Some("no-tokens"),
    );
    let found = support::run::<Color002>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].severity, Severity::Unresolved);
    assert!(
        found[0].message.contains("tokens sheet"),
        "{}",
        found[0].message
    );
}

// frob:tests crates/crunk-rules/src/color/defs.rs::unindexed_sources
#[test]
fn an_ungoverned_css_file_makes_the_definition_set_incomplete() {
    let complete = css(".a { color: var(--color-ink); }\n");
    assert!(
        crunk_rules::color::defs::unindexed_sources(&complete.spec, &complete.styles).is_empty()
    );
    let stray = support::project("other/x.css", ".a { color: red; }\n", None);
    let why = crunk_rules::color::defs::unindexed_sources(&stray.spec, &stray.styles);
    assert!(
        why.iter().any(|w| w.contains("outside css_root")),
        "{why:?}"
    );
}

// frob:tests crates/crunk-rules/src/host.rs::missing_inputs
#[test]
fn a_host_without_spec_or_styles_is_inapplicable() {
    struct Bare;
    impl CrunkHost for Bare {}
    assert_eq!(
        missing_inputs(&Bare).as_deref(),
        Some("no valid crunk.toml")
    );
    assert_eq!(missing_inputs(&css("")), None);
}

// frob:tests crates/crunk-rules/src/mode.rs::modes
#[test]
fn one_default_mode_until_phase_two() {
    let host = css("");
    let modes = mode::modes(&host.spec);
    assert_eq!(modes, [mode::Mode::DEFAULT]);
    assert!(modes[0].is_default());
    assert_eq!(modes[0].suffix(), "");
    assert_eq!(modes[0].palette(&host.spec).len(), 3);
}

fn def<R: RuleDecl>() -> &'static RuleDef {
    R::DEF
}

// frob:tests crates/crunk-rules/src/rules/color002.rs::Color002
#[test]
fn color002_is_a_p_minus_rule_and_color001_a_p_plus_rule() {
    assert_eq!(def::<Color002>().polarity, gob_rules::Polarity::Pminus);
    assert_eq!(def::<Color001>().polarity, gob_rules::Polarity::Pplus);
}

// frob:tests crates/crunk-rules/src/rules/color001.rs::Color001
#[test]
fn subjects_are_the_examined_sheets_without_the_tokens_sheet() {
    use gob_rules::Measured;
    let host = css(".a { color: #1a1a1a; }\n");
    assert_eq!(Measured::<support::Project>::subjects(&Color001, &host), 1);
    assert_eq!(Measured::<support::Project>::subjects(&Color002, &host), 1);
    let none = support::project("README.md", "x", None);
    assert_eq!(Measured::<support::Project>::subjects(&Color001, &none), 0);
}

// frob:tests crates/crunk-rules/src/color/defs.rs::defined_names
#[test]
fn the_definition_set_unions_the_token_export_and_the_sheets_own_properties() {
    let host = css(":root { --color-local: #1a1a1a; }\n");
    let defined =
        crunk_rules::color::defs::defined_names(&host.spec, &host.styles).expect("token set");
    assert!(defined.contains("--color-ink"), "exported");
    assert!(defined.contains("--color-local"), "sheet-defined");
    assert!(!defined.contains("--color-nope"));
}

// frob:tests crates/crunk-rules/src/color/mod.rs::off_palette_message
#[test]
fn the_message_is_alpha_aware_and_names_the_tolerance() {
    let opaque = Color::parse("#1b1b1b").expect("opaque");
    let near = crunk_rules::color::off_palette_message(opaque, "--color-ink", 1.0, true);
    assert_eq!(
        near,
        "color #1b1b1b is not a palette color; nearest is --color-ink (distance 1.00)"
    );
    let far = crunk_rules::color::off_palette_message(opaque, "--color-ink", 30.0, false);
    assert!(
        far.ends_with("beyond color_tolerance, so no automatic replacement"),
        "{far}"
    );
}

// frob:tests crates/crunk-rules/src/sheets.rs::is_tokens_sheet
// frob:tests crates/crunk-rules/src/sheets.rs::examined_sheets
#[test]
fn the_tokens_sheet_is_not_an_examined_sheet() {
    let host = css(".a { color: #1a1a1a; }\n");
    let tokens = host
        .styles
        .sheets
        .iter()
        .filter(|s| crunk_rules::sheets::is_tokens_sheet(s))
        .count();
    assert_eq!(tokens, 1, "the generated tokens sheet is indexed");
    assert_eq!(
        crunk_rules::sheets::examined_sheets(&host.styles),
        host.styles.sheets.len() - 1
    );
}
