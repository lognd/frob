//! Lowering a checked rule to a plan: shape, clause-order independence, and honest refusals.

// frob:ticket 01M3ZX7EKNE5Q0NB0DKCH77AZX

use gob_plan::grl::parse;
use gob_plan::lower::{LowerError, lower_rule};
use gob_plan::plan::{CmpOp, CountSide, Op, Operand, Plan, Polarity, Provenance, Scale};
use gob_text::FileInterner;

fn lower(src: &str) -> Result<Plan, LowerError> {
    let parsed = parse(FileInterner::new().intern("rules/T.grl"), src);
    assert!(parsed.is_ok(), "{:?}\n{src}", parsed.errors);
    lower_rule(&parsed.file.rules[0], Provenance::Std)
}

fn fixtures() -> Vec<(String, String)> {
    let dir = format!(
        "{}/src/grl/parse/tests/fixtures",
        env!("CARGO_MANIFEST_DIR")
    );
    let mut out: Vec<(String, String)> = std::fs::read_dir(&dir)
        .expect("fixtures dir")
        .filter_map(Result::ok)
        .filter(|e| e.path().extension().is_some_and(|x| x == "grl"))
        .map(|e| {
            (
                gob_path::Shown::with_home(std::path::Path::new(&e.file_name()), None).to_string(),
                std::fs::read_to_string(e.path()).expect("fixture reads"),
            )
        })
        .collect();
    out.sort();
    out
}

const BODY: [&str; 5] = [
    "find f: function",
    "find c: call where c inside f and c.name == \"unwrap\"",
    "no t: test where c inside t",
    "where c.line >= 1 and f.name ~ /^[a-z]/i",
    "report c \"unwrap in {f.name}\"",
];

const EXPLAIN: &str = "  explain \"\"\"\n    Why.\n    ## Remedy\n    Fix.\n  \"\"\"\n";

fn rule(lines: &[&str]) -> String {
    format!(
        "rule TST001 \"t\" {{\n  lang rust\n  {}\n{EXPLAIN}}}\n",
        lines.join("\n  ")
    )
}

// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn the_section_12_rules_built_from_covered_constructs_lower_to_valid_plans() {
    let all = fixtures();
    let mut lowered = Vec::new();
    for (name, src) in &all {
        match lower(src) {
            Ok(plan) => {
                assert_eq!(Plan::load(&plan.to_bytes()).expect("round trips"), plan);
                lowered.push(name.as_str());
            }
            Err(LowerError::Unsupported { .. }) => {}
            Err(e) => panic!("{name}: refused for the wrong reason: {e}"),
        }
    }
    assert_eq!(
        lowered,
        [
            "CAP001.grl",
            "CI002.grl",
            "COV001.grl",
            "DOC002.grl",
            "INV002.grl",
            "NEAT013.grl",
            "NEAT031.grl",
            "NOPE001.grl",
            "SCOPE001.grl",
            "SYS001.grl",
            "TODO001.grl"
        ]
    );
}

// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn the_same_clauses_in_every_order_lower_to_byte_identical_plans() {
    let want = lower(&rule(&BODY)).expect("lowers").to_bytes();
    let mut orders = 0;
    for rot in 0..4 {
        for flip in [false, true] {
            let mut lines = BODY[..4].to_vec();
            lines.rotate_left(rot);
            if flip {
                lines.reverse();
            }
            lines.push(BODY[4]);
            let got = lower(&rule(&lines)).expect("lowers").to_bytes();
            assert_eq!(got, want, "order {lines:?}");
            orders += 1;
        }
    }
    assert_eq!(orders, 8);
}

// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn a_p_minus_rule_splits_its_subjects_from_the_good_thing() {
    let src = &format!(
        "rule TST002 \"t\" {{\n  lang rust\n  polarity P-\n  no t: test where f inside t\n  find f: function where f.public\n  report f \"untested\"\n{EXPLAIN}}}\n"
    );
    let plan = lower(src).expect("lowers");
    assert_eq!(plan.polarity(), Polarity::Pminus);
    let p = plan.parts();
    assert_eq!(p.subjects, 2, "the find and its filter are subjects");
    assert!(matches!(p.ops[p.clauses[0] as usize], Op::Find { .. }));
    assert_eq!(p.clauses.len(), 3);
}

// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn constructs_outside_the_ir_are_refused_by_name_not_mislowered() {
    let roles = rule(&["find c: rust`$X.unwrap()` as roles", "report c \"x\""]);
    assert!(matches!(
        lower(&roles),
        Err(LowerError::Unsupported {
            what: "a snippet as roles",
            ..
        })
    ));
    let vocab = &format!(
        "rule TST003 \"t\" {{\n  knob v: list<int> = [1] \"d\"\n  find f: function where f.name == knob.v\n  report f \"x\"\n{EXPLAIN}}}\n"
    );
    assert!(matches!(lower(vocab), Err(LowerError::Unsupported { .. })));
    let unbound = rule(&["find c: call where h.x == 1", "report c \"x\""]);
    assert!(matches!(
        lower(&unbound),
        Err(LowerError::UnknownVar { .. })
    ));
}

// frob:ticket 01M3ZX7EQ5NARR4Z2SAY4H23AQ
#[test]
fn the_prefilter_lists_exactly_the_found_kinds_and_not_negated_ones() {
    let plan = lower(&rule(&[
        "find d: directive",
        "find c: comment where c inside d or d inside c",
        "no t: test where c inside t",
        "report c \"x\"",
    ]))
    .expect("lowers");
    let mut kinds: Vec<&str> = plan.prefilter_kinds().collect();
    kinds.sort_unstable();
    assert_eq!(kinds, ["comment", "directive"]);
}

fn knob_rule(knob: &str, clause: &str) -> String {
    format!(
        "rule TST004 \"t\" {{\n  lang rust\n  {knob}\n  find f: function {clause}\n  report f \"x\"\n{EXPLAIN}}}\n"
    )
}

// frob:ticket 01M4WGCDCJVBP0SZ33BC6W2KWJ
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn int_string_bool_and_regex_knobs_lower_at_their_declared_defaults() {
    for (knob, clause) in [
        ("knob n: int = 3 \"d\"", "where f.line >= knob.n"),
        ("knob s: string = \"x\" \"d\"", "where f.name == knob.s"),
        ("knob b: bool = true \"d\"", "where f.public == knob.b"),
        ("knob r: regex = /^t/i \"d\"", "where f.name ~ knob.r"),
        (
            "knob g: glob = \"src/**\" \"d\"",
            "where f.path matches knob.g",
        ),
    ] {
        let plan = lower(&knob_rule(knob, clause));
        assert!(plan.is_ok(), "{knob} {clause}: {plan:?}");
    }
}

// frob:ticket 01M4WGCDCJVBP0SZ33BC6W2KWJ
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn an_undeclared_knob_is_an_unknown_var() {
    let src = knob_rule("knob n: int = 3 \"d\"", "where f.line >= knob.m");
    assert!(matches!(lower(&src), Err(LowerError::UnknownVar { .. })));
}

// frob:ticket 01M4WGCDG1786P1D7BT26X4K6K
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn in_is_exists_has_attr_under_and_in_unit_lower() {
    for clause in [
        "where f.name in [\"a\", \"b\"]",
        "where f.line in 1..10",
        "where f is public",
        "where exists f.name",
        "where f has attr \"cfg\"",
        "where f.path under \"src\"",
        "where f is relative_is_not_a_word_but_kinds_are_checked_at_run",
    ] {
        let src = knob_rule("", clause);
        let plan = lower(&src);
        let want_ok = !clause.contains("relative_is_not");
        assert_eq!(plan.is_ok(), want_ok, "{clause}: {plan:?}");
    }
}

// frob:ticket 01M4WGCDG1786P1D7BT26X4K6K
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn in_unit_lowers_with_an_object() {
    let src = rule(&[
        "find u: module",
        "find f: function where f in unit u",
        "report f \"x\"",
    ]);
    assert!(lower(&src).is_ok(), "{:?}", lower(&src));
}

fn def_rule(defs: &[&str], body: &[&str]) -> String {
    let mut lines: Vec<&str> = defs.to_vec();
    lines.extend_from_slice(body);
    rule(&lines)
}

// frob:ticket 01M4WGCDK2ND23SEPX38Q9444T
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn defs_and_calls_lower_to_views_and_call_ops() {
    let src = def_rule(
        &[
            "def is_x(f) = f.name == \"x\"",
            "def is_x_and_long(f) = is_x(f) and f.line > 3",
        ],
        &[
            "find g: function",
            "where is_x_and_long(g)",
            "report g \"x\"",
        ],
    );
    let plan = lower(&src).expect("defs lower");
    let parts = plan.parts();
    assert_eq!(parts.defs.len(), 2);
    assert_eq!(parts.defs[0].params.len(), 1);
    let calls = parts
        .ops
        .iter()
        .filter(|o| matches!(o, Op::Call { .. }))
        .count();
    assert_eq!(
        calls, 2,
        "one call in the body of the second def, one in the rule"
    );
}

