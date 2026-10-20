//! The rule coverage check over synthetic workspaces.

// frob:ticket 01M47QTTKVRY3C52CXZBGB8V55

use std::fs;
use std::path::Path;

use gob_mdtest::coverage::{
    ALLOWLIST_PATH, Allowlist, CaseKind, CoverageRule, Gap, analyze, scan_corpus,
};
use gob_rules::{Needs, Polarity};

const PAIR: &str = "<!-- mdtest: rule=ZZZ001 -->\n# ZZZ001\n\n```rust expect=fire\nfn a() {}\n```\n\n```rust expect=clean\nfn b() {}\n```\n";
const UNRESOLVED: &str = "\n```rust expect=unresolved reason=fidelity\nfn c() {}\n```\n";
const ISLAND_FIRE: &str = "\n```rust expect=fire cell=island\nfn e() {}\n```\n";
const VACUOUS: &str = "\n```rust expect=unresolved reason=vacuous\nfn d() {}\n```\n";

/// A full suite for `ZZZ001`: the pair plus its unresolved case.
fn full() -> String {
    format!("{PAIR}{UNRESOLVED}")
}

fn write(root: &Path, rel: &str, text: &str) {
    let p = root.join(rel);
    fs::create_dir_all(p.parent().unwrap()).unwrap();
    fs::write(p, text).unwrap();
}

fn rule(id: &str) -> CoverageRule {
    CoverageRule::new(id)
}

fn gap(rule: &str, ticket: &str) -> Allowlist {
    gap_kind(rule, CaseKind::Fire, ticket)
}

fn gap_kind(rule: &str, kind: CaseKind, ticket: &str) -> Allowlist {
    Allowlist {
        gap: vec![Gap {
            product: "frob".into(),
            rule: rule.into(),
            kind,
            ticket: ticket.into(),
        }],
        matrix_gap: Vec::new(),
    }
}

// frob:tests crates/gob-mdtest/src/coverage.rs::analyze
#[test]
fn pair_covers_and_removing_it_fails_naming_the_rule() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "crates/x/tests/mdtest/zzz001.md", &full());
    let rules = [rule("ZZZ001")];
    let ok = analyze(
        "frob",
        &rules,
        &scan_corpus(dir.path()),
        &Allowlist::default(),
    );
    assert!(ok.passed(), "{}", ok.render());

    fs::remove_file(dir.path().join("crates/x/tests/mdtest/zzz001.md")).unwrap();
    let bad = analyze(
        "frob",
        &rules,
        &scan_corpus(dir.path()),
        &Allowlist::default(),
    );
    assert!(!bad.passed());
    assert!(bad.render().contains("ZZZ001"), "{}", bad.render());
}

#[test]
fn fire_without_clean_is_not_coverage() {
    let dir = tempfile::tempdir().unwrap();
    let fire_only = PAIR.replace("expect=clean", "expect=fire");
    write(dir.path(), "crates/x/tests/mdtest/zzz001.md", &fire_only);
    let r = analyze(
        "frob",
        &[rule("ZZZ001")],
        &scan_corpus(dir.path()),
        &Allowlist::default(),
    );
    assert_eq!(r.uncovered.len(), 2);
    assert!(r.render().contains("lacks clean"));
}

#[test]
fn fixture_needs_its_snapshot() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "crates/x/resources/test/fixtures/ZZZ/ZZZ001.rs",
        "fn a() {}\n",
    );
    let rules = [rule("ZZZ001")];
    let no_snap = analyze(
        "frob",
        &rules,
        &scan_corpus(dir.path()),
        &Allowlist::default(),
    );
    assert!(!no_snap.passed());
    write(
        dir.path(),
        "crates/x/resources/test/fixtures/ZZZ/ZZZ001.snap",
        "snap\n",
    );
    write(
        dir.path(),
        "crates/x/tests/mdtest/zzz001.md",
        &format!("<!-- mdtest: rule=ZZZ001 -->\n# ZZZ001\n{UNRESOLVED}"),
    );
    let ok = analyze(
        "frob",
        &rules,
        &scan_corpus(dir.path()),
        &Allowlist::default(),
    );
    assert!(ok.passed(), "{}", ok.render());
}

#[test]
fn allowlist_hides_a_gap_and_only_shrinks() {
    let dir = tempfile::tempdir().unwrap();
    let rules = [rule("ZZZ001")];
    let mut allowed = gap("ZZZ001", "~ABCDEFG");
    for kind in [CaseKind::Clean, CaseKind::Unresolved] {
        allowed.gap.push(Gap {
            kind,
            ..allowed.gap[0].clone()
        });
    }
    let ok = analyze("frob", &rules, &scan_corpus(dir.path()), &allowed);
    assert!(ok.passed(), "{}", ok.render());

    write(dir.path(), "crates/x/tests/mdtest/zzz001.md", &full());
    let stale = analyze("frob", &rules, &scan_corpus(dir.path()), &allowed);
    assert_eq!(
        stale.stale,
        ["ZZZ001 [fire]", "ZZZ001 [clean]", "ZZZ001 [unresolved]"]
    );

    let unknown = analyze("frob", &[], &scan_corpus(dir.path()), &allowed);
    assert_eq!(unknown.unknown.len(), 3);
}

