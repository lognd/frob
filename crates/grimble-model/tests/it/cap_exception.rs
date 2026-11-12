//! CAP exceptions: an accept/defer on a capability rule names the atom and expires (MDL013).

// frob:ticket 01M5XNNHN8RQ6486GS073YMCSS

use grimble_model::{ModelFiles, check_model};

/// The MDL013 messages `check_model` yields for a node whose body is `body`.
fn exception_findings(body: &str) -> Vec<String> {
    let text = format!(
        "grimble = \"2\";\nmodule m;\nnode a : trusted {{\n  owns \"src/**\";\n  {body}\n}}\n"
    );
    let model = ModelFiles::new()
        .with_file("design/model.grmb", text.as_bytes())
        .with_root("design/model.grmb")
        .with_rule("CAP001")
        .with_rule("CAP002")
        .with_rule("CAP003")
        .with_rule("CAP005");
    check_model(&model)
        .into_iter()
        .filter(|f| f.rule.to_string() == "MDL013")
        .map(|f| f.message)
        .collect()
}

// frob:tests crates/grimble-model/src/check.rs::check_model
#[test]
fn accept_cap001_without_an_atom_is_an_error() {
    let got = exception_findings("accept CAP001 until=2999-01-01 because=\"x\";");
    assert_eq!(got.len(), 1, "{got:?}");
    assert!(got[0].contains("atom="), "{got:?}");
}

// frob:tests crates/grimble-model/src/check.rs::check_model
#[test]
fn accept_cap001_without_an_expiry_is_an_error() {
    let got = exception_findings("accept CAP001 atom=\"process.spawn\" because=\"x\";");
    assert_eq!(got.len(), 1, "{got:?}");
    assert!(got[0].contains("until="), "{got:?}");
}

// frob:tests crates/grimble-model/src/check.rs::check_model
#[test]
fn accept_cap001_with_atom_and_expiry_is_clean() {
    let got =
        exception_findings("accept CAP001 atom=\"process.spawn\" until=2999-01-01 because=\"x\";");
    assert!(got.is_empty(), "{got:?}");
}

// frob:tests crates/grimble-model/src/check.rs::check_model
#[test]
fn defer_cap001_needs_the_atom_too() {
    let ticket = "01M3ZEH3S0PG61C2AEBM691F69";
    let got = exception_findings(&format!(
        "defer CAP001 ticket=\"{ticket}\" until=2999-01-01 because=\"x\";"
    ));
    assert_eq!(got.len(), 1, "{got:?}");
}

// frob:tests crates/grimble-model/src/check.rs::check_model
#[test]
fn the_ledger_rule_cannot_be_excepted() {
    let got = exception_findings("accept CAP005 because=\"x\";");
    assert_eq!(got.len(), 1, "{got:?}");
    assert!(got[0].contains("cannot be excepted"), "{got:?}");
}

// frob:tests crates/grimble-model/src/check.rs::check_model
#[test]
fn other_rules_keep_their_old_shape() {
    let got = exception_findings("accept CAP003 because=\"x\";");
    assert!(got.is_empty(), "{got:?}");
}
