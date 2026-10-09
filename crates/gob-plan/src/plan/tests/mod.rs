//! Plan format tests: round trips, every rejection reason, and hostile-byte properties.

mod props;

use super::*;

/// A valid plan using every op family; also the seed for mutation properties.
#[allow(
    clippy::too_many_lines,
    reason = "one flat match or field list per wire item"
)]
pub(super) fn sample() -> PlanParts {
    let strings = [
        "function",
        "call",
        "changed",
        "calls",
        "name",
        "main",
        "avoid {f.name}",
        "todo",
        "max_callers",
    ]
    .map(String::from)
    .to_vec();
    PlanParts {
        rule: "NEAT013".into(),
        provenance: Provenance::Pack("acme-pack".into()),
        polarity: Polarity::Pminus,
        langs: Langs::Only(vec![0, 4]),
        needs: NeedSet::of(&[Need::Diff]),
        prefilter: vec![0],
        cost: CostClass::Closure(3),
        vars: 5,
        strings,
        ops: vec![
            Op::Find { var: 0, kind: 0 },
            Op::FindSide {
                var: 1,
                need: Need::Diff,
                table: 2,
            },
            Op::Cmp {
                lhs: Operand::Field(0, 4),
                op: CmpOp::Eq,
                rhs: Operand::Str(5),
            },
            Op::Verb {
                subject: 0,
                object: 1,
                verb: 3,
                certainty: Certainty::Default,
            },
            Op::Reaches {
                from: 0,
                to: 2,
                via: 3,
                within: 3,
                certainty: Certainty::Certainly,
            },
            Op::Quant {
                quant: Quant::Some,
                var: 2,
                kind: 1,
                cond: 4,
            },
            Op::Not(5),
            Op::MatchRegex {
                subject: Operand::Field(0, 4),
                pattern: 7,
            },
            // The def body, then a count against a knob and a call of the def.
            Op::Cmp {
                lhs: Operand::Field(4, 4),
                op: CmpOp::Eq,
                rhs: Operand::Str(5),
            },
            Op::Inside {
                sub: 3,
                sup: 0,
                direct: false,
            },
            Op::CountCmp {
                var: 3,
                kind: 1,
                cond: 9,
                op: CmpOp::Gt,
                limit: Limit::Knob {
                    name: 8,
                    default: 3,
                },
            },
            Op::Call {
                def: 0,
                args: vec![0],
            },
        ],
        defs: vec![Def {
            params: vec![4],
            body: 8,
        }],
        clauses: vec![0, 1, 2, 3, 6, 10, 11],
        reports: vec![
            Report {
                when: Some(7),
                subject: 0,
                message: 6,
            },
            Report {
                when: None,
                subject: 0,
                message: 6,
            },
        ],
    }
}

fn err(p: PlanParts) -> PlanError {
    Plan::new(p).expect_err("plan should be rejected")
}

// frob:tests crates/gob-plan/src/plan/mod.rs::Plan.to_bytes
#[test]
fn round_trip_keeps_every_header_field() {
    let plan = Plan::new(sample()).expect("sample is valid");
    let back = Plan::load(&plan.to_bytes()).expect("round trip");
    assert_eq!(back, plan);
    assert_eq!(back.rule(), "NEAT013");
    assert_eq!(back.provenance(), &Provenance::Pack("acme-pack".into()));
    assert_eq!(back.polarity(), Polarity::Pminus);
    assert!(back.needs().contains(Need::Diff) && !back.needs().contains(Need::Lease));
    assert_eq!(back.prefilter_kinds().collect::<Vec<_>>(), ["function"]);
    assert_eq!(back.cost(), CostClass::Closure(3));
    assert_eq!(back.to_bytes(), plan.to_bytes());
}

