//! Inline parser test extraction: block syntax, escapes, staleness and orphans.

// frob:ticket 01M47QTW8CA2FD3BQTH2GG2KXR

use std::path::Path;

use gob_dev::render::inline::{InlineError, Outcome, extract, generate};
use gob_dev::{Mode, apply};

const SOURCE: &str = "\
// test_ok first_case
// frob\\:ticket abc
// second line
fn a() {}

// test_err bad_case
// oops
// test_ok adjacent
// x
";

/// Lay down a fake workspace with one GRL source file holding `SOURCE`.
fn fake_root(dir: &Path) {
    let src = dir.join("crates/gob-plan/src/grl");
    std::fs::create_dir_all(&src).expect("mkdir");
    std::fs::write(src.join("x.rs"), SOURCE).expect("write source");
}

// frob:tests extract
#[test]
fn extract_reads_names_outcomes_and_bodies() {
    let blocks = extract("x.rs", SOURCE).expect("extract");
    let got: Vec<_> = blocks
        .iter()
        .map(|b| (b.outcome, b.name.as_str()))
        .collect();
    assert_eq!(
        got,
        vec![
            (Outcome::Ok, "first_case"),
            (Outcome::Err, "bad_case"),
            (Outcome::Ok, "adjacent")
        ]
    );
    assert_eq!(blocks[0].body, "frob:ticket abc\nsecond line\n");
    assert_eq!(blocks[1].body, "oops\n");
}

// frob:tests extract
#[test]
fn extract_rejects_bad_empty_and_duplicate_blocks() {
    assert!(matches!(
        extract("x.rs", "// test_ok\n// a\n"),
        Err(InlineError::BadName { .. })
    ));
    assert!(matches!(
        extract("x.rs", "// test_ok Bad-Name\n// a\n"),
        Err(InlineError::BadName { .. })
    ));
    assert!(matches!(
        extract("x.rs", "// test_ok a\nfn f() {}\n"),
        Err(InlineError::Empty { .. })
    ));
    assert!(matches!(
        extract("x.rs", "// test_ok a\n// x\n\n// test_ok a\n// y\n"),
        Err(InlineError::Duplicate { .. })
    ));
}

// frob:tests extract
#[test]
fn doc_comments_are_not_blocks() {
    assert!(
        extract("x.rs", "/// test_ok a\n//! test_err b\n")
            .expect("extract")
            .is_empty()
    );
}

// frob:tests generate
#[test]
fn stale_extraction_fails_check() {
    let root = tempfile::tempdir().expect("tmp");
    fake_root(root.path());
    let files = generate(root.path()).expect("generate");
    assert_eq!(files.len(), 3);
    apply(root.path(), &files, Mode::Write).expect("write");
    assert_eq!(
        apply(root.path(), &files, Mode::Check)
            .expect("check")
            .differing,
        0
    );
    // The source changes but the checked-in extraction is not regenerated.
    let src = root.path().join("crates/gob-plan/src/grl/x.rs");
    std::fs::write(&src, SOURCE.replace("oops", "changed")).expect("edit");
    let fresh = generate(root.path()).expect("generate");
    let r = apply(root.path(), &fresh, Mode::Check).expect("check");
    assert_eq!(r.differing, 1);
}

// frob:tests is_inline_path
#[test]
fn removed_block_leaves_a_reported_orphan() {
    let root = tempfile::tempdir().expect("tmp");
    fake_root(root.path());
    apply(
        root.path(),
        &generate(root.path()).expect("generate"),
        Mode::Write,
    )
    .expect("write");
    let src = root.path().join("crates/gob-plan/src/grl/x.rs");
    std::fs::write(&src, "// test_ok first_case\n// body\n").expect("edit");
    let fresh = generate(root.path()).expect("generate");
    assert_eq!(fresh.len(), 1);
    let r = apply(root.path(), &fresh, Mode::Check).expect("check");
    assert!(
        r.differing + r.marker_problems > 0,
        "orphaned extraction must fail the check"
    );
}
