//! The relation layer of the executor: edge verbs, bounded `reaches`, `count`, knobs and the
//! typed side relations (grl-spec.md sections 6, 7.0.2, 7.0.3, 7.1 and 7.4).
//!
//! Everything a rule reads that is not the term itself arrives as a typed input in
//! [`Relations`]: named edge relations (a [`gob_ir::Relation`] per verb family, whose stored
//! `Yes` pairs are the certain bound, stored `Unknown` pairs the possible edges and
//! `unknown_out` the frontier), side tables (`diff.changed`, `lease.globs`, `config.<table>`,
//! ...) and knob overrides from `[rules]`. A relation the plan names but the caller did not
//! supply is refused before the run starts ([`ExecError::MissingRelation`]), never answered as
//! empty.
//!
//! [`ExecError::MissingRelation`]: super::ExecError::MissingRelation

mod count;
mod edges;
mod side;

use std::collections::BTreeMap;

use gob_ir::Relation;

pub use count::{Count, Knobs};
pub(crate) use edges::{reaches, verb};
pub use side::{SideData, SideError, SideRow, SideTable};

/// The relation word that is answered from the term itself (same parent unit).
pub(crate) const PEER_OF: &str = "peer of";

/// The default cap on condition evaluations per run; an overrun is Unknown with reason `budget`
/// (grl-spec.md 7.0.8, plugins.md 6.5).
pub const DEFAULT_STEP_BUDGET: u64 = 20_000_000;

/// The typed inputs of a run beyond the model: edges, side tables and knobs.
#[derive(Debug, Clone)]
pub struct Relations {
    pub(crate) edges: BTreeMap<String, Relation>,
    pub(crate) side: SideData,
    pub(crate) knobs: Knobs,
    pub(crate) step_budget: u64,
}

impl Default for Relations {
    fn default() -> Self {
        Self {
            edges: BTreeMap::new(),
            side: SideData::default(),
            knobs: Knobs::default(),
            step_budget: DEFAULT_STEP_BUDGET,
        }
    }
}

impl Relations {
    /// No edges, no side tables, no knob overrides.
    pub fn new() -> Self {
        Self::default()
    }

    /// Supplies the edge relation `name` (a verb word such as `calls`, or a family a rule names
    /// after `via`); several relations can be merged first with [`Relation::union`].
    #[must_use]
    pub fn with_edges(mut self, name: &str, relation: Relation) -> Self {
        tracing::debug!(name, pairs = relation.len(), "edge relation supplied");
        self.edges.insert(name.to_owned(), relation);
        self
    }

    /// Supplies the side tables.
    #[must_use]
    pub fn with_side(mut self, side: SideData) -> Self {
        self.side = side;
        self
    }

    /// Supplies the knob overrides read from `[rules]`.
    #[must_use]
    pub fn with_knobs(mut self, knobs: Knobs) -> Self {
        self.knobs = knobs;
        self
    }

    /// Caps the condition evaluations of one run at `steps`; an overrun leaves the remaining
    /// bindings Unknown with the `budget` reason instead of running on.
    #[must_use]
    pub fn with_step_budget(mut self, steps: u64) -> Self {
        self.step_budget = steps;
        self
    }

    /// The knob overrides.
    pub fn knobs(&self) -> &Knobs {
        &self.knobs
    }
}
