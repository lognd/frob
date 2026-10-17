//! The `unity` evidence provider's editor discovery and license refusal, against the `fake-dotnet` stand-in as the editor.

use std::path::Path;
use std::time::Duration;

use frob_evidence::EvidenceError;
use frob_evidence::provider::{
    UnityMode, UnityRun, UnityTestRun, parse_nunit, parse_unity_version, prepare_unity,
    resolve_unity_editor, run_unity, unity_hub_candidates,
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

const NUNIT: &str = r#"<test-run result="Failed" total="3">
<test-suite type="Assembly"><test-case id="1" name="Adds" fullname="Game.Tests.MathTests.Adds" methodname="Adds" classname="Game.Tests.MathTests" result="Passed" duration="0.01" />
<test-case id="2" name="Subtracts" fullname="Game.Tests.MathTests.Subtracts" methodname="Subtracts" classname="Game.Tests.MathTests" result="Failed" duration="0.02"><failure><message><![CDATA[Expected 1 but was 2]]></message></failure><output><![CDATA[subtract ran]]></output></test-case>
<test-case id="3" name="Ignored" fullname="Game.Tests.MathTests.Ignored" methodname="Ignored" classname="Game.Tests.MathTests" result="Skipped" duration="0" />
</test-suite></test-run>"#;

fn unity_run<'a>(
    dir: &'a Path,
    home: &'a Path,
    editor: &'a str,
    mode: UnityMode,
) -> UnityTestRun<'a> {
    UnityTestRun {
        run: run(editor, dir, home),
        mode,
        assemblies: &[],
        ids: &[],
    }
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
#[test]
fn nunit_xml_with_a_pass_and_a_fail_yields_both_per_test_results() {
    // frob:tests crates/frob-evidence/src/provider.rs::parse_nunit
    let trx = parse_nunit(NUNIT);
    assert_eq!(
        trx.parsed.tests,
        vec![
            "Game.Tests.MathTests.Adds",
            "Game.Tests.MathTests.Subtracts"
        ]
    );
    assert_eq!(trx.parsed.failed, vec!["Game.Tests.MathTests.Subtracts"]);
    assert!(
        trx.summary.contains("Expected 1 but was 2"),
        "{}",
        trx.summary
    );
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
#[test]
fn a_batch_run_stores_the_measured_per_test_results() {
    // frob:tests crates/frob-evidence/src/provider.rs::run_unity
    let dir = project("6000.0.43f1");
    std::fs::write(dir.path().join("fake-unity.xml"), NUNIT).expect("xml");
    std::fs::write(dir.path().join("fake-unity.exit"), "2").expect("exit");
    let home = tempfile::tempdir().expect("home");
    let fake = gob_testsupport::fake_dotnet();
    let cap = run_unity(
        &Runner::new(Limits::default()),
        &unity_run(
            dir.path(),
            home.path(),
            fake.to_str().expect("utf8"),
            UnityMode::PlayMode,
        ),
        Duration::from_secs(30),
    )
    .expect("run");
    assert!(!cap.passed);
    assert_eq!(cap.exit_code, Some(2));
    assert_eq!(cap.tests.len(), 2);
    assert_eq!(cap.failed_tests, vec!["Game.Tests.MathTests.Subtracts"]);
    assert!(
        cap.transcript.contains("-testPlatform PlayMode"),
        "{}",
        cap.transcript
    );
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
#[test]
fn edit_mode_is_passed_through_and_a_clean_run_passes() {
    // frob:tests crates/frob-evidence/src/provider.rs::run_unity
    let dir = project("6000.0.43f1");
    let ok = NUNIT.replace("result=\"Failed\" duration", "result=\"Passed\" duration");
    std::fs::write(dir.path().join("fake-unity.xml"), ok).expect("xml");
    let home = tempfile::tempdir().expect("home");
    let fake = gob_testsupport::fake_dotnet();
    let cap = run_unity(
        &Runner::new(Limits::default()),
        &unity_run(
            dir.path(),
            home.path(),
            fake.to_str().expect("utf8"),
            UnityMode::EditMode,
        ),
        Duration::from_secs(30),
    )
    .expect("run");
    assert!(cap.passed, "{:?}", cap.failed_tests);
    assert!(
        cap.transcript.contains("-testPlatform EditMode"),
        "{}",
        cap.transcript
    );
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
#[test]
fn a_project_open_in_another_editor_refuses_with_a_remedy() {
    // frob:tests crates/frob-evidence/src/provider.rs::check_unity_unlocked
    let dir = project("6000.0.43f1");
    std::fs::create_dir_all(dir.path().join("Temp")).expect("temp");
    std::fs::write(dir.path().join("Temp/UnityLockfile"), "").expect("lock");
    let home = tempfile::tempdir().expect("home");
    let fake = gob_testsupport::fake_dotnet();
    let err = run_unity(
        &Runner::new(Limits::default()),
        &unity_run(
            dir.path(),
            home.path(),
            fake.to_str().expect("utf8"),
            UnityMode::EditMode,
        ),
        Duration::from_secs(30),
    )
    .expect_err("open");
    assert!(matches!(err, EvidenceError::UnityProjectOpen { .. }));
    let cli = format!("{:?}", err.into_cli());
    assert!(cli.contains("close the Unity editor"), "{cli}");
}
