//! A count compared with a scaled count (`count(..) >= knob.ratio * count(..)`), end to end:
//! lowering to a `CountPair`, then the example runner over real python.

// frob:ticket 01M5GA77VTC3VDYVZ2HBZNRM2K

use gob_plan::examples::{RunError, install_model_reader, run_example};
use gob_plan::grl::parse;
use gob_text::FileInterner;

/// Calls and assignments inside `f`, compared by `clause`, with the given examples.
fn rule(knob: &str, clause: &str, examples: &str) -> String {
    format!(
        r#"rule RAT001 "ratio" {{
  lang python
  severity warn
  {knob}

  find f: function
  where {clause}
  report f "ratio holds in {{f.name}}"
{examples}
  explain """
    Test rule.
    ## Remedy
    None.
  """
}}
"#
    )
}

const RATIO: &str = "knob ratio: float = 0.5 \"d\"";
const CALLS: &str = "count(c: call inside f)";
const ASSIGNS: &str = "count(a: assignment inside f)";

/// Run every example of a rule: whether each passed.
fn results(src: &str) -> Vec<Result<bool, RunError>> {
    install_model_reader(grimble_check::example_model::read_example_model);
    let parsed = parse(FileInterner::new().intern("rules/T.grl"), src);
    assert!(parsed.is_ok(), "{:?}", parsed.errors);
    let rule = &parsed.file.rules[0];
    rule.examples
        .iter()
        .map(|e| run_example(rule, e).map(|r| r.passed))
        .collect()
}

fn all_pass(src: &str) {
    for (i, r) in results(src).into_iter().enumerate() {
        assert!(matches!(r, Ok(true)), "example {i}: {r:?}");
    }
}

/// One python example: `fire` marks the `def` line, `clean` does not.
fn example(fire: bool, body: &str) -> String {
    let mut lines = body.lines();
    let first = lines.next().expect("def line");
    let first = if fire {
        format!("{first}   #~ warn")
    } else {
        first.to_owned()
    };
    let rest: String = lines.fold(String::new(), |mut acc, l| {
        acc.push_str("\n    ");
        acc.push_str(l);
        acc
    });
    format!(
        "  example {} python \"\"\"\n    {first}{rest}\n  \"\"\"\n",
        if fire { "fire" } else { "clean" }
    )
}

// frob:tests crates/gob-plan/src/exec/relations/count.rs::Count.compare_scaled
#[test]
fn the_ratio_on_the_right_scales_the_second_count() {
    // 2 calls vs 0.5 * 2 assignments: holds. 1 call vs 0.5 * 4: does not.
    let src = rule(
        RATIO,
        &format!("{CALLS} >= knob.ratio * {ASSIGNS}"),
        &[
            example(true, "def f():\n    a = 1\n    b = 2\n    g()\n    h()"),
            example(
                false,
                "def f():\n    a = 1\n    b = 2\n    c = 3\n    d = 4\n    g()",
            ),
        ]
        .concat(),
    );
    all_pass(&src);
}

// frob:tests crates/gob-plan/src/exec/relations/count.rs::Count.compare_scaled
#[test]
fn the_ratio_on_the_left_scales_the_first_count() {
    // 0.5 * 2 calls <= 2 assignments holds; 0.5 * 6 calls <= 1 assignment does not.
    let src = rule(
        RATIO,
        &format!("knob.ratio * {CALLS} <= {ASSIGNS}"),
        &[
            example(true, "def f():\n    a = 1\n    b = 2\n    g()\n    h()"),
            example(
                false,
                "def f():\n    a = 1\n    g()\n    g()\n    g()\n    g()\n    g()\n    g()",
            ),
        ]
        .concat(),
    );
    all_pass(&src);
}

// frob:tests crates/gob-plan/src/exec/relations/count.rs::Count.compare_scaled
#[test]
fn zero_counts_and_a_zero_ratio_compare_exactly() {
    // With no assignments, `calls >= 0.5 * 0` holds even for a function with no calls (0 >= 0).
    let empty = rule(
        RATIO,
        &format!("{CALLS} >= knob.ratio * {ASSIGNS}"),
        &example(true, "def f():\n    pass"),
    );
    all_pass(&empty);
    // A zero ratio makes the right side 0 whatever the assignments are.
    let zero = rule(
        "knob ratio: float = 0.0 \"d\"",
        &format!("{CALLS} >= knob.ratio * {ASSIGNS}"),
        &example(true, "def f():\n    a = 1\n    b = 2"),
    );
    all_pass(&zero);
    // A strict comparison with a zero right side is false for zero calls.
    let strict = rule(
        "knob ratio: float = 0.0 \"d\"",
        &format!("{CALLS} > knob.ratio * {ASSIGNS}"),
        &[
            example(false, "def f():\n    pass"),
            example(true, "def f():\n    g()"),
        ]
        .concat(),
    );
    all_pass(&strict);
}

// frob:tests crates/gob-plan/src/exec/relations/count.rs::Count.compare_scaled
#[test]
fn a_negative_ratio_flips_the_scaled_side() {
    // -1 * 2 assignments = -2 <= any number of calls.
    let src = rule(
        "knob ratio: float = -1.0 \"d\"",
        &format!("{CALLS} >= knob.ratio * {ASSIGNS}"),
        &example(true, "def f():\n    a = 1\n    b = 2"),
    );
    all_pass(&src);
}

// frob:tests crates/gob-plan/src/exec/relations/count.rs::Count.compare_scaled
#[test]
fn a_literal_factor_and_nested_counts_lower_and_run() {
    // A literal decimal factor, with the second count nested in a quantifier's condition.
    let src = rule(
        RATIO,
        &format!(
            "{CALLS} >= 0.5 * count(a: assignment inside f where count(c: call inside a) >= 0)"
        ),
        &example(true, "def f():\n    a = 1\n    g()"),
    );
    all_pass(&src);
}
