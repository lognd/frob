//! The std pack: builtin entry, frozen lock digest, embedded plans match the GRL, PACK004 on std families.

// frob:ticket 01M3ZX7FYE5D1N2SY01VNVVACK

use gob_packs::std_pack::{self, PackSource};
use gob_packs::{Manifest, PackCode};

const GRL: &str = include_str!("../../../packs/std/rules/TODO001.grl");

// frob:tests entry
#[test]
fn std_lists_as_builtin_with_a_digest_and_every_tier0_family_as_an_exception() {
    let e = std_pack::entry().unwrap();
    assert_eq!(e.name, "std");
    assert_eq!(e.source, PackSource::Builtin);
    assert!(e.digest.starts_with("blake3:") && e.digest.len() == 7 + 64);
    assert_eq!(e.version, env!("CARGO_PKG_VERSION"));
    assert!(!e.known_exceptions.is_empty());
    for f in &e.known_exceptions {
        assert!(e.families.contains(f), "{f} must be a std family");
    }
    assert!(!e.known_exceptions.contains(&"TODO".to_owned()));
}

// frob:tests locked
#[test]
fn the_lock_entry_is_frozen_to_the_binary_and_matches_the_entry() {
    let a = std_pack::locked().unwrap();
    let b = std_pack::locked().unwrap();
    assert_eq!(a, b);
    assert_eq!(a.name, "std");
    assert_eq!(a.version, env!("CARGO_PKG_VERSION"));
    assert_eq!(a.tree, std_pack::entry().unwrap().digest);
    assert!(a.items.contains_key("plan:TODO001"));
}

// frob:tests plans
#[test]
fn embedded_plans_are_exactly_what_the_grl_source_lowers_to() {
    let plans = std_pack::plans().unwrap();
    let lowered = gob_plan::lower::lower_source("rules/TODO001.grl", GRL).unwrap();
    assert_eq!(plans.len(), lowered.len());
    for (a, b) in plans.iter().zip(&lowered) {
        assert_eq!(a.to_bytes(), b.to_bytes());
    }
}

// frob:tests check_plugin
#[test]
fn a_plugin_declaring_cap_or_the_name_std_is_pack004() {
    let cap = Manifest::parse(
        "p/pack.toml",
        "[pack]\nname = \"evil\"\nversion = \"1.0.0\"\nfamilies = [\"CAP\"]\n",
    )
    .unwrap();
    let err = std_pack::check_plugin("p/pack.toml", &cap).unwrap_err();
    assert_eq!(err.code(), PackCode::Pack004);
    let named = Manifest::parse(
        "q/pack.toml",
        "[pack]\nname = \"std\"\nversion = \"1.0.0\"\n",
    )
    .unwrap();
    assert_eq!(
        std_pack::check_plugin("q/pack.toml", &named)
            .unwrap_err()
            .code(),
        PackCode::Pack004
    );
    let ok = Manifest::parse(
        "r/pack.toml",
        "[pack]\nname = \"fine\"\nversion = \"1.0.0\"\nfamilies = [\"ZZZ\"]\n",
    )
    .unwrap();
    assert!(std_pack::check_plugin("r/pack.toml", &ok).is_ok());
}
