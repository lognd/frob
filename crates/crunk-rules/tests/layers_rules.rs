//! LAYER001 beyond the rule page: the acceptance case and what is not judged.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

mod support;

use crunk_rules::rules::layer001::Layer001;

// frob:tests crates/crunk-rules/src/rules/layer001.rs::Layer001
#[test]
fn z_index_99_outside_the_declared_layers_fires() {
    let host = support::project("styles/base/a.css", ".m { z-index: 99; }\n", None);
    let found = support::run::<Layer001>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].rule.as_str(), "LAYER001");
}

// frob:tests crates/crunk-rules/src/rules/layer001.rs::Layer001
#[test]
fn keywords_and_functions_are_not_judged() {
    let host = support::project(
        "styles/base/a.css",
        ".m { z-index: auto; }\n.n { z-index: calc(var(--x) + 1); }\n",
        None,
    );
    assert!(support::run::<Layer001>(&host).is_empty());
}
