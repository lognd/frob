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
//! comparisons of variables, fields and literals, regex and glob literals, `matches` against a
//! side-relation glob column (`lease.globs`, or a `config.<table>.<key>` list read through its
//! `value` column; lowered to `MatchGlobSet`), `report` and `unresolved when`. Knobs (`knob NAME: ty = default`) lower at their declared default:
//! `knob.NAME` of type int/string/bool is an operand, a regex knob follows `~`, and a string or list-of-string knob is a glob
//! set (a `[rules]` override is honoured only by a `count` limit). `in` over a list, range or
//! list knob, `is` (kind words, `public`, `exported`, `relative`, `valid_glob`), `exists`, `has attr`, `under` and `in unit`
//! lower too, as do defs (each a view over its parameters, every call by index; a def body
//! calls only earlier defs), `count(x: SRC ...)` against an integer or an int knob (either side
//! of the comparison; a knob limit honours a `[rules]` override), and operand paths of any
//! length (`l.target.anchor` reads the dotted field). `a reaches b via VERB within N` lowers when `N` is an integer literal or int knob from 1 to 65535 (one verb; an unbounded or multi-verb `reaches` is refused). A glob read from a field of a bound variable (`i.file.path matches row.from`) lowers to `MatchGlobOperand`; an invalid glob is unknown, not a mismatch. A kind's string argument (`directive "todo"`) tests the node's `name`. a snippet binder and `x is` a snippet lower to a snippet match op (the rule's one `lang` stands in for a missing tag; `as KIND` binds nodes of KIND inside a match via `within`; `x is SNIPPET as roles` lowers when the snippet is a branch or loop whose body is empty or one call, to `x is branch` plus a directly-inside call; other roles shapes and fix templates are refused). A relation object may be a field path of a bound variable (`p peer of s.unit`), lowered to an any-node quantifier equating the field with the object. `slug(s)` and `resolve(path, from)` lower to call operands over call-free arguments (a nested call or a wrong argument count is refused; a file node as an argument stands for its path). A `vocab(...)` knob lowers `v in knob.NAME` to `InVocab` (the node name against the union of the language's callee vocabularies for those classes; `needs vocab(NAME)` is checked against the knob and records nothing in the plan). A count may also be compared with a scaled count (`count(..) >= knob.ratio * count(..)`, the factor an int or decimal literal or an int/float knob at its declared default on either side), lowered to `CountPair`; a decimal beyond 18 places or 64 bits is refused. An alternative of plain kind words (`find b: (branch | loop)`) lowers to an any-node find with an `or` of kind tests. Everything else (a count compared with
//! anything but an integer, knob or scaled count, other `is` words, other side-relation operands) is a [`LowerError::Unsupported`] that names
//! the construct. Notes and fixes are not part of the plan and are dropped.

mod convert;
mod emit;
mod error;
mod prefilter;
mod roles;
mod source;

pub use convert::needed_capabilities;
pub use error::LowerError;
pub use prefilter::prefilter_kinds;
pub use source::{SourceError, lower_source};

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