#[test]
fn std_provenance_and_other_polarities_round_trip() {
    for pol in [
        Polarity::Pplus,
        Polarity::Pminus,
        Polarity::P0,
        Polarity::Pn,
        Polarity::Pc,
    ] {
        let mut p = sample();
        p.provenance = Provenance::Std;
        p.polarity = pol;
        let plan = Plan::new(p).expect("valid");
        assert_eq!(Plan::load(&plan.to_bytes()).expect("load"), plan);
    }
}

#[test]
fn embedded_load_matches_checked_load() {
    let bytes: &'static [u8] = Box::leak(
        Plan::new(sample())
            .expect("valid")
            .to_bytes()
            .into_boxed_slice(),
    );
    assert_eq!(
        Plan::load_embedded(bytes).expect("embedded"),
        Plan::load(bytes).expect("checked")
    );
}

// frob:tests crates/gob-plan/src/plan/mod.rs::Plan.load
#[test]
fn every_truncation_is_an_error() {
    let bytes = Plan::new(sample()).expect("valid").to_bytes();
    for n in 0..bytes.len() {
        assert!(
            Plan::load(&bytes[..n]).is_err(),
            "prefix of {n} bytes was accepted"
        );
    }
}

#[test]
fn header_defects_are_named() {
    let bytes = Plan::new(sample()).expect("valid").to_bytes();
    let mut bad = bytes.clone();
    bad[0] ^= 0xff;
    assert_eq!(Plan::load(&bad), Err(PlanError::BadMagic));
    let mut bad = bytes.clone();
    bad[8] = 9;
    assert!(matches!(
        Plan::load(&bad),
        Err(PlanError::UnsupportedVersion { found: 9, .. })
    ));
    let mut bad = bytes;
    bad.push(0);
    assert_eq!(Plan::load(&bad), Err(PlanError::TrailingBytes { extra: 1 }));
}

#[test]
fn hostile_counts_do_not_allocate_or_panic() {
    let mut bytes = Plan::new(sample()).expect("valid").to_bytes();
    // Overwrite the string count (after magic, version, rule, provenance, ..) by scanning for it.
    let at = bytes
        .windows(4)
        .position(|w| w == 9u32.to_le_bytes())
        .expect("string count");
    bytes[at..at + 4].copy_from_slice(&u32::MAX.to_le_bytes());
    assert!(matches!(
        Plan::load(&bytes),
        Err(PlanError::TooLarge { .. })
    ));
}

#[test]
fn out_of_range_references_are_rejected() {
    let mut p = sample();
    p.ops[2] = Op::Cmp {
        lhs: Operand::Field(0, 99),
        op: CmpOp::Eq,
        rhs: Operand::Int(1),
    };
    assert!(matches!(
        err(p),
        PlanError::OutOfRange {
            what: "string",
            index: 99,
            ..
        }
    ));
    let mut p = sample();
    p.clauses.push(500);
    assert!(matches!(err(p), PlanError::OutOfRange { what: "op", .. }));
    let mut p = sample();
    p.reports[0].subject = 7;
    assert!(matches!(
        err(p),
        PlanError::OutOfRange {
            what: "variable",
            ..
        }
    ));
    let mut p = sample();
    p.prefilter = vec![50];
    assert!(matches!(
        err(p),
        PlanError::OutOfRange { what: "string", .. }
    ));
}

// frob:tests crates/gob-plan/src/plan/validate.rs::validate
#[test]
fn cycles_and_forward_references_are_rejected_from_bytes() {
    let mut p = sample();
    p.ops[6] = Op::Not(6);
    assert_eq!(
        Plan::load(&codec::encode(&p)),
        Err(PlanError::Cyclic { op: 6, target: 6 })
    );
    let mut p = sample();
    p.ops[5] = Op::Quant {
        quant: Quant::Some,
        var: 2,
        kind: 1,
        cond: 6,
    };
    assert_eq!(
        Plan::load(&codec::encode(&p)),
        Err(PlanError::Cyclic { op: 5, target: 6 })
    );
}

