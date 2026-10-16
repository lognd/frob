//! The `resolves to` edge relation of an example model: references, their calls, and the
//! external ambient units (`time.time`) an unresolved reference names.

// frob:ticket 01M539NQGFCK3VJGRBM3H6CT56

use crate::exec::is_external_unit;
use gob_ir::eval::{Ctx, Relation};
use gob_ir::{Model, Operator, Truth, Universal};

/// The `resolves to` relation: each ref's declarations, each call's head-ref targets, and a ref
/// that names an external ambient unit resolving to itself (certainly, not on the unknown frontier).
pub(crate) fn resolves_relation(model: &Model) -> Relation {
    let base = Ctx::new(model).rel_resolves();
    let term = model.term();
    let mut out = Relation::new();
    let external = |n| is_external_unit(model, n);
    for (a, b, t) in base.iter() {
        out.insert(a, b, t);
    }
    for a in base.unknown_out().filter(|&a| !external(a)) {
        out.mark_unknown_out(a);
    }
    for id in term.ids().filter(|&n| external(n)) {
        tracing::debug!(node = id.index(), "external ambient unit resolved");
        out.insert(id, id, Truth::Yes);
    }
    for id in term.ids() {
        let node = term.node(id);
        if !matches!(node.op(), Operator::Universal(Universal::Apply { kind }) if kind == "call") {
            continue;
        }
        let Some(&head) = node.children().first() else {
            continue;
        };
        for (b, t) in out.image(head) {
            out.insert(id, b, t);
        }
        if base.is_unknown_out(head) && !external(head) {
            out.mark_unknown_out(id);
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::resolves_relation;
    use gob_ir::Truth;

    fn call_and_head(model: &gob_ir::Model) -> (gob_ir::NodeId, gob_ir::NodeId) {
        let t = model.term();
        let call = t
            .ids()
            .find(|&n| matches!(t.node(n).op(), gob_ir::Operator::Universal(gob_ir::Universal::Apply { kind }) if kind == "call"))
            .expect("a call");
        (call, t.node(call).children()[0])
    }

    // frob:tests crates/gob-plan/src/examples/resolves.rs::resolves_relation
    #[test]
    fn an_ambient_python_call_resolves_to_its_external_unit() {
        let m = gob_symbols::model_of_source("python", "def f():\n    return time.time()\n")
            .expect("model");
        let (call, head) = call_and_head(&m);
        let rel = resolves_relation(&m);
        assert_eq!(rel.get(call, head), Truth::Yes);
        assert!(!rel.is_unknown_out(call));
    }

    // frob:tests crates/gob-plan/src/examples/resolves.rs::resolves_relation
    #[test]
    fn an_unknown_non_ambient_call_stays_on_the_unknown_frontier() {
        let m = gob_symbols::model_of_source("python", "def f():\n    return helper()\n")
            .expect("model");
        let (call, head) = call_and_head(&m);
        let rel = resolves_relation(&m);
        assert!(rel.is_unknown_out(call));
        assert_eq!(rel.get(call, head), Truth::Unknown);
    }
}
