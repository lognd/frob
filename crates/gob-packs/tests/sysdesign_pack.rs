#![allow(
    clippy::disallowed_methods,
    reason = "a test reads the pack tree on disk, not a walked snapshot"
)]
//! The grimble-sysdesign pack: one rule per family, GRL011 without examples, lock digest.

// frob:ticket 01M43AYJ2RMDD8DGZ5Q060142M

use std::path::{Path, PathBuf};

use gob_packs::sysdesign::{self as pack, PackBuildError};

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../packs/grimble-sysdesign")
}

fn disk(p: &Path) -> Option<Vec<u8>> {
    std::fs::read(p).ok()
}

// frob:tests catalog
#[test]
fn catalog_has_one_rule_per_family() {
    let rows = pack::catalog().unwrap();
    let got: Vec<(&str, &str)> = rows
        .iter()
        .map(|r| (r.family.as_str(), r.rule.as_str()))
        .collect();
    assert_eq!(
        got,
        [
            ("STORE", "STORE101"),
            ("SYSDESIGN", "SYSDESIGN101"),
            ("GRAMMAR", "GRAMMAR101")
        ]
    );
    assert!(rows.iter().all(|r| r.pack == "grimble-sysdesign"));
}

// frob:tests manifest
#[test]
fn manifest_registers_the_three_families() {
    let m = pack::manifest().unwrap();
    for fam in ["STORE", "SYSDESIGN", "GRAMMAR"] {
        assert!(m.pack.families.iter().any(|f| f == fam), "{fam}");
    }
}

// frob:tests compile_rule
#[test]
fn a_rule_without_examples_does_not_compile() {
    let src = "rule STORE999 \"x\" {\n  lang python\n  find c: call\n  report c \"x\"\n  explain \"\"\"\n    x\n    ## Remedy\n    y\n  \"\"\"\n}\n";
    let err = pack::compile_rule("rules/STORE999.grl", src).unwrap_err();
    assert!(matches!(err, PackBuildError::Rule { .. }), "{err}");
}

// frob:tests locked
#[test]
fn the_lock_digest_matches_the_pack_tree() {
    let lock = pack::locked(&root(), disk).unwrap();
    let digest = gob_packs::tree_digest(&root(), &[]).unwrap();
    assert_eq!(lock.name, "grimble-sysdesign");
    assert_eq!(lock.tree, format!("blake3:{}", gob_packs::to_hex(&digest)));
}

// frob:tests verify_tree
#[test]
fn a_drifted_tree_is_refused() {
    let dir = tempfile::tempdir().unwrap();
    std::fs::write(dir.path().join("pack.toml"), "x").unwrap();
    assert!(matches!(
        pack::verify_tree(dir.path(), disk),
        Err(PackBuildError::Drift(_))
    ));
}

// frob:tests compile_rule
#[test]
fn every_rule_passes_its_examples() {
    for (file, src) in pack::RULES {
        let t = gob_plan::verbs::test::test_file(file, src);
        assert!(t.passed(), "{file}: {:?} {:?}", t.diagnostics, t.examples);
        assert!(t.examples.len() >= 2, "{file}");
        assert!(src.contains("## Remedy"), "{file}");
    }
}
