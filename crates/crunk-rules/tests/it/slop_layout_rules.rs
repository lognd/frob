//! The SLOP T1 layout tells called directly: each fires on its rule page's fire fixture and is
//! silent on the clean one, and the file solve backs them.

// frob:ticket 01M4CXTCXCKKPRDHXEEZ2NK7PP

use crate::support;

use crunk_rules::slop_layout::{
    SceneView, Tell, card_nesting, centred_long_text, flat_rhythm, identical_cards, one_layout,
    uniform_density,
};

const FILE: &str = "design/scenes/page.scene.html";

/// The body of the first fenced block on a rule page that carries `expect`.
fn fixture(page: &str, expect: &str) -> String {
    let marker = format!("```html expect={expect} file={FILE}\n");
    let start = page.find(&marker).expect("fixture present") + marker.len();
    let end = page[start..].find("```").expect("fence closed");
    page[start..start + end].to_string()
}

fn tells(page: &str, expect: &str, tell: fn(&SceneView<'_>) -> Vec<Tell>) -> Vec<Tell> {
    let host = support::project(FILE, &fixture(page, expect), None);
    let facts = host.scene_docs.as_ref().expect("scene facts");
    tell(&SceneView::new(&facts.files[0]))
}

fn assert_fires_then_clean(page: &str, tell: fn(&SceneView<'_>) -> Vec<Tell>) {
    assert!(!tells(page, "fire", tell).is_empty(), "fire fixture fires");
    assert!(
        tells(page, "clean", tell).is_empty(),
        "clean fixture is silent"
    );
}

// frob:tests crates/crunk-rules/src/scene_docs.rs::SceneDocFile
#[test]
fn a_scene_with_data_ids_solves_and_one_without_does_not() {
    let ok = support::project(
        FILE,
        &fixture(include_str!("../../src/rules/slop020.md"), "fire"),
        None,
    );
    assert!(ok.scene_docs.as_ref().unwrap().files[0].solve().is_some());
    let bad = support::project(FILE, "<div style=\"width:10px\"></div>\n", None);
    assert!(bad.scene_docs.as_ref().unwrap().files[0].solve().is_none());
}

// frob:tests crates/crunk-rules/src/slop_layout.rs::identical_cards
#[test]
fn identical_cards_fire_on_the_trio_only() {
    assert_fires_then_clean(include_str!("../../src/rules/slop020.md"), identical_cards);
}

// frob:tests crates/crunk-rules/src/slop_layout.rs::card_nesting
#[test]
fn card_nesting_fires_on_deep_cards_only() {
    assert_fires_then_clean(include_str!("../../src/rules/slop021.md"), card_nesting);
}

// frob:tests crates/crunk-rules/src/slop_layout.rs::centred_long_text
#[test]
fn centred_long_text_fires_on_long_centred_text_only() {
    assert_fires_then_clean(
        include_str!("../../src/rules/slop026.md"),
        centred_long_text,
    );
}

// frob:tests crates/crunk-rules/src/slop_layout.rs::one_layout
#[test]
fn one_layout_fires_on_a_repeated_section_layout_only() {
    assert_fires_then_clean(include_str!("../../src/rules/slop027.md"), one_layout);
}

// frob:tests crates/crunk-rules/src/slop_layout.rs::flat_rhythm
#[test]
fn flat_rhythm_fires_on_uniform_spacing_only() {
    assert_fires_then_clean(include_str!("../../src/rules/slop028.md"), flat_rhythm);
}

// frob:tests crates/crunk-rules/src/slop_layout.rs::uniform_density
#[test]
fn uniform_density_fires_on_even_density_only() {
    assert_fires_then_clean(include_str!("../../src/rules/slop029.md"), uniform_density);
}
