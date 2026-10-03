//! Changelog compile: grouping, validation, idempotency, hand-edit detection, write ordering.
// frob:ticket 01M4069W8ECWEPBH6YPAR7X0X0

use std::fs;
use std::path::Path;

use frob_release::{Mode, Options, ReleaseError, run};

const A: &str = "01M4069W8ECWEPBH6YPAR7X0X0";
const B: &str = "01M4069QWSJEH5KW8K0YR8CA0D";
const C: &str = "01M4065Y4N6DQG30TRSP2QNP8T";

fn resolver(ulid: &str) -> Option<String> {
    [A, B, C]
        .contains(&ulid)
        .then(|| format!("~{}", &ulid[ulid.len() - 7..]))
}

fn frag(root: &Path, name: &str, body: &str) {
    let d = root.join("changelog.d");
    fs::create_dir_all(&d).unwrap();
    fs::write(d.join(name), body).unwrap();
}

fn opts(mode: Mode) -> Options {
    Options {
        version: "0.532.0".into(),
        date: "2026-10-03".into(),
        mode,
    }
}

fn repo() -> tempfile::TempDir {
    let d = tempfile::tempdir().unwrap();
    frag(
        d.path(),
        &format!("{A}.fixed.md"),
        "frob: Fixed the thing.\n",
    );
    frag(
        d.path(),
        &format!("{B}.added.md"),
        "frob: Added a thing.\nSecond line.\n",
    );
    frag(
        d.path(),
        &format!("{C}.added.md"),
        "gob: Added a gob thing.\n",
    );
    d
}

#[test]
fn groups_by_product_type_then_ulid_and_removes_fragments() {
    // frob:tests crates/frob-release/src/lib.rs::run
    let d = repo();
    let out = run(d.path(), &opts(Mode::Write), &resolver).unwrap();
    assert!(out.written);
    let text = fs::read_to_string(d.path().join("CHANGELOG.md")).unwrap();
    let pos = |s: &str| text.find(s).unwrap_or_else(|| panic!("missing {s}"));
    assert!(pos("### frob") < pos("### gob"));
    assert!(pos("#### Added") < pos("#### Fixed"));
    assert!(pos("Added a thing. Second line.") < pos("Fixed the thing."));
    assert!(text.contains(&format!(
        "([~{}](tickets/{B}/ticket.md))",
        &B[B.len() - 7..]
    )));
    assert!(text.contains("CHANGELOG-v1.md"));
    assert!(
        !d.path()
            .join("changelog.d")
            .join(format!("{A}.fixed.md"))
            .exists()
    );
}

#[test]
fn same_type_entries_sort_by_ulid() {
    // frob:tests crates/frob-release/src/changelog.rs::render_section
    let d = tempfile::tempdir().unwrap();
    frag(d.path(), &format!("{B}.added.md"), "second\n");
    frag(d.path(), &format!("{C}.added.md"), "first\n");
    let out = run(d.path(), &opts(Mode::DryRun), &resolver).unwrap();
    let s = out.section.unwrap();
    assert!(s.find("first").unwrap() < s.find("second").unwrap());
}

#[test]
fn dry_run_touches_nothing() {
    // frob:tests crates/frob-release/src/lib.rs::Mode
    let d = repo();
    let out = run(d.path(), &opts(Mode::DryRun), &resolver).unwrap();
    assert!(out.section.unwrap().starts_with("## 0.532.0 - 2026-10-03"));
    assert!(!d.path().join("CHANGELOG.md").exists());
    assert!(
        d.path()
            .join("changelog.d")
            .join(format!("{A}.fixed.md"))
            .exists()
    );
}

#[test]
fn invalid_names_are_refused_with_the_remedy() {
    // frob:tests crates/frob-release/src/error.rs::FragmentError
    // frob:tests crates/frob-release/src/fragment.rs::Kind.valid_list
    let d = repo();
    frag(d.path(), "notes.md", "x");
    frag(d.path(), &format!("{A}.bugfix.md"), "x");
    let err = run(d.path(), &opts(Mode::Check), &resolver)
        .unwrap_err()
        .to_string();
    assert!(err.contains("changelog.d/notes.md"), "{err}");
    assert!(err.contains("<ulid>.<type>.md"), "{err}");
    assert!(err.contains("unknown type `bugfix`"), "{err}");
    assert!(
        err.contains("added, changed, fixed, removed, deprecated, security"),
        "{err}"
    );
}

