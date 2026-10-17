//! C# test selection and runs: `.csproj` projects run through the dotnet provider, Unity assemblies run through the unity provider (~J5RTJ6, ~F17DMKH).

// frob:ticket 01M44YQXBGJW1VKDF64YJ5RTJ6

use std::path::Path;

use frob_tests::{
    Framework, RunOptions, TestTarget, build_repo_graph, dotnet_groups, run, select_tests,
    touched_set, unity_assemblies, unity_groups,
};
use gob_git::Repo;

mod common;
use common::{git, write};

const SHIP: &str = "namespace Game\n{\n    public class Ship\n    {\n        public int Thrust(int n) { return n * 2; }\n        public int Unused(int n) { return n; }\n    }\n}\n";
const SHIP_TESTS: &str = "using NUnit.Framework;\n\nnamespace Game.Tests\n{\n    public class ShipTests\n    {\n        [Test]\n        public void Thrusts()\n        {\n            Assert.AreEqual(4, new Game.Ship().Thrust(2));\n        }\n\n        [Test]\n        public void ThrustsZero()\n        {\n            Assert.AreEqual(0, new Game.Ship().Thrust(0));\n        }\n\n        [Test]\n        public void Standalone()\n        {\n            Assert.AreEqual(1, 1);\n        }\n    }\n}\n";
const GAME_CSPROJ: &str = "<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>\n";
const TESTS_CSPROJ: &str = "<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup><ItemGroup><ProjectReference Include=\"../../src/Game/Game.csproj\" /></ItemGroup></Project>\n";
const TRX: &str = r#"<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010"><Results>
<UnitTestResult testId="a" testName="Thrusts" duration="00:00:00.01" outcome="Passed" />
<UnitTestResult testId="b" testName="ThrustsZero" duration="00:00:00.01" outcome="Passed" />
</Results><TestDefinitions>
<UnitTest name="Thrusts" id="a"><TestMethod className="Game.Tests.ShipTests" name="Thrusts" /></UnitTest>
<UnitTest name="ThrustsZero" id="b"><TestMethod className="Game.Tests.ShipTests" name="ThrustsZero" /></UnitTest>
</TestDefinitions></TestRun>"#;

/// A repository on `main` with a `.csproj` game and test project; returns the dir and the base commit.
fn csproj_repo(extra: impl FnOnce(&Path)) -> (tempfile::TempDir, String) {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    git(p, &["init", "-q"]);
    git(p, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(p, &["config", "user.name", "Test User"]);
    git(p, &["config", "user.email", "test@example.com"]);
    git(p, &["config", "core.autocrlf", "false"]);
    write(p, "src/Game/Game.csproj", GAME_CSPROJ);
    write(p, "src/Game/Ship.cs", SHIP);
    write(p, "tests/Game.Tests/Game.Tests.csproj", TESTS_CSPROJ);
    write(p, "tests/Game.Tests/ShipTests.cs", SHIP_TESTS);
    extra(p);
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "base"]);
    let base = git(p, &["rev-parse", "HEAD"]);
    (dir, base)
}

fn selected(dir: &Path, base: &str) -> Vec<TestTarget> {
    let repo = Repo::discover(dir).expect("repo");
    let graph = build_repo_graph(dir).expect("graph");
    let touched = touched_set(&repo, &graph, base).expect("touched");
    select_tests(dir, &graph, &touched)
}

fn cli() -> gob_cli::Cli {
    frob_tests::register(frob_evidence::register(gob_cli::Cli::new("frob", "0.0.0")))
}