#[test]
fn allowlist_entry_needs_a_ticket_handle() {
    let dir = tempfile::tempdir().unwrap();
    let rules = [rule("ZZZ001")];
    for bad in ["", "ABCDEFG", "~abcdefg", "~ABC"] {
        let r = analyze(
            "frob",
            &rules,
            &scan_corpus(dir.path()),
            &gap("ZZZ001", bad),
        );
        assert_eq!(r.bad_ticket, ["ZZZ001 [fire]"], "ticket {bad:?}");
    }
}

#[test]
fn allowlist_file_rejects_a_missing_ticket() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "a.toml",
        "[[gap]]\nproduct = \"frob\"\nrule = \"ZZZ001\"\nkind = \"fire\"\n",
    );
    assert!(Allowlist::load(&dir.path().join("a.toml")).is_err());
}

#[test]
fn the_checked_in_allowlist_parses() {
    let root = gob_mdtest::manifest_dir(env!("CARGO_MANIFEST_DIR"));
    let list = Allowlist::load(&root.join("../..").join(ALLOWLIST_PATH)).unwrap();
    assert!(list.gap.iter().all(|g| !g.ticket.is_empty()));
}

// frob:tests crates/gob-mdtest/src/coverage.rs::analyze
#[test]
fn alias_rule_is_exempt_without_its_own_corpus() {
    let dir = tempfile::tempdir().unwrap();
    let r = analyze(
        "frob",
        &[rule("COV003")],
        &scan_corpus(dir.path()),
        &Allowlist::default(),
    );
    assert!(r.passed(), "{}", r.render());
    let stale = analyze(
        "frob",
        &[rule("COV003")],
        &scan_corpus(dir.path()),
        &gap("COV003", "~ABCDEFG"),
    );
    assert_eq!(stale.stale, vec!["COV003 [fire]".to_owned()]);
}

fn kinds(r: &gob_mdtest::coverage::CoverageReport) -> Vec<CaseKind> {
    r.uncovered.iter().map(|m| m.kind).collect()
}

// frob:tests crates/gob-mdtest/src/coverage.rs::analyze
#[test]
fn removing_the_unresolved_case_fails_naming_the_rule_and_polarity() {
    let dir = tempfile::tempdir().unwrap();
    let mut cov = rule("COV001");
    cov.polarity = Polarity::Pminus;
    let suite = |extra: &str| format!("{}{extra}", PAIR.replace("ZZZ001", "COV001"));
    write(
        dir.path(),
        "crates/x/tests/mdtest/cov001.md",
        &suite(UNRESOLVED),
    );
    let ok = analyze(
        "frob",
        &[cov.clone()],
        &scan_corpus(dir.path()),
        &Allowlist::default(),
    );
    assert!(ok.passed(), "{}", ok.render());

    write(dir.path(), "crates/x/tests/mdtest/cov001.md", &suite(""));
    let bad = analyze(
        "frob",
        &[cov],
        &scan_corpus(dir.path()),
        &Allowlist::default(),
    );
    assert_eq!(kinds(&bad), [CaseKind::Unresolved]);
    assert!(
        bad.render().contains("COV001 P- unresolved"),
        "{}",
        bad.render()
    );
}

// frob:tests crates/gob-mdtest/src/coverage.rs::analyze
#[test]
fn every_polarity_names_its_own_unresolved_shape() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "crates/x/tests/mdtest/zzz001.md", PAIR);
    for (p, sym) in [
        (Polarity::Pplus, "P+"),
        (Polarity::Pminus, "P-"),
        (Polarity::P0, "P0"),
        (Polarity::Pn, "Pn"),
        (Polarity::Pc, "Pc"),
    ] {
        let mut r = rule("ZZZ001");
        r.polarity = p;
        let rep = analyze(
            "frob",
            &[r],
            &scan_corpus(dir.path()),
            &Allowlist::default(),
        );
        assert!(
            rep.render().contains(&format!("ZZZ001 {sym} unresolved")),
            "{}",
            rep.render()
        );
    }
}

