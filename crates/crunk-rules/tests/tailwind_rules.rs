//! TW001-005 against throwaway projects: the arbitrary-value and dynamic-class rules.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

mod support;

use crunk_rules::rules::{tw001::Tw001, tw003::Tw003, tw004::Tw004, tw005::Tw005};

fn tsx(class: &str) -> String {
    format!("export const A = () => <div className=\"{class}\" />;")
}

// frob:tests crates/crunk-rules/src/rules/tw001.rs::Tw001
#[test]
fn an_off_scale_arbitrary_length_fires_tw001() {
    let host = support::project("src/a.tsx", &tsx("p-[13px]"), None);
    let found = support::run::<Tw001>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].message.contains("p-[13px]"),
        "{}",
        found[0].message
    );
}

// frob:tests crates/crunk-rules/src/rules/tw001.rs::Tw001
#[test]
fn an_on_scale_arbitrary_length_is_clean_for_tw001_and_fires_tw003() {
    let host = support::project("src/a.tsx", &tsx("p-[16px]"), None);
    assert!(support::run::<Tw001>(&host).is_empty());
    assert_eq!(support::run::<Tw003>(&host).len(), 1);
}

// frob:tests crates/crunk-rules/src/rules/tw004.rs::Tw004
#[test]
fn a_hard_coded_arbitrary_property_fires_tw004() {
    let host = support::project("src/a.tsx", &tsx("[width:13px]"), None);
    assert_eq!(support::run::<Tw004>(&host).len(), 1);
}

// frob:tests crates/crunk-rules/src/rules/tw005.rs::Tw005
#[test]
fn a_runtime_built_class_fires_tw005() {
    let src = "export const A = (p: { n: string }) => <div className={`p-${p.n}`} />;";
    let host = support::project("src/a.tsx", src, None);
    assert_eq!(support::run::<Tw005>(&host).len(), 1);
}
