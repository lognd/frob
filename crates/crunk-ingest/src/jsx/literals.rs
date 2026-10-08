//! String and template literals of a folded source, as [`Segment`]s of class-list text.
//!
//! The folder keeps three shapes for the same JavaScript: the `const_value` forms (`lit str`,
//! `apply(op template)`) inside JSX attributes and call arguments, and the plain syntax shapes
//! (`lit string`, the `template_string` adapter node) everywhere else. Both are read here, so a
//! caller never cares which context a literal was folded in.

// frob:ticket 01M43ARYFVG86PAGGM78JGRZY3

use gob_ir::NodeId;

use super::cx::Cx;
use super::tokens::Segment;

/// The `(start, end)` of the text between the quotes when `id` is a quoted string literal.
fn string_inner(cx: &Cx<'_>, id: NodeId) -> Option<(usize, usize)> {
    let (kind, _) = cx.lit(id)?;
    if kind != "str" && kind != "string" {
        return None;
    }
    let (s, e) = cx.range(id)?;
    let text = &cx.src[s..e];
    let quote = text.chars().next().filter(|c| matches!(c, '"' | '\''))?;
    (text.len() >= 2 && text.ends_with(quote)).then(|| (s + 1, e - 1))
}

/// One child of a template literal.
enum Part {
    /// A static fragment: its text range.
    Quasi(usize, usize),
    /// A `${}` substitution (or, in the lowered form, the expression inside it).
    Subst(NodeId),
    /// An escape sequence between fragments; it separates text but is no substitution.
    Escape,
}

/// The parts of a template literal node, or `None` when `id` is not one.
fn template_parts(cx: &Cx<'_>, id: NodeId) -> Option<Vec<Part>> {
    if cx.is_op(id, "template") {
        let mut parts = Vec::new();
        for &c in &cx.kids(id)[1..] {
            let quasi = cx.lit(c).filter(|(k, _)| *k == "str").and_then(|_| {
                let (s, e) = cx.range(c)?;
                let text = &cx.src[s..e];
                let after_open = s > 0 && matches!(cx.src.as_bytes()[s - 1], b'`' | b'}');
                let quoted_expr = text.starts_with(['"', '\'']) && !after_open;
                if text.starts_with('\\') {
                    Some(Part::Escape)
                } else if quoted_expr {
                    None
                } else {
                    Some(Part::Quasi(s, e))
                }
            });
            parts.push(quasi.unwrap_or(Part::Subst(c)));
        }
        return Some(parts);
    }
    if cx.is_adapter(id, "template_string") {
        let mut parts = Vec::new();
        for &c in cx.kids(id) {
            match cx.lit(c) {
                Some(("string_fragment", _)) => {
                    if let Some((s, e)) = cx.range(c) {
                        parts.push(Part::Quasi(s, e));
                    }
                }
                Some(("escape_sequence", _)) => parts.push(Part::Escape),
                None if cx.is_adapter(c, "template_substitution") => parts.push(Part::Subst(c)),
                Some(_) | None => {}
            }
        }
        return Some(parts);
    }
    None
}

/// The static fragments of the template `parts`, each with its substitution boundaries.
fn template_segments(cx: &Cx<'_>, parts: &[Part]) -> Vec<Segment> {
    let mut out = Vec::new();
    for (i, part) in parts.iter().enumerate() {
        let Part::Quasi(s, e) = part else { continue };
        out.push(Segment {
            text: cx.src[*s..*e].to_owned(),
            start: *s,
            left: i > 0 && matches!(parts[i - 1], Part::Subst(_)),
            right: matches!(parts.get(i + 1), Some(Part::Subst(_))),
            template: true,
        });
    }
    out
}

/// The segments of `id` when it is a string or template literal itself; `None` for anything else.
pub(super) fn literal_segments(cx: &Cx<'_>, id: NodeId) -> Option<Vec<Segment>> {
    if let Some((s, e)) = string_inner(cx, id) {
        return Some(vec![Segment {
            text: cx.src[s..e].to_owned(),
            start: s,
            left: false,
            right: false,
            template: false,
        }]);
    }
    template_parts(cx, id).map(|parts| template_segments(cx, &parts))
}

/// Every string and template literal anywhere under `id` (itself included), in pre-order, each
/// tokenized independently: the `className` attribute's own meaning makes any literal inside it
/// a class list, whichever helper call or expression wraps it.
pub(super) fn blind_segments(cx: &Cx<'_>, id: NodeId, out: &mut Vec<Segment>) {
    if let Some(segments) = literal_segments(cx, id) {
        out.extend(segments);
        if let Some(parts) = template_parts(cx, id) {
            for part in parts {
                if let Part::Subst(c) = part {
                    blind_segments(cx, c, out);
                }
            }
        }
        return;
    }
    for &c in cx.kids(id) {
        blind_segments(cx, c, out);
    }
}

/// True when `id` is a string literal or a template literal.
pub(super) fn is_literal(cx: &Cx<'_>, id: NodeId) -> bool {
    string_inner(cx, id).is_some() || template_parts(cx, id).is_some()
}
