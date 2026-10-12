//! The fragment skeleton writer: mapping, validity, refusal on existing, force.
// frob:ticket 01M4069WHH6KXYWDAJD3TXB8SR
// frob:ticket 01M4FDQXEST75DK0NHDH4P5H15

use frob_release::skeleton::{Request, default_kind, skeleton_text, write};
use frob_release::{Kind, Mode, Options, SkeletonError, run};

const A: &str = "01M4069WHH6KXYWDAJD3TXB8SR";

fn resolver(ulid: &str) -> Option<String> {
    (ulid == A).then(|| "~3TXB8SR".to_owned())
}

fn req(root: &std::path::Path, kind: Kind, force: bool) -> Request<'_> {
    Request {
        root,
        ulid: A,
        title: "Land helps with fragments",
        kind,
        prefix: "",
        text: None,
        force,
    }
}

fn check(root: &std::path::Path) -> Result<frob_release::Outcome, frob_release::ReleaseError> {
    let opts = Options {
        version: "0.532.0".into(),
        date: "2026-10-03".into(),
        mode: Mode::Check,
    };
    run(root, &opts, &resolver)
}

// frob:tests crates/frob-release/src/skeleton.rs::default_kind
#[test]
fn ticket_types_map_to_documented_fragment_types() {
    for (ty, want) in [
        ("bug", Kind::Fixed),
        ("incident", Kind::Fixed),
        ("security", Kind::Security),
        ("story", Kind::Added),
        ("epic", Kind::Added),
        ("task", Kind::Changed),
        ("docs", Kind::Changed),
        ("chore", Kind::Changed),
    ] {
        assert_eq!(default_kind(ty), want, "{ty}");
    }
}

// frob:tests crates/frob-release/src/skeleton.rs::write
#[test]
fn writes_a_valid_fragment_from_the_title_that_passes_the_changelog_check() {
    let d = tempfile::tempdir().unwrap();
    let w = write(&req(d.path(), Kind::Changed, false), &resolver).unwrap();
    assert_eq!(w.file, format!("{A}.changed.md"));
    assert_eq!(w.body, "Land helps with fragments.\n");
    assert_eq!(std::fs::read_to_string(&w.path).unwrap(), w.body);
    let out = check(d.path()).expect("changelog --check accepts the skeleton");
    assert_eq!(out.fragments, vec![w.file]);
}

// frob:tests crates/frob-release/src/skeleton.rs::write
#[test]
fn refuses_when_one_exists_and_force_replaces_it() {
    let d = tempfile::tempdir().unwrap();
    write(&req(d.path(), Kind::Added, false), &resolver).unwrap();
    let e = write(&req(d.path(), Kind::Fixed, false), &resolver).unwrap_err();
    assert_eq!(
        e,
        SkeletonError::Exists {
            file: format!("{A}.added.md")
        }
    );
    let w = write(&req(d.path(), Kind::Fixed, true), &resolver).unwrap();
    assert_eq!(w.replaced, vec![format!("{A}.added.md")]);
    let names: Vec<_> = std::fs::read_dir(d.path().join("changelog.d"))
        .unwrap()
        .map(|e| e.unwrap().file_name().into_string().unwrap())
        .collect();
    assert_eq!(names, vec![format!("{A}.fixed.md")]);
}

// frob:tests crates/frob-release/src/skeleton.rs::write
#[test]
fn an_invalid_text_writes_nothing() {
    let d = tempfile::tempdir().unwrap();
    let mut r = req(d.path(), Kind::Added, false);
    r.text = Some("frbo: oops");
    assert!(matches!(
        write(&r, &resolver),
        Err(SkeletonError::Invalid(_))
    ));
    r.text = Some("caf\u{e9}");
    assert!(matches!(
        write(&r, &resolver),
        Err(SkeletonError::Invalid(_))
    ));
    assert!(!d.path().join("changelog.d").exists());
    assert!(matches!(
        write(
            &Request {
                ulid: "01M4069WHH6KXYWDAJD3TXB8SS",
                ..req(d.path(), Kind::Added, false)
            },
            &resolver
        ),
        Err(SkeletonError::UnknownTicket { .. })
    ));
}

// frob:tests crates/frob-release/src/skeleton.rs::skeleton_text
#[test]
fn skeleton_text_adds_a_period_only_when_missing() {
    assert_eq!(skeleton_text("Add a thing", ""), "Add a thing.");
    assert_eq!(skeleton_text("Add  a thing!", ""), "Add a thing!");
}

// frob:tests crates/frob-release/src/skeleton.rs::skeleton_text
#[test]
fn a_configured_prefix_starts_the_skeleton_and_still_passes_the_check() {
    assert_eq!(skeleton_text("Add a thing", "frob: "), "frob: Add a thing.");
    let d = tempfile::tempdir().unwrap();
    let r = Request {
        prefix: "frob: ",
        ..req(d.path(), Kind::Changed, false)
    };
    let w = write(&r, &resolver).unwrap();
    assert_eq!(w.body, "frob: Land helps with fragments.\n");
    check(d.path()).expect("changelog --check accepts the prefixed skeleton");
}
