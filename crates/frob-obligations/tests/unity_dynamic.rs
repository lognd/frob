//! The unity pack names the reason of a dynamic call in COV001's unresolved report (~19GKAYY).

mod common;

use frob_obligations::InvariantsConfig;

// frob:ticket 01M5FX89B11DR9HP9QH19GKAYY
const DOOR: &str = "using UnityEngine;\n\npublic class Door : MonoBehaviour\n{\n    /// <summary>Opens by name.</summary>\n    public void Open() { Invoke(\"Reload\", 1f); }\n}\n";
const POOL: &str = "public class Pool\n{\n    /// <summary>A project method that shares the dynamic call's name.</summary>\n    public void Invoke(string name, float delay) { }\n}\n";
const CACHE: &str = "public class Cache\n{\n    /// <summary>A second method of that name, so the name scan cannot pick one.</summary>\n    public void Invoke(string name, float delay) { }\n}\n";
const TESTS: &str = "using NUnit.Framework;\n\npublic class DoorTests\n{\n    [Test]\n    public void Smoke() { new Door().Open(); }\n}\n";
const ENABLED: &str = "[[packs.enable]]\nname = \"unity\"\n";
const GATED: &str = "[[packs.enable]]\nname = \"unity\"\npaths = [\"Elsewhere/**\"]\n";

fn pool_report(config: Option<&str>) -> Vec<String> {
    let dir = tempfile::tempdir().expect("tempdir");
    let mut files = vec![
        ("Assets/Door.cs", DOOR),
        ("Assets/Pool.cs", POOL),
        ("Assets/Cache.cs", CACHE),
        ("tests/DoorTests.cs", TESTS),
    ];
    if let Some(c) = config {
        files.push(("frob.toml", c));
    }
    common::write_tree(dir.path(), &files);
    let cfg = InvariantsConfig::load(tempfile::tempdir().expect("tempdir").path()).expect("cfg");
    common::evaluate_tree(dir.path(), None, &cfg, None)
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "COV001" && f.message.contains("Pool.Invoke"))
        .map(|f| f.message.clone())
        .collect()
}

#[test]
fn an_enabled_pack_names_the_dynamic_call_behind_an_unresolved_report() {
    // frob:tests crates/frob-obligations/src/cov.rs::cov001
    // frob:tests crates/frob-tests/src/reach.rs::dynamic_calls
    let found = pool_report(Some(ENABLED));
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].contains("literal method name at run time"),
        "{found:?}"
    );
}

#[test]
fn a_disabled_or_gated_out_pack_leaves_the_call_anonymous() {
    // frob:tests crates/frob-obligations/src/cov.rs::cov001
    // frob:tests crates/frob-tests/src/reach.rs::dynamic_calls
    for config in [None, Some(GATED)] {
        let found = pool_report(config);
        assert_eq!(found.len(), 1, "{found:?}");
        assert!(!found[0].contains("at run time"), "{found:?}");
    }
}
