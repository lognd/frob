#![allow(
    clippy::disallowed_methods,
    reason = "a test reads the pack tree on disk, not a walked snapshot"
)]
//! The grimble-websec pack: one rule per family, WEBSEC under SEC, GRL011 without examples, lock digest.

// frob:ticket 01M43AWPD2DYMS2CVTJRD56D5R

use std::path::{Path, PathBuf};

use grimble_check::websec_pack::{self as pack, PackBuildError};

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../packs/grimble-websec")
}

fn disk(p: &Path) -> Option<Vec<u8>> {
    std::fs::read(p).ok()
}

// frob:tests catalog
#[test]
fn catalog_has_one_rule_per_family_with_websec_under_sec() {
    let rows = pack::catalog().unwrap();
    let got: Vec<(&str, &str, &str)> = rows
        .iter()
        .map(|r| (r.family.as_str(), r.namespace.as_str(), r.rule.as_str()))
        .collect();
    assert_eq!(
        got,
        [
            ("WEBSEC", "SEC", "SEC101"),
            ("SQL", "SQL", "SQL101"),
            ("COMPLY", "COMPLY", "COMPLY101"),
            ("ROUTE", "ROUTE", "ROUTE101"),
            ("ROUTE", "ROUTE", "ROUTE102"),
            ("ROUTE", "ROUTE", "ROUTE103"),
            ("ROUTE", "ROUTE", "ROUTE104"),
            ("PII", "PII", "PII101"),
            ("PII", "PII", "PII102"),
            ("PII", "PII", "PII103"),
            ("WEBPERF", "WEBPERF", "WEBPERF201"),
            ("WEBPERF", "WEBPERF", "WEBPERF202"),
            ("WEBPERF", "WEBPERF", "WEBPERF203"),
            ("WEBPERF", "WEBPERF", "WEBPERF204")
        ]
    );
    assert!(rows.iter().all(|r| r.pack == "grimble-websec"));
}

// frob:tests manifest
#[test]
fn manifest_registers_sec_and_pii_rows() {
    let m = pack::manifest().unwrap();
    for fam in ["SEC", "PII", "SQL", "COMPLY", "ROUTE", "WEBPERF"] {
        assert!(m.pack.families.iter().any(|f| f == fam), "{fam}");
    }
}

// frob:tests compile_rule
#[test]
fn a_rule_without_examples_does_not_compile() {
    let src = "rule SQL999 \"x\" {\n  lang python\n  find c: call\n  report c \"x\"\n  explain \"\"\"\n    x\n    ## Remedy\n    y\n  \"\"\"\n}\n";
    let err = pack::compile_rule("rules/SQL999.grl", src).unwrap_err();
    assert!(matches!(err, PackBuildError::Rule { .. }), "{err}");
}

// frob:tests locked
#[test]
fn the_lock_digest_matches_the_pack_tree() {
    let lock = pack::locked(&root(), disk).unwrap();
    let digest = gob_packs::tree_digest(&root(), &[]).unwrap();
    assert_eq!(lock.name, "grimble-websec");
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
        assert_eq!(t.examples.len(), 3, "{file}");
        assert!(src.contains("## Remedy"), "{file}");
    }
}

// frob:tests compile_rule
#[test]
fn route_slice_rules_fire_on_their_example_and_teach_a_remedy() {
    for id in ["ROUTE102", "ROUTE103", "ROUTE104"] {
        let (file, src) = pack::RULES
            .iter()
            .find(|(f, _)| f.ends_with(&format!("{id}.grl")))
            .unwrap();
        let t = gob_plan::verbs::test::test_file(file, src);
        assert!(t.passed(), "{id}: {:?} {:?}", t.diagnostics, t.examples);
        assert!(src.contains("## Remedy"), "{id}");
    }
}

// frob:tests compile_rule
#[test]
fn route_rules_are_not_applicable_outside_python() {
    // No adapter for other languages: the markdown example proves NotApplicable, never clean.
    for id in ["ROUTE102", "ROUTE103", "ROUTE104"] {
        let (_, src) = pack::RULES
            .iter()
            .find(|(f, _)| f.ends_with(&format!("{id}.grl")))
            .unwrap();
        assert!(src.contains("example notapplicable markdown"), "{id}");
    }
}

// frob:tests compile_rule
#[test]
fn pii_slice_rules_fire_on_their_example_and_teach_a_remedy() {
    for id in ["PII101", "PII102", "PII103"] {
        let (file, src) = pack::RULES
            .iter()
            .find(|(f, _)| f.ends_with(&format!("{id}.grl")))
            .unwrap();
        let t = gob_plan::verbs::test::test_file(file, src);
        assert!(t.passed(), "{id}: {:?} {:?}", t.diagnostics, t.examples);
        assert!(src.contains("## Remedy"), "{id}");
    }
}

// frob:tests compile_rule
#[test]
fn pii_rules_are_not_applicable_outside_python() {
    // No adapter for other languages: the markdown example proves NotApplicable, never clean.
    for id in ["PII101", "PII102", "PII103"] {
        let (_, src) = pack::RULES
            .iter()
            .find(|(f, _)| f.ends_with(&format!("{id}.grl")))
            .unwrap();
        assert!(src.contains("example notapplicable markdown"), "{id}");
    }
}

// frob:tests grimble_check.websec_pack.compile_rule
#[test]
fn webperf_server_rules_fire_on_their_example_and_teach_a_remedy() {
    for id in ["WEBPERF202", "WEBPERF203", "WEBPERF204"] {
        let (file, src) = pack::RULES
            .iter()
            .find(|(f, _)| f.ends_with(&format!("{id}.grl")))
            .unwrap();
        let t = gob_plan::verbs::test::test_file(file, src);
        assert!(t.passed(), "{id}: {:?} {:?}", t.diagnostics, t.examples);
        assert!(src.contains("example fire python"), "{id}");
        assert!(src.contains("## Remedy"), "{id}");
    }
}

// frob:tests grimble_check.websec_pack.compile_rule
#[test]
fn webperf_server_rules_are_not_applicable_outside_python() {
    // No adapter for other languages: the markdown example proves NotApplicable, never clean.
    for id in ["WEBPERF202", "WEBPERF203", "WEBPERF204"] {
        let (_, src) = pack::RULES
            .iter()
            .find(|(f, _)| f.ends_with(&format!("{id}.grl")))
            .unwrap();
        assert!(src.contains("example notapplicable markdown"), "{id}");
    }
}