// frob:ticket 01M4WGCDK2ND23SEPX38Q9444T
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn a_call_with_the_wrong_arity_or_an_unknown_def_is_refused() {
    for body in ["where nope(g)", "where is_x(g, g)"] {
        let src = def_rule(
            &["def is_x(f) = f.name == \"x\""],
            &["find g: function", body, "report g \"x\""],
        );
        assert!(
            matches!(lower(&src), Err(LowerError::Unsupported { .. })),
            "{body}"
        );
    }
}

// frob:ticket 01M4WGCDK2ND23SEPX38Q9444T
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn count_lowers_against_an_integer_or_a_knob_in_either_order() {
    for (knob, clause) in [
        ("", "where count(c: call directly inside f) > 3"),
        ("", "where 3 < count(c: call directly inside f)"),
        (
            "knob n: int = 4 \"d\"",
            "where count(c: call directly inside f where c.name == \"a\") >= knob.n",
        ),
    ] {
        let plan = lower(&knob_rule(knob, clause)).unwrap_or_else(|e| panic!("{clause}: {e}"));
        let counts: Vec<&Op> = plan
            .parts()
            .ops
            .iter()
            .filter(|o| matches!(o, Op::CountCmp { .. }))
            .collect();
        assert_eq!(counts.len(), 1, "{clause}");
    }
    let flipped = lower(&knob_rule("", "where 3 < count(c: call directly inside f)")).unwrap();
    let plain = lower(&knob_rule("", "where count(c: call directly inside f) > 3")).unwrap();
    assert_eq!(flipped.to_bytes(), plain.to_bytes());
}

// frob:ticket 01M5GA77VTC3VDYVZ2HBZNRM2K
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn a_scaled_count_compared_with_a_non_count_is_refused() {
    for clause in [
        "where 2 * count(c: call directly inside f) > 3.5",
        "where count(c: call directly inside f) >= 1.5 * 2",
        "where count(c: call directly inside f) >= 0.1234567890123456789 * count(c: call directly inside f)",
    ] {
        let src = knob_rule("", clause);
        assert!(
            matches!(lower(&src), Err(LowerError::Unsupported { .. })),
            "{clause}"
        );
    }
}

fn pairs(plan: &Plan) -> Vec<(CountSide, CmpOp, CountSide)> {
    plan.parts()
        .ops
        .iter()
        .filter_map(|o| match o {
            Op::CountPair { lhs, op, rhs } => Some((*lhs, *op, *rhs)),
            _ => None,
        })
        .collect()
}

// frob:ticket 01M5GA77VTC3VDYVZ2HBZNRM2K
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn a_count_against_a_scaled_count_lowers_to_a_count_pair() {
    let knob = "knob ratio: float = 0.75 \"d\"";
    let c = "count(c: call directly inside f)";
    let right = lower(&knob_rule(knob, &format!("where {c} >= knob.ratio * {c}"))).unwrap();
    let p = pairs(&right);
    assert_eq!(p.len(), 1);
    assert_eq!(p[0].0.scale, Scale::ONE);
    assert_eq!(p[0].2.scale, Scale { num: 75, places: 2 });
    let left = lower(&knob_rule(knob, &format!("where knob.ratio * {c} <= {c}"))).unwrap();
    let p = pairs(&left);
    assert_eq!(p[0].0.scale, Scale { num: 75, places: 2 });
    assert_eq!(p[0].2.scale, Scale::ONE);
}

