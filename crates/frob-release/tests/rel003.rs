//! `REL003` unit tests: invalid fragments, the per-ticket missing finding, applicability, and the shared validator.
// frob:ticket 01M4069WD4P8ZZ5HGQ5HE2EX99

use frob_release::fragment::validate_ticket;
use frob_release::rel003::{evaluate, missing, not_applicable};
use gob_rules::Severity;

mod rel003_corpus;
use rel003_corpus::{KNOWN, OTHER, fragment, resolver};

#[test]
fn a_ticket_without_a_fragment_is_named_with_the_remedy() {
    // frob:tests crates/frob-release/src/rel003.rs::missing
    let d = tempfile::tempdir().unwrap();
    fragment(d.path(), &format!("{OTHER}.added.md"), "frob: Added.\n");
    let f = missing(d.path(), KNOWN, "~KNOWN").expect("fires");
    assert_eq!(f.severity, Severity::Error);
    for want in ["REL003", "~KNOWN", "frob ticket fragment ~KNOWN", KNOWN] {
        assert!(f.message.contains(want), "{want} in {}", f.message);
    }
}

#[test]
fn any_file_of_the_ticket_counts_as_present_and_case_is_ignored() {
    // frob:tests crates/frob-release/src/rel003.rs::missing
    let d = tempfile::tempdir().unwrap();
    fragment(
        d.path(),
        &format!("{}.nonsense.md", KNOWN.to_lowercase()),
        "x\n",
    );
    assert!(missing(d.path(), KNOWN, "~KNOWN").is_none());
}

#[test]
fn invalid_fragments_report_the_validation_message() {
    // frob:tests crates/frob-release/src/rel003.rs::evaluate
    let d = tempfile::tempdir().unwrap();
    fragment(d.path(), &format!("{KNOWN}.improved.md"), "frob: x.\n");
    fragment(d.path(), &format!("{OTHER}.changed.md"), "\n");
    let e = evaluate(d.path(), &resolver);
    assert_eq!(e.subjects, 2);
    assert_eq!(e.findings.len(), 2, "{:?}", e.findings);
    let all: String = e.findings.iter().map(|f| f.message.clone()).collect();
    assert!(all.contains("unknown type `improved`"), "{all}");
    assert!(all.contains("empty fragment"), "{all}");
    assert!(all.contains("frob ticket fragment"), "{all}");
}

#[test]
fn no_directory_is_an_empty_evaluation() {
    // frob:tests crates/frob-release/src/rel003.rs::evaluate
    let d = tempfile::tempdir().unwrap();
    let e = evaluate(d.path(), &resolver);
    assert_eq!((e.subjects, e.findings.len()), (0, 0));
}

#[test]
fn not_applicable_only_when_unrequired_and_no_directory() {
    // frob:tests crates/frob-release/src/rel003.rs::not_applicable
    let d = tempfile::tempdir().unwrap();
    let why = not_applicable(d.path(), false).expect("not applicable");
    assert!(
        why.contains("done_requires") && why.contains("changelog.d"),
        "{why}"
    );
    assert!(not_applicable(d.path(), true).is_none());
    std::fs::create_dir(d.path().join("changelog.d")).unwrap();
    assert!(not_applicable(d.path(), false).is_none());
}

#[test]
fn validate_ticket_distinguishes_missing_valid_and_invalid() {
    // frob:tests crates/frob-release/src/fragment.rs::validate_ticket
    let d = tempfile::tempdir().unwrap();
    let dir = d.path().join("changelog.d");
    assert!(validate_ticket(&dir, KNOWN, &resolver).unwrap().is_empty());
    fragment(d.path(), &format!("{KNOWN}.fixed.md"), "Fixed it.\n");
    assert_eq!(validate_ticket(&dir, KNOWN, &resolver).unwrap().len(), 1);
    fragment(d.path(), &format!("{KNOWN}.bogus.md"), "Fixed it.\n");
    let errs = validate_ticket(&dir, KNOWN, &resolver).unwrap_err();
    assert_eq!(errs.len(), 1);
    assert!(errs[0].to_string().contains("unknown type"));
}