#[test]
fn a_changed_method_selects_exactly_the_two_tests_that_reach_it() {
    // frob:tests crates/frob-tests/src/select.rs::select_tests
    let (dir, base) = csproj_repo(|_| {});
    write(
        dir.path(),
        "src/Game/Ship.cs",
        &SHIP.replace("n * 2", "n * 3"),
    );
    let got = selected(dir.path(), &base);
    let ids: Vec<(Framework, &str, &str)> = got
        .iter()
        .map(|t| (t.framework, t.package.as_str(), t.test_path.as_str()))
        .collect();
    assert_eq!(
        ids,
        [
            (
                Framework::Dotnet,
                "tests/Game.Tests/Game.Tests.csproj",
                "Game.Tests.ShipTests.Thrusts"
            ),
            (
                Framework::Dotnet,
                "tests/Game.Tests/Game.Tests.csproj",
                "Game.Tests.ShipTests.ThrustsZero"
            ),
        ],
        "{got:?}"
    );
    assert_eq!(
        got[0].plan_line(),
        "dotnet tests/Game.Tests/Game.Tests.csproj Game.Tests.ShipTests.Thrusts"
    );
}

#[test]
fn a_method_no_test_reaches_selects_nothing_and_the_gap_is_reported() {
    // frob:tests crates/frob-tests/src/verb.rs::TestVerb
    let (dir, base) = csproj_repo(|p| {
        write(
            p,
            "src/Game/Orphan.cs",
            "namespace Game\n{\n    public class Orphan\n    {\n        public int Lonely(int n) { return n; }\n    }\n}\n",
        );
    });
    write(
        dir.path(),
        "src/Game/Orphan.cs",
        "namespace Game\n{\n    public class Orphan\n    {\n        public int Lonely(int n) { return n + 1; }\n    }\n}\n",
    );
    let got = selected(dir.path(), &base);
    assert!(got.is_empty(), "{got:?}");
    let (code, out, err) =
        gob_cli::run_for_test(&cli(), &["--text", "test", "--base", &base], dir.path());
    assert_eq!(code, 0, "{out}{err}");
    assert!(
        out.contains("no tests reach the touched set; nothing was run"),
        "{out}"
    );
    assert!(out.contains("ran: false"), "{out}");
}

#[test]
fn the_test_verb_runs_the_selected_ids_through_the_dotnet_provider() {
    // frob:tests crates/frob-tests/src/run.rs::run
    let fake = gob_testsupport::fake_dotnet();
    let (dir, base) = csproj_repo(|p| {
        write(
            p,
            "frob.toml",
            &format!("[evidence.dotnet]\npath = '{}'\n", fake.display()),
        );
        write(p, "fake-dotnet.trx", TRX);
    });
    write(
        dir.path(),
        "src/Game/Ship.cs",
        &SHIP.replace("n * 2", "n * 3"),
    );
    let (code, out, err) =
        gob_cli::run_for_test(&cli(), &["--json", "test", "--base", &base], dir.path());
    assert_eq!(code, 0, "{out}{err}");
    let v: serde_json::Value = serde_json::from_str(&out).expect("json");
    assert_eq!(v["data"]["ran"], true, "{out}");
    assert_eq!(v["data"]["passed"], true, "{out}");
    assert_eq!(
        v["data"]["executed"],
        serde_json::json!([
            "Game.Tests.ShipTests.Thrusts",
            "Game.Tests.ShipTests.ThrustsZero"
        ]),
        "{out}"
    );
}

#[test]
fn groups_run_one_project_with_its_ids_and_all_runs_every_test_project_whole() {
    // frob:tests crates/frob-tests/src/run.rs::dotnet_groups
    let (dir, base) = csproj_repo(|_| {});
    write(
        dir.path(),
        "src/Game/Ship.cs",
        &SHIP.replace("n * 2", "n * 3"),
    );
    let got = selected(dir.path(), &base);
    let mut opts = RunOptions::new(
        dir.path().to_path_buf(),
        std::time::Duration::from_secs(60),
        String::new(),
        vec!["dotnet".to_owned()],
        false,
    );
    let groups = dotnet_groups(&got, &opts);
    assert_eq!(groups.len(), 1, "{groups:?}");
    assert_eq!(groups[0].project, "tests/Game.Tests/Game.Tests.csproj");
    assert_eq!(groups[0].ids.len(), 2);
    opts.all = true;
    let whole = dotnet_groups(&[], &opts);
    assert_eq!(whole.len(), 1);
    assert!(whole[0].ids.is_empty(), "{whole:?}");
}

