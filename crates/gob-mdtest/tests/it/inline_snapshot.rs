//! Inline `snapshot` fences: insert, rewrite, remove, the three failures and the update switch.

use gob_mdtest::{Case, FileReport, Runner, SnapshotMode, parse_document, run_file_with};
use gob_rules::{Finding, Severity, UnresolvedReason};
use gob_text::{FileInterner, Span, TextRange, TextSize};

/// Fires on `forbidden`; reports `unsure;` as an Unresolved hole.
fn toy(case: &Case) -> Vec<Finding> {
    let file = FileInterner::new().intern(&case.file_name);
    let mut out = Vec::new();
    let mut off = 0usize;
    for line in case.text.split_inclusive('\n') {
        for (word, sev, msg) in [
            ("forbidden", Severity::Error, "forbidden word"),
            ("unsure;", Severity::Unresolved, "undecided"),
        ] {
            let Some(at) = line.find(word) else { continue };
            let start = TextSize::try_from(off + at).unwrap();
            let len = TextSize::try_from(word.len()).unwrap();
            let span = Span::new(file, TextRange::at(start, len));
            let mut f = Finding::new(case.rule.clone(), sev, Some(span), msg, &case.file_name);
            if sev == Severity::Unresolved {
                f.reason = Some(UnresolvedReason::Hole);
            }
            out.push(f);
        }
        off += line.len();
    }
    out
}

const HEAD: &str = "<!-- mdtest: rule=MDT001 inline-snapshots -->\n# Suite\n\n## case\n\n";
const FIRE: &str = "```rust expect=fire\nlet b = forbidden; // error: MDT001\n```\n";
const CLEAN: &str = "```rust expect=clean\nlet ok = 1;\n```\n";

/// Write `md` to a temp suite file and run it in `mode`; returns the report, file path and guard.
fn run(md: &str, mode: SnapshotMode) -> (FileReport, std::path::PathBuf, tempfile::TempDir) {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("suite.md");
    std::fs::write(&path, md).unwrap();
    let report = run_file_with(&path, &Runner::new(toy), mode);
    (report, path, dir)
}

fn failures(r: &FileReport) -> String {
    r.cases
        .iter()
        .filter_map(|c| c.outcome.as_ref().err().cloned())
        .collect::<String>()
}

// frob:ticket 01M48PC0TZ7MHW4KA89V6ZFY72
// frob:tests crates/gob-mdtest/src/run.rs::run_file_with
#[test]
fn update_inserts_a_missing_snapshot_and_recheck_passes() {
    let (r, path, _g) = run(&format!("{HEAD}{FIRE}"), SnapshotMode::Update);
    assert!(r.cases.iter().all(|c| c.outcome.is_ok()), "{r:?}");
    assert_eq!(r.updated.len(), 1, "{:?}", r.updated);
    let md = std::fs::read_to_string(&path).unwrap();
    assert!(md.contains("```snapshot\n"), "{md}");
    assert!(md.contains("forbidden word"), "{md}");
    let again = run_file_with(&path, &Runner::new(toy), SnapshotMode::Check);
    assert!(again.cases.iter().all(|c| c.outcome.is_ok()), "{again:?}");
    assert!(again.updated.is_empty());
}

// frob:ticket 01M48PC0TZ7MHW4KA89V6ZFY72
// frob:tests crates/gob-mdtest/src/run.rs::run_file_with
#[test]
fn check_fails_a_missing_snapshot_without_touching_the_file() {
    let md = format!("{HEAD}{FIRE}");
    let (r, path, _g) = run(&md, SnapshotMode::Check);
    let t = failures(&r);
    assert!(t.contains("missing inline snapshot"), "{t}");
    assert!(t.contains("FROB_MDTEST_UPDATE=1"), "{t}");
    assert_eq!(std::fs::read_to_string(&path).unwrap(), md);
}

// frob:ticket 01M48PC0TZ7MHW4KA89V6ZFY72
// frob:tests crates/gob-mdtest/src/run.rs::run_file_with
#[test]
fn stale_snapshot_fails_in_check_and_is_rewritten_in_update() {
    let md = format!("{HEAD}{FIRE}\n```snapshot\nold text\n```\n");
    let (r, path, _g) = run(&md, SnapshotMode::Check);
    let t = failures(&r);
    assert!(t.contains("stale inline snapshot"), "{t}");
    assert!(
        t.contains("old text") && t.contains("forbidden word"),
        "{t}"
    );
    let (_, path2, _g2) = run(&md, SnapshotMode::Update);
    let md2 = std::fs::read_to_string(&path2).unwrap();
    assert!(!md2.contains("old text"), "{md2}");
    assert!(md2.contains("forbidden word"), "{md2}");
    assert_eq!(std::fs::read_to_string(&path).unwrap(), md);
    let again = run_file_with(&path2, &Runner::new(toy), SnapshotMode::Check);
    assert!(again.cases.iter().all(|c| c.outcome.is_ok()), "{again:?}");
}

