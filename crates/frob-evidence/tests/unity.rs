//! The `unity` evidence provider's editor discovery and license refusal, against the `fake-dotnet` stand-in as the editor.

use std::path::Path;
use std::time::Duration;

use frob_evidence::EvidenceError;
use frob_evidence::provider::{
    UnityRun, parse_unity_version, prepare_unity, resolve_unity_editor, unity_hub_candidates,
};
use gob_exec::{Limits, Runner};

/// A Unity project directory whose `ProjectVersion.txt` names `version`.
fn project(version: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let settings = dir.path().join("ProjectSettings");
    std::fs::create_dir_all(&settings).expect("settings");
    std::fs::write(
        settings.join("ProjectVersion.txt"),
        format!("m_EditorVersion: {version}\nm_EditorVersionWithRevision: {version} (abc)\n"),
    )
    .expect("version file");
    dir
}

fn run<'a>(editor: &'a str, dir: &'a Path, home: &'a Path) -> UnityRun<'a> {
    UnityRun {
        editor,
        project: dir,
        home: Some(home),
        timeout: Duration::from_secs(30),
    }
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
#[test]
fn a_missing_editor_refuses_naming_the_version_and_the_config_key() {
    // frob:tests crates/frob-evidence/src/provider.rs::resolve_unity_editor
    let dir = project("6000.0.43f1");
    let home = tempfile::tempdir().expect("home");
    let err = resolve_unity_editor(&run("", dir.path(), home.path())).expect_err("no editor");
    let msg = err.to_string();
    assert!(msg.contains("6000.0.43f1"), "{msg}");
    assert!(
        msg.contains("Unity/Hub/Editor/6000.0.43f1/Editor/Unity"),
        "{msg}"
    );
    let cli = format!("{:?}", err.into_cli());
    assert!(cli.contains("[evidence.unity] editor"), "{cli}");
    assert!(cli.contains("6000.0.43f1"), "{cli}");
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
#[test]
fn a_configured_editor_is_used_regardless_of_the_version_file() {
    // frob:tests crates/frob-evidence/src/provider.rs::prepare_unity
    let dir = project("6000.0.43f1");
    let home = tempfile::tempdir().expect("home");
    let fake = gob_testsupport::fake_dotnet();
    let runner = Runner::new(Limits::default());
    let editor = prepare_unity(
        &runner,
        &run(fake.to_str().expect("utf8"), dir.path(), home.path()),
    )
    .expect("configured editor");
    assert_eq!(editor, fake);
    let (resolved, version) =
        resolve_unity_editor(&run(fake.to_str().expect("utf8"), dir.path(), home.path()))
            .expect("resolved");
    assert_eq!((resolved, version.as_str()), (fake, "6000.0.43f1"));
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
#[test]
fn a_configured_path_that_is_not_a_file_refuses() {
    // frob:tests crates/frob-evidence/src/provider.rs::resolve_unity_editor
    let dir = project("6000.0.43f1");
    let home = tempfile::tempdir().expect("home");
    let err = resolve_unity_editor(&run("/no/such/Unity", dir.path(), home.path()))
        .expect_err("not a file");
    assert!(matches!(err, EvidenceError::UnityEditorMissing { .. }));
    assert!(err.to_string().contains("/no/such/Unity"));
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
#[test]
fn an_editor_without_a_valid_license_refuses_with_a_remedy() {
    // frob:tests crates/frob-evidence/src/provider.rs::prepare_unity
    let dir = project("6000.0.43f1");
    std::fs::write(dir.path().join("fake-dotnet.exit"), "1").expect("exit");
    let home = tempfile::tempdir().expect("home");
    let fake = gob_testsupport::fake_dotnet();
    let runner = Runner::new(Limits::default());
    let err = prepare_unity(
        &runner,
        &run(fake.to_str().expect("utf8"), dir.path(), home.path()),
    )
    .expect_err("no license");
    assert!(matches!(err, EvidenceError::UnityLicense { .. }), "{err}");
    let msg = err.to_string();
    assert!(
        msg.contains("license") && msg.contains("6000.0.43f1"),
        "{msg}"
    );
    let cli = format!("{:?}", err.into_cli());
    assert!(cli.contains("E-EVIDENCE-UNITY-LICENSE"), "{cli}");
    assert!(cli.contains("activate or renew"), "{cli}");
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
#[test]
fn an_editor_found_under_the_hub_location_is_resolved() {
    // frob:tests crates/frob-evidence/src/provider.rs::unity_hub_candidates
    let dir = project("2022.3.1f1");
    let home = tempfile::tempdir().expect("home");
    let hub = home.path().join("Unity/Hub/Editor/2022.3.1f1/Editor");
    std::fs::create_dir_all(&hub).expect("hub");
    std::fs::write(hub.join("Unity"), "").expect("editor");
    assert!(
        unity_hub_candidates("2022.3.1f1", Some(home.path()))
            .iter()
            .any(|p| p == &hub.join("Unity"))
    );
    let (found, version) =
        resolve_unity_editor(&run("", dir.path(), home.path())).expect("hub editor");
    assert_eq!((found, version.as_str()), (hub.join("Unity"), "2022.3.1f1"));
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
#[test]
fn the_version_is_read_from_the_editor_version_line() {
    // frob:tests crates/frob-evidence/src/provider.rs::parse_unity_version
    assert_eq!(
        parse_unity_version("m_EditorVersion: 6000.0.43f1\nm_EditorVersionWithRevision: x\n")
            .as_deref(),
        Some("6000.0.43f1")
    );
    assert_eq!(parse_unity_version("nothing here"), None);
}
