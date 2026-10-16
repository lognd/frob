//! Acceptance tests for gob-fix.
#![allow(missing_docs)]

use gob_fix::{
    Applicability, DropReason, Edit, FileOutcome, Fix, Mode, Snapshot, Tier, apply, plan,
};

fn edit(path: &str, s: usize, e: usize, r: &str) -> Edit {
    Edit {
        path: path.into(),
        start: s,
        end: e,
        replacement: r.into(),
    }
}
fn fix(rule: &str, edits: Vec<Edit>) -> Fix {
    Fix {
        rule: rule.into(),
        title: rule.into(),
        applicability: Applicability::Machine,
        edits,
    }
}

#[test]
fn overlap_first_wins_and_loser_reported() {
    let p = plan(
        vec![
            fix("B", vec![edit("a", 3, 8, "x")]),
            fix("A", vec![edit("a", 0, 5, "y")]),
        ],
        Tier::A,
    );
    assert_eq!(p.accepted.len(), 1);
    assert_eq!(p.accepted[0].rule, "A");
    assert_eq!(p.dropped.len(), 1);
    assert_eq!(p.dropped[0].fix.rule, "B");
    match &p.dropped[0].reason {
        DropReason::Overlap { winner_rule, edit } => {
            assert_eq!(winner_rule, "A");
            assert_eq!((edit.start, edit.end), (3, 8));
        }
        other => panic!("unexpected {other:?}"),
    }
}

#[test]
fn tier_gates_applicability() {
    let mut f = fix("M", vec![edit("a", 0, 1, "x")]);
    f.applicability = Applicability::MaybeIncorrect;
    assert_eq!(
        plan(vec![f.clone()], Tier::A).dropped[0].reason,
        DropReason::Tier
    );
    assert_eq!(plan(vec![f], Tier::B).accepted.len(), 1);
}

#[test]
fn dry_run_diff_equals_real_and_outside_bytes_unchanged() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("a.txt");
    std::fs::write(&path, "hello wide world").unwrap();
    let mut snap = Snapshot::new();
    snap.record("a.txt", b"hello wide world");
    let p = plan(vec![fix("R", vec![edit("a.txt", 6, 10, "big")])], Tier::A);
    let dry = apply(&p, dir.path(), &snap, Mode::DryRun).unwrap();
    assert_eq!(std::fs::read_to_string(&path).unwrap(), "hello wide world");
    let real = apply(&p, dir.path(), &snap, Mode::Write).unwrap();
    assert_eq!(dry.diffs, real.diffs);
    assert_eq!(dry.journal, real.journal);
    assert_eq!(std::fs::read_to_string(&path).unwrap(), "hello big world");
}

#[test]
fn changed_file_is_refused_and_untouched() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("a.txt");
    std::fs::write(&path, "hello").unwrap();
    let mut snap = Snapshot::new();
    snap.record("a.txt", b"hello");
    std::fs::write(&path, "hello!").unwrap();
    let p = plan(vec![fix("R", vec![edit("a.txt", 0, 1, "J")])], Tier::A);
    let r = apply(&p, dir.path(), &snap, Mode::Write).unwrap();
    assert_eq!(r.files["a.txt"], FileOutcome::Stale);
    assert!(r.diffs.is_empty());
    assert_eq!(std::fs::read_to_string(&path).unwrap(), "hello!");
}