// frob:ticket 01M5GA77VTC3VDYVZ2HBZNRM2K
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn count_pair_scales_cover_int_negative_zero_and_literal_factors() {
    let c = "count(c: call directly inside f)";
    let cases = [
        (
            "knob ratio: int = 3 \"d\"",
            "knob.ratio * ",
            Scale { num: 3, places: 0 },
        ),
        (
            "knob ratio: float = -1.5 \"d\"",
            "knob.ratio * ",
            Scale {
                num: -15,
                places: 1,
            },
        ),
        (
            "knob ratio: float = 0.0 \"d\"",
            "knob.ratio * ",
            Scale { num: 0, places: 1 },
        ),
        ("", "0.25 * ", Scale { num: 25, places: 2 }),
        ("", "2 * ", Scale { num: 2, places: 0 }),
    ];
    for (knob, factor, want) in cases {
        let plan = lower(&knob_rule(knob, &format!("where {c} > {factor}{c}"))).unwrap();
        let p = pairs(&plan);
        assert_eq!(p.len(), 1, "{factor}");
        assert_eq!(p[0].2.scale, want, "{knob} {factor}");
    }
}

// frob:ticket 01M5GA77VTC3VDYVZ2HBZNRM2K
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn an_alternative_of_plain_kinds_lowers_and_one_with_fields_is_refused() {
    let alt = |shape: &str| {
        lower(&format!(
            "rule TST005 \"t\" {{\n  lang rust\n  find b: {shape}\n  report b \"x\"\n{EXPLAIN}}}\n"
        ))
    };
    let plan = alt("(branch | loop)").expect("a plain alternative lowers");
    assert!(plan.parts().ops.iter().any(|o| matches!(o, Op::Or(_))));
    assert!(matches!(
        alt("(branch | loop(name = \"x\"))"),
        Err(LowerError::Unsupported { .. })
    ));
}

// frob:ticket 01M5GA77VTC3VDYVZ2HBZNRM2K
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn nested_counts_in_a_count_pair_lower_to_separate_counts() {
    let src = knob_rule(
        "",
        "where count(c: call directly inside f) >= 2 * count(a: assignment inside f where count(c: call inside a) >= 1)",
    );
    let plan = lower(&src).unwrap();
    assert_eq!(pairs(&plan).len(), 1);
    let cmps = plan
        .parts()
        .ops
        .iter()
        .filter(|o| matches!(o, Op::CountCmp { .. }))
        .count();
    assert_eq!(cmps, 1);
}

// frob:ticket 01M4WGCDK2ND23SEPX38Q9444T
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn paths_of_three_or_more_segments_are_dotted_field_operands() {
    let src = knob_rule("", "where exists f.target.anchor and f.a.b.c == \"x\"");
    let plan = lower(&src).expect("deep paths lower");
    assert!(plan.parts().strings.iter().any(|s| s == "target.anchor"));
    assert!(plan.parts().strings.iter().any(|s| s == "a.b.c"));
}

fn reaches_rule(knob: &str, tail: &str) -> String {
    knob_rule(
        knob,
        &format!("\n  find g: function where f reaches g {tail}"),
    )
}

// frob:ticket 01M4WGCDP6MTWDWNGRTNVMH9MV
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn reaches_lowers_with_a_literal_or_knob_within_bound() {
    for (knob, tail) in [
        ("", "via calls within 4"),
        ("knob n: int = 3 \"d\"", "via calls within knob.n"),
    ] {
        let plan = lower(&reaches_rule(knob, tail)).expect("reaches lowers");
        assert!(
            plan.parts()
                .ops
                .iter()
                .any(|o| matches!(o, Op::Reaches { .. })),
            "{tail}"
        );
    }
}

// frob:ticket 01M4WGCDP6MTWDWNGRTNVMH9MV
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn reaches_without_a_usable_bound_or_with_many_verbs_is_refused() {
    for (knob, tail) in [
        ("", "via calls"),
        ("", "via calls within 0"),
        ("", "via calls within 70000"),
        ("knob s: string = \"x\" \"d\"", "via calls within knob.s"),
        ("", "via calls, imports within 2"),
    ] {
        let r = lower(&reaches_rule(knob, tail));
        assert!(
            matches!(r, Err(LowerError::Unsupported { .. })),
            "{tail}: {r:?}"
        );
    }
}

// frob:ticket 01M4X779QGF0CRSE952A3BARD0
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn a_kind_string_argument_tests_the_name_as_binder_and_as_relation_object() {
    let binder = rule(&["find d: directive \"todo\"", "report d \"x\""]);
    let plan = lower(&binder).expect("binder lowers");
    assert!(plan.parts().strings.iter().any(|s| s == "todo"));
    let object = rule(&[
        "find c: comment",
        "no d: directive \"todo\" where d adjoins c",
        "report c \"x\"",
    ]);
    let plan = lower(&object).expect("quantifier lowers");
    assert!(plan.parts().strings.iter().any(|s| s == "todo"));
    let rel = rule(&[
        "find c: comment",
        "where c adjoins directive \"todo\"",
        "report c \"x\"",
    ]);
    assert!(lower(&rel).is_ok(), "{:?}", lower(&rel));
}

