//! `rule why`: the per-clause trace agrees with what `rule check` runs.

// frob:ticket 01M3ZX7H8FPEAY1X1WVW1PNXXN

mod support;

use gob_ir::{NodeId, NodeSpec, Operator, Relation, Truth};
use gob_plan::exec::Input;
use gob_plan::exec::outcome::{Kind, outcomes};
use gob_plan::exec::relations::Relations;
use gob_plan::lower::lower_rule;
use gob_plan::plan::Provenance;
use gob_plan::verbs::why::why_source;
use gob_plan::why::why;
use support::Doc;

const RULE: &str = r#"rule NOPE001 "no-dbg" {
  lang typescript
  severity error
  find d: call where d.callee == "danger"
  where not d inside function
  report d "remove dbg"
  explain """
    Remove dbg.

    ## Remedy
    Delete it.
  """
}
"#;

const TARGET: &str = "function main() {
  danger();
}

test(\"lexes numbers\", () => {
  danger();
});
";

// frob:tests crates/gob-plan/src/verbs/why.rs::why_source
#[test]
fn why_prints_candidates_and_the_failed_inside_clause() {
    let w = why_source("r.grl", RULE, "NOPE001", "typescript", TARGET, 2).unwrap();
    let text = w.lines().join("\n");
    assert_eq!(w.candidates.len(), 1, "{text}");
    assert!(text.contains("1 candidate at 2:"), "{text}");
    assert!(text.contains("failed: 2:3 is inside function"), "{text}");
    assert_eq!(w.candidates[0].outcome, "clean");
}

const P_MINUS: &str = r#"rule CALL001 "uncalled" {
  lang rust
  severity error
  polarity P-
  find f: function
  where some t: function where t calls f
  report f "never called"
  explain """
    Nothing calls it.

    ## Remedy
    Call it.
  """
}
"#;

// frob:tests crates/gob-plan/src/why/mod.rs::why
#[test]
fn why_names_the_may_edge_clauses_and_agrees_with_check_on_every_line() {
    let mut d = Doc::new("a.rs", "rust");
    let fs: Vec<NodeId> = (0..3u32)
        .map(|i| {
            d.at_range(
                |loc| NodeSpec::new(Operator::unit("function", "impl"), loc).named("f"),
                6 * i,
                6 * i + 5,
                &[],
            )
        })
        .collect();
    let (m, _) = d.root(&fs);
    let text = "aaaaa\nbbbbb\nccccc\n".to_owned();
    let source = gob_text::SourceText::new(text).unwrap();
    let input = Input {
        model: &m,
        source: Some(&source),
    };
    let mut edges = Relation::new();
    edges.insert(fs[2], fs[0], Truth::Unknown); // line 3 maybe calls line 1
    edges.insert(fs[2], fs[1], Truth::Yes); // line 3 certainly calls line 2
    let rels = Relations::new().with_edges("calls", edges);
    let parsed = gob_plan::grl::parse(gob_text::FileInterner::new().intern("r.grl"), P_MINUS);
    let rule = &parsed.file.rules[0];

    let plan = lower_rule(rule, Provenance::Std).unwrap();
    let out = outcomes(&plan, &input, &rels).unwrap();
    let mut checked = 0;
    for line in 1..=3u32 {
        let w = why(rule, P_MINUS, &input, &rels, line).unwrap();
        assert_eq!(w.candidates.len(), 1, "line {line}");
        let node = fs[usize::try_from(line).unwrap() - 1];
        let want = match out.findings.iter().find(|f| f.subject == Some(node)) {
            Some(f) if f.kind == Kind::Fire => "fire",
            Some(_) => "unresolved",
            None => "clean",
        };
        assert_eq!(w.candidates[0].outcome, want, "line {line}");
        checked += 1;
    }
    assert_eq!(checked, 3);

    let l1 = why(rule, P_MINUS, &input, &rels, 1).unwrap();
    assert_eq!(l1.candidates[0].outcome, "unresolved");
    let step = &l1.candidates[0].steps[0];
    assert_eq!(step.value, "unknown");
    assert!(
        step.doubts[0].contains("May edge") && step.doubts[0].contains("P-"),
        "{step:?}"
    );
    let l2 = why(rule, P_MINUS, &input, &rels, 2).unwrap();
    assert_eq!(
        (
            l2.candidates[0].outcome.as_str(),
            l2.candidates[0].steps[0].value.as_str()
        ),
        ("clean", "yes")
    );
    assert!(l2.candidates[0].steps[0].doubts.is_empty());
    let l3 = why(rule, P_MINUS, &input, &rels, 3).unwrap();
    assert_eq!(l3.candidates[0].outcome, "fire");
}
