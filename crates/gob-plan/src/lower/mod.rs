//! Lowering: a checked rule to a validated [`Plan`] (grl-spec.md sections 7.1 and 7.4).
//!
//! Clause order in the source does not matter. [`lower_rule`] first turns every clause into a
//! name-based tree, then the planner places the work: binders sorted by what they range over
//! and then by name, each condition as early as every variable it uses is bound (ties broken by
//! the condition's structure; a P- plan keeps binders and the conditions written on them first),
//! and only then are variable slots, strings and ops numbered. Two sources that differ only in
//! clause order therefore lower to byte-identical plans. No construct recurses, so every lowered plan terminates (7.4).
//!
//! Covered: `find` of a kind (with field equalities and relations) or of a side relation,
//! `where`, `some`/`no`, `and`/`or`/`any`/`not`, `inside`/`has`, `before`/`after`/`adjoins`, verbs,
//! comparisons of variables, fields and literals, regex and glob literals, `report` and
//! `unresolved when`. Everything else (snippets, defs, `count`, knobs, `reaches`, `in`, `is`,
//! `exists`, side-relation operands, `under`, `in unit`) is a [`LowerError::Unsupported`] that names
//! the construct. Notes and fixes are not part of the plan and are dropped.

mod convert;
mod emit;
mod error;

pub use error::LowerError;

use crate::grl::ast::Rule;
use crate::plan::{Plan, Provenance};

// frob:ticket 01M3ZX7EKNE5Q0NB0DKCH77AZX
/// Lower one rule to a validated plan.
///
/// # Errors
///
/// A [`LowerError`] naming the first construct that cannot be lowered, the first unbound or
/// doubly bound variable, or the plan validation failure.
pub fn lower_rule(rule: &Rule, provenance: Provenance) -> Result<Plan, LowerError> {
    let parsed = convert::convert(rule)?;
    let plan = emit::emit(&parsed, provenance)?;
    tracing::debug!(rule = %rule.id.text, ops = plan.parts().ops.len(), "lowered rule");
    Ok(plan)
}
