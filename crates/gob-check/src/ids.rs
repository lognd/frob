//! Typed access to the check-owned rules' ids and registry metas, so no call site spells an id literal.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD

use gob_rules::{Registry, RuleDecl, RuleId, RuleMeta};

/// The validated [`RuleId`] of the rule `R` (its `#[rule]` id).
pub(crate) fn rule_id<R: RuleDecl>() -> RuleId {
    R::DEF
        .id
        .parse()
        .unwrap_or_else(|e| unreachable!("#[rule] validates the id: {e}"))
}

/// The registry meta of the rule `R` (bridged from its `#[rule]` declaration).
pub(crate) fn meta_of<R: RuleDecl>() -> &'static RuleMeta {
    Registry::global()
        .by_id(R::DEF.id)
        .unwrap_or_else(|| unreachable!("{} lists itself in the registry", R::DEF.id))
}
