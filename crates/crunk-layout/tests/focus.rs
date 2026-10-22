//! The focus graph: edges, defaults, reachability, traps, wrap and invalid authoring.

// frob:ticket 01M4CXRSYQQW9C6D7K2Q2ZC9QM

use crunk_layout::{Direction, FocusGraph, InvalidReason};
use crunk_scene::parse_scene_html;

fn graph(html: &str) -> FocusGraph {
    FocusGraph::from_scene(&parse_scene_html(html).expect("parses"))
}

fn names(g: &FocusGraph, ids: &[usize]) -> Vec<String> {
    ids.iter()
        .map(|&n| g.nodes[n].data_id.clone().unwrap_or_default())
        .collect()
}

const MENU: &str = "<button data-id=\"a\" data-focus-default></button>\n<button data-id=\"b\"></button>\n<button data-id=\"c\"></button>\n";

// frob:tests FocusGraph.from_scene
#[test]
fn document_order_gives_vertical_neighbours() {
    let g = graph(MENU);
    assert_eq!(g.nodes.len(), 3);
    assert_eq!(g.defaults, vec![0]);
    assert_eq!(g.edges.len(), 4);
    assert!(g.unreachable().is_empty());
    assert!(g.traps().is_empty());
}

// frob:tests FocusGraph.unreachable
#[test]
fn a_node_with_no_incoming_move_is_unreachable() {
    let g = graph(
        "<button data-id=\"a\" data-focus-default data-nav-down=\"none\"></button>\n<button data-id=\"b\"></button>\n",
    );
    assert_eq!(names(&g, &g.unreachable()), vec!["b"]);
}

// frob:tests FocusGraph.traps
#[test]
fn a_node_with_no_way_back_is_a_trap() {
    let g = graph(
        "<button data-id=\"a\" data-focus-default></button>\n<button data-id=\"b\" data-nav-up=\"none\"></button>\n",
    );
    assert_eq!(names(&g, &g.traps()), vec!["b"]);
    assert!(g.unreachable().is_empty());
}

// frob:tests FocusGraph.from_scene
#[test]
fn wrap_joins_the_ends_and_clamp_does_not() {
    let wrapped = graph(
        "<div data-focus-group data-focus-wrap=\"wrap\"><button data-id=\"a\"></button><button data-id=\"b\"></button><button data-id=\"c\"></button></div>",
    );
    assert!(
        wrapped
            .edges
            .iter()
            .any(|e| e.from == 2 && e.to == 0 && e.direction == Direction::Down)
    );
    assert!(
        wrapped
            .edges
            .iter()
            .any(|e| e.from == 0 && e.to == 2 && e.direction == Direction::Up)
    );
    let clamped = graph(MENU);
    assert!(!clamped.edges.iter().any(|e| e.from == 2 && e.to == 0));
}

// frob:tests FocusGraph.from_scene
#[test]
fn horizontal_groups_use_left_and_right() {
    let g = graph(
        "<div data-focus-group data-focus-axis=\"horizontal\"><Button data-id=\"a\"></Button><Button data-id=\"b\"></Button></div>",
    );
    assert!(
        g.edges
            .iter()
            .all(|e| matches!(e.direction, Direction::Left | Direction::Right))
    );
    assert_eq!(g.edges.len(), 2);
}

// frob:tests FocusGraph.from_scene
#[test]
fn explicit_neighbours_override_and_bad_targets_are_recorded() {
    let g = graph(
        "<button data-id=\"a\" data-nav-right=\"c\" data-nav-down=\"ghost\"></button>\n<button data-id=\"b\"></button>\n<button data-id=\"c\" data-nav-left=\"a\"></button>\n<p data-id=\"t\"></p><button data-id=\"d\" data-nav-up=\"t\"></button>",
    );
    assert!(
        g.edges
            .iter()
            .any(|e| e.from == 0 && e.to == 2 && e.direction == Direction::Right)
    );
    let reasons: Vec<_> = g.invalid.iter().map(|v| v.reason.clone()).collect();
    assert!(
        reasons.contains(&InvalidReason::UnknownTarget("ghost".into())),
        "{reasons:?}"
    );
    assert!(
        reasons.contains(&InvalidReason::UnfocusableTarget("t".into())),
        "{reasons:?}"
    );
}

// frob:tests FocusGraph.from_scene
#[test]
fn bad_wrap_and_axis_values_are_recorded() {
    let g = graph(
        "<div data-focus-group data-focus-wrap=\"loop\" data-focus-axis=\"diag\"><button data-id=\"a\"></button></div>",
    );
    let reasons: Vec<_> = g.invalid.iter().map(|v| v.reason.clone()).collect();
    assert!(
        reasons.contains(&InvalidReason::BadWrap("loop".into())),
        "{reasons:?}"
    );
    assert!(
        reasons.contains(&InvalidReason::BadAxis("diag".into())),
        "{reasons:?}"
    );
}

// frob:tests FocusGraph.from_scene
#[test]
fn disabled_elements_leave_the_graph_and_dead_defaults_are_recorded() {
    let g = graph(
        "<button data-id=\"a\"></button>\n<button data-id=\"b\" disabled data-focus-default></button>\n<button data-id=\"c\" aria-disabled=\"true\"></button>\n<button data-id=\"d\"></button>\n<div tabindex=\"0\" data-id=\"e\"></div><a data-id=\"f\"></a>",
    );
    assert_eq!(
        names(&g, &(0..g.nodes.len()).collect::<Vec<_>>()),
        vec!["a", "d", "e"]
    );
    assert!(g.defaults.is_empty());
    assert_eq!(g.dead_defaults.len(), 1);
}

// frob:tests FocusGraph.entries
#[test]
fn empty_scenes_and_missing_defaults_fall_back_sensibly() {
    let empty = graph("");
    assert!(
        empty.entries().is_empty() && empty.unreachable().is_empty() && empty.traps().is_empty()
    );
    let none = graph("<button data-id=\"a\"></button><button data-id=\"b\"></button>");
    assert_eq!(none.entries(), vec![0]);
    let two = graph(
        "<button data-id=\"a\" data-focus-default></button><button data-id=\"b\" data-focus-default data-nav-up=\"none\" data-nav-down=\"none\"></button>",
    );
    assert_eq!(two.entries(), vec![0, 1]);
}

// frob:tests FocusGraph.traps
#[test]
fn self_contained_cycles_off_the_entry_are_unreachable_not_traps() {
    let g = graph(
        "<button data-id=\"a\" data-focus-default data-nav-down=\"none\"></button>\n<div data-focus-group data-focus-wrap=\"wrap\"><button data-id=\"x\"></button><button data-id=\"y\"></button></div>",
    );
    assert_eq!(names(&g, &g.unreachable()), vec!["x", "y"]);
    assert!(g.traps().is_empty());
}
