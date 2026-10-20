//! The `unity` evidence provider: editor discovery and license refusal, against the `fake-unity` stand-in editor.

use gob_path::Shown;
use std::path::{Path, PathBuf};
use std::time::Duration;

use frob_evidence::EvidenceError;
use frob_evidence::provider::{
    UNITY_VERSION_FILE, UnityHost, UnityLookup, UnityMode, UnityRun, UnityTestRun,
    find_unity_editor, parse_nunit, parse_unity_version, run_unity, unity_license_refusal,
};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};

/// A Unity project directory whose version file names `version`.
fn project(version: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let file = dir.path().join(UNITY_VERSION_FILE);
    std::fs::create_dir_all(file.parent().expect("parent")).expect("mkdir");
    std::fs::write(
        file,
        format!(
            "m_EditorVersion: {version}\nm_EditorVersionWithRevision: {version} (97272b72f107)\n"
        ),
    )
    .expect("version file");
    dir
}

/// Install a fake editor file for `version` under a Hub root laid out for `host`; returns its path.
fn install(root: &Path, host: UnityHost, version: &str) -> PathBuf {
    let path = host.editor_in(root, version);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(&path, "fake").expect("editor");
    path
}

fn look<'a>(
    project: &'a Path,
    configured: &'a str,
    roots: &'a [PathBuf],
    host: UnityHost,
) -> UnityLookup<'a> {
    UnityLookup {
        project,
        configured,
        base: project,
        hub_roots: roots,
        host,
    }
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
// frob:tests crates/frob-evidence/src/provider.rs::parse_unity_version
#[test]
fn version_is_read_from_project_version_txt() {
    let text =
        "m_EditorVersion: 6000.0.43f1\nm_EditorVersionWithRevision: 6000.0.43f1 (97272b72f107)\n";
    assert_eq!(parse_unity_version(text).as_deref(), Some("6000.0.43f1"));
    assert_eq!(parse_unity_version("m_Other: 1\n"), None);
    assert_eq!(parse_unity_version("m_EditorVersion:\n"), None);
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
// frob:tests crates/frob-evidence/src/provider.rs::UnityHost
#[test]
fn hub_locations_follow_each_operating_system() {
    let home = Path::new("/home/u");
    assert_eq!(
        UnityHost::Linux.hub_roots(Some(home)),
        vec![PathBuf::from("/home/u/Unity/Hub/Editor")]
    );
    assert!(UnityHost::Linux.hub_roots(None).is_empty());
    assert_eq!(
        UnityHost::Windows.editor_in(&UnityHost::Windows.hub_roots(None)[0], "6000.0.43f1"),
        PathBuf::from("C:/Program Files/Unity/Hub/Editor/6000.0.43f1/Editor/Unity.exe")
    );
    assert_eq!(
        UnityHost::MacOs.editor_in(&UnityHost::MacOs.hub_roots(None)[0], "6000.0.43f1"),
        PathBuf::from("/Applications/Unity/Hub/Editor/6000.0.43f1/Unity.app/Contents/MacOS/Unity")
    );
    assert_eq!(
        UnityHost::Linux.editor_in(Path::new("/h/Editor"), "6000.0.43f1"),
        PathBuf::from("/h/Editor/6000.0.43f1/Editor/Unity")
    );
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
// frob:tests crates/frob-evidence/src/provider.rs::find_unity_editor
#[test]
fn a_missing_editor_refuses_naming_the_version_and_the_config_key() {
    let proj = project("6000.0.43f1");
    let hub = tempfile::tempdir().expect("hub");
    install(hub.path(), UnityHost::Linux, "2022.3.1f1");
    let roots = [hub.path().to_path_buf()];
    let err = find_unity_editor(&look(proj.path(), "", &roots, UnityHost::Linux)).unwrap_err();
    let text = err.to_string();
    assert!(text.contains("6000.0.43f1"), "{text}");
    assert!(!text.contains("2022.3.1f1 "), "{text}");
    assert!(text.contains("[evidence.unity] editor"), "{text}");
    assert!(text.contains("nothing was recorded"), "{text}");
    let refusal = format!("{:?}", err.into_cli());
    assert!(refusal.contains("E-EVIDENCE-UNITY-EDITOR"), "{refusal}");
    assert!(refusal.contains("Unity Hub"), "{refusal}");
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
// frob:tests crates/frob-evidence/src/provider.rs::find_unity_editor
#[test]
fn only_the_exact_required_version_is_ever_used() {
    let proj = project("6000.0.43f1");
    let hub = tempfile::tempdir().expect("hub");
    install(hub.path(), UnityHost::Linux, "6000.0.43f2");
    let roots = [hub.path().to_path_buf()];
    assert!(find_unity_editor(&look(proj.path(), "", &roots, UnityHost::Linux)).is_err());
    let want = install(hub.path(), UnityHost::Linux, "6000.0.43f1");
    let got = find_unity_editor(&look(proj.path(), "", &roots, UnityHost::Linux)).expect("found");
    assert_eq!(got.path, want);
    assert_eq!(got.version.as_deref(), Some("6000.0.43f1"));
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
// frob:tests crates/frob-evidence/src/provider.rs::find_unity_editor
#[test]
fn no_version_file_and_no_config_refuses_without_guessing() {
    let proj = tempfile::tempdir().expect("proj");
    let hub = tempfile::tempdir().expect("hub");
    install(hub.path(), UnityHost::Linux, "6000.0.43f1");
    let roots = [hub.path().to_path_buf()];
    let err = find_unity_editor(&look(proj.path(), "", &roots, UnityHost::Linux)).unwrap_err();
    assert!(err.to_string().contains("ProjectVersion.txt"), "{err}");
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
// frob:tests crates/frob-evidence/src/provider.rs::find_unity_editor
#[test]
fn a_configured_editor_wins_whatever_the_version_file_says() {
    let proj = project("6000.0.43f1");
    let other = tempfile::tempdir().expect("other");
    let mine = other.path().join("MyUnity");
    std::fs::write(&mine, "fake").expect("editor");
    let got = find_unity_editor(&look(
        proj.path(),
        Shown::with_home(&mine, None).as_str(),
        &[],
        UnityHost::Linux,
    ))
    .expect("configured");
    assert_eq!(got.path, mine);
    // A relative path starts at the base directory.
    std::fs::write(proj.path().join("editor.bin"), "fake").expect("rel");
    let got = find_unity_editor(&look(proj.path(), "editor.bin", &[], UnityHost::Linux))
        .expect("relative");
    assert_eq!(got.path, proj.path().join("editor.bin"));
    // A configured path that is not a file is a refusal, never a fall back to the Hub.
    let hub = tempfile::tempdir().expect("hub");
    install(hub.path(), UnityHost::Linux, "6000.0.43f1");
    let roots = [hub.path().to_path_buf()];
    let err = find_unity_editor(&look(proj.path(), "nope", &roots, UnityHost::Linux)).unwrap_err();
    assert!(matches!(err, EvidenceError::UnityEditor { .. }), "{err}");
}

/// Run the fake editor on `proj` and return its stdout.
fn run_fake(proj: &Path) -> String {
    let spec = Spec {
        program: Program::Hook {
            path: gob_testsupport::fake_unity(),
        },
        args: vec![
            "-batchmode".into(),
            "-projectPath".into(),
            Shown::with_home(proj, None).to_string(),
        ],
        cwd: Some(proj.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(60),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 })
        .run(&spec)
        .expect("fake unity");
    assert!(matches!(out.status, Outcome::Exited(_)));
    out.stdout
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
// frob:tests crates/frob-evidence/src/provider.rs::unity_license_refusal
#[test]
fn an_editor_without_a_valid_license_refuses_with_a_remedy() {
    let proj = project("6000.0.43f1");
    std::fs::write(
        proj.path().join("fake-unity.log"),
        "Built from 'x'\nNo valid Unity Editor license found. Please activate your license.\n",
    )
    .expect("log");
    let log = run_fake(proj.path());
    let err = unity_license_refusal(Some("6000.0.43f1"), &log).expect("refusal");
    let text = err.to_string();
    assert!(text.contains("6000.0.43f1"), "{text}");
    assert!(text.contains("No valid Unity Editor license"), "{text}");
    assert!(text.contains("nothing was recorded"), "{text}");
    let refusal = format!("{:?}", err.into_cli());
    assert!(refusal.contains("E-EVIDENCE-UNITY-LICENSE"), "{refusal}");
    assert!(refusal.contains("activate a license"), "{refusal}");
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
// frob:tests crates/frob-evidence/src/provider.rs::unity_license_refusal
#[test]
fn a_licensed_editor_log_is_not_a_license_refusal() {
    let proj = project("6000.0.43f1");
    std::fs::write(proj.path().join("fake-unity.log"), "Licensing: ok\n").expect("log");
    assert!(unity_license_refusal(None, &run_fake(proj.path())).is_none());
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
// frob:tests crates/frob-evidence/src/provider.rs::UnityHost.current
#[test]
fn the_current_host_matches_the_build_target() {
    let expected = if cfg!(windows) {
        UnityHost::Windows
    } else if cfg!(target_os = "macos") {
        UnityHost::MacOs
    } else {
        UnityHost::Linux
    };
    assert_eq!(UnityHost::current(), expected);
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
        run: UnityRun {
            editor,
            project: dir,
            base: dir,
            home: Some(home),
        },
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
    let fake = gob_testsupport::fake_unity();
    let cap = run_unity(
        &Runner::new(Limits::default()),
        &unity_run(
            dir.path(),
            home.path(),
            Shown::with_home(&fake, None).as_str(),
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
    let fake = gob_testsupport::fake_unity();
    let cap = run_unity(
        &Runner::new(Limits::default()),
        &unity_run(
            dir.path(),
            home.path(),
            Shown::with_home(&fake, None).as_str(),
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
    let fake = gob_testsupport::fake_unity();
    let err = run_unity(
        &Runner::new(Limits::default()),
        &unity_run(
            dir.path(),
            home.path(),
            Shown::with_home(&fake, None).as_str(),
            UnityMode::EditMode,
        ),
        Duration::from_secs(30),
    )
    .expect_err("open");
    assert!(matches!(err, EvidenceError::UnityProjectOpen { .. }));
    let cli = format!("{:?}", err.into_cli());
    assert!(cli.contains("close the Unity editor"), "{cli}");
}
