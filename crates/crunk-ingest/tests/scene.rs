//! Scene ingest and taffy solve: boxes and text runs to a deterministic layout-solve JSON.

// frob:ticket 01M4S9HRETE0RW4H034W1H7QCD

use crunk_ingest::scene::{SceneError, parse_scene, solve_scene};

const CARD: &str = include_str!("fixtures/scene/card.scene.json");

fn solve_json() -> String {
    let scene = parse_scene(CARD).expect("fixture parses");
    solve_scene(&scene)
        .expect("fixture solves")
        .to_json()
        .expect("serializes")
}

// frob:tests parse_scene
// frob:tests solve_scene
#[test]
fn scene_solves_to_deterministic_layout_json() {
    let first = solve_json();
    assert_eq!(first, solve_json(), "two solves must be byte-identical");
    let doc: serde_json::Value = serde_json::from_str(&first).unwrap();
    let nodes = doc["nodes"].as_array().unwrap();
    let ids: Vec<&str> = nodes.iter().map(|n| n["id"].as_str().unwrap()).collect();
    assert_eq!(ids, ["page", "title", "body", "button"]);
    // title: "Hello" at 20px = 5 * 12 wide, 24 tall, inside 16px padding.
    assert_eq!(
        (nodes[1]["x"].as_f64(), nodes[1]["y"].as_f64()),
        (Some(16.0), Some(16.0))
    );
    assert_eq!(
        (nodes[1]["width"].as_f64(), nodes[1]["height"].as_f64()),
        (Some(60.0), Some(24.0))
    );
    // body wraps at 120px / 6px per char = 20 chars per line: 38 chars -> 2 lines.
    assert_eq!(nodes[2]["text"]["lines"].as_u64(), Some(2));
    assert_eq!(nodes[2]["y"].as_f64(), Some(48.0));
    // button: 50% of the 288px content box, at an absolute offset.
    assert_eq!(nodes[3]["width"].as_f64(), Some(144.0));
    assert_eq!(nodes[3]["parent"].as_str(), Some("page"));
}

// frob:tests parse_scene
#[test]
fn bad_dimension_and_bad_json_are_typed_errors() {
    assert!(matches!(parse_scene("{"), Err(SceneError::Parse(_))));
    let scene = parse_scene(
        r#"{"viewport":{"width":10,"height":10},"root":{"id":"r","kind":"box","style":{"width":"wide"}}}"#,
    )
    .unwrap();
    assert!(matches!(
        solve_scene(&scene),
        Err(SceneError::BadDimension { .. })
    ));
}

// frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62
// frob:tests parse_scene
#[test]
fn interactive_and_safe_area_parse_and_default_off() {
    let json = r#"{"viewport":{"width":100,"height":100},"safe_area":8,
        "root":{"id":"r","kind":"box","children":[{"id":"b","kind":"box","interactive":true}]}}"#;
    let scene = parse_scene(json).expect("parses");
    assert!((scene.safe_area - 8.0).abs() < f32::EPSILON);
    assert!(scene.root.children[0].interactive);
    assert!(!scene.root.interactive);
    let plain =
        parse_scene(r#"{"viewport":{"width":1,"height":1},"root":{"id":"r","kind":"box"}}"#)
            .expect("parses");
    assert!(plain.safe_area.abs() < f32::EPSILON);
}
