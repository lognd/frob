//! Lowering a checked rule to a plan: shape, clause-order independence, and honest refusals.

// frob:ticket 01M3ZX7EKNE5Q0NB0DKCH77AZX

use gob_plan::grl::parse;
use gob_plan::lower::{LowerError, lower_rule};
use gob_plan::plan::{Op, Plan, Polarity, Provenance};
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
                e.file_name().to_string_lossy().into_owned(),
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
        ["CAP001.grl", "CI002.grl", "SCOPE001.grl", "SYS001.grl"]
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
    let snippet = rule(&["find c: rust`$X.unwrap()`", "report c \"x\""]);
    assert!(matches!(
        lower(&snippet),
        Err(LowerError::Unsupported {
            what: "a snippet",
            ..
        })
    ));
    let knob = &format!(
        "rule TST003 \"t\" {{\n  knob n: int = 1 \"d\"\n  find f: function\n  report f \"x\"\n{EXPLAIN}}}\n"
    );
    assert!(matches!(
        lower(knob),
        Err(LowerError::Unsupported { what: "a knob", .. })
    ));
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
