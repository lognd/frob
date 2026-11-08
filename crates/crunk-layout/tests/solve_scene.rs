//! The T1 solver driver (~BMREX1B): determinism, refusals and the edge cases of the pipeline.

// frob:ticket 01M5XCWYB9M2YSJ5EGABMREX1B

use crunk_layout::output::NodeKind;
use crunk_layout::solve::{SolveError, SolveNote, Solved, solve_scene_html};
use crunk_layout::style::TokenMap;
use crunk_layout::text::TextMeasurer;
use crunk_scene::parse_scene_html;
use std::fmt::Write;

const SCENE: &str = r#"<div data-id="root" style="width:400px;padding:8px">
<p data-id="title" style="font-size:20px">Hello world</p>
<button data-id="go" style="width:100px;height:40px">Go</button></div>"#;

fn solve_at(html: &str, tokens: &TokenMap, vp: (f32, f32)) -> Result<Solved, SolveError> {
    let doc = parse_scene_html(html).unwrap();
    solve_scene_html(&doc, tokens, vp, &mut TextMeasurer::new())
}

fn solve(html: &str) -> Result<Solved, SolveError> {
    solve_at(html, &TokenMap::new(), (800.0, 600.0))
}

#[test]
fn solving_twice_is_byte_identical() {
    let a = solve(SCENE).unwrap().doc.to_json().unwrap();
    let b = solve(SCENE).unwrap().doc.to_json().unwrap();
    assert_eq!(a, b);
}

#[test]
fn duplicate_data_id_is_refused_with_scene002() {
    let err = solve(r#"<div data-id="a"></div><div data-id="a"></div>"#).unwrap_err();
    assert!(matches!(&err, SolveError::Refused(_)) && err.to_string().contains("SCENE002"));
}

#[test]
fn missing_data_id_is_refused_with_scene002() {
    let err = solve(r#"<div data-id="a"><span>x</span></div>"#).unwrap_err();
    assert!(matches!(err, SolveError::Refused(_)));
}

#[test]
fn unknown_tag_is_an_empty_block_with_a_note() {
    let s = solve(r#"<my-widget data-id="w" style="width:50px">hi</my-widget>"#).unwrap();
    assert_eq!(s.doc.nodes[0].kind, NodeKind::Box);
    assert!(
        s.notes
            .iter()
            .any(|n| matches!(n, SolveNote::UnknownTag { id, .. } if id == "w"))
    );
}

#[test]
fn zero_viewport_gives_zero_size_boxes() {
    let s = solve_at(
        r#"<div data-id="r"><p data-id="t">x</p></div>"#,
        &TokenMap::new(),
        (0.0, 0.0),
    )
    .unwrap();
    assert!(s.doc.nodes.iter().any(|n| n.zero_size));
}

#[test]
fn root_taller_than_the_viewport_reports_page_overflow() {
    let s = solve(r#"<div data-id="r" style="height:900px"></div>"#).unwrap();
    assert!(s.notes.iter().any(
        |n| matches!(n, SolveNote::PageOverflow { amount, .. } if (*amount - 300.0).abs() < 0.01)
    ));
}

#[test]
fn deep_nesting_of_200_does_not_overflow_the_stack() {
    let mut html = String::new();
    for i in 0..200 {
        write!(html, r#"<div data-id="n{i}">"#).unwrap();
    }
    html.push_str(&"</div>".repeat(200));
    let s = solve(&html).unwrap();
    assert_eq!(s.doc.nodes.len(), 200);
}

#[test]
fn two_viewports_solve_independently() {
    let html = r#"<div data-id="r"><p data-id="t">The quick brown fox jumps over the lazy dog again and again</p></div>"#;
    let narrow = solve_at(html, &TokenMap::new(), (100.0, 600.0)).unwrap();
    let wide = solve_at(html, &TokenMap::new(), (1000.0, 600.0)).unwrap();
    let lines = |s: &Solved| {
        s.doc
            .nodes
            .iter()
            .find(|n| n.id == "t")
            .unwrap()
            .text
            .as_ref()
            .unwrap()
            .lines
    };
    assert!(lines(&narrow) > lines(&wide) && lines(&wide) == 1);
}

#[test]
fn nodes_keep_document_order() {
    let s = solve(SCENE).unwrap();
    let ids: Vec<_> = s.doc.nodes.iter().map(|n| n.id.as_str()).collect();
    assert_eq!(ids, ["root", "title", "go"]);
}

#[test]
fn unrelated_token_edit_leaves_the_solve_unchanged() {
    let a = solve_at(
        SCENE,
        &TokenMap::from_pairs([("--x", "1px")]),
        (800.0, 600.0),
    )
    .unwrap();
    let b = solve_at(
        SCENE,
        &TokenMap::from_pairs([("--x", "9px")]),
        (800.0, 600.0),
    )
    .unwrap();
    assert_eq!(a.doc, b.doc);
}

#[test]
fn token_bindings_are_recorded() {
    let html = r#"<div data-id="r" style="padding:var(--pad)"></div>"#;
    let s = solve_at(
        html,
        &TokenMap::from_pairs([("--pad", "4px")]),
        (800.0, 600.0),
    )
    .unwrap();
    assert_eq!(
        s.doc.nodes[0].tokens.get("padding").map(String::as_str),
        Some("pad")
    );
}

#[test]
fn font_outside_the_bundle_is_a_typed_error() {
    let err = solve(r#"<p data-id="t" style="font-family:'Comic Sans'">x</p>"#).unwrap_err();
    assert!(matches!(err, SolveError::Text(_)));
}