const PART_A: &str = "namespace Game\n{\n    public partial class Hull\n    {\n        public int Armor = 1;\n    }\n}\n";
const PART_B: &str = "namespace Game\n{\n    public partial class Hull\n    {\n        public int Plating() { return Armor * 2; }\n    }\n}\n";
const HULL_TESTS: &str = "using NUnit.Framework;\n\nnamespace Game.Tests\n{\n    public class HullTests\n    {\n        [Test]\n        public void Plates()\n        {\n            Assert.AreEqual(2, new Game.Hull().Plating());\n        }\n    }\n}\n";

#[test]
fn touching_one_part_of_a_partial_type_selects_tests_reaching_any_part() {
    // frob:tests crates/frob-tests/src/select.rs::select_tests
    let (dir, base) = csproj_repo(|p| {
        write(p, "src/Game/Hull.A.cs", PART_A);
        write(p, "src/Game/Hull.B.cs", PART_B);
        write(p, "tests/Game.Tests/HullTests.cs", HULL_TESTS);
    });
    write(
        dir.path(),
        "src/Game/Hull.A.cs",
        &PART_A.replace("Armor = 1", "Armor = 5"),
    );
    let got = selected(dir.path(), &base);
    let ids: Vec<&str> = got.iter().map(|t| t.test_path.as_str()).collect();
    assert!(ids.contains(&"Game.Tests.HullTests.Plates"), "{got:?}");
}

const UNITY_CODE: &str = "namespace Hb.Core\n{\n    public static class Math2\n    {\n        public static int Twice(int n) { return n * 2; }\n    }\n}\n";
const UNITY_TESTS: &str = "using NUnit.Framework;\n\nnamespace Hb.Core.Tests\n{\n    public class Math2Tests\n    {\n        [Test]\n        public void Doubles()\n        {\n            Assert.AreEqual(4, Hb.Core.Math2.Twice(2));\n        }\n    }\n}\n";
const CORE_ASMDEF: &str = "{ \"name\": \"Hb.Core\" }\n";
const TESTS_ASMDEF: &str = "{ \"name\": \"Hb.Core.Tests\", \"references\": [\"Hb.Core\", \"UnityEngine.TestRunner\"], \"includePlatforms\": [\"Editor\"], \"defineConstraints\": [\"UNITY_INCLUDE_TESTS\"] }\n";

/// A Unity project with a code assembly and an `EditMode` test assembly; returns the dir and the base commit.
fn unity_repo() -> (tempfile::TempDir, String) {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    git(p, &["init", "-q"]);
    git(p, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(p, &["config", "user.name", "Test User"]);
    git(p, &["config", "user.email", "test@example.com"]);
    git(p, &["config", "core.autocrlf", "false"]);
    write(
        p,
        "ProjectSettings/ProjectVersion.txt",
        "m_EditorVersion: 2022.3.10f1\n",
    );
    write(p, "Assets/Scripts/Hb.Core/Hb.Core.asmdef", CORE_ASMDEF);
    write(p, "Assets/Scripts/Hb.Core/Math2.cs", UNITY_CODE);
    write(
        p,
        "Assets/Tests/EditMode/Hb.Core.Tests/Hb.Core.Tests.asmdef",
        TESTS_ASMDEF,
    );
    write(
        p,
        "Assets/Tests/EditMode/Hb.Core.Tests/Math2Tests.cs",
        UNITY_TESTS,
    );
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "base"]);
    let base = git(p, &["rev-parse", "HEAD"]);
    (dir, base)
}

