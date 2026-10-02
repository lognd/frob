//! Small helpers shared by the rule modules.

use gob_rules::{Finding, Rule, RuleId};
use gob_text::Span;

/// The validated id of `rule`.
pub(crate) fn rule_id<R: Rule>(rule: &R) -> RuleId {
    rule.meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}

/// A finding of `rule` at its declared severity.
pub(crate) fn finding<R: Rule>(
    rule: &R,
    span: Option<Span>,
    message: impl Into<String>,
    anchor: &str,
) -> Finding {
    Finding::new(rule_id(rule), rule.meta().severity, span, message, anchor)
}

/// True when the word `w` is one of the bare work markers.
pub(crate) fn is_marker(w: &str) -> bool {
    matches!(w, "TODO" | "FIXME" | "XXX" | "HACK")
}
