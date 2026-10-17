//! TOKENS001: a stale generated tokens sheet fires, a fresh one is clean.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

mod support;

use std::path::PathBuf;

use crunk_rules::GeneratedFile;
use crunk_rules::rules::tokens001::Tokens001;

fn with_file(expected: &str, actual: Option<&str>) -> support::Project {
    let mut host = support::project("styles/base/app.css", ".a {\n  display: block;\n}\n", None);
    host.generated = Some(vec![GeneratedFile {
        path: PathBuf::from("styles/tokens.css"),
        expected: expected.to_owned(),
        actual: actual.map(str::to_owned),
    }]);
    host
}

// frob:tests crates/crunk-rules/src/rules/tokens001.rs::Tokens001
#[test]
fn a_stale_tokens_sheet_fires_tokens001() {
    let host = with_file(":root { --a: 1; }\n", Some(":root { --a: 2; }\n"));
    let found = support::run::<Tokens001>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].message.contains("crunk tokens"),
        "{}",
        found[0].message
    );
}

// frob:tests crates/crunk-rules/src/rules/tokens001.rs::Tokens001
#[test]
fn a_missing_tokens_sheet_fires_and_a_fresh_one_is_clean() {
    assert_eq!(support::run::<Tokens001>(&with_file("x\n", None)).len(), 1);
    assert!(support::run::<Tokens001>(&with_file("x\n", Some("x\n"))).is_empty());
}
