//! Waypoint outcome maps reach the plan findings: non-Exact facts are PLAN041 Unresolved, a map resolves.

// frob:ticket 01M69BW9J521P25FVVAK6GAMTK

use std::collections::BTreeMap;

use gob_ir::error_flow::ErrorFacts;
use grimble_bind::model;
use grimble_bind::owner::Owners;
use grimble_bind::plan::findings_with_facts;
use grimble_bind::relation::Relation;
use grimble_model::ModelFiles;

const SRC: &str = r#"grimble = "2";
module m;

system s {
  actor customer : human;
  goal customer { attr dimension = action; buy; }
  step customer.lands;
  scenario sc realizes customer.buy {
    customer.lands -> end ok;
  }
}

impl sc.lands for s {
  chain {
    call bare = "svc.ts::f";
    call mapped = "svc.ts::g" { E, 402 => ok; }
  }
}
"#;

fn run(facts: &BTreeMap<String, ErrorFacts>) -> grimble_bind::plan::PlanFindings {
    let files = ModelFiles::new().with_file("model.grmb", SRC.as_bytes().to_vec());
    let model = model::load(&files);
    findings_with_facts(&model, &Relation::default(), &Owners::default(), facts)
}

fn ts_facts() -> BTreeMap<String, ErrorFacts> {
    let files = ModelFiles::new().with_file("model.grmb", SRC.as_bytes().to_vec());
    let model = model::load(&files);
    model
        .plan
        .iter()
        .flat_map(|p| p.node.waypoints.iter())
        .map(|w| (w.anchor.clone(), ErrorFacts::typescript(&["svc.ts:1"])))
        .collect()
}

#[test]
// frob:tests crates/grimble-bind/src/plan.rs::findings_with_facts
fn unmapped_non_exact_waypoint_is_plan041_and_mapped_one_is_conditional() {
    let facts = ts_facts();
    assert_eq!(facts.len(), 2, "{facts:?}");
    let out = run(&facts);
    let hits: Vec<_> = out
        .findings
        .iter()
        .filter(|f| f.rule == "PLAN041")
        .collect();
    assert_eq!(hits.len(), 1, "{hits:?}");
    assert!(hits[0].anchor.ends_with("wp[bare]"), "{hits:?}");
    assert_eq!(out.subjects.get("PLAN041"), Some(&2));
}

#[test]
// frob:tests crates/grimble-bind/src/plan.rs::findings_with_facts
fn no_facts_means_no_outcome_findings() {
    let out = run(&BTreeMap::new());
    assert!(out.findings.iter().all(|f| f.rule != "PLAN041"));
}
