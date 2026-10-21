//! COV001 over C#: C# files are test-capable subjects, tested methods are covered and untested public ones are findings (~PMRA314).

mod common;

use frob_obligations::{InvariantsConfig, collect, cov001_subjects};

// frob:ticket 01M4D3H2MXY2G59N9ZHPMRA314
const SHIP: &str = "namespace Game\n{\n    public class Ship\n    {\n        /// <summary>Doubles.</summary>\n        public int Thrust(int n) { return n * 2; }\n\n        /// <summary>Never tested.</summary>\n        public int Drift(int n) { return n; }\n    }\n}\n";
const TESTS: &str = "using NUnit.Framework;\n\nnamespace Game.Tests\n{\n    public class ShipTests\n    {\n        [Test]\n        public void Thrusts()\n        {\n            Assert.AreEqual(4, new Game.Ship().Thrust(2));\n        }\n    }\n}\n";

fn tree() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(
        dir.path(),
        &[
            (
                "src/Game/Game.csproj",
                "<Project Sdk=\"Microsoft.NET.Sdk\" />\n",
            ),
            ("src/Game/Ship.cs", SHIP),
            ("tests/Game.Tests/ShipTests.cs", TESTS),
        ],
    );
    dir
}

#[test]
fn csharp_files_are_counted_as_cov001_subjects() {
    // frob:tests crates/frob-obligations/src/lib.rs::cov001_subjects
    let dir = tree();
    let collected = collect(dir.path()).expect("collect");
    assert_eq!(cov001_subjects(&collected.graph), 2);
}

#[test]
fn an_untested_public_csharp_method_is_a_cov001_finding_and_a_tested_one_is_not() {
    // frob:tests crates/frob-obligations/src/lib.rs::evaluate_repo
    let dir = tree();
    let cfg = InvariantsConfig::load(tempfile::tempdir().expect("tempdir").path()).expect("cfg");
    let ev = common::evaluate_tree(dir.path(), None, &cfg, None);
    let cov: Vec<String> = ev
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "COV001")
        .map(|f| f.message.clone())
        .collect();
    assert!(cov.iter().any(|m| m.contains("Ship.Drift")), "{cov:?}");
    assert!(!cov.iter().any(|m| m.contains("Ship.Thrust")), "{cov:?}");
}

// frob:ticket 01M44YQTSWW9EH49541MY9A7AX
const DOCS: &str = "/// <summary>A ship.</summary>\npublic class Ship\n{\n    /// <summary>Doubles.</summary>\n    /// <param name=\"n\">Input.</param>\n    [Obsolete]\n    public int Thrust(int n) { return n * 2; }\n\n    /// <inheritdoc/>\n    public int Inherited(int n) { return n; }\n\n    public int Drift(int n) { return n; }\n\n    /// Not xml but still a doc line.\n    public int Plain() { return 1; }\n\n    // ordinary comment\n    public int Ordinary() { return 1; }\n}\n";

#[test]
fn doc001_accepts_xml_doc_and_inheritdoc_and_flags_bare_public_csharp_members() {
    // frob:tests crates/frob-obligations/src/doc.rs::doc001
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(dir.path(), &[("src/Ship.cs", DOCS)]);
    let cfg = InvariantsConfig::load(tempfile::tempdir().expect("tempdir").path()).expect("cfg");
    let ev = common::evaluate_tree(dir.path(), None, &cfg, None);
    let docs: Vec<String> = ev
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "DOC001")
        .map(|f| f.message.clone())
        .collect();
    let named = |n: &str| docs.iter().any(|m| m.contains(n));
    assert!(named("Ship.Drift") && named("Ship.Ordinary"), "{docs:?}");
    assert!(
        !named("Ship.Thrust") && !named("Ship.Inherited"),
        "{docs:?}"
    );
    assert!(
        !docs.iter().any(|m| m.ends_with("`src/Ship.cs::Ship`")),
        "{docs:?}"
    );
    assert_eq!(docs.len(), 2, "{docs:?}");
}
