//! Kernel findings over the declared flows (grmb-spec 4.1, 4.2, 4.6): label closure against node
//! clearance, trust crossings without an endorsing boundary, and foreign flows without a rate.

// frob:ticket 01M4FGYG9TXDAMZ2VS2ZHGJKX1

use crate::ast::{ClauseKind, Direction, EntityKind, Header};
use crate::fold::{LABELS, TRUST_LEVELS};
use crate::model::{EntityRec, Index};
use crate::span::Span;

/// Which kernel rule a [`FlowFinding`] belongs to.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum FlowRule {
    /// A label above the destination node's clearance, not declassified on the flow.
    LabelClosure,
    /// A flow into a higher-trust node with no endorsing boundary.
    Unendorsed,
    /// A flow from a foreign node with no `rate`.
    NoRate,
}

impl FlowRule {
    /// The rule id.
    pub const fn id(self) -> &'static str {
        match self {
            Self::LabelClosure => "FLOW001",
            Self::Unendorsed => "FLOW002",
            Self::NoRate => "FLOW003",
        }
    }
}

/// One kernel finding on a flow: the rule, the flow's span and the message naming the flow.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct FlowFinding {
    /// The rule.
    pub rule: FlowRule,
    /// The index of the file holding the flow.
    pub file: usize,
    /// The flow's full name (the finding anchor).
    pub flow: String,
    /// The span to report on (the flow's name).
    pub span: Span,
    /// The message.
    pub message: String,
}

/// The position of `name` in `lattice`, lowest first; `None` when it is no element.
fn rank(lattice: &[&str], name: &str) -> Option<usize> {
    lattice.iter().position(|e| *e == name)
}

/// The trust element and clearance of node record `rec` (clearance defaults to `Secret`).
fn node_levels(idx: &Index<'_>, rec: usize) -> (Option<String>, String) {
    let e = idx.entities[rec].entity;
    let trust = match &e.header {
        Header::Node { trust } => trust.as_ref().map(|t| t.text.clone()),
        _ => None,
    };
    let clearance = e
        .clauses
        .iter()
        .find_map(|c| match &c.kind {
            ClauseKind::Clearance(l) => Some(l.text.clone()),
            _ => None,
        })
        .unwrap_or_else(|| "Secret".to_owned());
    (trust, clearance)
}

/// The boundaries acting on flow record `flow`, as (direction, from, to).
fn boundaries_on(idx: &Index<'_>, flow: usize) -> Vec<(Direction, String, String)> {
    idx.entities
        .iter()
        .filter_map(|b| match &b.entity.header {
            Header::Boundary {
                direction,
                flow: f,
                from,
                to,
                ..
            } if idx.resolve(&b.ctx, f).is_some_and(|r| r.rec == flow) => {
                Some((*direction, from.text.clone(), to.text.clone()))
            }
            _ => None,
        })
        .collect()
}

/// The kernel findings of the single flow record `rec` (index `at` in `idx`).
fn flow_findings(idx: &Index<'_>, at: usize, rec: &EntityRec<'_>, out: &mut Vec<FlowFinding>) {
    let Header::Flow { from, to } = &rec.entity.header else {
        return;
    };
    let resolve_node = |p| {
        idx.resolve(&rec.ctx, p)
            .filter(|r| idx.kind(r.rec) == EntityKind::Node)
            .map(|r| r.rec)
    };
    let (Some(src), Some(dst)) = (resolve_node(from), resolve_node(to)) else {
        return;
    };
    let span = rec.entity.name.span;
    let name = &rec.full;
    let (src_trust, _) = node_levels(idx, src);
    let (dst_trust, clearance) = node_levels(idx, dst);
    let bounds = boundaries_on(idx, at);
    let label = rec.entity.clauses.iter().find_map(|c| match &c.kind {
        ClauseKind::Label(l) => Some(l.text.clone()),
        _ => None,
    });
    let has_rate = rec
        .entity
        .clauses
        .iter()
        .any(|c| matches!(c.kind, ClauseKind::Quantity(crate::ast::QuantKey::Rate, _)));

    // Label closure: the label on arrival (after any declassify) must not exceed the clearance.
    if let Some(label) = label {
        let arriving = bounds
            .iter()
            .filter(|(d, f, _)| *d == Direction::Declassify && *f == label)
            .filter_map(|(_, _, t)| rank(&LABELS, t))
            .min()
            .or_else(|| rank(&LABELS, &label));
        if let (Some(have), Some(max)) = (arriving, rank(&LABELS, &clearance))
            && have > max
        {
            out.push(FlowFinding {
                rule: FlowRule::LabelClosure,
                file: rec.file,
                flow: name.clone(),
                span,
                message: format!(
                    "flow `{name}` carries `{label}` into a node with clearance `{clearance}` and no declassify boundary lowers it"
                ),
            });
        }
    }

    // Trust crossing: a flow into a higher-trust node needs an endorse boundary reaching it.
    if let (Some(s), Some(d)) = (
        src_trust.as_deref().and_then(|t| rank(&TRUST_LEVELS, t)),
        dst_trust.as_deref().and_then(|t| rank(&TRUST_LEVELS, t)),
    ) {
        let endorsed = bounds.iter().any(|(dir, f, t)| {
            *dir == Direction::Endorse
                && rank(&TRUST_LEVELS, f).is_some_and(|f| f <= s)
                && rank(&TRUST_LEVELS, t).is_some_and(|t| t >= d)
        });
        if s < d && !endorsed {
            out.push(FlowFinding {
                rule: FlowRule::Unendorsed,
                file: rec.file,
                flow: name.clone(),
                span,
                message: format!(
                    "flow `{name}` crosses from `{}` to `{}` trust with no endorse boundary on it",
                    TRUST_LEVELS[s], TRUST_LEVELS[d]
                ),
            });
        }
        if s == 0 && !has_rate {
            out.push(FlowFinding {
                rule: FlowRule::NoRate,
                file: rec.file,
                flow: name.clone(),
                span,
                message: format!("flow `{name}` comes from a foreign node and declares no `rate`"),
            });
        }
    }
}

/// Every kernel finding over the flows of `idx`, in entity order.
pub fn kernel_findings(idx: &Index<'_>) -> Vec<FlowFinding> {
    let mut out = Vec::new();
    for (at, rec) in idx.entities.iter().enumerate() {
        if rec.entity.kind == EntityKind::Flow {
            flow_findings(idx, at, rec, &mut out);
        }
    }
    tracing::debug!(count = out.len(), "kernel flow findings");
    out
}
