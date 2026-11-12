//! The VET rule pages as an mdtest corpus, plus the pass and wiring tests.

// frob:ticket 01M5A63T4BZ3XH842F3RDFJ929

use gob_rules::{Finding, Severity, UnresolvedReason};
use gob_text::FileInterner;
use grimble_vet::{Advisory, Snapshot, VetHost, VetInput, analyze};

/// A base lockfile holding only the workspace member.
const BASE: &str = "version = 4\n\n[[package]]\nname = \"app\"\nversion = \"0.1.0\"\n";

/// An advisory against `badcrate` fixed in 1.2.3, unaffected below 1.0.0.
const ADVISORY: &str = "[advisory]\nid = \"RUSTSEC-2099-0001\"\npackage = \"badcrate\"\ntitle = \"memory corruption\"\n[versions]\npatched = [\">=1.2.3\"]\nunaffected = [\"<1.0.0\"]\n";

/// The snapshot the `advisory` config word asks for.
fn snapshot() -> Snapshot {
    Snapshot::new(vec![Advisory::parse("t", ADVISORY).expect("advisory")])
}

/// The metadata text the `meta=<name>` config word asks for, all about the crate `pkg`.
fn meta_text(name: &str) -> String {
    let head = "as_of = \"2026-11-06\"\n[policy]\nallowed_licenses = [\"MIT\", \"Apache-2.0\"]\n[[package]]\nname = \"pkg\"\nversion = \"1.0.0\"\n";
    let tail = match name {
        "gpl" => "license = \"GPL-3.0-only\"\n",
        "dual" => "license = \"GPL-3.0-only OR MIT\"\n",
        "yanked" => "license = \"MIT\"\nyanked = true\n",
        "stale" => "license = \"MIT\"\nlast_release = \"2020-01-01\"\n",
        _ => "license = \"MIT\"\nlast_release = \"2026-06-01\"\n",
    };
    format!("{head}{tail}")
}

/// Run one example and keep the findings of the page's rule.
fn runner(case: &gob_mdtest::Case) -> Vec<Finding> {
    // frob:tests crates/grimble-vet/src/pass.rs::analyze
    // frob:tests crates/grimble-vet/src/rules/vet001.rs::Vet001
    // frob:tests crates/grimble-vet/src/rules/vet002.rs::Vet002
    // frob:tests crates/grimble-vet/src/rules/vet003.rs::Vet003
    // frob:tests crates/grimble-vet/src/rules/vet004.rs::Vet004
    // frob:tests crates/grimble-vet/src/rules/vet005.rs::Vet005
    // frob:tests crates/grimble-vet/src/rules/vet006.rs::Vet006
    // frob:tests crates/grimble-vet/src/rules/vet007.rs::Vet007
    // frob:tests crates/grimble-vet/src/rules/vet008.rs::Vet008
    let words = case.config.as_deref().unwrap_or("");
    let has = |w: &str| words.split_whitespace().any(|x| x == w);
    let allow: Vec<String> = words
        .split_whitespace()
        .filter_map(|x| x.strip_prefix("allow="))
        .flat_map(|v| v.split(','))
        .map(|n| format!("\"{n}\""))
        .collect();
    let allowlist = format!("allow = [{}]\n", allow.join(", "));
    let meta = words
        .split_whitespace()
        .find_map(|x| x.strip_prefix("meta="))
        .map(meta_text);
    let snap = snapshot();
    let report = analyze(&VetInput {
        lock: Some(case.text.as_str()),
        allowlist: Some(allowlist.as_str()),
        snapshot: has("advisory").then_some(&snap),
        base: has("base").then_some(BASE),
        meta: meta.as_deref(),
    });
    let mut files = FileInterner::new();
    report
        .findings
        .into_iter()
        .filter(|f| f.rule == case.rule.as_str())
        .filter_map(|f| f.into_finding(&mut files))
        .collect()
}

gob_mdtest::mdtest!(dir = "src/rules", runner = runner);

/// A host that reports a fixed subject count.
struct Fixed;

impl VetHost for Fixed {
    fn vet_subjects_of(&self, _id: &str) -> usize {
        3
    }
}

#[test]
fn every_rule_binds_to_a_host() {
    // frob:tests crates/grimble-vet/src/rules/mod.rs::bind
    assert_eq!(grimble_vet::rules::bind::<Fixed>().len(), 8);
    assert_eq!(grimble_vet::rules::METAS.len(), 8);
}

#[test]
fn a_measured_rule_reports_the_subjects_its_host_counted() {
    // frob:tests crates/grimble-vet/src/host.rs::VetHost.vet_subjects_of
    use gob_rules::Measured;
    use grimble_vet::rules::{vet001::Vet001, vet004::Vet004};
    assert_eq!(Measured::subjects(&Vet001, &Fixed), 3);
    assert_eq!(Measured::subjects(&Vet004, &Fixed), 3);
    assert_eq!(VetHost::vet_subjects_of(&Fixed, "VET002"), 3);
}

#[test]
fn no_lockfile_makes_every_rule_not_applicable() {
    // frob:tests crates/grimble-vet/src/pass.rs::analyze
    let report = analyze(&VetInput::default());
    assert!(report.findings.is_empty());
    assert_eq!(report.not_applicable.len(), 8);
}

#[test]
fn without_base_or_snapshot_only_duplicates_apply() {
    // frob:tests crates/grimble-vet/src/pass.rs::analyze
    let lock = "version = 4\n";
    let report = analyze(&VetInput {
        lock: Some(lock),
        ..VetInput::default()
    });
    let na: Vec<_> = report.not_applicable.keys().copied().collect();
    assert_eq!(
        na,
        ["VET001", "VET002", "VET003", "VET005", "VET006", "VET007"]
    );
    assert!(report.subjects.contains_key("VET008"));
    assert!(report.subjects.contains_key("VET004"));
}

#[test]
fn unparsable_lockfile_is_unresolved() {
    // frob:tests crates/grimble-vet/src/pass.rs::analyze
    let report = analyze(&VetInput {
        lock: Some("[[package"),
        ..VetInput::default()
    });
    let v = report.findings.first().expect("a verdict");
    assert_eq!(v.severity, Severity::Unresolved);
    assert!(matches!(v.reason, Some(UnresolvedReason::ParseFailed)));
}

#[test]
fn unchanged_lock_against_base_makes_delta_rules_not_applicable() {
    // frob:tests crates/grimble-vet/src/pass.rs::analyze
    let report = analyze(&VetInput {
        lock: Some(BASE),
        base: Some(BASE),
        ..VetInput::default()
    });
    for id in ["VET001", "VET002", "VET003"] {
        assert!(report.not_applicable.contains_key(id), "{id} applicable");
        assert!(!report.subjects.contains_key(id), "{id} reported subjects");
    }
}
