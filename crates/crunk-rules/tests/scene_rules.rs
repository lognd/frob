//! SCENE001 over scene documents beyond the rule page: the acceptance case, custom properties,
//! several offenders, ordering and the inapplicable path.

// frob:ticket 01M5H30AMSB0THE4GW322D4K54

mod support;

use crunk_rules::host::{missing_scene_doc_inputs, scene_doc_subjects};
use crunk_rules::rules::scene001::Scene001;
use gob_rules::Finding;

const FILE: &str = "design/scenes/home.scene.html";

fn messages(text: &str) -> Vec<String> {
    let host = support::project(FILE, text, None);
    let findings: Vec<Finding> = support::run::<Scene001>(&host);
    findings.into_iter().map(|f| f.message).collect()
}

// frob:tests crates/crunk-rules/src/rules/scene001.rs::Scene001
#[test]
fn scene001_fires_naming_an_unsupported_property() {
    let m = messages("<div data-id=\"hero\" style=\"float: left\"></div>\n");
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("float"), "{m:?}");
    assert!(m[0].contains("hero"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/scene001.rs::Scene001
#[test]
fn scene001_is_quiet_with_no_scenes() {
    let host = support::project("design/other.txt", "x", None);
    let findings: Vec<Finding> = support::run::<Scene001>(&host);
    assert!(findings.is_empty());
}

// frob:tests crates/crunk-rules/src/rules/scene001.rs::Scene001
#[test]
fn scene001_allows_custom_properties() {
    let m = messages("<div data-id=\"a\" style=\"--x: 1; display: flex\"></div>\n");
    assert!(m.is_empty(), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/scene001.rs::Scene001
#[test]
fn scene001_reports_each_offender_with_its_element_and_line_in_order() {
    let text = "<div data-id=\"a\" style=\"float: left\"></div>\n<div data-id=\"b\" style=\"clip-path: none\"></div>\n";
    let m = messages(text);
    assert_eq!(m.len(), 2, "{m:?}");
    assert!(
        m[0].contains("float") && m[0].contains("'a'") && m[0].contains("line 1"),
        "{m:?}"
    );
    assert!(
        m[1].contains("clip-path") && m[1].contains("'b'") && m[1].contains("line 2"),
        "{m:?}"
    );
    assert_eq!(m, messages(text));
}

// frob:tests crates/crunk-rules/src/rules/scene001.rs::Scene001
// frob:tests crates/crunk-rules/src/host.rs::scene_doc_subjects
// frob:tests crates/crunk-rules/src/host.rs::missing_scene_doc_inputs
#[test]
fn scene001_is_inapplicable_without_scene_documents() {
    let one = support::project(FILE, "<div></div>\n", None);
    assert_eq!(scene_doc_subjects(&one), 1);
    let host = support::project("design/other.txt", "x", None);
    assert!(missing_scene_doc_inputs(&host).is_some());
}

// frob:tests crates/crunk-rules/src/scene_docs.rs::SceneDocFacts
// frob:tests crates/crunk-rules/src/scene_docs.rs::SceneDocFile
#[test]
fn scene_doc_facts_load_label_and_fingerprint_change_with_the_text() {
    let a = support::project(FILE, "<div data-id=\"a\"></div>\n", None);
    let b = support::project(FILE, "<div data-id=\"b\"></div>\n", None);
    let (fa, fb) = (
        a.scene_docs.as_ref().unwrap(),
        b.scene_docs.as_ref().unwrap(),
    );
    assert_eq!(fa.files.len(), 1);
    assert_eq!(fa.files[0].path, FILE);
    assert_eq!(fa.files[0].element_label(0), "data-id 'a'");
    assert_ne!(fa.fingerprint(), fb.fingerprint());
}