// frob:tests crates/gob-mdtest/src/coverage.rs::analyze
#[test]
fn lexical_rule_requires_a_fire_inside_an_opaque_region() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "crates/x/tests/mdtest/zzz001.md", &full());
    let mut r = rule("ZZZ001");
    // A structural rule is not asked for the case.
    let plain = analyze(
        "frob",
        &[r.clone()],
        &scan_corpus(dir.path()),
        &Allowlist::default(),
    );
    assert!(plain.passed(), "{}", plain.render());

    r.needs = Needs::Lexical;
    let bad = analyze(
        "frob",
        &[r.clone()],
        &scan_corpus(dir.path()),
        &Allowlist::default(),
    );
    assert_eq!(kinds(&bad), [CaseKind::OpaqueFire]);
    assert!(bad.render().contains("ZZZ001 lexical opaque_fire"));

    // An allowlisted gap is tolerated; a present case makes the entry stale.
    let listed = analyze(
        "frob",
        &[r.clone()],
        &scan_corpus(dir.path()),
        &gap_kind("ZZZ001", CaseKind::OpaqueFire, "~ABCDEFG"),
    );
    assert!(listed.passed(), "{}", listed.render());

    write(
        dir.path(),
        "crates/x/tests/mdtest/zzz001.md",
        &format!("{}{ISLAND_FIRE}", full()),
    );
    let ok = analyze(
        "frob",
        &[r.clone()],
        &scan_corpus(dir.path()),
        &Allowlist::default(),
    );
    assert!(ok.passed(), "{}", ok.render());
    let stale = analyze(
        "frob",
        &[r],
        &scan_corpus(dir.path()),
        &gap_kind("ZZZ001", CaseKind::OpaqueFire, "~ABCDEFG"),
    );
    assert_eq!(stale.stale, ["ZZZ001 [opaque_fire]"]);
}

// frob:tests crates/gob-mdtest/src/coverage.rs::analyze
#[test]
fn must_measure_requires_a_vacuous_case() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "crates/x/tests/mdtest/zzz001.md", &full());
    let mut r = rule("ZZZ001");
    r.must_measure = true;
    let bad = analyze(
        "frob",
        &[r.clone()],
        &scan_corpus(dir.path()),
        &Allowlist::default(),
    );
    assert_eq!(kinds(&bad), [CaseKind::Vacuous]);
    assert!(bad.render().contains("ZZZ001 must_measure vacuous"));

    write(
        dir.path(),
        "crates/x/tests/mdtest/zzz001.md",
        &format!("{}{VACUOUS}", full()),
    );
    let ok = analyze(
        "frob",
        &[r],
        &scan_corpus(dir.path()),
        &Allowlist::default(),
    );
    assert!(ok.passed(), "{}", ok.render());
}

// frob:tests crates/gob-mdtest/src/coverage.rs::analyze
#[test]
fn fire_and_clean_in_different_files_do_not_pair() {
    let dir = tempfile::tempdir().unwrap();
    let fire = PAIR.replace("expect=clean", "expect=fire");
    let clean = PAIR.replace("expect=fire", "expect=clean");
    write(
        dir.path(),
        "crates/x/tests/mdtest/a.md",
        &format!("{fire}{UNRESOLVED}"),
    );
    write(dir.path(), "crates/x/tests/mdtest/b.md", &clean);
    let r = analyze(
        "frob",
        &[rule("ZZZ001")],
        &scan_corpus(dir.path()),
        &Allowlist::default(),
    );
    assert_eq!(kinds(&r), [CaseKind::Clean]);
    assert!(r.render().contains("different suite files"));
}

// frob:tests crates/gob-mdtest/src/coverage.rs::analyze
#[test]
fn allowlist_is_per_case_kind_and_shrink_only() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "crates/x/tests/mdtest/zzz001.md", PAIR);
    let rules = [rule("ZZZ001")];
    let corpus = scan_corpus(dir.path());
    let ok = analyze(
        "frob",
        &rules,
        &corpus,
        &gap_kind("ZZZ001", CaseKind::Unresolved, "~ABCDEFG"),
    );
    assert!(ok.passed(), "{}", ok.render());

    let stale = analyze(
        "frob",
        &rules,
        &corpus,
        &gap_kind("ZZZ001", CaseKind::Fire, "~ABCDEFG"),
    );
    assert_eq!(stale.stale, ["ZZZ001 [fire]"]);

    let unrequired = analyze(
        "frob",
        &rules,
        &corpus,
        &gap_kind("ZZZ001", CaseKind::Vacuous, "~ABCDEFG"),
    );
    assert_eq!(unrequired.unknown, ["ZZZ001 [vacuous]"]);
}

#[test]
fn the_checked_in_allowlist_entries_carry_kind_and_ticket() {
    let root = gob_mdtest::manifest_dir(env!("CARGO_MANIFEST_DIR"));
    let list = Allowlist::load(&root.join("../..").join(ALLOWLIST_PATH)).unwrap();
    assert!(list.gap.iter().all(|g| g.ticket.starts_with('~')));
}
