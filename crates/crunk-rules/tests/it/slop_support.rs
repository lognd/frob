//! The shared SLOP helpers: the decision gate, sheet filters, accent stops, emoji test and markup scanner.

// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use crate::support;

use crunk_rules::slop::{
    attrs_mention, decided, default_accent_of, default_accent_stops, is_emoji, judged_sheets,
    leading_char, markup_sheets, tags, text_after,
};
use crunk_values::Color;

// frob:tests crates/crunk-rules/src/slop/mod.rs::decided
#[test]
fn decided_is_true_only_for_a_declared_decision() {
    let spec = "\n[decisions]\nradius = \"square on purpose\"\n";
    let text = format!("{}{spec}", support::DEFAULT_SPEC);
    let host = support::project_with_spec(&text, "styles/app.css", "a { color: red; }\n");
    assert!(decided(&host.spec, "radius"));
    assert!(!decided(&host.spec, "accent"));
}

// frob:tests crates/crunk-rules/src/slop/mod.rs::judged_sheets
#[test]
fn judged_sheets_keeps_css_and_drops_token_sheets() {
    let css = support::project("styles/app.css", "a { color: red; }\n", None);
    assert!(markup_sheets(&css.styles).next().is_none());
    let judged = judged_sheets(&css.styles).count();
    assert!(judged >= 1 && judged <= css.styles.sheets.len());
    assert!(judged_sheets(&css.styles).all(|s| !crunk_rules::sheets::is_tokens_sheet(s)));
}

// frob:tests crates/crunk-rules/src/slop/mod.rs::markup_sheets
#[test]
fn markup_sheets_selects_the_sheet_of_a_tsx_file() {
    let tsx = support::project(
        "src/Card.tsx",
        "export const A = () => <div className=\"p-4\" />;\n",
        None,
    );
    assert_eq!(markup_sheets(&tsx.styles).count(), 1);
}

// frob:tests crates/crunk-rules/src/slop/mod.rs::default_accent_stops
// frob:tests crates/crunk-rules/src/slop/mod.rs::default_accent_of
#[test]
fn the_default_accent_stops_match_an_indigo_and_not_red() {
    let stops = default_accent_stops();
    assert_eq!(stops.len(), 12);
    let indigo = Color::parse("#6366f1").expect("indigo-500");
    assert_eq!(default_accent_of(indigo, &stops), Some("indigo-500"));
    let red = Color::parse("#ff0000").expect("red");
    assert_eq!(default_accent_of(red, &stops), None);
}

// frob:tests crates/crunk-rules/src/slop/mod.rs::is_emoji
#[test]
fn is_emoji_flags_pictographs_only() {
    assert!(is_emoji('\u{1F680}'));
    assert!(is_emoji('\u{2728}'));
    assert!(!is_emoji('a'));
    assert!(!is_emoji('-'));
}

// frob:tests crates/crunk-rules/src/slop/mod.rs::leading_char
#[test]
fn leading_char_reads_references_and_escapes() {
    assert_eq!(leading_char("  &#x1F680; go"), Some('\u{1F680}'));
    assert_eq!(leading_char("&#128640;"), Some('\u{1F680}'));
    assert_eq!(leading_char("\\1F680 x"), Some('\u{1F680}'));
    assert_eq!(leading_char("plain"), Some('p'));
    assert_eq!(leading_char("&#12"), None);
    assert_eq!(leading_char(""), None);
}

// frob:tests crates/crunk-rules/src/slop/mod.rs::text_after
// frob:tests crates/crunk-rules/src/slop/mod.rs::attrs_mention
#[test]
fn text_after_and_attrs_mention_read_a_tag() {
    let src = "<h1 className=\"Hero\">  Welcome  <b>x</b></h1>";
    let found = tags(src);
    let h1 = &found[0];
    assert_eq!(h1.name, "h1");
    let (at, text) = text_after(src, h1).expect("text");
    assert_eq!(text, "Welcome");
    assert_eq!(&src[at..at + 7], "Welcome");
    assert!(attrs_mention(h1, &["hero"]));
    assert!(!attrs_mention(h1, &["card"]));
    assert!(text_after(src, &found[1]).is_some());
    assert!(text_after("<br/><i>", &tags("<br/><i>")[0]).is_none());
}