// frob:ticket 01M48PC0TZ7MHW4KA89V6ZFY72
// frob:tests crates/gob-mdtest/src/run.rs::run_file_with
#[test]
fn snapshot_of_a_now_quiet_case_is_stale_and_update_removes_it() {
    let md = format!("{HEAD}{CLEAN}\n```snapshot\nleftover\n```\n\ntail\n");
    let (r, _p, _g) = run(&md, SnapshotMode::Check);
    assert!(failures(&r).contains("stale inline snapshot"), "{r:?}");
    let (r, path, _g) = run(&md, SnapshotMode::Update);
    assert_eq!(r.updated.len(), 1);
    let md2 = std::fs::read_to_string(&path).unwrap();
    assert_eq!(md2, format!("{HEAD}{CLEAN}\ntail\n"));
}

// frob:ticket 01M48PC0TZ7MHW4KA89V6ZFY72
// frob:tests crates/gob-mdtest/src/run.rs::run_file_with
#[test]
fn orphan_snapshot_fails_in_check_and_is_removed_in_update() {
    let md = format!("{HEAD}{CLEAN}\n## other\n\n```snapshot\nstray\n```\n");
    let (r, _p, _g) = run(&md, SnapshotMode::Check);
    assert!(failures(&r).contains("orphan inline snapshot"), "{r:?}");
    let (r, path, _g) = run(&md, SnapshotMode::Update);
    assert_eq!(r.updated.len(), 1, "{r:?}");
    let md2 = std::fs::read_to_string(&path).unwrap();
    assert!(!md2.contains("stray"), "{md2}");
    let again = run_file_with(&path, &Runner::new(toy), SnapshotMode::Check);
    assert!(again.cases.iter().all(|c| c.outcome.is_ok()), "{again:?}");
}

// frob:ticket 01M48PC0TZ7MHW4KA89V6ZFY72
// frob:tests crates/gob-mdtest/src/run.rs::run_file_with
#[test]
fn update_never_changes_a_failing_case_outcome() {
    let md = format!("{HEAD}```rust expect=clean\nlet b = forbidden;\n```\n");
    let (r, path, _g) = run(&md, SnapshotMode::Update);
    let t = failures(&r);
    assert!(t.contains("inline snapshot not updated"), "{t}");
    assert!(r.updated.is_empty());
    assert_eq!(std::fs::read_to_string(&path).unwrap(), md);
}

// frob:ticket 01M48PC0TZ7MHW4KA89V6ZFY72
// frob:tests crates/gob-mdtest/src/run.rs::run_file_with
#[test]
fn unresolved_snapshot_states_its_reason_and_remedy_in_words() {
    let md =
        format!("{HEAD}```rust expect=fire\nlet c = unsure; // unresolved[hole]: MDT001\n```\n");
    let (r, path, _g) = run(&md, SnapshotMode::Update);
    assert!(r.cases.iter().all(|c| c.outcome.is_ok()), "{r:?}");
    let out = std::fs::read_to_string(&path).unwrap();
    assert!(
        out.contains("reason: the code has a hole or parse error"),
        "{out}"
    );
    assert!(out.contains("remedy: fill or fix the hole"), "{out}");
}

// frob:ticket 01M48PC0TZ7MHW4KA89V6ZFY72
// frob:tests crates/gob-mdtest/src/run.rs::SnapshotMode
#[test]
fn only_the_value_one_selects_update_mode() {
    assert_eq!(SnapshotMode::from_value(Some("1")), SnapshotMode::Update);
    for v in [None, Some(""), Some("0"), Some("yes")] {
        assert_eq!(SnapshotMode::from_value(v), SnapshotMode::Check, "{v:?}");
    }
}

// frob:ticket 01M48PC0TZ7MHW4KA89V6ZFY72
// frob:tests crates/gob-mdtest/src/parse.rs::parse_document
#[test]
fn snapshot_fences_attach_to_their_case_or_become_orphans() {
    let md = format!(
        "{HEAD}{FIRE}\n```snapshot\na\n```\n\n```snapshot\nb\n```\n\n## next\n\n```snapshot\nc\n```\n"
    );
    let p = parse_document(&md).unwrap();
    assert_eq!(p.blocks.len(), 1);
    assert!(p.blocks[0].inline_required);
    assert_eq!(p.blocks[0].inline.as_ref().unwrap().body, "a\n");
    assert_eq!(p.orphans.len(), 2);
}
