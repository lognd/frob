//! The `certainly`/`possibly` assumption a finding rests on (grl-spec.md 7.0.4, D123).
//!
//! The evaluator applies the collapses; this layer decides whether they mattered. A fire whose
//! value with the collapses read as identity (`V0`) is Unresolved rests on the assumption and is
//! conditional: it is capped at Advisory.

use gob_ir::{Model, NodeId};
use gob_rules::UnresolvedReason;

use super::super::core::Eval;
use crate::plan::{Certainty, Op, PlanParts};

/// One assumption a conditional finding rests on.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Assumption {
    /// The collapse that was assumed (`Certainly` or `Possibly`, never `Default`).
    pub certainty: Certainty,
    /// Where the assumption was made: `line:col` of the binding's subject, or its node index.
    pub span: String,
}

impl Assumption {
    /// The stable reason code, `assumed:certainly@span` or `assumed:possibly@span`.
    #[must_use]
    pub fn code(&self) -> String {
        let word = match self.certainty {
            Certainty::Possibly => "possibly",
            Certainty::Certainly | Certainty::Default => "certainly",
        };
        format!("assumed:{word}@{}", self.span)
    }

    /// The typed reason this assumption stands for at the release gate.
    #[must_use]
    pub fn unresolved(&self) -> UnresolvedReason {
        UnresolvedReason::from_code(&self.code())
    }
}

/// The distinct non-default certainties the plan applies, `certainly` first.
pub(super) fn certainties(p: &PlanParts) -> Vec<Certainty> {
    let mut out = Vec::new();
    for op in &p.ops {
        if let Op::Verb { certainty, .. } | Op::Reaches { certainty, .. } = op
            && *certainty != Certainty::Default
            && !out.contains(certainty)
        {
            out.push(*certainty);
        }
    }
    out.sort_by_key(|c| *c == Certainty::Possibly);
    out
}

/// The span text for `node`: `line:col` of its start when the source has lines, else its index.
pub(super) fn span_of(ev: &Eval<'_>, model: &Model, node: Option<NodeId>) -> String {
    use std::fmt::Write as _;
    let Some(node) = node else {
        return "rule".to_owned();
    };
    let mut out = String::new();
    let lc = model
        .term()
        .node(node)
        .location()
        .span()
        .and_then(|s| ev.rd.source.and_then(|src| src.line_col(s.range.start())));
    match lc {
        Some(lc) => {
            let _ = write!(out, "{}:{}", lc.line, lc.col);
        }
        None => {
            let _ = write!(out, "n{}", node.index());
        }
    }
    out
}
