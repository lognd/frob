//! A vmodel `ref` is checked for spelling at load (grmb-spec 4.5.1): a malformed one is MDL014.

// frob:ticket 01M4FGZ39WXWBRDRHW2ADSY7K8

use grimble_model::check_model;
use grimble_model::model::ModelFiles;
use grimble_model::refspec::malformed_ref;

/// The MDL014 messages of a model whose artifact `req` carries `ref_text`.
fn mdl014(ref_text: &str) -> Vec<String> {
    let src = format!(
        "grimble = \"2\";\nmodule m;\nvmodel req {{\n  kind artifact;\n  level requirements;\n  ref \"{ref_text}\";\n}}\n"
    );
    let mf = ModelFiles::new().with_file("design/m.grmb", src);
    check_model(&mf)
        .into_iter()
        .filter(|f| f.rule.to_string() == "MDL014")
        .map(|f| f.message)
        .collect()
}

#[test]
// frob:tests crates/grimble-model/src/refspec.rs::malformed_ref
fn single_colon_ref_is_reported_with_the_hash_spelling() {
    let found = mdl014("docs/r.md:COMP-0101");
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(found[0].contains("docs/r.md:COMP-0101"), "{found:?}");
    assert!(found[0].contains("docs/r.md#COMP-0101"), "{found:?}");
}

#[test]
// frob:tests crates/grimble-model/src/refspec.rs::malformed_ref
fn well_formed_refs_are_quiet() {
    for ok in [
        "docs/r.md#comp-0101",
        "docs/r.md::comp-0101",
        "src/a.rs::Type.method",
        "web/e2e/gate.test.ts::[gate > shows: x]",
        "docs/spec/L2.md#spec-060",
        "plain.md",
    ] {
        assert!(malformed_ref(ok).is_none(), "{ok}");
        assert!(mdl014(ok).is_empty(), "{ok}");
    }
}

#[test]
// frob:tests crates/grimble-model/src/refspec.rs::malformed_ref
fn other_malformed_spellings_are_reported() {
    for bad in [
        "docs/r.md#",
        "docs/r.md#a#b",
        "docs/r.md#a b",
        "docs/r.md#a{b}",
        "#anchor",
        "C:/x/r.md",
        "C:\\\\x\\\\r.md",
        "a:b::c",
        "docs/r.md:",
    ] {
        assert!(malformed_ref(bad).is_some(), "{bad}");
    }
    let drive = malformed_ref("C:/x/r.md").unwrap_or_default();
    assert!(drive.contains("drive path"), "{drive}");
}
