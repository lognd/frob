//! The TESTQ rules as registered rules: the test pass through `grimble check`, with `TESTQ003` opt-in.

// frob:ticket 01M5HJNE91SN4N0MR8GHM30Z1Y

#![allow(unused_crate_dependencies)]

use grimble_check::{CheckOptions, run, sibling_document};

/// The TESTQ findings of a repo holding `grimble.toml` (`config`) and `tests/test_a.py` (`source`).
fn testq_findings(config: &str, source: &str) -> Vec<serde_json::Value> {
    let dir = tempfile::tempdir().unwrap();
    std::fs::write(dir.path().join("grimble.toml"), config).unwrap();
    std::fs::create_dir_all(dir.path().join("tests")).unwrap();
    std::fs::write(dir.path().join("tests/test_a.py"), source).unwrap();
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    sibling_document(&r)["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["rule"].as_str().is_some_and(|r| r.starts_with("TESTQ")))
        .cloned()
        .collect()
}

const NO_ASSERT: &str = "def test_a():\n    x = 1 + 2\n    print(x)\n";
const BRANCHY: &str = "def test_a():\n    for v in (1, 2):\n        assert v > 0\n";
const HELPER: &str = "from .support import finish\n\n\ndef test_a():\n    finish(1)\n";

// frob:tests crates/grimble-check/src/rules/testq001.rs::Testq001
// frob:tests crates/grimble-check/src/testq_pass.rs::analyze
// frob:tests crates/grimble-check/src/host.rs::TestqHost.testq_subjects_of
#[test]
fn a_test_without_an_assertion_is_an_error() {
    let found = testq_findings("[check]\n", NO_ASSERT);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0]["rule"], "TESTQ001");
    assert_eq!(found[0]["severity"], "error", "{found:?}");
}

// frob:tests crates/grimble-check/src/rules/testq001.rs::Testq001
// frob:tests crates/grimble-check/src/testq_pass.rs::analyze
#[test]
fn a_helper_out_of_sight_is_unresolved_never_error() {
    let found = testq_findings("[check]\n", HELPER);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0]["severity"], "unresolved", "{found:?}");
}

// frob:tests crates/grimble-check/src/rules/testq002.rs::Testq002
#[test]
fn a_sleep_in_a_test_is_reported() {
    let found = testq_findings(
        "[check]\n",
        "import time\n\n\ndef test_a():\n    time.sleep(1)\n    assert True\n",
    );
    assert!(found.iter().any(|f| f["rule"] == "TESTQ002"), "{found:?}");
}

// frob:tests crates/grimble-check/src/rules/testq003.rs::Testq003
// frob:tests crates/grimble-check/src/testq_pass.rs::analyze
#[test]
fn control_flow_is_off_until_the_project_opts_in() {
    let off = testq_findings("[check]\n", BRANCHY);
    assert!(off.is_empty(), "{off:?}");
    let on = testq_findings("[rules.TESTQ003]\nseverity = \"error\"\n", BRANCHY);
    assert_eq!(on.len(), 1, "{on:?}");
    assert_eq!(on[0]["rule"], "TESTQ003");
}
