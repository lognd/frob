//! I18N001-002 beyond the rule pages: the expansion boundary, a budget already blown, and the
//! physical-direction scan over CSS declarations and Tailwind utilities.

// frob:ticket 01M5H5P5H1CSMP9Q3NF4RY4M26

use crate::support;

use crunk_rules::rules::i18n001::I18n001;
use crunk_rules::rules::i18n002::I18n002;

fn keys(text: &str, max: u32) -> String {
    format!("locale = \"en\"\n\n[[key]]\nid = \"home.cta\"\ntext = \"{text}\"\nmax_chars = {max}\n")
}

// frob:tests crates/crunk-rules/src/rules/i18n001.rs::I18n001
// frob:tests crates/crunk-rules/src/i18n.rs::expanded_chars
#[test]
fn i18n001_fires_only_when_the_text_fits_but_its_expansion_does_not() {
    let file = "design/content/en.toml";
    // "Save" is 4 chars, 6 expanded.
    for (max, fires) in [(5, true), (6, false), (3, false)] {
        let host = support::project(file, &keys("Save", max), None);
        let found = support::run::<I18n001>(&host);
        assert_eq!(found.len(), usize::from(fires), "max {max}: {found:?}");
    }
    let host = support::project(
        file,
        "locale = \"en\"\n\n[[key]]\nid = \"a\"\ntext = \"Save\"\n",
        None,
    );
    assert!(support::run::<I18n001>(&host).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/i18n002.rs::I18n002
// frob:tests crates/crunk-rules/src/i18n.rs::logical_for_declaration
// frob:tests crates/crunk-rules/src/i18n.rs::logical_for_utility
// frob:tests crates/crunk-rules/src/i18n.rs::is_rtl_locale
#[test]
fn i18n002_fires_on_physical_sides_only_beside_a_right_to_left_locale() {
    let css = "styles/app.css";
    let physical = ".a { text-align: left; }\n";
    let host = support::project(css, physical, Some("i18n-rtl"));
    let found = support::run::<I18n002>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(found[0].message.contains("text-align: start"), "{found:?}");

    // No right-to-left locale: nothing to mirror.
    let host = support::project(css, physical, Some("content-en"));
    assert!(support::run::<I18n002>(&host).is_empty());

    let logical = ".a { margin-inline-start: 4px; text-align: center; }\n";
    let host = support::project(css, logical, Some("i18n-rtl"));
    assert!(support::run::<I18n002>(&host).is_empty());
}