// frob:ticket 01M4XBAPBBMQ5TMT0EH30ZJZBC
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn a_glob_matched_against_a_side_row_field_lowers_to_an_operand_glob_op() {
    let src = rule(&[
        "needs config",
        "find row: config.invariants.forbid_imports",
        "find i: import where i.file.path matches row.from and i.target under row.to",
        "report i \"{i.file.path} imports {i.target}: {row.reason}\"",
    ]);
    let plan = lower(&src).expect("lowers");
    assert_eq!(Plan::load(&plan.to_bytes()).expect("round trips"), plan);
    assert!(
        plan.parts()
            .ops
            .iter()
            .any(|o| matches!(o, Op::MatchGlobOperand { .. }))
    );
}

// frob:ticket 01M4X91TRR145XCPQ01R1CD7W9
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn a_vocab_knob_membership_lowers_and_a_vocab_need_must_name_a_vocab_knob() {
    let src = |needs: &str| {
        format!(
            "rule VOC001 \"t\" {{\n  lang rust\n  {needs}\n  knob srcs: vocab = vocab(\"clock\", \"net\") \"d\"\n  find f: function where f in knob.srcs\n  report f \"x\"\n{EXPLAIN}}}\n"
        )
    };
    let plan = lower(&src("needs vocab(srcs)")).expect("lowers");
    assert_eq!(Plan::load(&plan.to_bytes()).expect("round trips"), plan);
    let p = plan.parts();
    let classes: Vec<&str> = p
        .ops
        .iter()
        .find_map(|o| match o {
            Op::InVocab { classes, .. } => Some(
                classes
                    .iter()
                    .map(|&c| p.strings[c as usize].as_str())
                    .collect(),
            ),
            _ => None,
        })
        .expect("an InVocab op");
    assert_eq!(classes, ["clock", "net"]);
    assert!(matches!(
        lower(&src("needs vocab(missing)")),
        Err(LowerError::UnknownNeed { .. })
    ));
}

// frob:ticket 01M4X91TW6Y91R51R9BETGCVS0
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn slug_and_resolve_calls_lower_and_other_calls_or_nesting_are_refused() {
    let src = |cond: &str| {
        format!(
            "rule FNC001 \"t\" {{\n  lang rust\n  find f: function where {cond}\n  report f \"x\"\n{EXPLAIN}}}\n"
        )
    };
    let plan = lower(&src(
        "slug(f.name) == \"a-b\" and f.file == resolve(f.name, f.file)",
    ))
    .expect("lowers");
    assert_eq!(Plan::load(&plan.to_bytes()).expect("round trips"), plan);
    let calls = plan
        .parts()
        .ops
        .iter()
        .filter(|o| {
            matches!(o, Op::Cmp { lhs, rhs, .. }
                if matches!(lhs, Operand::Slug(_) | Operand::Resolve(..))
                    || matches!(rhs, Operand::Slug(_) | Operand::Resolve(..)))
        })
        .count();
    assert_eq!(calls, 2);
    for bad in [
        "slug(slug(f.name)) == \"a\"",
        "slug(f.name, f.name) == \"a\"",
        "resolve(f.name) == \"a\"",
    ] {
        assert!(
            matches!(lower(&src(bad)), Err(LowerError::Unsupported { .. })),
            "{bad}"
        );
    }
}

// frob:ticket 01M5ETB80YYSQNEDP9PG86WKD4
// frob:tests crates/gob-plan/src/lower/convert.rs::key_path_regex
#[test]
fn a_key_path_pattern_lowers_to_an_anchored_regex_where_star_stays_in_one_segment() {
    let star = lower(&rule(&[
        "find k: key(path = \"/jobs/*\")",
        "report k \"x\"",
    ]))
    .expect("lowers");
    assert!(format!("{star:?}").contains("^/jobs/[^/]*$"), "{star:?}");
    let deep = lower(&rule(&[
        "find k: key(path = \"/a.b/**\")",
        "report k \"x\"",
    ]))
    .expect("lowers");
    assert!(format!("{deep:?}").contains(r"^/a\\.b/.*$"), "{deep:?}");
}
