//! Tests of the layout-solve JSON model: determinism, grid snap, errors, schema, compatibility.

// frob:ticket 01M5XCWY267M72G3GPYE2ZAPQ5

use std::collections::BTreeMap;

use crunk_layout::FocusGraph;
use crunk_layout::output::{
    Axis, NodeKind, OutputError, RawNode, RawSolve, SCHEMA_V1, SolvedText, focus_order, snap,
};
use crunk_scene::parse_scene_html;

fn node(id: &str, parent: Option<&str>, w: f32, h: f32) -> RawNode {
    RawNode {
        id: id.to_owned(),
        parent: parent.map(str::to_owned),
        kind: NodeKind::Box,
        x: 0.0,
        y: 0.0,
        width: w,
        height: h,
        content_width: None,
        content_height: None,
        text: None,
        tokens: BTreeMap::new(),
    }
}

fn solve(nodes: Vec<RawNode>) -> RawSolve {
    RawSolve {
        viewport_width: 800.0,
        viewport_height: 600.0,
        nodes,
        focus_order: vec!["go".to_owned()],
    }
}

fn violations(json: &str) -> Vec<String> {
    let schema: serde_json::Value = serde_json::from_str(SCHEMA_V1).unwrap();
    let validator = jsonschema::validator_for(&schema).unwrap();
    let doc: serde_json::Value = serde_json::from_str(json).unwrap();
    validator.iter_errors(&doc).map(|e| e.to_string()).collect()
}

fn rich() -> RawSolve {
    let mut a = node("root", None, 800.0, 600.0);
    a.tokens.insert("padding".into(), "space-4".into());
    a.tokens.insert("color".into(), "ink".into());
    let mut b = node("label", Some("root"), 100.3, 20.0);
    b.kind = NodeKind::Text;
    b.text = Some(SolvedText {
        content: "hi".into(),
        font_size: 16.0,
        lines: 1,
    });
    b.content_width = Some(130.0);
    solve(vec![a, b, node("gone", Some("root"), 0.0, 10.0)])
}

#[test]
fn serializing_twice_is_byte_identical() {
    let doc = rich().finish().unwrap();
    assert_eq!(doc.to_json().unwrap(), doc.to_json().unwrap());
    let again = rich().finish().unwrap();
    assert_eq!(doc.to_json().unwrap(), again.to_json().unwrap());
    let json = doc.to_json().unwrap();
    assert!(json.ends_with('\n'));
    let ids: Vec<_> = doc.nodes.iter().map(|n| n.id.as_str()).collect();
    assert_eq!(ids, ["root", "label", "gone"]);
    // tokens are sorted by property regardless of insertion order
    assert!(json.find("\"color\"").unwrap() < json.find("\"padding\"").unwrap());
}

#[test]
fn coordinates_snap_to_the_64th_grid() {
    assert_eq!(snap(0.01), Some(0.015_625));
    assert_eq!(snap(10.5), Some(10.5));
    assert_eq!(snap(1.0 / 128.0 * 3.0), Some(0.031_25));
    let mut n = node("a", None, 10.1, 5.0);
    n.x = 3.3;
    let doc = solve(vec![n]).finish().unwrap();
    let got = &doc.nodes[0];
    assert!((got.x * 64.0).fract().abs() < f32::EPSILON);
    assert!((got.width * 64.0).fract().abs() < f32::EPSILON);
}

#[test]
fn negative_zero_prints_as_zero() {
    assert!(snap(-0.0).unwrap().is_sign_positive());
    assert!(snap(-0.001).unwrap().is_sign_positive());
    let mut n = node("a", None, 4.0, 4.0);
    n.x = -0.0;
    n.y = -0.004;
    let json = solve(vec![n]).finish().unwrap().to_json().unwrap();
    assert!(!json.contains("-0"), "{json}");
    // a hand-edited document is cleaned on write too
    let mut doc = solve(vec![node("a", None, 4.0, 4.0)]).finish().unwrap();
    doc.nodes[0].x = -0.0;
    assert!(!doc.to_json().unwrap().contains("-0"));
}

