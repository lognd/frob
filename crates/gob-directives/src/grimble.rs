//! Directives of the `grimble` namespace that code carries (binding.md 2.1).
//!
//! Only `binds` is registered here. The scanner honours the namespace only when a product asks
//! for it (`ScanConfig`), so frob never reads these comments (decision D28).

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC

use gob_macros::Directive;

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
