//! Style mapping: per-property taffy styles, tokens, and the acceptance edge cases.

// frob:ticket 01M5XCWXYNXW0RW8VRDQPY31M6

use crunk_layout::style::{
    ElementRef, FindingKind, MappedStyle, ParentCtx, StyleError, TokenMap, map_declarations,
};
use taffy::style_helpers::{TaffyGridLine, TaffyGridSpan};
use taffy::{
    AlignContent, AlignItems, BoxSizing, Dimension, Display, FlexDirection, FlexWrap, GridAutoFlow,
    GridPlacement, LengthPercentage, LengthPercentageAuto, Position, Size,
};

const EL: ElementRef<'static> = ElementRef {
    data_id: "box",
    line: 7,
};

fn decls(css: &str) -> Vec<(String, String)> {
    css.split(';')
        .filter_map(|d| d.split_once(':'))
        .map(|(k, v)| (k.trim().to_owned(), v.trim().to_owned()))
        .collect()
}

fn try_map(css: &str, tokens: &TokenMap, parent: ParentCtx) -> Result<MappedStyle, StyleError> {
    map_declarations(EL, &decls(css), tokens, parent)
}

fn map(css: &str) -> MappedStyle {
    try_map(css, &TokenMap::new(), ParentCtx::DEFINITE).expect("maps")
}

fn kinds(m: &MappedStyle) -> Vec<FindingKind> {
    m.findings.iter().map(|f| f.kind).collect()
}

const INDEFINITE: ParentCtx = ParentCtx {
    width_definite: false,
    height_definite: false,
};

// frob:tests map_declarations
#[test]
fn prop_display_and_defaults() {
    let m = map("");
    assert_eq!(m.style.display, Display::Block);
    assert_eq!(m.style.box_sizing, BoxSizing::ContentBox);
    assert_eq!(map("display:flex").style.display, Display::Flex);
    assert_eq!(map("display:grid").style.display, Display::Grid);
    assert_eq!(
        map("box-sizing:border-box").style.box_sizing,
        BoxSizing::BorderBox
    );
}

// frob:tests map_declarations
#[test]
fn prop_position_and_insets() {
    let m = map("position:absolute;top:4px;left:10%;right:1rem");
    assert_eq!(m.style.position, Position::Absolute);
    assert_eq!(m.style.inset.top, LengthPercentageAuto::length(4.0));
    assert_eq!(m.style.inset.left, LengthPercentageAuto::percent(0.1));
    assert_eq!(m.style.inset.right, LengthPercentageAuto::length(16.0));
    assert_eq!(m.style.inset.bottom, LengthPercentageAuto::auto());
    let m = map("inset:1px 2px");
    assert_eq!(m.style.inset.top, LengthPercentageAuto::length(1.0));
    assert_eq!(m.style.inset.left, LengthPercentageAuto::length(2.0));
}

// frob:tests map_declarations
#[test]
fn prop_sizes_min_max() {
    let m =
        map("width:100px;height:50%;min-width:10px;max-width:200px;min-height:0;max-height:none");
    assert_eq!(
        m.style.size,
        Size {
            width: Dimension::length(100.0),
            height: Dimension::percent(0.5)
        }
    );
    assert_eq!(m.style.min_size.width, LengthPercentageAuto::length(10.0));
    assert_eq!(m.style.max_size.width, LengthPercentageAuto::length(200.0));
    assert_eq!(m.style.min_size.height, LengthPercentageAuto::length(0.0));
    assert_eq!(m.style.max_size.height, LengthPercentageAuto::auto());
}

// frob:tests map_declarations
#[test]
fn prop_margin_padding_border() {
    let m = map("margin:1px 2px 3px 4px;padding:5px 6px;border:2px solid red");
    assert_eq!(m.style.margin.top, LengthPercentageAuto::length(1.0));
    assert_eq!(m.style.margin.left, LengthPercentageAuto::length(4.0));
    assert_eq!(m.style.padding.top, LengthPercentage::length(5.0));
    assert_eq!(m.style.padding.right, LengthPercentage::length(6.0));
    assert_eq!(m.style.border.bottom, LengthPercentage::length(2.0));
    assert_eq!(
        map("margin:auto").style.margin.left,
        LengthPercentageAuto::auto()
    );
    assert_eq!(
        map("padding-left:7px").style.padding.left,
        LengthPercentage::length(7.0)
    );
}

// frob:tests map_declarations
#[test]
fn prop_gap_forms() {
    let m = map("gap:4px 8px");
    assert_eq!(m.style.gap.height, LengthPercentage::length(4.0));
    assert_eq!(m.style.gap.width, LengthPercentage::length(8.0));
    let m = map("gap:6px;column-gap:2px");
    assert_eq!(m.style.gap.height, LengthPercentage::length(6.0));
    assert_eq!(m.style.gap.width, LengthPercentage::length(2.0));
}