#[test]
fn nan_and_infinity_are_typed_errors() {
    for bad in [f32::NAN, f32::INFINITY, f32::NEG_INFINITY, f32::MAX] {
        let mut n = node("a", None, 4.0, 4.0);
        n.height = bad;
        let err = solve(vec![n]).finish().unwrap_err();
        assert!(
            matches!(&err, OutputError::NonFinite { owner, field } if owner == "node 'a'" && *field == "height"),
            "{err}"
        );
    }
    let mut s = solve(vec![]);
    s.viewport_width = f32::NAN;
    assert!(matches!(
        s.finish().unwrap_err(),
        OutputError::NonFinite {
            field: "viewport_width",
            ..
        }
    ));
    let mut n = node("t", None, 1.0, 1.0);
    n.content_height = Some(f32::INFINITY);
    assert!(solve(vec![n]).finish().is_err());
    let mut doc = solve(vec![node("a", None, 4.0, 4.0)]).finish().unwrap();
    doc.nodes[0].y = f32::NAN;
    assert!(matches!(doc.to_json(), Err(OutputError::NonFinite { .. })));
}

#[test]
fn zero_width_or_height_sets_the_flag() {
    let doc = rich().finish().unwrap();
    assert!(doc.nodes[2].zero_size);
    assert!(!doc.nodes[0].zero_size);
    let json = doc.to_json().unwrap();
    assert_eq!(json.matches("zero_size").count(), 1);
    let flat = solve(vec![
        node("h", None, 10.0, 0.0),
        node("sliver", None, 0.001, 9.0),
    ])
    .finish()
    .unwrap();
    assert!(flat.nodes[0].zero_size && flat.nodes[1].zero_size);
}

#[test]
fn overflow_records_axis_and_amount() {
    let doc = rich().finish().unwrap();
    let o = &doc.nodes[1].overflow;
    assert_eq!(o.len(), 1);
    assert_eq!(o[0].axis, Axis::X);
    assert!((o[0].amount - 29.7).abs() < 0.02);
    let mut both = node("b", None, 10.0, 10.0);
    both.content_width = Some(15.0);
    both.content_height = Some(10.5);
    let doc = solve(vec![both]).finish().unwrap();
    let axes: Vec<_> = doc.nodes[0]
        .overflow
        .iter()
        .map(|o| (o.axis, o.amount))
        .collect();
    assert_eq!(axes, [(Axis::X, 5.0), (Axis::Y, 0.5)]);
    // exactly fitting or smaller content does not overflow
    let mut fit = node("f", None, 10.0, 10.0);
    fit.content_width = Some(10.0);
    fit.content_height = Some(3.0);
    assert!(
        solve(vec![fit]).finish().unwrap().nodes[0]
            .overflow
            .is_empty()
    );
}

#[test]
fn an_empty_scene_has_an_empty_node_list() {
    let mut s = solve(vec![]);
    s.focus_order.clear();
    let json = s.finish().unwrap().to_json().unwrap();
    assert!(json.contains("\"nodes\": []"), "{json}");
    assert!(json.contains("\"focus_order\": []"));
    assert!(violations(&json).is_empty());
}

#[test]
fn output_validates_against_the_schema() {
    let json = rich().finish().unwrap().to_json().unwrap();
    assert_eq!(violations(&json), Vec::<String>::new());
    // the schema rejects a bad document
    assert!(
        !violations(
            r#"{"version":1,"viewport_width":1,"viewport_height":1,"nodes":null,"focus_order":[]}"#
        )
        .is_empty()
    );
}

#[test]
fn existing_consumers_still_read_it() {
    let json = rich().finish().unwrap().to_json().unwrap();
    let old: crunk_ingest::scene::LayoutSolve = serde_json::from_str(&json).unwrap();
    assert_eq!(old.nodes.len(), 3);
    assert_eq!(old.nodes[1].id, "label");
    assert_eq!(old.nodes[1].text.as_ref().unwrap().lines, 1);
    assert!((old.viewport_width - 800.0).abs() < f32::EPSILON);
}

#[test]
fn focus_order_follows_the_focus_graph() {
    let doc = parse_scene_html(
        r#"<div data-id="root"><button data-id="a">A</button><button>anon</button><button data-id="b">B</button></div>"#,
    )
    .expect("parses");
    let graph = FocusGraph::from_scene(&doc);
    assert_eq!(focus_order(&graph), ["a", "b"]);
}