#[test]
fn shared_and_orphan_ops_are_rejected() {
    let mut p = sample();
    p.clauses.push(2);
    assert_eq!(err(p), PlanError::SharedOp { op: 2 });
    let mut p = sample();
    p.ops.push(Op::And(vec![]));
    assert_eq!(err(p), PlanError::OrphanOp { op: 12 });
}

#[test]
fn deep_nesting_is_rejected_not_overflowed() {
    let mut p = sample();
    p.ops.truncate(8);
    p.defs.clear();
    for i in 8..4000u32 {
        p.ops.push(Op::Not(i - 1));
    }
    p.clauses = vec![0, 1, 2, 3, 6, 3999];
    p.ops[6] = Op::Not(5);
    // op 7 is the report guard; the chain starts from it.
    p.ops[8] = Op::Not(7);
    p.reports[0].when = None;
    assert!(matches!(err(p), PlanError::TooDeep { .. }));
}

#[test]
fn binding_defects_are_rejected() {
    let mut p = sample();
    p.clauses = vec![2, 0, 1, 3, 6];
    assert_eq!(err(p), PlanError::Unbound { var: 0 });
    let mut p = sample();
    p.ops[1] = Op::FindSide {
        var: 0,
        need: Need::Diff,
        table: 2,
    };
    assert_eq!(err(p), PlanError::Rebound { var: 0 });
    let mut p = sample();
    p.vars = 4;
    assert_eq!(err(p), PlanError::UnusedVar { var: 3 });
    let mut p = sample();
    p.reports[0].subject = 2;
    assert_eq!(err(p), PlanError::Unbound { var: 2 });
}

#[test]
fn needs_prefilter_and_cost_must_agree_with_the_ops() {
    let mut p = sample();
    p.needs = NeedSet::default();
    assert_eq!(err(p), PlanError::UndeclaredNeed { need: "diff" });
    let mut p = sample();
    p.prefilter = vec![];
    assert_eq!(
        err(p),
        PlanError::PrefilterMissing {
            kind: "function".into()
        }
    );
    let mut p = sample();
    p.cost = CostClass::PerFile;
    assert!(matches!(err(p), PlanError::CostMismatch { .. }));
    let mut p = sample();
    p.cost = CostClass::Closure(9);
    assert!(matches!(err(p), PlanError::CostMismatch { .. }));
}

#[test]
fn names_and_canonical_sets_are_checked() {
    let mut p = sample();
    p.rule = "nope".into();
    assert!(matches!(
        err(p),
        PlanError::Invalid {
            what: "rule id",
            ..
        }
    ));
    let mut p = sample();
    p.provenance = Provenance::Pack("Bad Name".into());
    assert!(matches!(
        err(p),
        PlanError::Invalid {
            what: "pack name",
            ..
        }
    ));
    let mut p = sample();
    p.langs = Langs::Only(vec![4, 0]);
    assert!(matches!(err(p), PlanError::NotCanonical { .. }));
    let mut p = sample();
    p.needs = NeedSet(0x80);
    assert!(matches!(err(p), PlanError::Invalid { what: "needs", .. }));
    let mut p = sample();
    p.ops[4] = Op::Reaches {
        from: 0,
        to: 2,
        via: 3,
        within: 0,
        certainty: Certainty::Default,
    };
    assert!(matches!(err(p), PlanError::Invalid { what: "within", .. }));
    let mut p = sample();
    p.reports.clear();
    assert!(matches!(
        err(p),
        PlanError::Invalid {
            what: "reports",
            ..
        }
    ));
}

#[test]
fn a_find_nested_in_a_condition_is_misplaced() {
    let mut p = sample();
    p.ops[6] = Op::Not(5);
    p.ops[7] = Op::And(vec![]);
    p.ops[2] = Op::Find { var: 2, kind: 0 };
    p.clauses = vec![0, 1, 3, 6];
    p.ops.push(Op::Not(2));
    p.reports[0].when = Some(8);
    p.reports[1].when = Some(7);
    assert!(matches!(err(p), PlanError::Misplaced { op: 2, .. }));
}

