//! Why a binding is Unresolved: the Unknown leaves its value depends on (grl-spec.md 7.0.5).

use gob_ir::{Model, NodeId};
use gob_rules::UnresolvedReason;

use super::super::Doubt;

/// One reason an outcome is Unresolved.
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum Reason {
    /// A condition could not be decided.
    Doubt(Doubt),
    /// An `unresolved when` condition held, with the author's reason text.
    When(String),
    /// The binding touches an unread (opaque or hole) node.
    ParseError,
    /// The value is Unknown because the model has unread regions.
    Hidden,
}

impl Reason {
    /// The stable code of this reason, as the finding carries it.
    pub fn unresolved(&self) -> UnresolvedReason {
        UnresolvedReason::from_code(match self {
            Self::Doubt(d) => match d {
                Doubt::MayEdge { .. } | Doubt::CountBounds { .. } => "edge:may",
                Doubt::Frontier { .. } => "edge:unknown",
                Doubt::Budget { .. } | Doubt::StepBudget => "budget",
                Doubt::Hidden => "partial",
                Doubt::Dynamic { .. } | Doubt::Member { .. } => "dynamic:unresolvable",
            },
            Self::When(text) => text,
            Self::ParseError => "hole",
            Self::Hidden => "partial",
        })
    }
}

/// Whether `node` or anything below it is unread (opaque or a hole).
pub(super) fn touches_unread(model: &Model, node: NodeId) -> bool {
    let term = model.term();
    std::iter::once(node)
        .chain(term.descendants(node))
        .any(|n| {
            let op = term.node(n).op();
            op.is_opaque() || op.is_hole()
        })
}
