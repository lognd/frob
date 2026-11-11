//! Fix lowering and rendering: a fix with metavariables lowers into the plan and the executor
//! renders its replacement from the snippet bindings (grl-spec.md section 8).

// frob:ticket 01M4XJ9HCS3WP614D698VN2V5Y

use gob_plan::exec::Input;
use gob_plan::exec::fix::{FixEdit, render_fixes};
use gob_plan::exec::outcome::outcomes;
use gob_plan::exec::relations::Relations;
use gob_plan::grl::parse;
use gob_plan::lower::lower_rule;
use gob_plan::plan::{Applicability, FixAction, FixPlace, Plan, Provenance};
use gob_text::FileInterner;

const EXPLAIN: &str = "  explain \"\"\"\n    Why.\n    ## Remedy\n    Fix.\n  \"\"\"\n";
const TARGET: &str = "fn main() {\n    let a = x.unwrap();\n}\n";

fn lower(fix: &str) -> Plan {
    let src = format!(
        "rule TST001 \"t\" {{\n  lang rust\n  find c: `$X.unwrap()`\n  report c \"x\"\n  {fix}\n{EXPLAIN}}}\n"
    );
    let parsed = parse(FileInterner::new().intern("rules/T.grl"), &src);
    assert!(parsed.is_ok(), "{:?}\n{src}", parsed.errors);
    lower_rule(&parsed.file.rules[0], Provenance::Std).unwrap()
}

// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn a_fix_template_with_metavariables_lowers_into_the_plan() {
    let plan = lower("fix c -> `$X.expect(\"msg\")` [machine]");
    let fixes = &plan.parts().fixes;
    assert_eq!(fixes.len(), 1);
    assert_eq!(fixes[0].applicability, Some(Applicability::Machine));
    let FixAction::Replace { place, template } = fixes[0].action else {
        panic!("expected a replace fix");
    };
    assert_eq!(place, FixPlace::Over);
    assert_eq!(
        plan.parts().strings[template as usize],
        "$X.expect(\"msg\")"
    );
    let bytes = plan.to_bytes();
    assert_eq!(Plan::load(&bytes).unwrap(), plan);
}

// frob:tests crates/gob-plan/src/exec/fix.rs::render_fixes
#[test]
fn the_executor_renders_the_replacement_from_the_bindings() {
    let plan = lower(
        "fix c -> `$X.expect(\"msg\")` [machine]\n  fix after c -> `;` [machine]\n  fix delete c [maybe-incorrect]\n  fix manual \"by hand\"",
    );
    let model = gob_symbols::model_of_source("rust", TARGET).unwrap();
    let source = gob_text::SourceText::new(TARGET.to_owned()).unwrap();
    let input = Input {
        model: &model,
        source: Some(&source),
    };
    let out = outcomes(&plan, &input, &Relations::new()).unwrap();
    assert_eq!(out.findings.len(), 1);
    let row = &out.rows[out.findings[0].row];
    let fixes = render_fixes(&plan, &input, row).unwrap();
    assert_eq!(fixes.len(), 4);
    let FixEdit::Edit(e) = &fixes[0].edit else {
        panic!("expected an edit");
    };
    assert_eq!(&TARGET[e.range.clone()], "x.unwrap()");
    assert_eq!(e.text, "x.expect(\"msg\")");
    let FixEdit::Edit(after) = &fixes[1].edit else {
        panic!("expected an edit");
    };
    assert_eq!(after.range.start, after.range.end);
    assert_eq!(after.range.start, e.range.end);
    assert!(matches!(&fixes[3].edit, FixEdit::Manual(m) if m == "by hand"));
}
