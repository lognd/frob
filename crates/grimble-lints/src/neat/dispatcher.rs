//! `NEAT031`: a dispatcher whose branch condition is more than a guard.

// frob:ticket 01M3Z7151078ZAM6AM1GFWC6QP

use std::collections::BTreeMap;

use tree_sitter::Node;

use super::unit::Unit;

/// A branch condition heavier than a guard.
pub struct Offender<'t> {
    /// The `if` expression.
    pub node: Node<'t>,
    /// 0-based row of the `if`.
    pub row: usize,
    /// The condition weight.
    pub weight: usize,
}

const BRANCHES: [&str; 5] = [
    "if_expression",
    "match_expression",
    "for_expression",
    "while_expression",
    "loop_expression",
];

/// True when the unit is a dispatcher: marked, or a `match` on one of its own parameters.
fn is_dispatcher(unit: &Unit<'_>, src: &str) -> bool {
    if unit.is_marked_dispatcher() {
        return true;
    }
    let params = unit.params(src);
    let Some(body) = unit.node.child_by_field_name("body") else {
        return false;
    };
    let mut stack = vec![body];
    while let Some(n) = stack.pop() {
        if n.kind() == "match_expression"
            && let Some(v) = n.child_by_field_name("value")
        {
            let text = src[v.byte_range()].trim_start_matches(['*', '&']);
            let root = text.split(['.', '(', '[']).next().unwrap_or(text);
            if params.iter().any(|p| p == root) {
                return true;
            }
        }
        let mut cur = n.walk();
        stack.extend(n.children(&mut cur));
    }
    false
}

/// The weight of a condition: calls, closures (x2), nested branch groups (x2) and refs to the
/// unit's own locals, which weigh the call chain that feeds them plus one.
fn weight(node: Node<'_>, src: &str, locals: &BTreeMap<String, usize>) -> usize {
    let mut total = 0;
    let mut stack = vec![node];
    while let Some(n) = stack.pop() {
        total += match n.kind() {
            "call_expression" | "macro_invocation" => 1,
            "closure_expression" => 2,
            k if BRANCHES.contains(&k) => 2,
            "identifier" => locals.get(&src[n.byte_range()]).map_or(0, |w| w + 1),
            _ => 0,
        };
        let mut cur = n.walk();
        stack.extend(n.children(&mut cur));
    }
    total
}

/// The `let` locals of a body with the weight of each initializer.
fn locals(body: Node<'_>, src: &str) -> BTreeMap<String, usize> {
    let mut out = BTreeMap::new();
    let mut stack = vec![body];
    while let Some(n) = stack.pop() {
        if n.kind() == "let_declaration"
            && let (Some(p), Some(v)) = (
                n.child_by_field_name("pattern"),
                n.child_by_field_name("value"),
            )
        {
            out.insert(
                src[p.byte_range()].to_owned(),
                weight(v, src, &BTreeMap::new()),
            );
        }
        let mut cur = n.walk();
        stack.extend(n.children(&mut cur));
    }
    out
}

/// Every branch of a dispatcher whose condition weighs more than `limit`, in source order.
pub fn offenders<'t>(unit: &Unit<'t>, src: &str, limit: usize) -> Vec<Offender<'t>> {
    if !is_dispatcher(unit, src) {
        return Vec::new();
    }
    let Some(body) = unit.node.child_by_field_name("body") else {
        return Vec::new();
    };
    let locals = locals(body, src);
    let mut out = Vec::new();
    let mut stack = vec![body];
    while let Some(n) = stack.pop() {
        if n.kind() == "if_expression"
            && let Some(c) = n.child_by_field_name("condition")
        {
            let w = weight(c, src, &locals);
            if w > limit {
                out.push(Offender {
                    node: n,
                    row: n.start_position().row,
                    weight: w,
                });
            }
        }
        let mut cur = n.walk();
        stack.extend(n.children(&mut cur));
    }
    out.sort_by_key(|o| o.node.start_byte());
    out
}
