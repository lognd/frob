#![allow(
    clippy::disallowed_methods,
    reason = "a test reads the pack tree on disk, not a walked snapshot"
)]
//! The crunk-web pack: four families, three A11Y, SEO and LAUNCH rules, GRL011 without examples, lock digest.

// frob:ticket 01M43AVHX91K72WYKYFX5W2SPP

use std::path::{Path, PathBuf};

use crunk_check::packs::{self, PackBuildError, PacksSwitch};

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../packs/crunk-web")
}

fn disk(p: &Path) -> Option<Vec<u8>> {
    std::fs::read(p).ok()
}

// frob:tests catalog
#[test]
fn catalog_lists_the_pack_rules_when_on() {
    let rows = packs::catalog(PacksSwitch { crunk_web: true }).unwrap();
    let got: Vec<(&str, &str)> = rows
        .iter()
        .map(|r| (r.family.as_str(), r.rule.as_str()))
        .collect();
    assert_eq!(
        got,
        [
            ("A11Y", "A11Y101"),
            ("A11Y", "A11Y102"),
            ("A11Y", "A11Y103"),
            ("LAUNCH", "LAUNCH101"),
            ("LAUNCH", "LAUNCH102"),
            ("LAUNCH", "LAUNCH103"),
            ("LAUNCH", "LAUNCH104"),
            ("SEO", "SEO101"),
            ("SEO", "SEO102"),
            ("SEO", "SEO103"),
            ("WEBPERF", "WEBPERF101")
        ]
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
    let lock = packs::locked(&root(), disk).unwrap();
    let digest = gob_packs::tree_digest(&root(), &[]).unwrap();
    assert_eq!(lock.name, "crunk-web");
    assert_eq!(lock.tree, format!("blake3:{}", gob_packs::to_hex(&digest)));
}

// frob:tests verify_tree
#[test]
fn a_drifted_tree_is_refused() {
    let dir = tempfile::tempdir().unwrap();
    std::fs::write(dir.path().join("pack.toml"), "x").unwrap();
    assert!(matches!(
        packs::verify_tree(dir.path(), disk),
        Err(PackBuildError::Drift(_))
    ));
}

// frob:ticket 01M43AVJ85D28XYZKWSSHGXWRT
// frob:tests compile_rule
#[test]
fn every_a11y_rule_passes_its_examples() {
    let mut ran = 0;
    for (file, src) in packs::RULES.iter().filter(|(f, _)| f.contains("A11Y")) {
        let t = gob_plan::verbs::test::test_file(file, src);
        assert!(t.passed(), "{file}: {:?} {:?}", t.diagnostics, t.examples);
        assert_eq!(t.examples.len(), 3, "{file}");
        ran += 1;
    }
    assert_eq!(ran, 3);
}

// frob:ticket 01M43AVJ85D28XYZKWSSHGXWRT
// frob:tests compile_rule
#[test]
fn a11y_rules_fire_with_teaching_text_on_a_violation() {
    let (file, src) = packs::RULES
        .iter()
        .find(|(f, _)| f.contains("A11Y102"))
        .unwrap();
    assert!(src.contains("lang=\\\"en\\\""));
    assert!(src.contains("## Remedy"));
    assert!(packs::compile_rule(file, src).is_ok());
}

// frob:ticket 01M43AVJJEGJB09WH8QWDSAP5S
// frob:tests compile_rule
#[test]
fn every_seo_rule_passes_its_examples() {
    let mut ran = 0;
    for (file, src) in packs::RULES.iter().filter(|(f, _)| f.contains("SEO")) {
        let t = gob_plan::verbs::test::test_file(file, src);
        assert!(t.passed(), "{file}: {:?} {:?}", t.diagnostics, t.examples);
        assert_eq!(t.examples.len(), 3, "{file}");
        ran += 1;
    }
    assert_eq!(ran, 3);
}

// frob:ticket 01M43AVJJEGJB09WH8QWDSAP5S
// frob:tests compile_rule
#[test]
fn seo_rules_carry_teaching_text_and_a_remedy() {
    for (file, src) in packs::RULES.iter().filter(|(f, _)| f.contains("SEO")) {
        assert!(src.contains("## Remedy"), "{file}");
        assert!(src.contains("example fire"), "{file}");
        assert!(src.contains("example notapplicable"), "{file}");
        assert!(packs::compile_rule(file, src).is_ok(), "{file}");
    }
}

// frob:ticket 01M43AVJWX0T0XSYDX323BQFSY
// frob:tests compile_rule
#[test]
fn every_launch_rule_passes_its_examples() {
    let mut ran = 0;
    for (file, src) in packs::RULES.iter().filter(|(f, _)| f.contains("LAUNCH")) {
        let t = gob_plan::verbs::test::test_file(file, src);
        assert!(t.passed(), "{file}: {:?} {:?}", t.diagnostics, t.examples);
        assert_eq!(t.examples.len(), 3, "{file}");
        ran += 1;
    }
    assert_eq!(ran, 4);
}

// frob:ticket 01M43AVJWX0T0XSYDX323BQFSY
// frob:tests compile_rule
#[test]
fn launch_rules_carry_teaching_text_and_a_remedy() {
    for (file, src) in packs::RULES.iter().filter(|(f, _)| f.contains("LAUNCH")) {
        assert!(src.contains("## Remedy"), "{file}");
        assert!(src.contains("example fire"), "{file}");
        assert!(src.contains("example notapplicable"), "{file}");
        assert!(packs::compile_rule(file, src).is_ok(), "{file}");
    }
}