// frob:tests map_declarations
#[test]
fn prop_flex_both_wrap_directions() {
    let m = map("display:flex;flex-direction:row;flex-wrap:wrap");
    assert_eq!(m.style.flex_direction, FlexDirection::Row);
    assert_eq!(m.style.flex_wrap, FlexWrap::Wrap);
    let m = map("display:flex;flex-direction:column-reverse;flex-wrap:wrap-reverse");
    assert_eq!(m.style.flex_direction, FlexDirection::ColumnReverse);
    assert_eq!(m.style.flex_wrap, FlexWrap::WrapReverse);
    let m = map("flex-flow:column wrap");
    assert_eq!(m.style.flex_direction, FlexDirection::Column);
    assert_eq!(m.style.flex_wrap, FlexWrap::Wrap);
}

// frob:tests map_declarations
#[test]
fn prop_flex_shorthand() {
    let m = map("flex:1");
    assert_eq!((m.style.flex_grow, m.style.flex_shrink), (1.0, 1.0));
    assert_eq!(m.style.flex_basis, Dimension::percent(0.0));
    let m = map("flex:2 0 10px");
    assert_eq!((m.style.flex_grow, m.style.flex_shrink), (2.0, 0.0));
    assert_eq!(m.style.flex_basis, Dimension::length(10.0));
    let m = map("flex:none");
    assert_eq!((m.style.flex_grow, m.style.flex_shrink), (0.0, 0.0));
    assert_eq!(m.style.flex_basis, Dimension::auto());
    assert_eq!(
        map("flex-basis:25%").style.flex_basis,
        Dimension::percent(0.25)
    );
}

// frob:tests map_declarations
#[test]
fn prop_alignment() {
    let m = map(
        "align-items:center;justify-content:space-between;align-content:flex-end;align-self:stretch",
    );
    assert_eq!(m.style.align_items, AlignItems::CENTER);
    assert_eq!(m.style.justify_content, AlignContent::SPACE_BETWEEN);
    assert_eq!(m.style.align_content, AlignContent::FLEX_END);
    assert_eq!(m.style.align_self, Some(AlignItems::STRETCH));
}

// frob:tests map_declarations
#[test]
fn prop_aspect_ratio() {
    assert_eq!(
        map("aspect-ratio:16 / 9").style.aspect_ratio,
        Some(16.0 / 9.0)
    );
    assert_eq!(map("aspect-ratio:2").style.aspect_ratio, Some(2.0));
    assert_eq!(map("aspect-ratio:auto").style.aspect_ratio, None);
}

// frob:tests map_declarations
#[test]
fn prop_grid_tracks_and_flow() {
    use taffy::{GridTemplateComponent, MaxTrackSizingFunction, MinTrackSizingFunction};
    let m = map(
        "display:grid;grid-template-columns:100px 1fr 20%;grid-auto-flow:column dense;grid-auto-rows:minmax(10px, auto)",
    );
    assert_eq!(m.style.grid_template_columns.len(), 3);
    let GridTemplateComponent::Single(t0) = m.style.grid_template_columns[0] else {
        panic!("single")
    };
    assert_eq!(t0.min, MinTrackSizingFunction::length(100.0));
    assert_eq!(t0.max, MaxTrackSizingFunction::length(100.0));
    let GridTemplateComponent::Single(t1) = m.style.grid_template_columns[1] else {
        panic!("single")
    };
    assert_eq!(t1.max, MaxTrackSizingFunction::fr(1.0));
    assert_eq!(m.style.grid_auto_flow, GridAutoFlow::ColumnDense);
    assert_eq!(m.style.grid_auto_rows.len(), 1);
    assert_eq!(
        m.style.grid_auto_rows[0].min,
        MinTrackSizingFunction::length(10.0)
    );
    let m = map("grid-template-columns:repeat(3, 1fr)");
    assert!(matches!(
        m.style.grid_template_columns[0],
        GridTemplateComponent::Repeat(_)
    ));
    assert!(
        try_map(
            "grid-template-columns:[a] 1fr",
            &TokenMap::new(),
            ParentCtx::DEFINITE
        )
        .is_err()
    );
}

// frob:tests map_declarations
#[test]
fn prop_grid_spans_and_lines() {
    let m = map("grid-column:1 / span 2;grid-row:3");
    assert_eq!(m.style.grid_column.start, GridPlacement::from_line_index(1));
    assert_eq!(m.style.grid_column.end, GridPlacement::from_span(2));
    assert_eq!(m.style.grid_row.start, GridPlacement::from_line_index(3));
    assert_eq!(m.style.grid_row.end, GridPlacement::Auto);
    let m = map("grid-column:span 3;grid-row-end:-1");
    assert_eq!(m.style.grid_column.start, GridPlacement::from_span(3));
    assert_eq!(m.style.grid_row.end, GridPlacement::from_line_index(-1));
}

// frob:tests map_declarations
#[test]
fn edge_min_above_max_resolves_to_min() {
    let m = map("min-width:300px;max-width:100px");
    assert_eq!(m.style.min_size.width, LengthPercentageAuto::length(300.0));
    assert_eq!(m.style.max_size.width, LengthPercentageAuto::length(300.0));
    assert_eq!(kinds(&m), vec![FindingKind::MinExceedsMax]);
}

