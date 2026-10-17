//! TOKENS001: a missing or drifted generated sheet fires, a fresh one is clean.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

mod support;

use crunk_rules::rules::tokens001::Tokens001;

// frob:tests crates/crunk-rules/src/rules/tokens001.rs::Tokens001
// frob:tests crates/crunk-rules/src/host.rs::CrunkHost.generated_files
#[test]
fn a_stale_tokens_sheet_fires_tokens001() {
    let host = support::project(
        "styles/base/app.css",
        ".a {\n  display: block;\n}\n",
        Some("stale-tokens"),
    );
    let found = support::run::<Tokens001>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].message.contains("crunk tokens"),
        "{}",
        found[0].message
    );
}

// frob:tests crates/crunk-rules/src/rules/tokens001.rs::Tokens001
// frob:tests crates/crunk-rules/src/host.rs::CrunkHost.read_generated
#[test]
fn a_missing_tokens_sheet_fires_tokens001() {
    let host = support::project(
        "styles/base/app.css",
        ".a {\n  display: block;\n}\n",
        Some("stale-tokens,no-tokens"),
    );
    let found = support::run::<Tokens001>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(found[0].message.contains("missing"), "{}", found[0].message);
}
