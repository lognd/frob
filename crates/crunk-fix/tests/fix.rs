//! Acceptance and property tests for the crunk fix engine.
#![allow(missing_docs)]

use crunk_fix::{apply_findings, collect, is_stylesheet};
use gob_rules::{Applicability, Finding, Fix, FixKind, Severity, TextEdit};
use gob_text::{FileInterner, TextRange, TextSize};
use proptest::prelude::*;

fn finding(
    files: &mut FileInterner,
    path: &str,
    range: (u32, u32),
    with: &str,
    applicability: Applicability,
) -> Finding {
    let id = files.intern(path);
    Finding::new(
        "COLOR001".parse().unwrap(),
        Severity::Error,
        None,
        "off-scale value",
        path,
    )
    .with_fix(Fix {
        kind: FixKind::Deterministic,
        applicability,
        title: "use token".into(),
        edits: vec![TextEdit {
            file: id,
            range: TextRange::new(TextSize::new(range.0), TextSize::new(range.1)),
            replacement: with.into(),
        }],
    })
}

fn project(path: &str, body: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().unwrap();
    std::fs::write(dir.path().join(path), body).unwrap();
    dir
}

#[test]
fn in_tolerance_value_is_rewritten() {
    let dir = project("a.css", "a { color: #fff; }");
    let mut files = FileInterner::new();
    let f = finding(
        &mut files,
        "a.css",
        (11, 15),
        "var(--c)",
        Applicability::Machine,
    );
    let r = apply_findings(dir.path(), &[f], &files, false).unwrap();
    assert_eq!(r.applied.journal.len(), 1);
    assert_eq!(
        std::fs::read_to_string(dir.path().join("a.css")).unwrap(),
        "a { color: var(--c); }"
    );
}

#[test]
fn dry_run_diff_equals_real_diff_and_writes_nothing() {
    let body = "a { color: #fff; }";
    let dir = project("a.css", body);
    let mut files = FileInterner::new();
    let f = finding(
        &mut files,
        "a.css",
        (11, 15),
        "var(--c)",
        Applicability::Machine,
    );
    let dry = apply_findings(dir.path(), std::slice::from_ref(&f), &files, true).unwrap();
    assert_eq!(
        std::fs::read_to_string(dir.path().join("a.css")).unwrap(),
        body
    );
    let real = apply_findings(dir.path(), &[f], &files, false).unwrap();
    assert_eq!(dry.applied.diffs, real.applied.diffs);
    assert!(dry.dry_run && !real.dry_run);
}

#[test]
fn out_of_tolerance_finding_without_fix_is_left_alone() {
    let body = "a { color: #123; }";
    let dir = project("a.css", body);
    let mut files = FileInterner::new();
    let id = files.intern("a.css");
    let _ = id;
    let f = Finding::new(
        "COLOR001".parse().unwrap(),
        Severity::Error,
        None,
        "m",
        "a.css",
    );
    let r = apply_findings(dir.path(), &[f], &files, false).unwrap();
    assert!(r.applied.diffs.is_empty());
    assert_eq!(
        std::fs::read_to_string(dir.path().join("a.css")).unwrap(),
        body
    );
}

#[test]
fn non_machine_fixes_are_not_collected() {
    let mut files = FileInterner::new();
    let f = finding(
        &mut files,
        "a.css",
        (0, 1),
        "x",
        Applicability::MaybeIncorrect,
    );
    assert!(collect(&[f], &files).fixes.is_empty());
}

#[test]
fn jsx_style_prop_sites_are_never_fixed() {
    let body = "const a = <div style={{ color: '#fff' }} />;";
    let dir = project("a.tsx", body);
    let mut files = FileInterner::new();
    let f = finding(&mut files, "a.tsx", (0, 5), "x", Applicability::Machine);
    let c = collect(std::slice::from_ref(&f), &files);
    assert!(c.fixes.is_empty());
    assert_eq!(c.skipped_non_stylesheet, 1);
    apply_findings(dir.path(), &[f], &files, false).unwrap();
    assert_eq!(
        std::fs::read_to_string(dir.path().join("a.tsx")).unwrap(),
        body
    );
}

