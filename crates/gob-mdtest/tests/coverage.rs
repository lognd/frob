//! The rule coverage check over synthetic workspaces.

// frob:ticket 01M47QTTKVRY3C52CXZBGB8V55

use std::fs;
use std::path::Path;

use gob_mdtest::coverage::{ALLOWLIST_PATH, Allowlist, CoverageRule, Gap, analyze, scan_corpus};

const PAIR: &str = "<!-- mdtest: rule=ZZZ001 -->\n# ZZZ001\n\n```rust expect=fire\nfn a() {}\n```\n\n```rust expect=clean\nfn b() {}\n```\n";

fn write(root: &Path, rel: &str, text: &str) {
    let p = root.join(rel);
    fs::create_dir_all(p.parent().unwrap()).unwrap();
    fs::write(p, text).unwrap();
}

fn rule(id: &str) -> CoverageRule {
    CoverageRule {
        id: id.to_owned(),
        family: id.trim_end_matches(char::is_numeric).to_owned(),
    }
}

fn gap(rule: &str, ticket: &str) -> Allowlist {
    Allowlist {
        gap: vec![Gap {
            product: "frob".into(),
            rule: rule.into(),
            ticket: ticket.into(),
        }],
    }
}

// frob:tests crates/gob-mdtest/src/coverage.rs::analyze
#[test]
fn pair_covers_and_removing_it_fails_naming_the_rule() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "crates/x/tests/mdtest/zzz001.md", PAIR);
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
    assert_eq!(r.uncovered.len(), 1);
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
    let allowed = gap("ZZZ001", "~ABCDEFG");
    let ok = analyze("frob", &rules, &scan_corpus(dir.path()), &allowed);
    assert!(ok.passed(), "{}", ok.render());

    write(dir.path(), "crates/x/tests/mdtest/zzz001.md", PAIR);
    let stale = analyze("frob", &rules, &scan_corpus(dir.path()), &allowed);
    assert_eq!(stale.stale, ["ZZZ001"]);

    let unknown = analyze("frob", &[], &scan_corpus(dir.path()), &allowed);
    assert_eq!(unknown.unknown, ["ZZZ001"]);
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
        assert_eq!(r.bad_ticket, ["ZZZ001"], "ticket {bad:?}");
    }
}

#[test]
fn allowlist_file_rejects_a_missing_ticket() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "a.toml",
        "[[gap]]\nproduct = \"frob\"\nrule = \"ZZZ001\"\n",
    );
    assert!(Allowlist::load(&dir.path().join("a.toml")).is_err());
}

#[test]
fn the_checked_in_allowlist_parses() {
    let root = gob_mdtest::manifest_dir(env!("CARGO_MANIFEST_DIR"));
    let list = Allowlist::load(&root.join("../..").join(ALLOWLIST_PATH)).unwrap();
    assert!(list.gap.iter().all(|g| !g.ticket.is_empty()));
}
