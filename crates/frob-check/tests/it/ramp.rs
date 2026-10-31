#![allow(
    clippy::disallowed_methods,
    reason = "a test reads fixtures and outputs, not a walked snapshot"
)]
//! A rule new in the current release line reports at Warn (naming the next release) unless `[rules] ramp = false`.

// frob:ticket 01M5WAN9GG0E1M9PM16B3EMY2Z

use std::path::Path;

use frob_check::{CheckOptions, run};
use gob_rules::Severity;

fn write(root: &Path, path: &str, text: &str) {
    let full = root.join(path);
    std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
    std::fs::write(full, text).expect("write");
}

/// The first TEST001 finding of a repo whose frob.toml is `config` and whose source binds `frob:tests` to nothing.
fn test001(config: &str) -> gob_rules::Finding {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "frob.toml", config);
    write(
        dir.path(),
        "src/lib.rs",
        "//! Library.\n/* frob:tests tests::missing */\n/// Bound to nothing.\npub fn dangling() {}\n",
    );
    let opts = CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        only: vec!["TEST001".to_owned()],
        ..CheckOptions::default()
    };
    run(dir.path(), &opts)
        .expect("run")
        .findings
        .into_iter()
        .find(|f| f.rule.to_string() == "TEST001")
        .expect("a TEST001 finding")
}

// frob:tests crates/frob-check/src/lib.rs::run
#[test]
fn a_new_error_rule_is_no_longer_ramped() {
    let ramped = test001("");
    assert_eq!(ramped.severity, Severity::Error);
    assert!(!ramped.message.contains("0.533.0"), "{}", ramped.message);
    let strict = test001("[rules]\nramp = false\n");
    assert_eq!(strict.severity, Severity::Error);
}