#[test]
fn ulid_without_a_ticket_is_refused_naming_the_file() {
    // frob:tests crates/frob-release/src/error.rs::FragmentError
    let d = tempfile::tempdir().unwrap();
    let name = "01ARZ3NDEKTSV4RRFFQ69G5FAV.added.md";
    frag(d.path(), name, "x");
    let err = run(d.path(), &opts(Mode::Write), &resolver).unwrap_err();
    assert!(matches!(err, ReleaseError::Fragments(_)));
    assert!(err.to_string().contains(name));
    assert!(!d.path().join("CHANGELOG.md").exists());
}

#[test]
fn empty_changelog_d_adds_nothing() {
    // frob:tests crates/frob-release/src/lib.rs::run
    let d = repo();
    run(d.path(), &opts(Mode::Write), &resolver).unwrap();
    let before = fs::read_to_string(d.path().join("CHANGELOG.md")).unwrap();
    let o = Options {
        version: "0.533.0".into(),
        ..opts(Mode::Write)
    };
    let out = run(d.path(), &o, &resolver).unwrap();
    assert!(!out.written && out.section.is_none());
    assert_eq!(
        before,
        fs::read_to_string(d.path().join("CHANGELOG.md")).unwrap()
    );
}

#[test]
fn second_release_goes_above_the_first() {
    // frob:tests crates/frob-release/src/changelog.rs::split
    let d = repo();
    run(d.path(), &opts(Mode::Write), &resolver).unwrap();
    frag(d.path(), &format!("{A}.security.md"), "later\n");
    let o = Options {
        version: "0.533.0".into(),
        ..opts(Mode::Write)
    };
    run(d.path(), &o, &resolver).unwrap();
    let t = fs::read_to_string(d.path().join("CHANGELOG.md")).unwrap();
    assert!(t.find("## 0.533.0").unwrap() < t.find("## 0.532.0").unwrap());
    run(d.path(), &opts(Mode::Check), &resolver).unwrap();
}

#[test]
fn check_detects_a_hand_edit_of_an_older_section() {
    // frob:tests crates/frob-release/src/changelog.rs::verify
    let d = repo();
    run(d.path(), &opts(Mode::Write), &resolver).unwrap();
    run(d.path(), &opts(Mode::Check), &resolver).unwrap();
    let p = d.path().join("CHANGELOG.md");
    let t = fs::read_to_string(&p)
        .unwrap()
        .replace("Fixed the thing.", "Fixed it.");
    fs::write(&p, t).unwrap();
    let err = run(d.path(), &opts(Mode::Check), &resolver).unwrap_err();
    assert!(matches!(err, ReleaseError::Tampered(v) if v == "0.532.0"));
}

#[test]
fn existing_version_is_refused() {
    // frob:tests crates/frob-release/src/error.rs::ReleaseError
    let d = repo();
    run(d.path(), &opts(Mode::Write), &resolver).unwrap();
    frag(d.path(), &format!("{A}.added.md"), "again\n");
    let err = run(d.path(), &opts(Mode::Write), &resolver).unwrap_err();
    assert!(matches!(err, ReleaseError::VersionExists(_)));
}

#[test]
fn fragments_survive_a_failed_write() {
    // frob:tests crates/frob-release/src/lib.rs::run
    let d = repo();
    fs::create_dir(d.path().join("CHANGELOG.md.tmp")).unwrap();
    let err = run(d.path(), &opts(Mode::Write), &resolver).unwrap_err();
    assert!(matches!(err, ReleaseError::Io { .. }));
    assert!(
        d.path()
            .join("changelog.d")
            .join(format!("{A}.fixed.md"))
            .exists()
    );
    assert!(!d.path().join("CHANGELOG.md").exists());
}

#[test]
fn bad_version_and_non_ascii_are_refused() {
    // frob:tests crates/frob-release/src/error.rs::ReleaseError
    let d = repo();
    let o = Options {
        version: "v1".into(),
        ..opts(Mode::Check)
    };
    assert!(matches!(
        run(d.path(), &o, &resolver),
        Err(ReleaseError::InvalidVersion(_))
    ));
    frag(d.path(), &format!("{A}.added.md"), "caf\u{e9}\n");
    let err = run(d.path(), &opts(Mode::Check), &resolver)
        .unwrap_err()
        .to_string();
    assert!(err.contains("non-ASCII"), "{err}");
}