// frob:tests crates/gob-plan/src/plan/mod.rs::Plan.parts
// frob:tests crates/gob-plan/src/plan/mod.rs::Plan.rule
// frob:tests crates/gob-plan/src/plan/mod.rs::Plan.polarity
// frob:tests crates/gob-plan/src/plan/mod.rs::Plan.cost
// frob:tests crates/gob-plan/src/plan/ir.rs::NeedSet.iter
#[test]
fn accessors_expose_the_validated_fields() {
    let plan = Plan::new(sample()).expect("valid");
    assert_eq!(plan.parts(), &sample());
    assert_eq!(plan.rule(), "NEAT013");
    assert_eq!(plan.polarity(), Polarity::Pminus);
    assert_eq!(plan.cost(), CostClass::Closure(3));
    assert_eq!(plan.needs().iter().collect::<Vec<_>>(), [Need::Diff]);
    assert_eq!(
        NeedSet::of(&[Need::Model, Need::Config])
            .iter()
            .collect::<Vec<_>>(),
        [Need::Config, Need::Model]
    );
}

// frob:tests crates/gob-plan/src/plan/validate.rs::validate
#[test]
fn count_limits_and_def_calls_are_checked() {
    // The sample round-trips with a knob limit, a def and a call (see `sample`).
    let plan = Plan::new(sample()).expect("valid");
    assert!(plan.parts().ops.iter().any(|o| matches!(
        o,
        Op::CountCmp {
            limit: Limit::Knob { .. },
            ..
        }
    )));
    assert_eq!(Plan::load(&plan.to_bytes()).expect("load"), plan);

    // A def may not call itself or a later def.
    let mut p = sample();
    p.ops[8] = Op::Call {
        def: 0,
        args: vec![4],
    };
    assert!(matches!(err(p), PlanError::Misplaced { op: 8, .. }));
    // A call names a def that exists, with as many arguments as parameters.
    let mut p = sample();
    p.ops[11] = Op::Call {
        def: 3,
        args: vec![0],
    };
    assert!(matches!(err(p), PlanError::OutOfRange { what: "def", .. }));
    let mut p = sample();
    p.ops[11] = Op::Call {
        def: 0,
        args: vec![0, 0],
    };
    assert!(matches!(err(p), PlanError::Invalid { what: "call", .. }));
    // The knob's name is a pooled string.
    let mut p = sample();
    p.ops[10] = Op::CountCmp {
        var: 3,
        kind: 1,
        cond: 9,
        op: CmpOp::Gt,
        limit: Limit::Knob {
            name: 99,
            default: 3,
        },
    };
    assert!(matches!(
        err(p),
        PlanError::OutOfRange {
            what: "string",
            index: 99,
            ..
        }
    ));
    // A def body sees only its parameters, not the rule's variables.
    let mut p = sample();
    p.ops[8] = Op::Cmp {
        lhs: Operand::Field(0, 4),
        op: CmpOp::Eq,
        rhs: Operand::Str(5),
    };
    assert_eq!(err(p), PlanError::Unbound { var: 0 });
}

#[test]
fn a_later_def_may_call_an_earlier_one() {
    let mut p = sample();
    // Def 1 (param 2 is bound by the rule's quantifier, so use a fresh slot) calls def 0.
    p.vars = 6;
    p.ops.push(Op::Call {
        def: 0,
        args: vec![5],
    });
    p.defs.push(Def {
        params: vec![5],
        body: 12,
    });
    p.ops.push(Op::Call {
        def: 1,
        args: vec![0],
    });
    p.clauses.push(13);
    let plan = Plan::new(p).expect("def 1 calls def 0");
    assert_eq!(Plan::load(&plan.to_bytes()).expect("load"), plan);
}
