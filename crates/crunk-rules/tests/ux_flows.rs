//! The flow and wireframe checks: the acceptance cases and edge cases.

// frob:ticket 01M5XCZ119D08JHJJZ8TTR3HMR

use std::collections::{BTreeMap, BTreeSet};

use crunk_rules::flow_files::FlowFacts;
use crunk_rules::ux::flows::{FlowIssue, FlowNotes, SceneTokens, check_flow_rules};
use crunk_spec::{FlowEdge, FlowFile};

const PATH: &str = "design/flows/f.flow.toml";

fn facts(nodes: &[&str], edges: &[(&str, &str, &str)]) -> FlowFacts {
    let flow = FlowFile {
        name: "f".to_owned(),
        nodes: nodes.iter().map(|n| (*n).to_owned()).collect(),
        edges: edges
            .iter()
            .map(|(from, to, trigger)| FlowEdge {
                from: (*from).to_owned(),
                to: (*to).to_owned(),
                trigger: (*trigger).to_owned(),
                action: None,
                motion: None,
            })
            .collect(),
    };
    FlowFacts {
        files: vec![(PATH.to_owned(), flow)],
        problems: Vec::new(),
    }
}

fn set(items: &[&str]) -> BTreeSet<String> {
    items.iter().map(|s| (*s).to_owned()).collect()
}

fn run(f: &FlowFacts, notes: FlowNotes) -> Vec<(FlowIssue, String)> {
    let map = BTreeMap::from([(PATH.to_owned(), notes)]);
    check_flow_rules(f, &map, &[])
        .into_iter()
        .map(|x| (x.issue, x.subject))
        .collect()
}

fn scene(fidelity: Option<&str>, tokens: &[&str]) -> Vec<(FlowIssue, String)> {
    let s = SceneTokens {
        path: "design/scenes/s.toml".to_owned(),
        fidelity: fidelity.map(str::to_owned),
        tokens: tokens.iter().map(|t| (*t).to_owned()).collect(),
    };
    check_flow_rules(&FlowFacts::default(), &BTreeMap::new(), &[s])
        .into_iter()
        .map(|x| (x.issue, x.subject))
        .collect()
}

// frob:tests crates/crunk-rules/src/ux/flows.rs::check_flow_rules
#[test]
fn dead_end_names_the_state() {
    let f = facts(&["a:one", "a:two"], &[("a:one", "a:two", "click")]);
    let got = run(&f, FlowNotes::default());
    assert_eq!(got, vec![(FlowIssue::DeadEnd, "a:two".to_owned())]);
}

// frob:tests crates/crunk-rules/src/ux/flows.rs::check_flow_rules
#[test]
fn terminal_state_is_not_a_dead_end() {
    let f = facts(&["a:one", "a:done"], &[("a:one", "a:done", "click")]);
    let notes = FlowNotes {
        terminal: set(&["a:done"]),
        ..FlowNotes::default()
    };
    assert!(run(&f, notes).is_empty());
}

// frob:tests crates/crunk-rules/src/ux/flows.rs::check_flow_rules
#[test]
fn single_node_flow_is_valid() {
    assert!(run(&facts(&["a:one"], &[]), FlowNotes::default()).is_empty());
}

// frob:tests crates/crunk-rules/src/ux/flows.rs::check_flow_rules
#[test]
fn unreachable_states_are_named_in_stable_order() {
    let f = facts(
        &["a:one", "z:late", "m:mid"],
        &[("z:late", "m:mid", "x"), ("m:mid", "z:late", "y")],
    );
    let got: Vec<_> = run(&f, FlowNotes::default())
        .into_iter()
        .filter(|(i, _)| *i == FlowIssue::Unreachable)
        .map(|(_, s)| s)
        .collect();
    assert_eq!(got, vec!["m:mid", "z:late"]);
}

// frob:tests crates/crunk-rules/src/ux/flows.rs::check_flow_rules
#[test]
fn cycle_with_an_exit_is_not_a_trap() {
    let f = facts(
        &["a:one", "a:two", "a:out"],
        &[
            ("a:one", "a:two", "next"),
            ("a:two", "a:one", "back"),
            ("a:two", "a:out", "done"),
        ],
    );
    let notes = FlowNotes {
        terminal: set(&["a:out"]),
        ..FlowNotes::default()
    };
    assert!(run(&f, notes).is_empty());
}

// frob:tests crates/crunk-rules/src/ux/flows.rs::check_flow_rules
#[test]
fn fallible_step_without_error_path_fires() {
    let f = facts(&["a:form", "a:ok"], &[("a:form", "a:ok", "submit")]);
    let notes = FlowNotes {
        fallible: set(&["a:form"]),
        terminal: set(&["a:ok"]),
        ..FlowNotes::default()
    };
    assert_eq!(
        run(&f, notes),
        vec![(FlowIssue::NoErrorPath, "a:form".to_owned())]
    );
}

// frob:tests crates/crunk-rules/src/ux/flows.rs::check_flow_rules
#[test]
fn unmarked_step_needs_no_error_path() {
    let f = facts(&["a:form", "a:ok"], &[("a:form", "a:ok", "submit")]);
    let notes = FlowNotes {
        terminal: set(&["a:ok"]),
        ..FlowNotes::default()
    };
    assert!(run(&f, notes).is_empty());
}

// frob:tests crates/crunk-rules/src/ux/flows.rs::check_flow_rules
#[test]
fn fallible_step_with_error_path_is_clean() {
    let f = facts(
        &["a:form", "a:error"],
        &[
            ("a:form", "a:error", "fail"),
            ("a:error", "a:form", "retry"),
        ],
    );
    let notes = FlowNotes {
        fallible: set(&["a:form"]),
        ..FlowNotes::default()
    };
    assert!(run(&f, notes).is_empty());
}

// frob:tests crates/crunk-rules/src/ux/flows.rs::check_flow_rules
#[test]
fn decision_missing_a_branch_fires() {
    let f = facts(
        &["a:ask", "a:yes", "a:no"],
        &[
            ("a:ask", "a:yes", "yes"),
            ("a:yes", "a:ask", "back"),
            ("a:no", "a:ask", "back"),
        ],
    );
    let notes = FlowNotes {
        decisions: BTreeMap::from([("a:ask".to_owned(), set(&["yes", "no"]))]),
        ..FlowNotes::default()
    };
    let got = run(&f, notes);
    assert!(got.contains(&(FlowIssue::MissingBranch, "a:ask".to_owned())));
}

// frob:tests crates/crunk-rules/src/ux/flows.rs::check_flow_rules
#[test]
fn wire_scene_with_brand_token_fires() {
    let got = scene(Some("wire"), &["color.brand.primary", "space.2"]);
    assert_eq!(
        got,
        vec![(FlowIssue::BrandInWire, "color.brand.primary".to_owned())]
    );
}

// frob:tests crates/crunk-rules/src/ux/flows.rs::check_flow_rules
#[test]
fn absent_fidelity_is_final_and_silent() {
    assert!(scene(None, &["color.brand.primary"]).is_empty());
}
