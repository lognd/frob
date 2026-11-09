//! Geometry findings read from a solved document: a child that spills out of its parent
//! (LAYOUT001) and siblings whose rectangles collide (LAYOUT002). The crunk-rules LAYOUT rules and
//! the solver corpus test both call these, so there is one definition of "overflows" and "overlaps".

// frob:ticket 01M6Z15WBQCQDYSHC0HSXJJYWH

use crate::output::{LayoutSolve, SolvedNode};

/// The tolerance in pixels: touching edges and sub-pixel slivers are neither overflow nor overlap.
pub const EPSILON: f32 = 0.5;

/// The rectangle `(left, top, right, bottom)` of a solved node.
pub fn rect(n: &SolvedNode) -> (f32, f32, f32, f32) {
    (n.x, n.y, n.x + n.width, n.y + n.height)
}

/// A node whose rectangle extends beyond its parent's.
#[derive(Debug, Clone, Copy)]
pub struct ChildOverflow<'a> {
    /// The overflowing child.
    pub node: &'a SolvedNode,
    /// Its parent.
    pub parent: &'a SolvedNode,
}

/// Two siblings whose rectangles intersect with positive area.
#[derive(Debug, Clone, Copy)]
pub struct SiblingOverlap<'a> {
    /// The earlier sibling in document order.
    pub a: &'a SolvedNode,
    /// The later sibling in document order.
    pub b: &'a SolvedNode,
    /// Width of the intersection in pixels.
    pub across: f32,
    /// Height of the intersection in pixels.
    pub down: f32,
}

/// Every node of `doc` that extends more than [`EPSILON`] beyond its parent, in document order.
pub fn child_overflows(doc: &LayoutSolve) -> Vec<ChildOverflow<'_>> {
    doc.nodes
        .iter()
        .filter_map(|node| {
            let parent_id = node.parent.as_deref()?;
            let parent = doc.nodes.iter().find(|p| p.id == parent_id)?;
            let (l, t, r, b) = rect(node);
            let (pl, pt, pr, pb) = rect(parent);
            let spills =
                l < pl - EPSILON || t < pt - EPSILON || r > pr + EPSILON || b > pb + EPSILON;
            spills.then_some(ChildOverflow { node, parent })
        })
        .collect()
}

/// Every pair of siblings (same non-root parent) of `doc` that overlap by more than [`EPSILON`]
/// in both directions, in document order.
pub fn sibling_overlaps(doc: &LayoutSolve) -> Vec<SiblingOverlap<'_>> {
    let mut out = Vec::new();
    for (i, a) in doc.nodes.iter().enumerate() {
        for b in &doc.nodes[i + 1..] {
            if a.parent.is_none() || a.parent != b.parent {
                continue;
            }
            let (al, at, ar, ab) = rect(a);
            let (bl, bt, br, bb) = rect(b);
            let across = ar.min(br) - al.max(bl);
            let down = ab.min(bb) - at.max(bt);
            if across > EPSILON && down > EPSILON {
                out.push(SiblingOverlap { a, b, across, down });
            }
        }
    }
    out
}
