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

fn run_messages<R>(text: &str) -> Vec<String>
where
    R: gob_rules::RepoRule<support::Project> + Default,
{
    let host = support::project(FILE, text, None);
    support::run::<R>(&host)
        .into_iter()
        .map(|f| f.message)
        .collect()
}

// frob:ticket 01M5H30AQNZSC77EY70P28KM3V
// frob:tests crates/crunk-rules/src/rules/scene002.rs::Scene002
#[test]
fn scene002_fires_on_missing_blank_and_duplicate_data_ids() {
    use crunk_rules::rules::scene002::Scene002;
    let m = run_messages::<Scene002>(
        "<div data-id=\"a\"><p></p><span data-id=\" \"></span></div>\n<div data-id=\"a\"></div>\n",
    );
    assert_eq!(m.len(), 3, "{m:?}");
    assert!(m[0].contains("<p>") && m[0].contains("no data-id"), "{m:?}");
    assert!(
        m[1].contains("<span>") && m[1].contains("no data-id"),
        "{m:?}"
    );
    assert!(
        m[2].contains("'a'") && m[2].contains("line 1") && m[2].contains("line 2"),
        "{m:?}"
    );
}

// frob:ticket 01M5H30AQNZSC77EY70P28KM3V
// frob:tests crates/crunk-rules/src/rules/scene002.rs::Scene002
#[test]
fn scene002_is_clean_for_unique_ids_scaffolding_and_svg_children() {
    use crunk_rules::rules::scene002::Scene002;
    let text = "<html><head><style>.a{display:flex}</style></head><body>\n<div data-id=\"a\"><svg data-id=\"icon\"><path d=\"M0 0\"></path></svg><Button data-id=\"b\"></Button></div>\n</body></html>\n";
    let m = run_messages::<Scene002>(text);
    assert!(m.is_empty(), "{m:?}");
}

// frob:ticket 01M5H30AQNZSC77EY70P28KM3V
// frob:tests crates/crunk-rules/src/rules/scene003.rs::Scene003
#[test]
fn scene003_fires_on_an_unknown_tag_and_names_it() {
    use crunk_rules::rules::scene003::Scene003;
    let m = run_messages::<Scene003>(
        "<div data-id=\"a\"><blink data-id=\"b\"></blink><my-widget></my-widget></div>\n",
    );
    assert_eq!(m.len(), 2, "{m:?}");
    assert!(
        m[0].contains("<blink>") && m[1].contains("<my-widget>"),
        "{m:?}"
    );
}

// frob:ticket 01M5H30AQNZSC77EY70P28KM3V
// frob:tests crates/crunk-rules/src/rules/scene003.rs::Scene003
#[test]
fn scene003_is_clean_for_known_tags_components_and_svg_content() {
    use crunk_rules::rules::scene003::Scene003;
    let text = "<DIV data-id=\"a\"><P data-id=\"p\"></P><svg data-id=\"s\"><circle r=\"1\"></circle></svg><Button data-id=\"b\"></Button></DIV>\n";
    let m = run_messages::<Scene003>(text);
    assert!(m.is_empty(), "{m:?}");
}

// frob:ticket 01M5H30AQNZSC77EY70P28KM3V
// frob:tests crates/crunk-rules/src/rules/scene004.rs::Scene004
#[test]
fn scene004_fires_on_at_rules_other_than_media_even_nested() {
    use crunk_rules::rules::scene004::Scene004;
    let text = "<style>@font-face { font-family: x }\n@media (min-width: 1px) { @supports (display: grid) { .a { display: grid } } }</style>\n<div data-id=\"a\"></div>\n";
    let m = run_messages::<Scene004>(text);
    assert_eq!(m.len(), 2, "{m:?}");
    assert!(
        m[0].contains("@font-face") && m[1].contains("@supports"),
        "{m:?}"
    );
}

// frob:ticket 01M5H30AQNZSC77EY70P28KM3V
// frob:tests crates/crunk-rules/src/rules/scene004.rs::Scene004
#[test]
fn scene004_is_clean_for_media_only() {
    use crunk_rules::rules::scene004::Scene004;
    let m = run_messages::<Scene004>(
        "<style>@media (min-width: 1px) { .a { display: flex } }</style>\n<div data-id=\"a\"></div>\n",
    );
    assert!(m.is_empty(), "{m:?}");
}

// frob:ticket 01M5H30AT7FM2BAXCTTDEGWV6J
// frob:tests crates/crunk-rules/src/rules/scene005.rs::Scene005
// frob:tests crates/crunk-rules/src/host.rs::scene_doc_load_subjects
#[test]
fn scene005_is_clean_for_a_loadable_scene() {
    use crunk_rules::rules::scene005::Scene005;
    let host = support::project(FILE, "<div data-id=\"a\"></div>\n", None);
    let findings: Vec<Finding> = support::run::<Scene005>(&host);
    assert!(findings.is_empty(), "{findings:?}");
    assert_eq!(crunk_rules::host::scene_doc_load_subjects(&host), 1);
}

// frob:tests crates/crunk-rules/src/rules/scene005.rs::Scene005
#[test]
fn scene005_is_quiet_with_no_scenes() {
    use crunk_rules::rules::scene005::Scene005;
    let host = support::project("design/other.txt", "x", None);
    let findings: Vec<Finding> = support::run::<Scene005>(&host);
    assert!(findings.is_empty());
}
