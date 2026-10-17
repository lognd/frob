//! Small helpers shared by the rule modules.

use gob_rules::{Finding, Rule, RuleDef, RuleId};
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

/// The validated id of the declared rule `def`.
pub(crate) fn def_id(def: &RuleDef) -> RuleId {
    def.id
        .parse()
        .unwrap_or_else(|e| unreachable!("#[rule] validates the id: {e}"))
}

/// A finding of the declared rule `def` at its declared severity.
pub(crate) fn finding_def(
    def: &RuleDef,
    span: Option<Span>,
    message: impl Into<String>,
    anchor: &str,
) -> Finding {
    Finding::new(def_id(def), def.severity, span, message, anchor)
}

/// True when the word `w` is one of the bare work markers.
pub(crate) fn is_marker(w: &str) -> bool {
    matches!(w, "TODO" | "FIXME" | "XXX" | "HACK")
}