#[test]
fn stylesheet_extensions() {
    assert!(is_stylesheet("x/y.scss"));
    assert!(!is_stylesheet("x/y.tsx"));
    assert!(!is_stylesheet("css"));
}

#[test]
fn out_of_range_edit_is_skipped() {
    let dir = project("a.css", "a { color: #fff; }");
    let mut files = FileInterner::new();
    let f = finding(
        &mut files,
        "a.css",
        (11, 15),
        "var(--c)",
        Applicability::Machine,
    );
    let g = finding(&mut files, "a.css", (500, 600), "x", Applicability::Machine);
    let r = apply_findings(dir.path(), &[f, g], &files, false).unwrap();
    assert_eq!(r.applied.skipped.len(), 1);
}

/// Run one fix over `body` (written byte-exact) and return the resulting bytes.
fn fixed_bytes(body: &[u8], range: (u32, u32), with: &str) -> Vec<u8> {
    let dir = tempfile::tempdir().unwrap();
    std::fs::write(dir.path().join("a.css"), body).unwrap();
    let mut files = FileInterner::new();
    let f = finding(&mut files, "a.css", range, with, Applicability::Machine);
    apply_findings(dir.path(), &[f], &files, false).unwrap();
    std::fs::read(dir.path().join("a.css")).unwrap()
}

#[test]
fn crlf_file_keeps_crlf_when_fix_text_has_newlines() {
    let body = b"a {\r\n  color: #fff;\r\n}\r\n";
    let got = fixed_bytes(body, (14, 18), "var(--c)\n/* x */");
    assert_eq!(got, b"a {\r\n  color: var(--c)\r\n/* x */;\r\n}\r\n");
}

#[test]
fn crlf_file_without_newline_in_fix_is_byte_exact_with_bom() {
    let body = b"\xEF\xBB\xBFa {\r\n  color: #fff;\r\n}";
    let got = fixed_bytes(body, (17, 21), "var(--c)");
    assert_eq!(got, b"\xEF\xBB\xBFa {\r\n  color: var(--c);\r\n}");
}

#[test]
fn lf_file_stays_lf_and_crlf_in_fix_text_is_not_doubled() {
    let lf = fixed_bytes(b"a { color: #fff; }\n", (11, 15), "x\ny");
    assert_eq!(lf, b"a { color: x\ny; }\n");
    let crlf = fixed_bytes(b"a {\r\n#fff\r\n}\r\n", (5, 9), "x\r\ny");
    assert_eq!(crlf, b"a {\r\nx\r\ny\r\n}\r\n");
}

#[test]
fn mixed_endings_follow_the_edited_line_and_unterminated_last_line() {
    let body = b"a {\n#fff\r\nb: #fff";
    let got = fixed_bytes(body, (4, 8), "x\ny");
    assert_eq!(got, b"a {\nx\r\ny\r\nb: #fff");
    let last = fixed_bytes(body, (13, 17), "p\nq");
    assert_eq!(last, b"a {\n#fff\r\nb: p\r\nq");
}

proptest! {
    // INV-FIX-01: bytes outside the edited span are untouched.
    #[test]
    fn bytes_outside_edited_span_are_untouched(
        prefix in "[a-z .:;{}#0-9]{0,40}",
        old in "[a-z0-9#]{1,8}",
        suffix in "[a-z .:;{}#0-9]{0,40}",
        new in "[a-z0-9()-]{0,12}",
    ) {
        let body = format!("{prefix}{old}{suffix}");
        let dir = project("p.css", &body);
        let mut files = FileInterner::new();
        let start = u32::try_from(prefix.len()).unwrap();
        let end = start + u32::try_from(old.len()).unwrap();
        let f = finding(&mut files, "p.css", (start, end), &new, Applicability::Machine);
        apply_findings(dir.path(), &[f], &files, false).unwrap();
        let got = std::fs::read_to_string(dir.path().join("p.css")).unwrap();
        prop_assert_eq!(got, format!("{prefix}{new}{suffix}"));
    }
}
