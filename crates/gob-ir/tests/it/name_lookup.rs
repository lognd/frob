//! The shared name-lookup rule: one table, one literal rule, for every language.

// frob:ticket 01M6422ZFEPZJYJQDDM6CV37RW

use gob_ir::const_value::{ConstValue, Fragment};
use gob_ir::name_lookup::{
    NameGap, Resolved, concat, literal, mentions_lookup, primitive, resolve_name,
};

// frob:tests crates/gob-ir/src/name_lookup.rs::resolve_name
#[test]
fn only_a_single_string_literal_resolves() {
    assert_eq!(resolve_name(&literal("os")), Resolved::Literal("os".into()));
    assert_eq!(
        resolve_name(&ConstValue::Unknown),
        Resolved::Unresolved(NameGap::NotConstant)
    );
    assert_eq!(
        resolve_name(&concat(
            &literal("a"),
            &ConstValue::Fragments(vec![Fragment::Unknown])
        )),
        Resolved::Unresolved(NameGap::Partial)
    );
}

// frob:tests crates/gob-ir/src/name_lookup.rs::primitive
#[test]
fn every_language_family_has_its_primitives() {
    for (lang, callee) in [
        ("python", "getattr"),
        ("python", "__import__"),
        ("python", "importlib.import_module"),
        ("javascript", "require"),
        ("tsx", "import"),
        ("csharp", "Type.GetType"),
    ] {
        assert!(primitive(lang, callee).is_some(), "{lang} {callee}");
    }
    assert!(primitive("rust", "getattr").is_none());
}

// frob:tests crates/gob-ir/src/name_lookup.rs::mentions_lookup
#[test]
fn the_prefilter_bypass_follows_the_table() {
    assert!(mentions_lookup("python", "sys.modules[n]"));
    assert!(!mentions_lookup("python", "print(1)"));
}
