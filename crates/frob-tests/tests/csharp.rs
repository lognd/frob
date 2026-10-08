//! C# test detection through the catalog: attributes decide, ids are fully qualified, fixtures are not tests.

// frob:ticket 01M44YQV7C3FYXB3QH20R4E5N8

use frob_tests::build_repo_graph;
use frob_tests::catalog::{csharp_test, is_test_fn};
use gob_symbols::{CallEdge, CsharpTestFramework, SymbolKind, Symref};

/// Writes `text` to `rel` under `root`, creating parents.
fn write(root: &std::path::Path, rel: &str, text: &str) {
    let full = root.join(rel);
    std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
    std::fs::write(full, text).expect("write");
}

const SHIP: &str = "using System.Collections;\nnamespace Game\n{\n    public class Ship\n    {\n        public int Thrust(int n) { return n * 2; }\n        public int Unused(int n) { return n; }\n    }\n}\n";
const TESTS: &str = "using System.Collections;\nusing NUnit.Framework;\nusing Xunit;\nusing Microsoft.VisualStudio.TestTools.UnitTesting;\n\nnamespace Game.Tests\n{\n    public class ShipTests\n    {\n        [SetUp]\n        public void Init() { }\n\n        [Test]\n        public void Thrusts()\n        {\n            var ship = new Game.Ship();\n            Assert.AreEqual(4, ship.Thrust(2));\n        }\n\n        [UnityTest]\n        public IEnumerator ThrustsOverFrames()\n        {\n            yield return null;\n        }\n    }\n\n    public class Other\n    {\n        [Fact]\n        public void X() { }\n\n        [TestMethod]\n        public void Y() { }\n    }\n}\n";

fn fixture() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "Assets/Scripts/Ship.cs", SHIP);
    write(dir.path(), "Assets/Tests/EditMode/ShipTests.cs", TESTS);
    dir
}

#[test]
// frob:tests crates/frob-tests/src/catalog.rs::is_test_fn
// frob:tests crates/frob-tests/src/catalog.rs::csharp_test
fn each_attributed_csharp_method_is_a_test_and_unity_test_is_play_mode_capable() {
    let dir = fixture();
    let graph = build_repo_graph(dir.path()).expect("graph");
    let mut found = Vec::new();
    for rec in graph.records() {
        if rec.symref.path() != "Assets/Tests/EditMode/ShipTests.cs" {
            continue;
        }
        if is_test_fn(rec, Some(TESTS)) {
            let t = csharp_test(rec, TESTS).expect("detail agrees with is_test_fn");
            found.push((t.id, t.framework, t.play_mode_capable));
        } else {
            assert!(
                csharp_test(rec, TESTS).is_none(),
                "{} must not be a test",
                rec.symref
            );
        }
    }
    found.sort();
    assert_eq!(
        found,
        [
            (
                "Game.Tests.Other.X".to_owned(),
                CsharpTestFramework::XUnit,
                false
            ),
            (
                "Game.Tests.Other.Y".to_owned(),
                CsharpTestFramework::MsTest,
                false
            ),
            (
                "Game.Tests.ShipTests.Thrusts".to_owned(),
                CsharpTestFramework::NUnit,
                false
            ),
            (
                "Game.Tests.ShipTests.ThrustsOverFrames".to_owned(),
                CsharpTestFramework::NUnit,
                true
            ),
        ]
    );
    let init = graph
        .records()
        .find(|r| r.symref.name() == Some("Init"))
        .expect("Init");
    assert!(!is_test_fn(init, Some(TESTS)));
    // Without text the fallback is the path hint over methods only.
    assert!(is_test_fn(init, None) || init.kind != SymbolKind::Method);
}

#[test]
// frob:tests crates/frob-tests/src/catalog.rs::is_test_fn
fn a_method_called_only_by_a_test_is_reached_from_that_test() {
    let dir = fixture();
    let graph = build_repo_graph(dir.path()).expect("graph");
    let thrust = Symref::parse("Assets/Scripts/Ship.cs::Game.Ship.Thrust").expect("symref");
    let unused = Symref::parse("Assets/Scripts/Ship.cs::Game.Ship.Unused").expect("symref");
    let test = Symref::parse("Assets/Tests/EditMode/ShipTests.cs::Game.Tests.ShipTests.Thrusts")
        .expect("symref");
    // COV001 walks call edges forward from the tests: Thrust is reached, Unused is not.
    let callees: Vec<&Symref> = graph
        .call_edges()
        .iter()
        .filter_map(|e| match e {
            CallEdge::Resolved { caller, callee } if *caller == test => Some(callee),
            _ => None,
        })
        .collect();
    assert!(
        callees.contains(&&thrust),
        "calls from the test: {callees:?}"
    );
    assert!(!callees.contains(&&unused));
    let rec = graph.get(&test).expect("test record");
    assert!(is_test_fn(rec, Some(TESTS)));
}
