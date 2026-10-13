//! Directives of the `grimble` namespace that code carries (binding.md 2.1, cohesion.md 4).
//!
//! Model binding (`binds`) and the design claims about code (`effects`, `core`, `shell`, `calls`). The scanner honours the namespace only when a product asks
//! for it (`ScanConfig`), so frob never reads these comments (decision D28).

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC

use gob_macros::Directive;
use gob_symbols::Symref;

use crate::effects::EffectSet;

/// Bind the unit this comment attaches to: to a model entity (`design:node/N`) or to a symref.
///
/// The operand is `design:<kind>/<full name>` (the unit becomes an `owns`, producer, consumer,
/// shape, runnable, ref or evidence row of that entity, `role=` choosing for flows and vmodels)
/// or a symref (a code-to-code `binds` edge, `via=` names the mechanism and defaults to
/// `manual`). The operand is resolved by grimble, never by this scanner.
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "grimble", verb = "binds")]
pub struct Binds {
    /// The entity (`design:node/cli`) or symref (`crates/a/src/lib.rs::f`) bound to.
    #[arg(positional)]
    pub target: String,
    /// For a flow: `producer` or `consumer`; for a vmodel: `runnable` or `ref`.
    #[arg(key = "role", optional)]
    pub role: Option<String>,
    /// For a symref operand: the binding mechanism (`manual`, `pyo3`, ...).
    #[arg(key = "via", optional)]
    pub via: Option<String>,
}

/// Claim this unit's effect set: `none`, `honest`, `io`, `any` or atoms, optionally `total`.
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "grimble", verb = "effects")]
pub struct Effects {
    /// `none`, `honest`, `io`, `any`, or atoms (`reads(X)`, `writes(Y)`, `clock`, `rng`, `env`, `fs`, `net`, `stdio`, `exit`, `panic`, `diverge`) then optional `total`.
    #[arg(rest)]
    pub set: EffectSet,
    /// Why the claim holds where inference cannot reach.
    #[arg(key = "because", optional)]
    pub because: Option<String>,
}

/// Mark this unit as functional core (pure decisions, no effects of its own).
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "grimble", verb = "core")]
pub struct Core;

/// Mark this unit as imperative shell (effects at the edge, thin logic).
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "grimble", verb = "shell")]
pub struct Shell;

/// Declare the targets of the dynamic call at this site (May precision).
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "grimble", verb = "calls")]
pub struct Calls {
    /// The symrefs the call may reach.
    #[arg(list)]
    pub targets: Vec<Symref>,
}
