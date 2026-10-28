//! CRAFT013 beyond its rule page: the acceptance cases (scene copy keys with and without
//! `design/content/voice.toml`), and the edges around them: no scenes, scenes with no copy key,
//! attribute keys, an empty or comment-only voice file, a malformed one, and a directory in the
//! file's place.

// frob:ticket 01M5HM3W7MK7255AGEN27SXEXP

mod support;

use crunk_rules::content_files::{ContentFacts, VoiceFile};
use crunk_rules::host::missing_scene_doc_inputs;
use crunk_rules::rules::craft013::Craft013;
use gob_rules::{Finding, RepoRule, Severity};

const SCENE: &str = "design/scenes/home.scene.html";
const KEYED: &str = "<h1 data-id=\"hero\" data-copy=\"home.hero\">Welcome back</h1>\n";

fn run(text: &str) -> (support::Project, Vec<Finding>) {
    let host = support::project(SCENE, text, None);
    let found = support::run::<Craft013>(&host);
    (host, found)
}

/// Write `design/content/voice.toml` with `text` and reload the content facts from disk.
fn with_voice(host: &mut support::Project, text: &str) {
    let dir = host.spec.root.join("design/content");
    std::fs::create_dir_all(&dir).expect("mkdir");
    std::fs::write(dir.join("voice.toml"), text).expect("write voice");
    host.content = Some(ContentFacts::load(&host.spec));
}

// frob:tests crates/crunk-rules/src/rules/craft013.rs::Craft013
#[test]
fn copy_keys_without_a_voice_file_report_it_and_name_slop060() {
    let (_host, found) = run(KEYED);
    assert_eq!(found.len(), 1, "{found:?}");
    let finding = &found[0];
    assert!(finding.message.contains("SLOP060"), "{}", finding.message);
    assert!(
        finding.message.contains("design/content/voice.toml"),
        "{}",
        finding.message
    );
    assert!(finding.message.contains("home.hero"), "{}", finding.message);
    assert_eq!(finding.severity, Severity::Error);
}

// frob:tests crates/crunk-rules/src/rules/craft013.rs::Craft013
// frob:tests crates/crunk-rules/src/content_files.rs::VoiceFile
#[test]
fn a_voice_file_with_content_reports_nothing() {
    let (mut host, _) = run(KEYED);
    with_voice(&mut host, "voice = \"plain and warm\"\n");
    assert_eq!(
        host.content.as_ref().expect("content").voice,
        VoiceFile::Present
    );
    assert!(support::run::<Craft013>(&host).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/craft013.rs::Craft013
#[test]
fn an_attribute_copy_key_counts_as_using_copy_keys() {
    let (_host, found) = run("<img data-id=\"logo\" data-copy-alt=\"home.logo\">\n");
    assert_eq!(found.len(), 1, "{found:?}");
}

// frob:tests crates/crunk-rules/src/rules/craft013.rs::Craft013
#[test]
fn scenes_without_copy_keys_need_no_voice_file() {
    let (_host, found) = run("<div data-id=\"hero\"></div>\n");
    assert!(found.is_empty(), "{found:?}");
    let (_host, literal) = run("<h1 data-id=\"hero\">Welcome back</h1>\n");
    assert!(literal.is_empty(), "{literal:?}");
    let (_host, empty_key) = run("<h1 data-copy=\"\">Welcome back</h1>\n");
    assert!(empty_key.is_empty(), "{empty_key:?}");
}

// frob:tests crates/crunk-rules/src/rules/craft013.rs::Craft013
#[test]
fn a_project_with_no_scenes_is_inapplicable_and_quiet() {
    let host = support::project("styles/app.css", ".a { color: #111111; }\n", None);
    assert!(support::run::<Craft013>(&host).is_empty());
    assert_eq!(
        RepoRule::<support::Project>::inapplicable(&Craft013, &host),
        missing_scene_doc_inputs(&host)
    );
    assert!(missing_scene_doc_inputs(&host).is_some());
}

// frob:tests crates/crunk-rules/src/rules/craft013.rs::Craft013
#[test]
fn a_project_with_scenes_and_content_facts_is_applicable() {
    let (host, _) = run(KEYED);
    assert_eq!(
        RepoRule::<support::Project>::inapplicable(&Craft013, &host),
        None
    );
}

// frob:tests crates/crunk-rules/src/rules/craft013.rs::Craft013
#[test]
fn an_empty_or_comment_only_voice_file_is_a_placeholder_and_fires_at_the_file() {
    for text in ["", "  \n\n", "# voice goes here\n# tone\n"] {
        let (mut host, _) = run(KEYED);
        with_voice(&mut host, text);
        assert_eq!(
            host.content.as_ref().expect("content").voice,
            VoiceFile::Blank
        );
        let found = support::run::<Craft013>(&host);
        assert_eq!(found.len(), 1, "{text:?}: {found:?}");
        assert!(found[0].message.contains("SLOP060"), "{}", found[0].message);
        assert!(
            found[0].message.contains("has no content"),
            "{}",
            found[0].message
        );
        assert!(found[0].span.is_some(), "located at the voice file");
    }
}

// frob:tests crates/crunk-rules/src/rules/craft013.rs::Craft013
#[test]
fn a_malformed_voice_file_still_counts_as_present() {
    let (mut host, _) = run(KEYED);
    with_voice(&mut host, "this is = = not toml [[\n");
    assert!(support::run::<Craft013>(&host).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/craft013.rs::Craft013
#[test]
fn a_directory_named_voice_toml_is_not_a_voice_file() {
    let (mut host, _) = run(KEYED);
    let dir = host.spec.root.join("design/content/voice.toml");
    std::fs::create_dir_all(&dir).expect("mkdir");
    host.content = Some(ContentFacts::load(&host.spec));
    assert_eq!(
        host.content.as_ref().expect("content").voice,
        VoiceFile::Missing
    );
    assert_eq!(support::run::<Craft013>(&host).len(), 1);
}

// frob:tests crates/crunk-rules/src/content_files.rs::ContentFacts
#[test]
fn the_voice_file_is_not_loaded_as_a_copy_file_and_changes_the_fingerprint() {
    let (mut host, _) = run(KEYED);
    let before = host.content.as_ref().expect("content").fingerprint();
    with_voice(&mut host, "voice = \"plain\"\n");
    let content = host.content.as_ref().expect("content");
    assert!(content.files.is_empty(), "voice.toml is not a copy file");
    assert_ne!(content.fingerprint(), before);
}
