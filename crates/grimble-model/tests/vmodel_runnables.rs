//! A test vmodel carries several `runnable` clauses or one `manual because=` (grmb-spec 4.5.2).

// frob:ticket 01M4FGZ4KY03QKSWXACP7APFVH

use grimble_model::check_model;
use grimble_model::fmt::format_file;
use grimble_model::model::ModelFiles;
use grimble_model::parse::parse_file;

/// The MDL014 and MDL008 messages of a test vmodel whose body is `body`.
fn findings(body: &str) -> Vec<String> {
    let src = format!(
        "grimble = \"2\";\nmodule m;\nvmodel t {{\n  kind test;\n  level unit;\n{body}}}\n"
    );
    let mf = ModelFiles::new().with_file("design/m.grmb", src);
    check_model(&mf)
        .into_iter()
        .filter(|f| matches!(f.rule.to_string().as_str(), "MDL014" | "MDL008"))
        .map(|f| format!("{}: {}", f.rule, f.message))
        .collect()
}

#[test]
// frob:tests crates/grimble-model/src/check.rs::vmodel
fn several_runnables_or_one_manual_are_clean() {
    assert!(findings("  runnable \"a.rs::x\";\n  runnable \"a.rs::y\";\n").is_empty());
    assert!(findings("  manual because=\"needs a person\";\n").is_empty());
}

#[test]
// frob:tests crates/grimble-model/src/check.rs::vmodel
fn neither_both_and_blank_reason_are_mdl014() {
    for body in [
        "",
        "  runnable \"a.rs::x\";\n  manual because=\"r\";\n",
        "  manual because=\"\";\n",
        "  manual because=\"   \";\n",
    ] {
        let found = findings(body);
        assert_eq!(found.len(), 1, "{body:?}: {found:?}");
        assert!(found[0].starts_with("MDL014"), "{found:?}");
    }
}

#[test]
// frob:tests crates/grimble-model/src/text.rs::clause_text
fn manual_clause_formats_to_a_fixed_point() {
    let src = "grimble = \"2\";\nmodule m;\nvmodel t {\n  kind test;\n  level unit;\n  manual because=\"by hand\";\n}\n";
    let fmt = |t: &str| format_file(&parse_file("design/m.grmb", t.as_bytes())).expect("formats");
    let once = fmt(src);
    assert!(once.contains("manual because=\"by hand\""), "{once}");
    assert_eq!(fmt(&once), once);
}
