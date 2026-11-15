//! A vmodel carries `verified_by` evidence without MDL000 or MDL012 (grmb-spec 4.5, 4.5.2).

// frob:ticket 01M7ET17BM017983KQXF9ZNSC3

use grimble_model::check_model;
use grimble_model::fmt::format_file;
use grimble_model::model::ModelFiles;
use grimble_model::parse::parse_file;

const REQ: &str = "grimble = \"2\";\nmodule m;\nvmodel req {\n  kind artifact;\n  level requirements;\n  ref \"docs/r.md#r1\";\n  verified_by \"tests/t.py::test_a\";\n}\n";

/// Rule ids and messages of every finding for `src`.
fn findings(src: &str) -> Vec<(String, String)> {
    let mf = ModelFiles::new().with_file("design/m.grmb", src.to_owned());
    check_model(&mf)
        .into_iter()
        .filter(|f| matches!(f.rule.to_string().as_str(), "MDL000" | "MDL012"))
        .map(|f| (f.rule.to_string(), f.message))
        .collect()
}

#[test]
// frob:tests crates/grimble-model/src/check.rs::check_model
fn vmodel_verified_by_selector_raises_no_mdl000_or_mdl012() {
    assert!(findings(REQ).is_empty(), "{:?}", findings(REQ));
}

#[test]
// frob:tests crates/grimble-model/src/check.rs::check_model
fn vmodel_verified_by_manual_raises_no_mdl000_or_mdl012() {
    let src = REQ.replace(
        "verified_by \"tests/t.py::test_a\";",
        "verified_by manual because=\"audited\";",
    );
    assert!(findings(&src).is_empty(), "{:?}", findings(&src));
}

#[test]
// frob:tests crates/grimble-model/src/check.rs::check_model
fn mdl000_names_the_verified_by_keyword_as_written() {
    let node = "grimble = \"2\";\nmodule m;\ncontract c {\n  shape \"s.py::C\";\n  verified_by \"t.py\";\n}\n";
    let found = findings(node);
    assert!(
        found.iter().any(|(r, m)| r == "MDL000"
            && m.contains("`verified_by`")
            && !m.contains("`evidence`")),
        "{found:?}"
    );
}

#[test]
// frob:tests crates/grimble-model/src/fmt.rs::format_file
fn fmt_keeps_verified_by_after_ref_on_a_vmodel() {
    let f = parse_file("m.grmb", REQ.as_bytes());
    assert!(f.diags.is_empty(), "{:?}", f.diags);
    let out = format_file(&f).expect("formats");
    let at = |k: &str| out.find(k).unwrap_or_else(|| panic!("{k} in {out}"));
    assert!(
        at("level") < at("ref \"") && at("ref \"") < at("verified_by"),
        "{out}"
    );
}