const NUNIT_PASS: &str = r#"<test-run result="Passed"><test-suite type="Assembly">
<test-case id="1" name="Doubles" fullname="Hb.Core.Tests.Math2Tests.Doubles" methodname="Doubles" classname="Hb.Core.Tests.Math2Tests" result="Passed" duration="0.01" />
</test-suite></test-run>"#;
const PLAY_ASMDEF: &str = "{ \"name\": \"Hb.Play.Tests\", \"references\": [\"Hb.Core\", \"UnityEngine.TestRunner\"], \"defineConstraints\": [\"UNITY_INCLUDE_TESTS\"] }\n";
const PLAY_TESTS: &str = "using NUnit.Framework;\n\nnamespace Hb.Play.Tests\n{\n    public class SpinTests\n    {\n        [Test]\n        public void Spins()\n        {\n            Assert.AreEqual(4, Hb.Core.Math2.Twice(2));\n        }\n    }\n}\n";

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
#[test]
fn a_touched_unity_assembly_prints_the_selection_and_the_run_goes_through_the_unity_provider() {
    // frob:tests crates/frob-tests/src/run.rs::run
    let fake = gob_testsupport::fake_dotnet();
    let (dir, base) = unity_repo();
    write(
        dir.path(),
        "frob.toml",
        &format!("[evidence.unity]\neditor = '{}'\n", fake.display()),
    );
    write(dir.path(), "fake-unity.xml", NUNIT_PASS);
    write(
        dir.path(),
        "Assets/Scripts/Hb.Core/Math2.cs",
        &UNITY_CODE.replace("n * 2", "n * 3"),
    );
    let got = selected(dir.path(), &base);
    assert_eq!(got.len(), 1, "{got:?}");
    assert_eq!(got[0].framework, Framework::Unity);
    assert_eq!(
        got[0].package,
        "Assets/Tests/EditMode/Hb.Core.Tests/Hb.Core.Tests.asmdef"
    );
    assert_eq!(got[0].test_path, "Hb.Core.Tests.Math2Tests.Doubles");
    let (code, out, err) = gob_cli::run_for_test(
        &cli(),
        &["--text", "test", "--base", &base, "--dry-run"],
        dir.path(),
    );
    assert_eq!(code, 0, "{out}{err}");
    assert!(
        out.contains("- unity Assets/Tests/EditMode/Hb.Core.Tests/Hb.Core.Tests.asmdef Hb.Core.Tests.Math2Tests.Doubles"),
        "{out}"
    );
    let (code, out, err) =
        gob_cli::run_for_test(&cli(), &["--json", "test", "--base", &base], dir.path());
    assert_eq!(code, 0, "{out}{err}");
    let v: serde_json::Value = serde_json::from_str(&out).expect("json");
    assert_eq!(v["data"]["passed"], true, "{out}");
    assert_eq!(
        v["data"]["executed"],
        serde_json::json!(["Hb.Core.Tests.Math2Tests.Doubles"]),
        "{out}"
    );
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
#[test]
fn a_play_mode_only_test_runs_play_mode_and_edit_mode_tests_run_edit_mode() {
    // frob:tests crates/frob-tests/src/run.rs::unity_groups
    let fake = gob_testsupport::fake_dotnet();
    let (dir, base) = unity_repo();
    write(
        dir.path(),
        "Assets/Tests/PlayMode/Hb.Play.Tests/Hb.Play.Tests.asmdef",
        PLAY_ASMDEF,
    );
    write(
        dir.path(),
        "Assets/Tests/PlayMode/Hb.Play.Tests/SpinTests.cs",
        PLAY_TESTS,
    );
    write(
        dir.path(),
        "Assets/Tests/EditMode/Hb.Core.Tests/Math2Tests.cs",
        &UNITY_TESTS
            .replace("Doubles", "Quadruples")
            .replace("Twice(2)", "Missing(2)"),
    );
    write(dir.path(), "fake-unity.xml", NUNIT_PASS);
    git(dir.path(), &["add", "-A"]);
    git(dir.path(), &["commit", "-q", "-m", "play"]);
    let base2 = git(dir.path(), &["rev-parse", "HEAD"]);
    let _ = base;
    write(
        dir.path(),
        "Assets/Scripts/Hb.Core/Math2.cs",
        &UNITY_CODE.replace("n * 2", "n * 3"),
    );
    let got = selected(dir.path(), &base2);
    let mut opts = RunOptions::new(
        dir.path().to_path_buf(),
        std::time::Duration::from_secs(60),
        String::new(),
        Vec::new(),
        false,
    );
    opts.unity_editor = fake.display().to_string();
    let groups = unity_groups(&got, &opts);
    let modes: Vec<&str> = groups.iter().map(|g| g.mode).collect();
    assert!(modes.contains(&"PlayMode"), "{groups:?}");
    // Only the PlayMode test reaches the function: run just that selection.
    let play_only: Vec<TestTarget> = got
        .iter()
        .filter(|t| t.package.contains("PlayMode"))
        .cloned()
        .collect();
    assert!(!play_only.is_empty(), "{got:?}");
    let runner = gob_exec::Runner::new(gob_exec::Limits::default());
    let report = run(&runner, &play_only, &opts).expect("run");
    assert_eq!(report.runs.len(), 1);
    let transcript = &report.runs[0].capture.transcript;
    assert!(
        transcript.contains("-testPlatform PlayMode"),
        "{transcript}"
    );
    assert!(
        transcript.contains("-assemblyNames Hb.Play.Tests"),
        "{transcript}"
    );
    assert_eq!(
        report.runs[0].provider(),
        frob_evidence::record::Provider::Unity
    );
    assert_eq!(report.runs[0].args[0], "PlayMode");
    let edit_only: Vec<TestTarget> = got
        .iter()
        .filter(|t| t.package.contains("EditMode"))
        .cloned()
        .collect();
    let edit = unity_groups(&edit_only, &opts);
    assert!(edit.iter().all(|g| g.mode == "EditMode"), "{edit:?}");
}

#[test]
fn all_finds_the_unity_test_assemblies_and_groups_them_whole() {
    // frob:tests crates/frob-tests/src/run.rs::unity_assemblies
    let (dir, _) = unity_repo();
    let mut opts = RunOptions::new(
        dir.path().to_path_buf(),
        std::time::Duration::from_secs(60),
        String::new(),
        Vec::new(),
        true,
    );
    assert_eq!(
        unity_assemblies(&[], &opts),
        ["Assets/Tests/EditMode/Hb.Core.Tests/Hb.Core.Tests.asmdef"]
    );
    let groups = unity_groups(&[], &opts);
    assert_eq!(groups.len(), 1, "{groups:?}");
    assert_eq!(groups[0].mode, "EditMode");
    assert!(groups[0].ids.is_empty());
    opts.all = false;
    assert!(unity_assemblies(&[], &opts).is_empty());
}

#[test]
fn a_crlf_test_file_keeps_every_test_detectable() {
    // frob:tests crates/frob-tests/src/select.rs::select_tests
    let (dir, base) = csproj_repo(|p| {
        write(
            p,
            "tests/Game.Tests/CrlfTests.cs",
            &SHIP_TESTS
                .replace("ShipTests", "CrlfTests")
                .replace('\n', "\r\n"),
        );
    });
    write(
        dir.path(),
        "tests/Game.Tests/CrlfTests.cs",
        &format!(
            "{}// touched\r\n",
            SHIP_TESTS
                .replace("ShipTests", "CrlfTests")
                .replace('\n', "\r\n")
        ),
    );
    let got = selected(dir.path(), &base);
    let ids: Vec<&str> = got.iter().map(|t| t.test_path.as_str()).collect();
    assert_eq!(
        ids,
        [
            "Game.Tests.CrlfTests.Standalone",
            "Game.Tests.CrlfTests.Thrusts",
            "Game.Tests.CrlfTests.ThrustsZero"
        ]
    );
}
