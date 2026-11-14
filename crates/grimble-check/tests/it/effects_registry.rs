//! The effects capability tables agree with the adapters' registry vocabulary.

// frob:ticket 01M642307T98S89GQ4APKW7X2J
// frob:ticket 01M5M05N51MZ3RYXFYJT28A73Q

use gob_ir::effects_for;
use std::collections::BTreeSet;

/// Every first segment and bare name the registry holds for `lang` over all atoms.
fn registered_heads(lang: &str) -> BTreeSet<&'static str> {
    let sep = if lang == "rust" { "::" } else { "." };
    let mut out = BTreeSet::new();
    if let gob_ir::Answer::Exact(names) = gob_ir::registry::callee_vocab(lang, "coh002.qualifiers")
    {
        out.extend(names);
    }
    for atom in gob_ir::registry::atoms() {
        for (_, name) in gob_ir::registry::callee_names(lang, atom.name) {
            let bare = name.trim_end_matches('*').trim_end_matches(['.', ':']);
            out.insert(bare.split(sep).next().unwrap_or(bare));
        }
    }
    out
}

// frob:tests crates/gob-ir/src/effects_capability.rs::effects_for
#[test]
fn every_effect_qualifier_and_builtin_is_in_the_capability_registry() {
    for lang in ["rust", "python", "typescript"] {
        let heads = registered_heads(lang);
        let cap = effects_for(lang).expect("language has a capability");
        assert!(
            !cap.effect_qualifiers.is_empty(),
            "{lang} has no qualifiers"
        );
        for name in cap.effect_qualifiers.iter().chain(cap.effect_builtins) {
            assert!(
                heads.contains(name),
                "{lang}: {name} is not a registry name"
            );
        }
    }
    let ts = effects_for("typescript").unwrap();
    assert!(ts.effect_builtins.contains(&"fetch"));
    assert!(ts.effect_qualifiers.contains(&"fs"));
}

// frob:tests crates/gob-ir/src/effects_capability.rs::effects_for
#[test]
fn methods_trivial_tables_and_persistence_qualifiers_come_from_the_registry() {
    for lang in ["rust", "python", "typescript"] {
        let cap = effects_for(lang).expect("language has a capability");
        assert!(cap.effect_methods.contains(&"write_all"), "{lang} methods");
        assert!(
            cap.trivial_names.contains(&"assert"),
            "{lang} trivial names"
        );
        assert!(
            !cap.trivial_qualifiers.is_empty(),
            "{lang} trivial qualifiers"
        );
    }
    assert!(
        effects_for("python")
            .unwrap()
            .effect_qualifiers
            .contains(&"sqlite3")
    );
    assert!(
        effects_for("typescript")
            .unwrap()
            .effect_qualifiers
            .contains(&"localStorage")
    );
    assert!(
        effects_for("typescript")
            .unwrap()
            .effect_qualifiers
            .contains(&"axios")
    );
}
