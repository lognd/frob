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
fn catalog_has_one_row_per_rule() {
    let rows = pack::catalog().unwrap();
    let got: Vec<(&str, &str)> = rows
        .iter()
        .map(|r| (r.family.as_str(), r.rule.as_str()))
        .collect();
    assert_eq!(
        got,
        [
            ("STORE", "STORE101"),
            ("STORE", "STORE102"),
            ("STORE", "STORE103"),
            ("STORE", "STORE104"),
            ("STORE", "STORE105"),
            ("SYSDESIGN", "SYSDESIGN101"),
            ("SYSDESIGN", "SYSDESIGN102"),
            ("SYSDESIGN", "SYSDESIGN103"),
            ("SYSDESIGN", "SYSDESIGN104"),
            ("GRAMMAR", "GRAMMAR101"),
            ("GRAMMAR", "GRAMMAR102"),
            ("GRAMMAR", "GRAMMAR103"),
            ("GRAMMAR", "GRAMMAR104")
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
fn store_rules_have_fire_clean_and_not_applicable_examples() {
    let store: Vec<_> = pack::RULES
        .iter()
        .filter(|(f, _)| f.contains("store/"))
        .collect();
    assert_eq!(store.len(), 4);
    for (file, src) in store {
        let t = gob_plan::verbs::test::test_file(file, src);
        assert!(t.passed(), "{file}: {:?} {:?}", t.diagnostics, t.examples);
        assert_eq!(t.examples.len(), 3, "{file}");
        assert!(src.contains("example notapplicable"), "{file}");
        assert!(src.contains("severity error"), "{file}");
    }
}

// frob:tests compile_rule
#[test]
fn store_rules_are_registered_in_the_manifest_globs() {
    let m = pack::manifest().unwrap();
    assert!(m.provides.rules.iter().any(|g| g == "rules/store/*.grl"));
}

// frob:tests compile_rule
#[test]
fn sysdesign_rules_are_registered_in_the_manifest_globs() {
    let m = pack::manifest().unwrap();
    assert!(
        m.provides
            .rules
            .iter()
            .any(|g| g == "rules/sysdesign/*.grl")
    );
}
