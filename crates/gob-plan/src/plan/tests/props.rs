//! Properties: arbitrary and mutated bytes never panic and never yield an invalid plan.

use proptest::prelude::*;

use super::{sample, *};

/// The security invariant for any bytes: refused with a reason, or valid and canonical.
fn check_bytes(bytes: &[u8]) {
    if let Ok(plan) = Plan::load(bytes) {
        assert!(
            validate::validate(plan.parts()).is_ok(),
            "accepted plan fails the validator"
        );
        assert_eq!(
            plan.to_bytes(),
            bytes,
            "accepted bytes do not round-trip exactly"
        );
        assert_eq!(Plan::load(&plan.to_bytes()), Ok(plan));
    }
}

fn seed() -> Vec<u8> {
    Plan::new(sample()).expect("valid").to_bytes()
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(2000))]

    #[test]
    fn arbitrary_bytes_are_safe(bytes in proptest::collection::vec(any::<u8>(), 0..600)) {
        check_bytes(&bytes);
    }

    #[test]
    fn arbitrary_bytes_behind_a_valid_header_are_safe(tail in proptest::collection::vec(any::<u8>(), 0..600)) {
        let mut bytes = seed()[..10].to_vec();
        bytes.extend(tail);
        check_bytes(&bytes);
    }

    #[test]
    fn mutated_valid_plans_are_safe(
        edits in proptest::collection::vec((any::<prop::sample::Index>(), any::<u8>(), 0u8..3), 1..6),
    ) {
        let mut bytes = seed();
        for (at, val, how) in edits {
            if bytes.is_empty() { break; }
            let i = at.index(bytes.len());
            match how {
                0 => bytes[i] = val,
                1 => bytes.insert(i, val),
                _ => { bytes.remove(i); }
            }
        }
        check_bytes(&bytes);
    }

    #[test]
    fn truncated_valid_plans_are_refused(cut in 0usize..10_000) {
        let bytes = seed();
        let n = cut % bytes.len();
        prop_assert!(Plan::load(&bytes[..n]).is_err());
    }
}

/// A random structurally-small plan: ids are drawn from tiny ranges so some are valid.
fn arb_op() -> impl Strategy<Value = Op> {
    let var = 0u16..4;
    let st = 0u32..4;
    let id = 0u32..8;
    let operand = prop_oneof![
        var.clone().prop_map(Operand::Var),
        (var.clone(), st.clone()).prop_map(|(v, f)| Operand::Field(v, f)),
        any::<i64>().prop_map(Operand::Int),
        st.clone().prop_map(Operand::Str),
        any::<bool>().prop_map(Operand::Bool),
    ];
    prop_oneof![
        (var.clone(), st.clone()).prop_map(|(var, kind)| Op::Find { var, kind }),
        (var.clone(), st.clone()).prop_map(|(var, table)| Op::FindSide {
            var,
            need: Need::Diff,
            table
        }),
        proptest::collection::vec(id.clone(), 0..3).prop_map(Op::And),
        proptest::collection::vec(id.clone(), 0..3).prop_map(Op::Or),
        id.clone().prop_map(Op::Not),
        (var.clone(), var.clone(), any::<bool>()).prop_map(|(sub, sup, direct)| Op::Inside {
            sub,
            sup,
            direct
        }),
        (var.clone(), var, 0u16..4).prop_map(|(from, to, within)| Op::Reaches {
            from,
            to,
            via: 0,
            within,
            certainty: Certainty::Default
        }),
        (operand.clone(), operand).prop_map(|(lhs, rhs)| Op::Cmp {
            lhs,
            op: CmpOp::Lt,
            rhs
        }),
    ]
}

fn arb_parts() -> impl Strategy<Value = PlanParts> {
    (
        proptest::collection::vec(arb_op(), 0..8),
        proptest::collection::vec(0u32..8, 0..5),
        proptest::collection::vec((proptest::option::of(0u32..8), 0u16..4), 1..3),
        0u16..5,
        proptest::collection::vec(0u32..4, 0..3),
        0u8..4,
    )
        .prop_map(|(ops, clauses, reports, vars, prefilter, cost)| PlanParts {
            rule: "NEAT013".into(),
            provenance: Provenance::Std,
            polarity: Polarity::Pplus,
            langs: Langs::Any,
            needs: NeedSet::of(&[Need::Diff]),
            prefilter,
            cost: match cost {
                0 => CostClass::PerFile,
                1 => CostClass::PerRepo,
                n => CostClass::Closure(u16::from(n)),
            },
            vars,
            strings: ["a", "b", "c", "d"].map(String::from).to_vec(),
            ops,
            defs: vec![],
            clauses,
            reports: reports
                .into_iter()
                .map(|(when, subject)| Report {
                    when,
                    subject,
                    message: 0,
                })
                .collect(),
        })
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(5000))]

    #[test]
    fn any_plan_value_is_either_refused_or_round_trips(parts in arb_parts()) {
        let bytes = codec::encode(&parts);
        match Plan::new(parts.clone()) {
            Ok(plan) => {
                prop_assert_eq!(Plan::load(&bytes), Ok(plan.clone()));
                prop_assert_eq!(plan.to_bytes(), bytes);
            }
            Err(e) => prop_assert_eq!(Plan::load(&bytes), Err(e)),
        }
    }
}

/// Plans valid by construction: a chain of finds, then random relations over bound variables.
fn arb_valid() -> impl Strategy<Value = PlanParts> {
    (
        1u16..5,
        proptest::collection::vec((0u16..4, 0u16..4, 0u8..3), 0..6),
    )
        .prop_map(|(vars, rels)| {
            let strings: Vec<String> = (0..vars).map(|i| format!("kind{i}")).collect();
            let mut ops: Vec<Op> = (0..vars)
                .map(|v| Op::Find {
                    var: v,
                    kind: u32::from(v),
                })
                .collect();
            for (a, b, k) in rels {
                let (a, b) = (a % vars, b % vars);
                ops.push(match k {
                    0 => Op::Inside {
                        sub: a,
                        sup: b,
                        direct: false,
                    },
                    1 => Op::Order {
                        a,
                        b,
                        pos: Position::Before,
                    },
                    _ => Op::Cmp {
                        lhs: Operand::Var(a),
                        op: CmpOp::Ne,
                        rhs: Operand::Var(b),
                    },
                });
            }
            let clauses = (0..u32::try_from(ops.len()).expect("small")).collect();
            PlanParts {
                rule: "TODO001".into(),
                provenance: Provenance::Pack("p".into()),
                polarity: Polarity::Pplus,
                langs: Langs::Nothing,
                needs: NeedSet::default(),
                prefilter: (0..u32::from(vars)).collect(),
                cost: CostClass::PerFile,
                vars,
                strings,
                ops,
                defs: vec![],
                clauses,
                reports: vec![Report {
                    when: None,
                    subject: 0,
                    message: 0,
                }],
            }
        })
}

proptest! {
    #[test]
    fn valid_plans_round_trip_exactly(parts in arb_valid()) {
        let plan = Plan::new(parts).expect("valid by construction");
        let bytes = plan.to_bytes();
        prop_assert_eq!(Plan::load(&bytes), Ok(plan));
        check_bytes(&bytes);
    }
}
