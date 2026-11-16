//! SPEC001 over the design files beyond the rule page: each file kind, the voice file, a broken
//! file keeping other files' findings, and the inapplicable path.

// frob:ticket 01M7ETK8WHHFV8590QXMH57TRZ
// frob:ticket 01M7HC8V861YF6HNVQXDAJGW83

use crate::support;

use crunk_rules::host::design_file_subjects;
use crunk_rules::rules::spec001::Spec001;
use gob_rules::{Measured, RepoRule};

fn messages(file: &str, text: &str) -> Vec<(bool, String)> {
    let host = support::project(file, text, None);
    support::run::<Spec001>(&host)
        .into_iter()
        .map(|f| (f.span.is_some(), f.message))
        .collect()
}

// frob:tests crates/crunk-rules/src/rules/spec001.rs::Spec001
#[test]
fn a_component_with_an_unknown_key_fires_and_names_the_file() {
    let m = messages(
        "design/components/readout.component.toml",
        "name = \"readout\"\nmotion = \"flicker\"\n",
    );
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].0, "located at the broken file");
    assert!(m[0].1.contains("component file invalid"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/spec001.rs::Spec001
#[test]
fn a_screen_file_that_is_not_toml_fires() {
    let m = messages("design/screens/home.screen.toml", "id = = =\n");
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].1.contains("screen file invalid"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/spec001.rs::Spec001
#[test]
fn a_content_file_that_is_not_toml_fires() {
    let m = messages("design/content/en.toml", "[[keys\n");
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].1.contains("content file invalid"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/spec001.rs::Spec001
#[test]
fn a_voice_file_whose_rules_do_not_parse_fires() {
    let m = messages("design/content/voice.toml", "banned = 3\n");
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].1.contains("voice file invalid"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/spec001.rs::Spec001
#[test]
fn valid_files_do_not_fire() {
    let m = messages(
        "design/components/readout.component.toml",
        "name = \"readout\"\n",
    );
    assert!(m.is_empty(), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/spec001.rs::Spec001
// frob:tests crates/crunk-rules/src/host.rs::inapplicable_without
#[test]
fn a_project_with_no_design_files_is_inapplicable_with_no_subjects() {
    let host = support::project("src/app.css", "a { color: red }\n", None);
    assert_eq!(design_file_subjects(&host), 0);
    assert_eq!(Measured::<support::Project>::subjects(&Spec001, &host), 0);
    assert!(RepoRule::<support::Project>::inapplicable(&Spec001, &host).is_some());
}

// frob:tests crates/crunk-rules/src/rules/spec001.rs::Spec001
#[test]
fn a_broken_file_counts_as_a_subject() {
    let host = support::project(
        "design/components/a.component.toml",
        "name = \"a\"\nmotion = 1\n",
        None,
    );
    assert_eq!(design_file_subjects(&host), 1);
    assert!(RepoRule::<support::Project>::inapplicable(&Spec001, &host).is_none());
}

// frob:tests crates/crunk-rules/src/rules/spec001.rs::Spec001
// frob:tests crates/crunk-rules/src/host.rs::design_file_problems
#[test]
fn a_flow_file_that_is_not_toml_fires() {
    let m = messages("design/flows/main.flow.toml", "id = = =\n");
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].1.contains("flow file invalid"), "{m:?}");
}
