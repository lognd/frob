//! The opt-in `unity` pack: engine entry points are COV001 reach roots (~YR0STJ5).

mod common;

use frob_obligations::InvariantsConfig;

// frob:ticket 01M44YQXS4BXE0X07FBYR0STJ5
const HERO: &str = "using UnityEngine;\n\npublic class Hero : MonoBehaviour\n{\n    /// <summary>Per frame.</summary>\n    public void Update() { }\n\n    /// <summary>Trigger message.</summary>\n    public void OnTriggerEnter(Collider c) { }\n\n    /// <summary>Not a message.</summary>\n    public void Tick() { }\n}\n";
const BOSS: &str = "public class Boss : Hero\n{\n    /// <summary>Inherited base chain.</summary>\n    public void LateUpdate() { }\n}\n";
const EDITOR: &str = "using UnityEditor;\n\npublic static class Tools\n{\n    /// <summary>Menu entry.</summary>\n    [MenuItem(\"Tools/Run\")]\n    public static void Run() { }\n\n    /// <summary>Plain helper.</summary>\n    public static void Helper() { }\n}\n\n[InitializeOnLoad]\npublic static class Boot\n{\n    /// <summary>Runs on load.</summary>\n    static Boot() { }\n}\n";
const TESTS: &str = "using NUnit.Framework;\n\npublic class HeroTests\n{\n    [Test]\n    public void Smoke() { Assert.AreEqual(1, 1); }\n}\n";
const ENABLED: &str = "[[packs.enable]]\nname = \"unity\"\n";

fn tree(config: Option<&str>) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let mut files = vec![
        ("Assets/Scripts/Hero.cs", HERO),
        ("Assets/Scripts/Boss.cs", BOSS),
        ("Assets/Editor/Tools.cs", EDITOR),
        ("tests/HeroTests.cs", TESTS),
    ];
    if let Some(c) = config {
        files.push(("frob.toml", c));
    }
    common::write_tree(dir.path(), &files);
    dir
}

fn cov(dir: &tempfile::TempDir) -> Vec<String> {
    let cfg = InvariantsConfig::load(tempfile::tempdir().expect("tempdir").path()).expect("cfg");
    common::evaluate_tree(dir.path(), None, &cfg, None)
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "COV001")
        .map(|f| f.message.clone())
        .collect()
}

#[test]
fn unity_enabled_makes_update_a_root_and_not_unreached() {
    // frob:tests crates/frob-obligations/src/cov.rs::cov001
    let found = cov(&tree(Some(ENABLED)));
    let named = |n: &str| found.iter().any(|m| m.contains(n));
    assert!(!named("Hero.Update"), "{found:?}");
    assert!(!named("Hero.OnTriggerEnter"), "{found:?}");
    assert!(!named("Boss.LateUpdate"), "{found:?}");
    assert!(named("Hero.Tick"), "non-message stays reported: {found:?}");
}

#[test]
fn unity_disabled_reports_update_as_unreached() {
    // frob:tests crates/frob-obligations/src/cov.rs::cov001
    let found = cov(&tree(None));
    assert!(found.iter().any(|m| m.contains("Hero.Update")), "{found:?}");
    let found = cov(&tree(Some("[project]\nname = \"x\"\n")));
    assert!(found.iter().any(|m| m.contains("Hero.Update")), "{found:?}");
}

#[test]
fn menu_item_and_initialize_on_load_are_roots_when_enabled() {
    // frob:tests crates/frob-obligations/src/cov.rs::cov001
    let found = cov(&tree(Some(ENABLED)));
    let named = |n: &str| found.iter().any(|m| m.contains(n));
    assert!(!named("Tools.Run"), "{found:?}");
    assert!(!named("Boot.Boot") && !named("$cctor"), "{found:?}");
    assert!(named("Tools.Helper"), "{found:?}");
    let off = cov(&tree(None));
    assert!(off.iter().any(|m| m.contains("Tools.Run")), "{off:?}");
}
