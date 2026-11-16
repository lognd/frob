//! The prototyping checks over parsed flows and tokens: the acceptance and edge cases.

// frob:ticket 01M5XCZ1K91B012K3QDSH0JBCS

use crunk_rules::flow_files::FlowFacts;
use crunk_rules::ux::motion::{MotionIssue, check_motion_rules};
use crunk_spec::{FlowEdge, FlowFile};
use crunk_tokens::TokenSet;

const MAX: f64 = 1000.0;

fn flow(to: &str, motion: Option<&str>) -> FlowFacts {
    // Built directly: the file parser rejects a dangling edge, the rule must still catch one.
    let parsed = FlowFile {
        name: "f".to_owned(),
        nodes: vec!["a:one".to_owned(), "a:two".to_owned()],
        edges: vec![FlowEdge {
            from: "a:one".to_owned(),
            to: to.to_owned(),
            trigger: "click".to_owned(),
            action: None,
            motion: motion.map(str::to_owned),
        }],
    };
    FlowFacts {
        files: vec![("design/flows/f.flow.toml".to_owned(), parsed)],
        problems: Vec::new(),
    }
}

fn tokens(toml: &str) -> TokenSet {
    crunk_tokens::dialect::parse(toml, "t.toml").expect("tokens")
}

fn issues(facts: &FlowFacts, set: Option<&TokenSet>) -> Vec<MotionIssue> {
    check_motion_rules(facts, set, Some(MAX))
        .iter()
        .map(|f| f.issue)
        .collect()
}

const TWINNED: &str =
    "[motion.slide]\nvalue = \"200ms\"\n[motion.slide-reduced]\nvalue = \"0ms\"\n";

// frob:tests crates/crunk-rules/src/ux/motion.rs::check_motion_rules
#[test]
fn motion_missing_target_fires() {
    let set = tokens(TWINNED);
    let got = issues(&flow("a:gone", Some("motion.slide")), Some(&set));
    assert_eq!(got, vec![MotionIssue::MissingTarget]);
}

// frob:tests crates/crunk-rules/src/ux/motion.rs::check_motion_rules
#[test]
fn motion_over_bound_fires() {
    let set = tokens("[motion.slide]\nvalue = \"4s\"\n[motion.slide-reduced]\nvalue = \"0ms\"\n");
    let got = issues(&flow("a:two", Some("motion.slide")), Some(&set));
    assert_eq!(got, vec![MotionIssue::OverBound]);
}

// frob:tests crates/crunk-rules/src/ux/motion.rs::check_motion_rules
#[test]
fn motion_without_twin_fires() {
    let set = tokens("[motion.slide]\nvalue = \"200ms\"\n");
    let got = issues(&flow("a:two", Some("motion.slide")), Some(&set));
    assert_eq!(got, vec![MotionIssue::NoReducedTwin]);
}

// frob:tests crates/crunk-rules/src/ux/motion.rs::check_motion_rules
#[test]
fn motion_literal_duration_fires() {
    let set = tokens(TWINNED);
    let got = issues(&flow("a:two", Some("200ms")), Some(&set));
    assert_eq!(got, vec![MotionIssue::LiteralDuration]);
}

// frob:tests crates/crunk-rules/src/ux/motion.rs::check_motion_rules
#[test]
fn motion_zero_twin_is_clean() {
    let set = tokens(TWINNED);
    assert!(issues(&flow("a:two", Some("motion.slide")), Some(&set)).is_empty());
}

// frob:tests crates/crunk-rules/src/ux/motion.rs::check_motion_rules
#[test]
fn motion_twin_over_bound_fires() {
    let set = tokens("[motion.slide]\nvalue = \"200ms\"\n[motion.slide-reduced]\nvalue = \"3s\"\n");
    let got = issues(&flow("a:two", Some("motion.slide")), Some(&set));
    assert_eq!(got, vec![MotionIssue::TwinOverBound]);
}

// frob:tests crates/crunk-rules/src/ux/motion.rs::check_motion_rules
#[test]
fn motion_without_tokens_is_unresolved() {
    let empty = tokens("[color.ink]\nvalue = \"#101820\"\n");
    let facts = flow("a:two", Some("motion.slide"));
    assert_eq!(issues(&facts, Some(&empty)), vec![MotionIssue::Unresolved]);
    assert_eq!(issues(&facts, None), vec![MotionIssue::Unresolved]);
}

// frob:tests crates/crunk-rules/src/ux/motion.rs::check_motion_rules
#[test]
fn motion_free_flow_is_silent() {
    assert!(issues(&flow("a:two", None), None).is_empty());
}
