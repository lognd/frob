//! CONTENT001-003 over scenes and content files beyond the rule pages: the acceptance case (a
//! literal in a scene fires and suggests a key), edge cases and the inapplicable paths.

// frob:ticket 01M4CXR96GDDX460SZZVAAWD0R

use crate::support;

use crunk_rules::content_files::{is_copy, quote, suggest_key};
use crunk_rules::host::{content_subjects, missing_content_inputs};
use crunk_rules::rules::content001::Content001;
use crunk_rules::rules::content002::Content002;
use crunk_rules::rules::content003::Content003;
use crunk_rules::rules::content004::Content004;
use crunk_rules::rules::content005::Content005;
use crunk_rules::rules::content006::Content006;
use gob_rules::Finding;

const SCENE: &str = "design/scenes/home.scene.html";

fn c1(text: &str) -> Vec<String> {
    let host = support::project(SCENE, text, None);
    let f: Vec<Finding> = support::run::<Content001>(&host);
    f.into_iter().map(|f| f.message).collect()
}

fn c3(text: &str, config: Option<&str>) -> Vec<String> {
    let host = support::project(SCENE, text, config);
    let f: Vec<Finding> = support::run::<Content003>(&host);
    f.into_iter().map(|f| f.message).collect()
}

// frob:tests crates/crunk-rules/src/rules/content001.rs::Content001
// frob:tests crates/crunk-rules/src/content_files.rs::literal_copy
// frob:tests crates/crunk-rules/src/content_files.rs::suggest_key
#[test]
fn content001_fires_on_a_literal_and_suggests_a_key() {
    let m = c1("<h1 data-id=\"hero\">Welcome back</h1>\n");
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("Welcome back"), "{m:?}");
    assert!(m[0].contains("home.hero"), "{m:?}");
    assert!(m[0].contains("data-copy=\"home.hero\""), "{m:?}");
    assert!(m[0].contains("line 1"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/content001.rs::Content001
#[test]
fn content001_flags_copy_attributes_and_suggests_an_attribute_key() {
    let m = c1("<img data-id=\"logo\" alt=\"Company logo\">\n");
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("home.logo.alt"), "{m:?}");
    assert!(m[0].contains("data-copy-alt"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/content_files.rs::literal_copy
#[test]
fn content001_flags_component_text_props_but_not_option_props() {
    let m = c1("<Button data-id=\"save\" variant=\"primary\" label=\"Save changes\"></Button>\n");
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(
        m[0].contains("Save changes") && m[0].contains("label attribute"),
        "{m:?}"
    );
    assert!(m[0].contains("data-copy-label"), "{m:?}");
    let clean = "<Button label=\"Save\" data-copy-label=\"home.save\"></Button>\n";
    assert!(c1(clean).is_empty());
}

// frob:tests crates/crunk-rules/src/content_files.rs::literal_copy
#[test]
fn content001_flags_top_level_text_nodes() {
    let m = c1(
        "Welcome home\n<!-- note -->\n<div data-id=\"a\"><span>42</span></div>\n\nGoodbye\n<style>.a { color: red }</style>\n",
    );
    assert_eq!(m.len(), 2, "{m:?}");
    assert!(
        m[0].contains("Welcome home") && m[0].contains("top level"),
        "{m:?}"
    );
    assert!(m[0].contains("line 1"), "{m:?}");
    assert!(m[1].contains("Goodbye") && m[1].contains("line 5"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/content001.rs::Content001
#[test]
fn content001_ignores_empty_whitespace_numeric_and_punctuation_text() {
    assert!(c1("<p></p><p>   </p><p>42</p><p>-</p><p>$1,000</p>\n").is_empty());
}

// frob:tests crates/crunk-rules/src/rules/content001.rs::Content001
#[test]
fn content001_exempts_referenced_keys_and_style_bodies() {
    let text = "<style>.a { color: red }</style>\n<h1 data-copy=\"home.hero\">Welcome</h1>\n<img alt=\"Logo\" data-copy-alt=\"home.logo\">\n";
    assert!(c1(text).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/content001.rs::Content001
#[test]
fn content001_reports_nested_elements_each_once_in_order() {
    let m = c1("<div data-id=\"card\">Title <span data-id=\"sub\">Subtitle</span></div>\n");
    assert_eq!(m.len(), 2, "{m:?}");
    assert!(m[0].contains("Title") && m[1].contains("Subtitle"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/content001.rs::Content001
// frob:tests crates/crunk-rules/src/host.rs::missing_scene_doc_inputs
#[test]
fn content001_is_inapplicable_without_scenes() {
    let host = support::project("design/other.txt", "x", None);
    assert!(missing_content_inputs(&host).is_some());
    let f: Vec<Finding> = support::run::<Content001>(&host);
    assert!(f.is_empty());
}

// frob:tests crates/crunk-rules/src/content_files.rs::is_copy
// frob:tests crates/crunk-rules/src/content_files.rs::quote
#[test]
fn copy_detection_and_quoting() {
    assert!(is_copy("Save") && !is_copy("12.5") && !is_copy(" - "));
    assert_eq!(quote("short"), "short");
    assert!(quote(&"x".repeat(60)).ends_with("..."));
    assert_eq!(
        suggest_key(SCENE, "Hero Title", Some("alt")),
        "home.hero_title.alt"
    );
}

// frob:tests crates/crunk-rules/src/rules/content002.rs::Content002
// frob:tests crates/crunk-rules/src/content_files.rs::ContentFacts
// frob:tests crates/crunk-rules/src/content_files.rs::ContentDocFile
// frob:tests crates/crunk-rules/src/host.rs::content_subjects
// frob:tests crates/crunk-rules/src/host.rs::missing_content_inputs
#[test]
fn content002_fires_only_over_budget_and_anchors_on_the_key() {
    let over = "locale = \"en\"\n\n[[key]]\nid = \"a.b\"\ntext = \"Hello there\"\nmax_chars = 5\n\n[[key]]\nid = \"c\"\ntext = \"ok\"\nmax_chars = 5\n\n[[key]]\nid = \"d\"\ntext = \"unbounded copy\"\n";
    let host = support::project("design/content/en.toml", over, None);
    assert_eq!(content_subjects(&host), 1);
    assert!(missing_content_inputs(&host).is_none());
    let f: Vec<Finding> = support::run::<Content002>(&host);
    assert_eq!(f.len(), 1, "{f:?}");
    assert!(
        f[0].message.contains("a.b") && f[0].message.contains("by 6"),
        "{f:?}"
    );
    let facts = host.content.as_ref().unwrap();
    assert!(facts.defines("c") && !facts.defines("zzz"));
    assert_eq!(facts.key_count(), 3);
    assert!(facts.files[0].offset_of_key("a.b") > 0);
    let other = support::project("design/content/en.toml", "locale = \"en\"\n", None);
    assert_ne!(
        facts.fingerprint(),
        other.content.as_ref().unwrap().fingerprint()
    );
}

// frob:tests crates/crunk-rules/src/rules/content002.rs::Content002
#[test]
fn content002_counts_characters_not_bytes_and_is_inapplicable_without_files() {
    let text = "[[key]]\nid = \"k\"\ntext = \"\u{e9}\u{e9}\u{e9}\"\nmax_chars = 3\n";
    let host = support::project("design/content/en.toml", text, None);
    let f: Vec<Finding> = support::run::<Content002>(&host);
    assert!(f.is_empty(), "{f:?}");
    let none = support::project("design/other.txt", "x", None);
    assert!(missing_content_inputs(&none).is_some());
}

// frob:tests crates/crunk-rules/src/rules/content003.rs::Content003
// frob:tests crates/crunk-rules/src/content_files.rs::copy_refs
#[test]
fn content003_fires_for_undefined_keys_and_passes_defined_ones() {
    let m = c3("<h1 data-id=\"hero\" data-copy=\"home.nope\"></h1>\n", None);
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("home.nope"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/content003.rs::Content003
// frob:tests crates/crunk-rules/src/content_files.rs::copy_refs
#[test]
fn content003_fires_for_undefined_keys_and_passes_defined_ones_part_2() {
    let defined = c3(
        "<h1 data-id=\"hero\" data-copy=\"home.hero\"></h1>\n",
        Some("content-en"),
    );
    assert!(defined.is_empty(), "{defined:?}");
}

// frob:tests crates/crunk-rules/src/rules/content003.rs::Content003
// frob:tests crates/crunk-rules/src/content_files.rs::copy_refs
#[test]
fn content003_fires_for_undefined_keys_and_passes_defined_ones_part_3() {
    let attr = c3("<img data-copy-alt=\"missing\">\n", Some("content-en"));
    assert_eq!(attr.len(), 1, "{attr:?}");
}

// frob:tests crates/crunk-rules/src/content_files.rs::duplicate_keys
#[test]
fn duplicate_keys_lists_ids_defined_in_more_than_one_file() {
    let host = support::project(
        "design/content/en.toml",
        "[[key]]\nid = \"x\"\ntext = \"a\"\n",
        Some("content-en"),
    );
    let facts = host.content.as_ref().unwrap();
    assert!(crunk_rules::content_files::duplicate_keys(facts).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/content004.rs::Content004
// frob:tests crates/crunk-rules/src/content_files.rs::duplicate_keys
#[test]
fn content004_fires_for_a_key_in_two_files_and_passes_a_single_definition() {
    let toml = "locale = \"en\"\n\n[[key]]\nid = \"home.hero\"\ntext = \"Welcome back\"\n";
    let host = support::project("design/content/en.toml", toml, Some("content-dup"));
    let m: Vec<String> = support::run::<Content004>(&host)
        .into_iter()
        .map(|f| f.message)
        .collect();
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("home.hero"), "{m:?}");
    assert!(
        m[0].contains("en.toml") && m[0].contains("fr.toml"),
        "{m:?}"
    );

    let host = support::project("design/content/en.toml", toml, None);
    assert!(support::run::<Content004>(&host).is_empty());
}

// frob:ticket 01M5H5P5E98XTANP62H5TVTSC4
/// The `config=content-voice-rules` voice file (glossary `log in` -> `sign in`, banned `seamless`).
const VOICE_RULES: &str = "content-voice-rules";

// frob:tests crates/crunk-rules/src/rules/content005.rs::Content005
// frob:tests crates/crunk-rules/src/content_files.rs::glossary_hits
// frob:tests crates/crunk-rules/src/content_files.rs::uses_term
#[test]
fn content005_names_the_avoided_variant_and_the_preferred_term() {
    let toml = "[[key]]\nid = \"a\"\ntext = \"Log in now\"\n[[key]]\nid = \"b\"\ntext = \"Catalog in stock\"\n[[key]]\nid = \"c\"\ntext = \"Sign in\"\n";
    let host = support::project("design/content/en.toml", toml, Some(VOICE_RULES));
    let m: Vec<String> = support::run::<Content005>(&host)
        .into_iter()
        .map(|f| f.message)
        .collect();
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("'a'") && m[0].contains("'log in'"), "{m:?}");
    assert!(m[0].contains("prefers 'sign in'"), "{m:?}");

    let host = support::project("design/content/en.toml", toml, None);
    assert!(support::run::<Content005>(&host).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/content006.rs::Content006
// frob:tests crates/crunk-rules/src/content_files.rs::banned_hits
#[test]
fn content006_fires_on_a_banned_word_as_a_whole_word_only() {
    let toml = "[[key]]\nid = \"a\"\ntext = \"A Seamless day\"\n[[key]]\nid = \"b\"\ntext = \"Seamlessly done\"\n";
    let host = support::project("design/content/en.toml", toml, Some(VOICE_RULES));
    let m: Vec<String> = support::run::<Content006>(&host)
        .into_iter()
        .map(|f| f.message)
        .collect();
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("'a'") && m[0].contains("bans"), "{m:?}");

    let host = support::project("design/content/en.toml", toml, None);
    assert!(support::run::<Content006>(&host).is_empty());
}
