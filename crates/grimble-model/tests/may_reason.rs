//! Grant reasons: a `may` clause without `because=` or `ticket=` draws an MDL008 request for one.

// frob:ticket 01M4GYBTXAPBEX9QYWYX5FKR67

use grimble_model::{ModelFiles, check_model};

/// The MDL008 messages `check_model` yields for a node whose body is `body`.
fn reason_findings(body: &str) -> Vec<String> {
    let text = format!(
        "grimble = \"2\";\nmodule m;\nnode a : trusted {{\n  owns \"src/**\";\n  {body}\n}}\n"
    );
    let model = ModelFiles::new()
        .with_file("design/model.grmb", text.as_bytes())
        .with_root("design/model.grmb");
    check_model(&model)
        .into_iter()
        .filter(|f| f.rule.to_string() == "MDL008")
        .map(|f| f.message)
        .collect()
}

// frob:tests crates/grimble-model/src/check.rs::check_model
#[test]
fn grant_without_reason_asks_for_one() {
    let got = reason_findings("may fs.read at \"src/**\";");
    assert_eq!(got.len(), 1, "{got:?}");
    assert!(got[0].contains("because"), "{got:?}");
    assert!(got[0].contains("ticket"), "{got:?}");
    let bare = reason_findings("may fs.read;");
    assert_eq!(bare.len(), 1, "{bare:?}");
}

// frob:tests crates/grimble-model/src/check.rs::check_model
#[test]
fn grant_reason_forms_are_accepted() {
    for body in [
        "may fs.read at \"src/**\" because=\"reads fixtures\";",
        "may fs.read at \"src/**\" ticket=\"T-0042\";",
        "may fs.read at \"src/**\" because=\"why\" ticket=\"T-0042\";",
        "may fs.read because=\"whole node\";",
        "may fs.read ticket=\"T-0042\";",
    ] {
        assert!(reason_findings(body).is_empty(), "{body}");
    }
}

// frob:tests crates/grimble-model/src/check.rs::check_model
#[test]
fn blank_reason_counts_as_missing() {
    assert_eq!(reason_findings("may fs.read because=\"  \";").len(), 1);
    assert_eq!(reason_findings("may fs.read ticket=\"\";").len(), 1);
}
