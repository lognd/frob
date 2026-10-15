//! The crunk-web pack: four families with one rule each, GRL011 without examples, lock digest.

// frob:ticket 01M43AVHX91K72WYKYFX5W2SPP

use std::path::{Path, PathBuf};

use crunk_check::packs::{self, PacksSwitch, PackBuildError};

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../packs/crunk-web")
}

// frob:tests catalog
#[test]
fn catalog_lists_four_families_with_one_rule_each_when_on() {
    let rows = packs::catalog(PacksSwitch { crunk_web: true }).unwrap();
    let got: Vec<(&str, &str)> = rows.iter().map(|r| (r.family.as_str(), r.rule.as_str())).collect();
    assert_eq!(
        got,
        [("A11Y", "A11Y101"), ("LAUNCH", "LAUNCH101"), ("SEO", "SEO101"), ("WEBPERF", "WEBPERF101")]
    );
    assert!(rows.iter().all(|r| r.pack == "crunk-web"));
}

// frob:tests catalog
#[test]
fn catalog_is_empty_when_the_switch_is_off() {
    assert!(packs::catalog(PacksSwitch::default()).unwrap().is_empty());
}

// frob:tests compile_rule
#[test]
fn a_rule_without_examples_does_not_compile() {
    let src = "rule A11Y999 \"x\" {\n  lang html\n  find e: element\n  report e \"x\"\n  explain \"\"\"\n    x\n    ## Remedy\n    y\n  \"\"\"\n}\n";
    let err = packs::compile_rule("rules/A11Y999.grl", src).unwrap_err();
    assert!(matches!(err, PackBuildError::Rule { .. }), "{err}");
}

// frob:tests locked
#[test]
fn the_lock_digest_matches_the_pack_tree() {
    let lock = packs::locked(&root()).unwrap();
    let digest = gob_packs::tree_digest(&root(), &[]).unwrap();
    assert_eq!(lock.name, "crunk-web");
    assert_eq!(lock.tree, format!("blake3:{}", gob_packs::to_hex(&digest)));
}

// frob:tests verify_tree
#[test]
fn a_drifted_tree_is_refused() {
    let dir = tempfile::tempdir().unwrap();
    std::fs::write(dir.path().join("pack.toml"), "x").unwrap();
    assert!(matches!(packs::verify_tree(dir.path()), Err(PackBuildError::Drift(_))));
}