// frob:tests map_declarations
#[test]
fn edge_percent_under_indefinite_parent_is_auto() {
    let m = try_map("width:50%;height:50%", &TokenMap::new(), INDEFINITE).expect("maps");
    assert_eq!(
        m.style.size,
        Size {
            width: Dimension::auto(),
            height: Dimension::auto()
        }
    );
    assert_eq!(
        kinds(&m),
        vec![
            FindingKind::PercentUnderIndefiniteParent,
            FindingKind::PercentUnderIndefiniteParent
        ]
    );
    let m = try_map(
        "width:50%",
        &TokenMap::new(),
        ParentCtx {
            width_definite: true,
            height_definite: false,
        },
    )
    .expect("maps");
    assert_eq!(m.style.size.width, Dimension::percent(0.5));
}

// frob:tests map_declarations
#[test]
fn edge_percent_height_needs_definite_parent_height() {
    let outer = map("width:100px");
    assert!(outer.child_ctx.width_definite);
    assert!(!outer.child_ctx.height_definite);
    let m = try_map("height:50%", &TokenMap::new(), outer.child_ctx).expect("maps");
    assert_eq!(m.style.size.height, Dimension::auto());
    let outer = map("width:100px;height:40px");
    assert!(outer.child_ctx.height_definite);
}

// frob:tests map_declarations
#[test]
fn edge_aspect_ratio_ignored_with_width_and_height() {
    let m = map("width:100px;height:50px;aspect-ratio:2");
    assert_eq!(m.style.aspect_ratio, None);
    assert_eq!(kinds(&m), vec![FindingKind::AspectRatioIgnored]);
    let m = map("width:100px;aspect-ratio:2");
    assert_eq!(m.style.aspect_ratio, Some(2.0));
}

// frob:tests map_declarations
#[test]
fn edge_negative_padding_and_gap_are_findings() {
    let m = map("padding:-4px;gap:-2px;border-width:-1px");
    assert_eq!(m.style.padding.top, LengthPercentage::length(0.0));
    assert_eq!(m.style.gap.width, LengthPercentage::length(0.0));
    assert_eq!(m.style.border.left, LengthPercentage::length(0.0));
    assert!(kinds(&m).iter().all(|k| *k == FindingKind::NegativeValue));
    assert_eq!(m.findings.len(), 4 + 1 + 4);
    let m = map("width:-5px;flex-grow:-1");
    assert_eq!(m.style.size.width, Dimension::auto());
    assert!(m.style.flex_grow.abs() < f32::EPSILON);
}

// frob:tests TokenMap.insert
// frob:tests map_declarations
#[test]
fn edge_undefined_token_names_element_and_line() {
    let err = try_map(
        "width:var(--missing)",
        &TokenMap::new(),
        ParentCtx::DEFINITE,
    )
    .expect_err("fails");
    assert_eq!(
        err,
        StyleError::UndefinedToken {
            element: "box".into(),
            line: 7,
            property: "width".into(),
            token: "--missing".into(),
        }
    );
    let text = err.to_string();
    assert!(text.contains("box") && text.contains("line 7") && text.contains("--missing"));
}

// frob:tests TokenMap.insert
// frob:tests map_declarations
#[test]
fn tokens_resolve_nested_and_fallback() {
    let mut t = TokenMap::new();
    t.insert("--gap", "var(--unit)");
    t.insert("--unit", "8px");
    let m = try_map(
        "padding:var(--gap);width:var(--nope, 40px)",
        &t,
        ParentCtx::DEFINITE,
    )
    .expect("maps");
    assert_eq!(m.style.padding.left, LengthPercentage::length(8.0));
    assert_eq!(m.style.size.width, Dimension::length(40.0));
}

// frob:tests map_declarations
#[test]
fn tokens_cycle_is_an_error() {
    let t = TokenMap::from_pairs([("--a", "var(--b)"), ("--b", "var(--a)")]);
    let err = try_map("width:var(--a)", &t, ParentCtx::DEFINITE).expect_err("cycle");
    assert!(matches!(err, StyleError::TokenCycle { .. }));
}

// frob:tests map_declarations
#[test]
fn bad_values_are_typed_errors_not_panics() {
    for css in [
        "display:inline",
        "width:12",
        "position:fixed",
        "gap:1px 2px 3px",
        "flex:1 2 3 4",
        "width:NaNpx",
        "grid-column:0",
    ] {
        let r = try_map(css, &TokenMap::new(), ParentCtx::DEFINITE);
        assert!(matches!(r, Err(StyleError::BadValue { .. })), "{css}");
    }
}

// frob:tests map_declarations
#[test]
fn unmapped_layout_property_is_a_finding() {
    let m = map("grid-template-areas:\"a b\";color:red");
    assert_eq!(kinds(&m), vec![FindingKind::UnmappedProperty]);
}

// frob:tests map_declarations
#[test]
fn display_none_sets_hidden() {
    let m = map("display:none");
    assert!(m.hidden);
    assert_eq!(m.style.display, Display::None);
    assert!(!map("display:flex").hidden);
}
