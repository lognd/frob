//! Readers for the `const_value` forms the TypeScript folder lowers object and array literals to
//! (gob-ir `const_value`, "Lowered forms").

// frob:ticket 01M47QKVBB5G9N1QZP3AVXTRHX

use gob_ir::const_value::{OP, OP_ARRAY, OP_OBJECT, OP_PROP, OP_SPREAD};
use gob_ir::{Model, NodeId, Operator, Universal};

/// The operator lexeme and arguments of an `apply(op)` node, if it is one.
fn op_form(model: &Model, node: NodeId) -> Option<(&str, &[NodeId])> {
    let term = model.term();
    let n = term.node(node);
    if !matches!(n.op(), Operator::Universal(Universal::Apply { kind }) if kind == OP) {
        return None;
    }
    let (&head, args) = n.children().split_first()?;
    match term.node(head).op() {
        Operator::Universal(Universal::Lit { kind, lexeme }) if kind == OP => {
            Some((lexeme.as_str(), args))
        }
        _ => None,
    }
}

/// One entry of an object literal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum Prop {
    /// `key: value` with a static key.
    Named(String, NodeId),
    /// A spread or a computed key: any property may be set.
    Unknown,
}

/// The entries of the object literal at `node`; `None` when `node` is not one.
pub(crate) fn object_props(model: &Model, node: NodeId) -> Option<Vec<Prop>> {
    let (op, args) = op_form(model, node)?;
    if op != OP_OBJECT {
        return None;
    }
    let term = model.term();
    Some(
        args.iter()
            .filter_map(|&a| match op_form(model, a) {
                Some((OP_PROP, kv)) => match (kv.first(), kv.get(1)) {
                    (Some(&k), Some(&v)) => Some(match term.node(k).op() {
                        Operator::Universal(Universal::Lit { kind, lexeme }) if kind == "str" => {
                            Prop::Named(lexeme.clone(), v)
                        }
                        _ => Prop::Unknown,
                    }),
                    _ => Some(Prop::Unknown),
                },
                Some((OP_SPREAD, _)) => Some(Prop::Unknown),
                // A method or other entry: it cannot set a plain value property.
                _ => None,
            })
            .collect(),
    )
}

/// The elements of the array literal at `node`; `None` when `node` is not one.
pub(crate) fn array_items(model: &Model, node: NodeId) -> Option<Vec<NodeId>> {
    match op_form(model, node) {
        Some((op, args)) => (op == OP_ARRAY).then(|| args.to_vec()),
        None => raw_array(model, node),
    }
}

/// The elements of an array literal the folder left as its raw syntax (one that is not a constant).
fn raw_array(model: &Model, node: NodeId) -> Option<Vec<NodeId>> {
    let term = model.term();
    if !matches!(
        term.operator(node),
        Operator::Universal(Universal::Lit { .. }) | Operator::Adapter(_)
    ) {
        return None;
    }
    let Operator::Adapter(a) = term.operator(node) else {
        return None;
    };
    (a.name == "array").then(|| {
        term.children(node)
            .iter()
            .copied()
            .filter(|&c| !matches!(term.operator(c), Operator::Universal(Universal::Lit { .. })))
            .collect()
    })
}

/// True when `node` is a spread element.
pub(crate) fn is_spread(model: &Model, node: NodeId) -> bool {
    matches!(op_form(model, node), Some((OP_SPREAD, _)))
}

/// The name of a `ref` node.
pub(crate) fn ref_name(model: &Model, node: NodeId) -> Option<&str> {
    match model.term().operator(node) {
        Operator::Universal(Universal::Ref { name }) => Some(name),
        _ => None,
    }
}

/// True when `node` is `apply(call)` (or the `call` operator form).
pub(crate) fn is_call(model: &Model, node: NodeId) -> bool {
    matches!(model.term().operator(node), Operator::Universal(Universal::Apply { kind }) if kind == "call")
}

/// The expression a spread element `node` spreads; `None` when `node` is not a spread.
pub(crate) fn spread_arg(model: &Model, node: NodeId) -> Option<NodeId> {
    match op_form(model, node) {
        Some((OP_SPREAD, args)) => args.first().copied(),
        Some(_) => None,
        None => match model.term().operator(node) {
            // The raw form: `...` then the expression.
            Operator::Adapter(a) if a.name == "spread_element" => {
                model.term().children(node).get(1).copied()
            }
            _ => None,
        },
    }
}
