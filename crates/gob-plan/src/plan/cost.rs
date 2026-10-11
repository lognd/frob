//! Cost class computation (grl-spec.md 7.4, plugins.md 6.2).

use super::ir::{CostClass, Op};

// frob:ticket 01M3ZX7EQ5NARR4Z2SAY4H23AQ
/// The cost class of a plan with these ops.
///
/// Any `reaches` makes the class `Closure(n)` with `n` the largest `within` among them; otherwise
/// a repository-scoped rule is `PerRepo` and every other rule is `PerFile`.
pub fn cost_class(ops: &[Op], repo_scope: bool) -> CostClass {
    let depth = ops
        .iter()
        .filter_map(|op| match op {
            Op::Reaches { within, .. } => Some(*within),
            _ => None,
        })
        .max();
    match depth {
        Some(d) => CostClass::Closure(d),
        None if repo_scope => CostClass::PerRepo,
        None => CostClass::PerFile,
    }
}
