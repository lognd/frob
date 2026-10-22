//! GX002-GX005 over scene documents: the focus-graph rules, including the acceptance case.

// frob:ticket 01M4CXRSYQQW9C6D7K2Q2ZC9QM

mod support;

use crunk_rules::rules::{gx002::Gx002, gx003::Gx003, gx004::Gx004, gx005::Gx005};
use gob_rules::Finding;

const FILE: &str = "design/scenes/menu.scene.html";

fn msgs<R>(text: &str) -> Vec<String>
where
    R: gob_rules::RepoRule<support::Project> + Default,
{
    let host = support::project(FILE, text, None);
    let findings: Vec<Finding> = support::run::<R>(&host);
    findings.into_iter().map(|f| f.message).collect()
}

// frob:tests crates/crunk-rules/src/rules/gx002.rs::Gx002
#[test]
fn gx002_fires_naming_an_unreachable_button() {
    let text = "<button data-id=\"play\" data-focus-default data-nav-down=\"none\"></button>\n<button data-id=\"options\"></button>\n";
    let m = msgs::<Gx002>(text);
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("options"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/gx003.rs::Gx003
#[test]
fn gx003_fires_naming_a_trap() {
    let text = "<button data-id=\"play\" data-focus-default></button>\n<button data-id=\"options\" data-nav-up=\"none\"></button>\n";
    let m = msgs::<Gx003>(text);
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("options"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/gx004.rs::Gx004
#[test]
fn gx004_fires_without_a_default_and_is_quiet_with_one() {
    let none = "<button data-id=\"a\"></button>\n<button data-id=\"b\"></button>\n";
    assert_eq!(msgs::<Gx004>(none).len(), 1);
    let one =
        "<button data-id=\"a\" data-focus-default></button>\n<button data-id=\"b\"></button>\n";
    assert!(msgs::<Gx004>(one).is_empty());
    let two = "<button data-id=\"a\" data-focus-default></button>\n<button data-id=\"b\" data-focus-default></button>\n";
    assert_eq!(msgs::<Gx004>(two).len(), 1);
}

// frob:tests crates/crunk-rules/src/rules/gx005.rs::Gx005
#[test]
fn gx005_fires_for_a_dangling_move() {
    let text = "<button data-id=\"a\" data-focus-default data-nav-down=\"ghost\"></button>\n<button data-id=\"b\"></button>\n";
    let m = msgs::<Gx005>(text);
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("ghost"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/scene_docs.rs::SceneDocFile.focus_graph
#[test]
fn focus_graph_lists_the_focusable_controls_of_a_scene() {
    let text =
        "<button data-id=\"a\" data-focus-default></button>\n<button data-id=\"b\"></button>\n";
    let host = support::project(FILE, text, None);
    let facts = crunk_rules::CrunkHost::scene_docs(&host).expect("scene docs");
    assert_eq!(facts.files[0].focus_graph().nodes.len(), 2);
}
