//! NEAT037 "effect-row-widening" (cohesion.md 5, neatness.md 4): a unit whose inferred effect
//! class got worse against the base branch. It is a ratchet that needs no annotation: a pure
//! helper that starts reading the clock is caught in review. Also NEAT011's applicability
//! (`effects-undeclared` only asks for a claim where inference cannot reach).

// frob:ticket 01M4CXT1GFPWZAMV0BCBH3WC4G

use gob_ir::effect_class::{EffectClass, Inferred};
use tracing::debug;

/// NEAT037's judgement of one unit.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Neat037 {
    /// The inferred class is worse than on the base.
    Fire {
        /// The class on the base branch.
        from: EffectClass,
        /// The class now.
        to: EffectClass,
        /// The call sites that left the new answer open (empty when the class is Impure).
        witnesses: Vec<String>,
        /// The claims the new class is conditional on (`assumed:<claim>` reasons).
        assumed: Vec<String>,
    },
    /// Same or better class.
    Clean,
    /// The unit is new (no base class), so there is nothing to widen from.
    NoBase,
}

/// Compare a unit's `head` inference against its `base` one; `None` base means a new unit.
pub fn neat037(base: Option<&Inferred>, head: &Inferred) -> Neat037 {
    let Some(base) = base else {
        debug!("NEAT037 skipped: unit has no base class");
        return Neat037::NoBase;
    };
    let (from, to) = (base.class(), head.class());
    if to.is_worse_than(from) {
        debug!(
            from = from.as_str(),
            to = to.as_str(),
            "NEAT037 effect row widened"
        );
        Neat037::Fire {
            from,
            to,
            witnesses: head.witnesses.clone(),
            assumed: head.reasons(),
        }
    } else {
        Neat037::Clean
    }
}

/// True when NEAT011 may ask for a `grimble:effects` claim: only a public unit whose class is
/// Unknown, which is exactly where a claim helps; a proven class never needs an annotation.
pub fn neat011_applies(public: bool, class: EffectClass) -> bool {
    public && class == EffectClass::Unknown
}
