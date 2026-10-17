//! ORG001-005 beyond the rule pages: the acceptance cases and the switches.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

mod support;

use crunk_rules::rules::{org001::Org001, org002::Org002, org003::Org003, org005::Org005};

const CSS: &str = ".x { display: block; }\n";

// frob:tests crates/crunk-rules/src/rules/org005.rs::Org005
#[test]
fn a_stylesheet_outside_every_declared_root_fires_org005() {
    let host = support::project("other/app.css", CSS, None);
    let found = support::run::<Org005>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].rule.as_str(), "ORG005");
}

// frob:tests crates/crunk-rules/src/rules/org001.rs::Org001
#[test]
fn a_stylesheet_in_no_declared_bucket_fires_org001() {
    let host = support::project("styles/app.css", CSS, None);
    let found = support::run::<Org001>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(support::run::<Org005>(&host).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/org002.rs::Org002
#[test]
fn card_title_under_kebab_fires_org002() {
    let host = support::project(
        "styles/base/a.css",
        ".Card_Title { display: block; }\n",
        None,
    );
    let found = support::run::<Org002>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].rule.as_str(), "ORG002");
}

// frob:tests crates/crunk-rules/src/rules/org003.rs::Org003
#[test]
fn the_component_prefix_is_judged_only_in_the_components_bucket() {
    let other = support::project("styles/base/card.css", ".title { display: block; }\n", None);
    assert!(support::run::<Org003>(&other).is_empty());
    let comp = support::project(
        "styles/components/card.css",
        ".title { display: block; }\n",
        None,
    );
    assert_eq!(support::run::<Org003>(&comp).len(), 1);
}
