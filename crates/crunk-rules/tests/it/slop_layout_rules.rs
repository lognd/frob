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
    assert!(ok.scene_docs.as_ref().unwrap().files[0].solve().is_ok());
    let bad = support::project(FILE, "<div style=\"width:10px\"></div>\n", None);
    assert!(bad.scene_docs.as_ref().unwrap().files[0].solve().is_err());
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

// frob:ticket 01M7AV3827P32YDAGDXDVS8CWV
const TOKEN_SCENE: &str = "<div data-id=\"outer\" style=\"width:10px;height:50px\"><div data-id=\"inner\" style=\"width:var(--space-16);height:10px\"></div></div>\n";
// frob:ticket 01M7AV3827P32YDAGDXDVS8CWV
const UNDEFINED_TOKEN_SCENE: &str = "<div data-id=\"outer\" style=\"width:10px;height:50px\"><div data-id=\"inner\" style=\"width:var(--no-such-token);height:10px\"></div></div>\n";

// frob:ticket 01M7AV3827P32YDAGDXDVS8CWV
/// Assert `R` reports only Unresolved findings (at least one) on `text`.
fn assert_unresolved<R: gob_rules::RepoRule<support::Project> + Default>(text: &str) {
    let host = support::project(FILE, text, Some("breakpoints"));
    let found = support::run::<R>(&host);
    assert!(
        !found.is_empty(),
        "{}: silent pass",
        std::any::type_name::<R>()
    );
    assert!(
        found
            .iter()
            .all(|f| f.severity == gob_rules::Severity::Unresolved),
        "{found:?}"
    );
}

// frob:tests crates/crunk-rules/src/rules/layout001.rs::Layout001
// frob:tests crates/crunk-rules/src/rules/layout002.rs::Layout002
// frob:tests crates/crunk-rules/src/rules/resp001.rs::Resp001
// frob:tests crates/crunk-rules/src/rules/slop020.rs::Slop020
// frob:tests crates/crunk-rules/src/rules/slop021.rs::Slop021
// frob:tests crates/crunk-rules/src/rules/slop026.rs::Slop026
// frob:tests crates/crunk-rules/src/rules/slop027.rs::Slop027
// frob:tests crates/crunk-rules/src/rules/slop028.rs::Slop028
// frob:tests crates/crunk-rules/src/rules/slop029.rs::Slop029
#[test]
fn an_unsolvable_token_scene_is_unresolved_never_a_silent_pass() {
    use crunk_rules::rules::{
        layout001::Layout001, layout002::Layout002, resp001::Resp001, slop020::Slop020,
        slop021::Slop021, slop026::Slop026, slop027::Slop027, slop028::Slop028, slop029::Slop029,
    };
    let t = UNDEFINED_TOKEN_SCENE;
    assert_unresolved::<Layout001>(t);
    assert_unresolved::<Layout002>(t);
    assert_unresolved::<Resp001>(t);
    assert_unresolved::<Slop020>(t);
    assert_unresolved::<Slop021>(t);
    assert_unresolved::<Slop026>(t);
    assert_unresolved::<Slop027>(t);
    assert_unresolved::<Slop028>(t);
    assert_unresolved::<Slop029>(t);
}

// frob:tests crates/crunk-rules/src/scene_docs.rs::SceneDocFacts.load
#[test]
fn spec_tokens_resolve_in_scene_styles_so_layout001_sees_the_overflow() {
    let host = support::project(FILE, TOKEN_SCENE, None);
    let file = &host.scene_docs.as_ref().unwrap().files[0];
    assert!(file.solve().is_ok(), "{:?}", file.solve().err());
    let found = support::run::<crunk_rules::rules::layout001::Layout001>(&host);
    assert!(
        found
            .iter()
            .any(|f| f.severity == gob_rules::Severity::Error),
        "{found:?}"
    );
}
