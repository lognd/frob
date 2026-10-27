//! Scene-level styling and the taffy tree: hidden nodes, ids, implicit tracks, stretching.

// frob:ticket 01M5XCWXYNXW0RW8VRDQPY31M6

use crunk_layout::style::{FindingKind, ParentCtx, StyleError, TokenMap, build_taffy, style_scene};
use crunk_scene::parse_scene_html;
use taffy::{AvailableSpace, Size, TraversePartialTree};

fn solve(
    html: &str,
    w: f32,
    h: f32,
) -> (
    crunk_layout::style::LayoutTree,
    crunk_layout::style::StyledScene,
) {
    let doc = parse_scene_html(html).expect("parses");
    let scene = style_scene(&doc, &TokenMap::new(), ParentCtx::DEFINITE).expect("styles");
    let mut lt = build_taffy(&scene).expect("builds");
    let root = lt.roots[0];
    lt.tree
        .compute_layout(
            root,
            Size {
                width: AvailableSpace::Definite(w),
                height: AvailableSpace::Definite(h),
            },
        )
        .expect("computes");
    (lt, scene)
}

// frob:tests build_taffy
// frob:tests style_scene
#[test]
fn display_none_is_hidden_but_keeps_its_id() {
    let html = "<div data-id=\"root\" style=\"width:100px;height:100px\">\
<div data-id=\"gone\" style=\"display:none\"><span data-id=\"inner\"></span></div>\
<div data-id=\"kept\" style=\"height:10px\"></div></div>";
    let doc = parse_scene_html(html).expect("parses");
    let scene = style_scene(&doc, &TokenMap::new(), ParentCtx::DEFINITE).expect("styles");
    assert_eq!(scene.nodes.len(), 4);
    let lt = build_taffy(&scene).expect("builds");
    assert_eq!(lt.hidden, vec!["gone".to_owned(), "inner".to_owned()]);
    assert!(lt.ids.contains_key("root") && lt.ids.contains_key("kept"));
    assert!(!lt.ids.contains_key("gone") && !lt.ids.contains_key("inner"));
    assert_eq!(lt.tree.child_count(lt.ids["root"]), 1);
}

// frob:tests style_scene
#[test]
fn undefined_token_in_scene_names_element_and_line() {
    let html =
        "<div data-id=\"root\">\n<div data-id=\"card\" style=\"padding: var(--pad)\"></div></div>";
    let doc = parse_scene_html(html).expect("parses");
    let errs = style_scene(&doc, &TokenMap::new(), ParentCtx::DEFINITE).expect_err("fails");
    assert_eq!(errs.len(), 1);
    assert!(
        matches!(&errs[0], StyleError::UndefinedToken { element, line: 2, .. } if element == "card")
    );
}

// frob:tests style_scene
#[test]
fn duplicate_data_id_is_an_error() {
    let doc =
        parse_scene_html("<div data-id=\"a\"></div><div data-id=\"a\"></div>").expect("parses");
    let errs = style_scene(&doc, &TokenMap::new(), ParentCtx::DEFINITE).expect_err("fails");
    assert!(matches!(errs[0], StyleError::DuplicateDataId { .. }));
}

// frob:tests style_scene
#[test]
fn scaffold_and_idless_elements_are_skipped_transparently() {
    let html =
        "<html><body><div data-id=\"root\"><p>x</p><div data-id=\"kid\"></div></div></body></html>";
    let doc = parse_scene_html(html).expect("parses");
    let scene = style_scene(&doc, &TokenMap::new(), ParentCtx::DEFINITE).expect("styles");
    let ids: Vec<&str> = scene.nodes.iter().map(|n| n.data_id.as_str()).collect();
    assert_eq!(ids, ["root", "kid"]);
    assert_eq!(scene.nodes[1].parent, Some(0));
    assert!(
        scene
            .findings
            .iter()
            .any(|f| f.kind == FindingKind::MissingDataId)
    );
}

// frob:tests build_taffy
#[test]
fn grid_span_past_explicit_tracks_creates_implicit_tracks() {
    let html = "<div data-id=\"g\" style=\"display:grid;width:300px;height:100px;grid-template-columns:100px 100px;grid-auto-columns:50px\">\
<div data-id=\"c\" style=\"grid-column:4;width:30px;height:10px\"></div></div>";
    let (lt, _) = solve(html, 300.0, 100.0);
    let l = lt.tree.layout(lt.ids["c"]).expect("layout");
    assert!((l.location.x - 250.0).abs() < 0.01, "x = {}", l.location.x);
    assert!((l.size.width - 30.0).abs() < 0.01);
}

// frob:tests build_taffy
#[test]
fn absolute_opposing_insets_without_size_stretch() {
    let html = "<div data-id=\"p\" style=\"position:relative;width:200px;height:100px\">\
<div data-id=\"a\" style=\"position:absolute;left:10px;right:10px;top:0;height:20px\"></div></div>";
    let (lt, _) = solve(html, 200.0, 100.0);
    let l = lt.tree.layout(lt.ids["a"]).expect("layout");
    assert!((l.size.width - 180.0).abs() < 0.01, "w = {}", l.size.width);
    assert!((l.location.x - 10.0).abs() < 0.01);
}

// frob:tests build_taffy
#[test]
fn flex_wrap_reverse_on_column_lays_out() {
    let html = "<div data-id=\"f\" style=\"display:flex;flex-direction:column;flex-wrap:wrap-reverse;width:100px;height:25px\">\
<div data-id=\"a\" style=\"width:10px;height:20px\"></div><div data-id=\"b\" style=\"width:10px;height:20px\"></div></div>";
    let (lt, _) = solve(html, 100.0, 25.0);
    let a = lt.tree.layout(lt.ids["a"]).expect("layout");
    let b = lt.tree.layout(lt.ids["b"]).expect("layout");
    assert!(
        b.location.x < a.location.x,
        "wrap-reverse puts the second line first: a={} b={}",
        a.location.x,
        b.location.x
    );
}

// frob:tests style_scene
#[test]
fn tokens_resolve_through_the_scene() {
    let doc =
        parse_scene_html("<div data-id=\"a\" style=\"width: var(--w)\"></div>").expect("parses");
    let tokens = TokenMap::from_pairs([("--w", "64px")]);
    let scene = style_scene(&doc, &tokens, ParentCtx::DEFINITE).expect("styles");
    assert_eq!(
        scene.nodes[0].style.size.width,
        taffy::Dimension::length(64.0)
    );
}
