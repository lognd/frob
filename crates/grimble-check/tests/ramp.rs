//! `grimble check` ramps a rule new in the current release line to a warning unless `[rules] ramp = false`.

// frob:ticket 01M5WAN9GG0E1M9PM16B3EMY2Z

use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

/// Severity and message of the first PATH001 finding with `config` as the repo's grimble.toml.
fn path001(config: &str) -> (String, String) {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", config);
    write(
        dir.path(),
        "src/lib.rs",
        "fn f() -> &'static str {\n    \"/home/ann/data.txt\"\n}\n",
    );
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    let f = doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .find(|f| f["rule"] == "PATH001")
        .unwrap_or_else(|| panic!("no PATH001 in {doc}"))
        .clone();
    (
        f["severity"].as_str().unwrap().to_owned(),
        f["message"].as_str().unwrap_or_default().to_owned(),
    )
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn new_error_rule_is_no_longer_ramped() {
    let (severity, message) = path001("[check]\n");
    assert_eq!(severity, "error");
    assert!(!message.contains("0.533.0"), "{message}");
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn ramp_false_keeps_the_declared_error() {
    let (severity, message) = path001("[rules]\nramp = false\n");
    assert_eq!(severity, "error");
    assert!(!message.contains("0.533.0"), "{message}");
}
