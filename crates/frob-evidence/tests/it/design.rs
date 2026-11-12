//! Design-entity digests stored on evidence records (grmb-spec 12.8, D207).

use frob_evidence::design::bound_digests;
use frob_evidence::{DesignDigest, EvidenceRecord};
use serde_json::json;

const TICKET: &str = "01M6BYM60R2RRMEKJ5ZVJ5RP7R";

fn graph() -> serde_json::Value {
    json!({"data": {"entities": [
        {"anchor": "a.md#one", "body_digest": "blake3:aa",
         "directives": [{"namespace": "frob", "verb": "ticket", "args": TICKET}]},
        {"anchor": "a.md#two", "body_digest": "blake3:bb",
         "directives": [{"namespace": "frob", "verb": "ticket", "args": "01OTHER"}]},
        {"anchor": "a.md#three", "body_digest": null,
         "directives": [{"namespace": "frob", "verb": "ticket", "args": TICKET}]},
        {"anchor": "a.md#four", "body_digest": "blake3:dd",
         "directives": [{"namespace": "frob", "verb": "ticket", "args": format!("X, {TICKET}")}]},
        {"anchor": "a.md#five", "body_digest": "blake3:ee", "directives": []}
    ]}})
}

#[test]
fn only_entities_naming_the_ticket_with_a_digest_are_bound() {
    // frob:ticket 01M6BYM60R2RRMEKJ5ZVJ5RP7R
    // frob:tests crates/frob-evidence/src/design.rs::bound_digests
    let got = bound_digests(&graph(), TICKET);
    let names: Vec<&str> = got.iter().map(|d| d.entity.as_str()).collect();
    assert_eq!(names, ["a.md#one", "a.md#four"]);
    assert_eq!(got[0].body_digest, "blake3:aa");
}

#[test]
fn a_graph_without_entities_binds_nothing() {
    // frob:ticket 01M6BYM60R2RRMEKJ5ZVJ5RP7R
    // frob:tests crates/frob-evidence/src/design.rs::bound_digests
    assert!(bound_digests(&json!({"data": {}}), TICKET).is_empty());
}

#[test]
fn a_design_digest_round_trips_and_the_record_schema_names_the_field() {
    // frob:ticket 01M6BYM60R2RRMEKJ5ZVJ5RP7R
    // frob:tests crates/frob-evidence/src/record.rs::EvidenceRecord
    let d = DesignDigest {
        entity: "a.md#one".into(),
        body_digest: "blake3:aa".into(),
    };
    let v = serde_json::to_value(&d).expect("ser");
    assert_eq!(v["body_digest"], "blake3:aa");
    let back: DesignDigest = serde_json::from_value(v).expect("de");
    assert_eq!(back, d);
    let schema = serde_json::to_string(&schemars::schema_for!(EvidenceRecord)).expect("schema");
    assert!(schema.contains("design"));
}
