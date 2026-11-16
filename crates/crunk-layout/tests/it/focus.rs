//! The focus graph: edges, defaults, reachability, traps, wrap and invalid authoring.

// frob:ticket 01M4CXRSYQQW9C6D7K2Q2ZC9QM

use crunk_layout::output::{LayoutSolve, NodeKind, SolvedNode};
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
}

// frob:tests FocusGraph.entries
#[test]
fn empty_scenes_and_missing_defaults_fall_back_sensibly_part_2() {
    let none = graph("<button data-id=\"a\"></button><button data-id=\"b\"></button>");
    assert_eq!(none.entries(), vec![0]);
}

// frob:tests FocusGraph.entries
#[test]
fn empty_scenes_and_missing_defaults_fall_back_sensibly_part_3() {
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

const GRID: &str = "<div data-focus-group style=\"display: grid; grid-template-columns: repeat(2, 1fr)\">\n<button data-id=\"a\" data-focus-default></button>\n<button data-id=\"b\"></button>\n<button data-id=\"c\"></button>\n<button data-id=\"d\"></button>\n</div>\n";

fn moves(g: &FocusGraph, from: &str, dir: Direction) -> Option<String> {
    let f = g
        .nodes
        .iter()
        .position(|n| n.data_id.as_deref() == Some(from))?;
    let e = g.edges.iter().find(|e| e.from == f && e.direction == dir)?;
    g.nodes[e.to].data_id.clone()
}

// frob:tests FocusGraph.from_scene
#[test]
fn a_grid_group_resolves_neighbours_along_both_axes() {
    let g = graph(GRID);
    assert_eq!(moves(&g, "a", Direction::Right).as_deref(), Some("b"));
    assert_eq!(moves(&g, "a", Direction::Down).as_deref(), Some("c"));
    assert_eq!(moves(&g, "d", Direction::Left).as_deref(), Some("c"));
    assert_eq!(moves(&g, "d", Direction::Up).as_deref(), Some("b"));
    assert_eq!(moves(&g, "b", Direction::Right), None);
    assert!(g.unreachable().is_empty());
}

// frob:tests FocusGraph.traps
#[test]
fn nodes_inside_a_modal_are_not_traps() {
    let html = "<button data-id=\"open\" data-focus-default data-nav-down=\"ok\"></button>\n<div aria-modal=\"true\">\n<button data-id=\"ok\" data-nav-up=\"none\" data-nav-down=\"none\"></button>\n</div>\n";
    let g = graph(html);
    assert!(g.traps().is_empty());
    assert_eq!(g.modal_nodes.len(), 1);
    let bare = html.replace(" aria-modal=\"true\"", "");
    assert_eq!(names(&graph(&bare), &graph(&bare).traps()), vec!["ok"]);
}

// frob:ticket 01M5HA924E3PTBVH6J8EBXP7XW
fn scene(name: &str, html: &str) -> crunk_layout::AtlasScene {
    crunk_layout::AtlasScene {
        name: name.to_owned(),
        graph: graph(html),
    }
}

// frob:ticket 01M5HA924E3PTBVH6J8EBXP7XW
fn hop(a: &str, b: &str) -> (String, String) {
    (a.to_owned(), b.to_owned())
}

// frob:ticket 01M5HA924E3PTBVH6J8EBXP7XW
const ONE_BUTTON: &str = "<button data-id=\"a\" data-focus-default></button>\n";

// frob:tests FocusAtlas.entries
#[test]
fn entries_are_the_scenes_nothing_transitions_into() {
    let atlas = crunk_layout::FocusAtlas::new(
        vec![scene("menu", ONE_BUTTON), scene("game", ONE_BUTTON)],
        &[hop("menu", "game")],
    );
    assert_eq!(atlas.entries(), vec![0]);
}

// frob:tests FocusAtlas.unreachable_scenes
#[test]
fn a_scene_no_transition_reaches_is_unreachable() {
    let atlas = crunk_layout::FocusAtlas::new(
        vec![
            scene("menu", ONE_BUTTON),
            scene("game", ONE_BUTTON),
            scene("a", ONE_BUTTON),
            scene("b", ONE_BUTTON),
        ],
        &[hop("menu", "game"), hop("a", "b"), hop("b", "a")],
    );
    // a and b enter each other, so only menu is an entry; the island is unreachable.
    assert_eq!(atlas.entries(), vec![0]);
    assert_eq!(atlas.unreachable_scenes(), vec![2, 3]);
}

// frob:tests FocusAtlas.unreachable_scenes
#[test]
fn a_connected_flow_has_no_unreachable_scene() {
    let atlas = crunk_layout::FocusAtlas::new(
        vec![scene("menu", ONE_BUTTON), scene("game", ONE_BUTTON)],
        &[hop("menu", "game"), hop("game", "menu")],
    );
    assert!(atlas.unreachable_scenes().is_empty());
}

// frob:tests FocusAtlas.stranded_scenes
#[test]
fn scenes_circling_with_no_way_back_are_stranded() {
    let atlas = crunk_layout::FocusAtlas::new(
        vec![
            scene("menu", ONE_BUTTON),
            scene("a", ONE_BUTTON),
            scene("b", ONE_BUTTON),
        ],
        &[hop("menu", "a"), hop("a", "b"), hop("b", "a")],
    );
    assert_eq!(atlas.stranded_scenes(), vec![1, 2]);
}

// frob:tests FocusAtlas.stranded_scenes
#[test]
fn a_scene_that_ends_the_flow_is_not_stranded() {
    let atlas = crunk_layout::FocusAtlas::new(
        vec![scene("menu", ONE_BUTTON), scene("credits", ONE_BUTTON)],
        &[hop("menu", "credits")],
    );
    assert!(atlas.stranded_scenes().is_empty());
}

// frob:tests FocusAtlas.new
#[test]
fn a_transition_to_an_unknown_screen_is_dangling() {
    let atlas =
        crunk_layout::FocusAtlas::new(vec![scene("menu", ONE_BUTTON)], &[hop("menu", "ghost")]);
    assert!(atlas.links.is_empty());
    assert_eq!(atlas.dangling.len(), 1);
    assert_eq!(atlas.dangling[0].to, "ghost");
}

fn solved_node(id: &str, x: f32, y: f32) -> SolvedNode {
    SolvedNode {
        id: id.to_owned(),
        parent: None,
        kind: NodeKind::Box,
        x,
        y,
        width: 10.0,
        height: 10.0,
        text: None,
        zero_size: false,
        overflow: Vec::new(),
        tokens: Default::default(),
    }
}

fn solved(nodes: Vec<SolvedNode>) -> LayoutSolve {
    LayoutSolve {
        version: 1,
        viewport_width: 100.0,
        viewport_height: 100.0,
        nodes,
        focus_order: Vec::new(),
    }
}

/// Buttons a, b, c in document order, laid out as a at top-left, b at top-right, c below a.
fn corner_graph() -> FocusGraph {
    let doc = parse_scene_html(MENU).expect("parses");
    let layout = solved(vec![
        solved_node("a", 0.0, 0.0),
        solved_node("b", 50.0, 0.0),
        solved_node("c", 0.0, 50.0),
    ]);
    FocusGraph::from_solved(&doc, &layout)
}

// frob:tests FocusGraph.from_solved
#[test]
fn solved_geometry_gives_horizontal_neighbours_document_order_cannot() {
    let g = corner_graph();
    assert_eq!(moves(&g, "a", Direction::Right).as_deref(), Some("b"));
    assert_eq!(moves(&g, "b", Direction::Left).as_deref(), Some("a"));
}

// frob:tests FocusGraph.from_solved
#[test]
fn solved_geometry_picks_the_straight_neighbour_below() {
    let g = corner_graph();
    assert_eq!(moves(&g, "a", Direction::Down).as_deref(), Some("c"));
    assert_eq!(moves(&g, "c", Direction::Up).as_deref(), Some("a"));
}

// frob:tests FocusGraph.from_solved
#[test]
fn solved_geometry_leaves_edges_with_nothing_beyond_them_open() {
    let g = corner_graph();
    assert_eq!(moves(&g, "a", Direction::Up), None);
    assert_eq!(moves(&g, "b", Direction::Right), None);
}

// frob:tests FocusGraph.from_solved
#[test]
fn a_group_with_an_unsolved_member_keeps_document_order() {
    let doc = parse_scene_html(MENU).expect("parses");
    let g = FocusGraph::from_solved(&doc, &solved(vec![solved_node("a", 0.0, 0.0)]));
    assert_eq!(moves(&g, "a", Direction::Down).as_deref(), Some("b"));
}
