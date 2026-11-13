//! Compute the tree and read the layout back as raw output nodes.

// frob:ticket 01M5XCWYB9M2YSJ5EGABMREX1B

use taffy::{AvailableSpace, Layout, NodeId, Size, TaffyTree};

use super::prepare::TextCtx;
use super::tree::{Built, Entry};
use super::{SolveError, SolveNote};
use crate::output::{Axis, NodeKind, RawNode, SolvedText};
use crate::text::{AvailableWidth, TextError, TextMeasurer, measure_for_taffy};

/// Lays every root out against the viewport, measuring text leaves with `fonts`.
pub(crate) fn compute(
    built: &mut Built,
    viewport: (f32, f32),
    fonts: &mut TextMeasurer,
) -> Result<(), SolveError> {
    let space = Size {
        width: AvailableSpace::Definite(viewport.0),
        height: AvailableSpace::Definite(viewport.1),
    };
    let roots: Vec<_> = built
        .entries
        .iter()
        .filter(|e| e.parent.is_none())
        .map(|e| e.id)
        .collect();
    let mut failed: Option<TextError> = None;
    for root in roots {
        layout_root(&mut built.tree, root, space, fonts, &mut failed)?;
    }
    failed.map_or(Ok(()), |e| Err(e.into()))
}

/// Lays out one root, measuring text through `fonts`; the first measure error lands in `failed`.
fn layout_root(
    tree: &mut TaffyTree<TextCtx>,
    root: NodeId,
    space: Size<AvailableSpace>,
    fonts: &mut TextMeasurer,
    failed: &mut Option<TextError>,
) -> Result<(), SolveError> {
    tree.compute_layout_with_measure(root, space, |input, _id, ctx, style| {
        taffy::compute_leaf_layout(
            input,
            style,
            |_, _| 0.0,
            |known, avail| {
                let Some(c) = ctx else { return Size::ZERO };
                measure_for_taffy(fonts, &c.text, &c.style, known, avail).unwrap_or_else(|e| {
                    failed.get_or_insert(e);
                    Size::ZERO
                })
            },
        )
    })
    .map_err(|e| SolveError::Engine(e.to_string()))
}

/// Reads positions (absolute, viewport coordinates) and text metrics for every entry.
pub(crate) fn collect(
    built: &Built,
    viewport: (f32, f32),
    fonts: &mut TextMeasurer,
    notes: &mut Vec<SolveNote>,
) -> Result<Vec<RawNode>, SolveError> {
    let mut origins: Vec<(f32, f32)> = Vec::with_capacity(built.entries.len());
    let mut out = Vec::with_capacity(built.entries.len());
    for e in &built.entries {
        let l = built
            .tree
            .layout(e.id)
            .map_err(|err| SolveError::Engine(err.to_string()))?;
        let base = e.parent.map_or((0.0, 0.0), |p| origins[p]);
        let pos = (base.0 + l.location.x, base.1 + l.location.y);
        origins.push(pos);
        note_entry(e, l, viewport, notes);
        let text = solved_text(e, l, fonts, notes)?;
        out.push(raw_node(built, e, l, pos, text));
    }
    Ok(out)
}

fn raw_node(
    built: &Built,
    e: &Entry,
    l: &Layout,
    pos: (f32, f32),
    text: Option<SolvedText>,
) -> RawNode {
    RawNode {
        id: e.name.clone(),
        parent: e.parent.map(|p| built.entries[p].name.clone()),
        kind: if text.is_some() {
            NodeKind::Text
        } else {
            NodeKind::Box
        },
        x: pos.0,
        y: pos.1,
        width: l.size.width,
        height: l.size.height,
        content_width: Some(content_extent(l).0),
        content_height: Some(content_extent(l).1),
        text,
        tokens: e.tokens.clone(),
    }
}

/// Unknown-tag and page-overflow notes.
fn note_entry(e: &Entry, l: &Layout, viewport: (f32, f32), notes: &mut Vec<SolveNote>) {
    if let Some(tag) = &e.unknown_tag {
        notes.push(SolveNote::UnknownTag {
            id: e.name.clone(),
            tag: tag.clone(),
        });
    }
    if e.parent.is_none() {
        for (axis, size, limit) in [
            (Axis::X, l.size.width, viewport.0),
            (Axis::Y, l.size.height, viewport.1),
        ] {
            if size > limit {
                notes.push(SolveNote::PageOverflow {
                    id: e.name.clone(),
                    axis,
                    amount: size - limit,
                });
            }
        }
    }
}

/// Final line count and notes of a text leaf, measured at its content width.
fn solved_text(
    e: &Entry,
    l: &Layout,
    fonts: &mut TextMeasurer,
    notes: &mut Vec<SolveNote>,
) -> Result<Option<SolvedText>, SolveError> {
    let Some(ctx) = &e.text else { return Ok(None) };
    let inner = l.size.width - l.padding.left - l.padding.right - l.border.left - l.border.right;
    let m = fonts.measure(
        &ctx.text,
        &ctx.style,
        AvailableWidth::Definite(inner.max(0.0)),
    )?;
    if !m.notes.is_empty() {
        notes.push(SolveNote::MissingGlyph { id: e.name.clone() });
    }
    Ok(Some(SolvedText {
        content: ctx.text.clone(),
        font_size: ctx.style.size_px,
        lines: m.lines as usize,
    }))
}

/// Content extent in border-box coordinates, counting the far padding and border as reachable.
fn content_extent(l: &Layout) -> (f32, f32) {
    let r = l.scrollable_overflow_rect;
    (
        l.border.left + r.right + l.padding.right + l.border.right,
        l.border.top + r.bottom + l.padding.bottom + l.border.bottom,
    )
}
