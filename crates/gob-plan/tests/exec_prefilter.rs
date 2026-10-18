//! The executor's node-kind prefilter (plugins.md section 6.2).

use crate::support;

use gob_ir::{Model, NodeId, NodeSpec, Operator};
use gob_plan::exec::outcome::outcomes;
use gob_plan::exec::prefilter::{Filtered, Tally, outcomes_prefiltered};
use gob_plan::exec::relations::Relations;
use gob_plan::exec::{ExecError, Input};
use gob_plan::plan::{Plan, Polarity};
use support::{Doc, PlanBuilder};

fn input(m: &Model) -> Input<'_> {
    Input {
        model: m,
        source: None,
    }
}

fn funcs(names: &[&str]) -> Model {
    let mut d = Doc::new("a.rs", "rust");
    let fs: Vec<NodeId> = names
        .iter()
        .enumerate()
        .map(|(i, n)| {
            let at = 100 + 10 * u32::try_from(i).unwrap();
            d.at_range(
                |loc| NodeSpec::new(Operator::unit("function", "impl"), loc).named(n),
                at,
                at + 5,
                &[],
            )
        })
        .collect();
    d.root(&fs).0
}

fn find_plan(kind: &str) -> Plan {
    let mut b = PlanBuilder::new("PRE001", Polarity::Pplus);
    let v = b.find(kind);
    b.report(None, v, "found");
    b.build()
}

// frob:ticket 01M3ZX7F57JCT6CZXY5VS9RHTR
// frob:tests crates/gob-plan/src/exec/prefilter.rs::outcomes_prefiltered
#[test]
fn a_file_lacking_a_prefilter_kind_is_skipped_and_counted_apart_from_clean() {
    let m = funcs(&["a", "b"]);
    let plan = find_plan("call");
    let got = outcomes_prefiltered(&plan, &input(&m), &Relations::new()).unwrap();
    assert_eq!(
        got,
        Filtered::Skipped {
            kind: "call".to_string()
        }
    );
    let mut t = Tally::default();
    t.record(&got);
    assert_eq!((t.skipped, t.examined), (1, 0));
    let ran = outcomes_prefiltered(&find_plan("function"), &input(&m), &Relations::new()).unwrap();
    t.record(&ran);
    assert_eq!((t.skipped, t.examined), (1, 1));
}

// frob:ticket 01M3ZX7F57JCT6CZXY5VS9RHTR
// frob:tests crates/gob-plan/src/exec/prefilter.rs::outcomes_prefiltered
#[test]
fn a_file_with_the_kind_gives_the_unfiltered_results() {
    let m = funcs(&["a", "b", "c"]);
    let plan = find_plan("function");
    let rels = Relations::new();
    let want = outcomes(&plan, &input(&m), &rels).unwrap();
    assert_eq!(want.findings.len(), 3);
    assert_eq!(
        outcomes_prefiltered(&plan, &input(&m), &rels).unwrap(),
        Filtered::Ran(want)
    );
}

// frob:ticket 01M3ZX7F57JCT6CZXY5VS9RHTR
// frob:tests crates/gob-plan/src/exec/prefilter.rs::outcomes_prefiltered
#[test]
fn a_file_with_unread_regions_is_never_skipped() {
    let mut d = Doc::new("a.rs", "rust");
    let hole = d.add(Operator::opaque("unread", b"?"), None, &[]);
    let (m, _) = d.root(&[hole]);
    let plan = find_plan("call");
    let got = outcomes_prefiltered(&plan, &input(&m), &Relations::new()).unwrap();
    assert!(!got.is_skipped());
}

// frob:ticket 01M3ZX7F57JCT6CZXY5VS9RHTR
// frob:tests crates/gob-plan/src/exec/prefilter.rs::outcomes_prefiltered
#[test]
fn a_kind_the_executor_cannot_test_is_refused_not_skipped() {
    let m = funcs(&["a"]);
    let err = outcomes_prefiltered(&find_plan("no_such_kind"), &input(&m), &Relations::new())
        .unwrap_err();
    assert!(matches!(err, ExecError::UnsupportedKind { .. }), "{err:?}");
}
