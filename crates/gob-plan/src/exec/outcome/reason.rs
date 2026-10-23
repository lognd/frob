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
    /// The typed reason of this Unresolved cause, using the dedicated variants where one exists.
    #[must_use]
    pub fn unresolved(&self) -> UnresolvedReason {
        match self {
            Self::Doubt(d) => match d {
                Doubt::MayEdge { .. } | Doubt::CountBounds { .. } => UnresolvedReason::EdgeMay,
                Doubt::Frontier { .. } => UnresolvedReason::EdgeUnknown,
                Doubt::Budget { .. } | Doubt::StepBudget => UnresolvedReason::Budget,
                Doubt::Hidden => UnresolvedReason::Partial,
                Doubt::Dynamic { .. } | Doubt::Member { .. } => {
                    UnresolvedReason::DynamicUnresolvable
                }
            },
            Self::When(text) => UnresolvedReason::from_code(text),
            Self::ParseError => UnresolvedReason::Hole,
            Self::Hidden => UnresolvedReason::Partial,
        }
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
