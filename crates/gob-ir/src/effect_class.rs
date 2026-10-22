//! Inferred effect classes (cohesion.md 5, D121): every unit gets a class from its `effects`
//! [`Answer`] with no annotation. Pure means no effect at all; honest means it touches the outside
//! world only through its parameters; impure means a provable ambient effect (clock, rng, io, a
//! global write); Unknown means the call closure is not fully resolvable. Writes are placed with
//! the may-alias facts of the def-use graph ([`write_target`]): a write through a name that may
//! alias something else counts against `hi` (it might be a global) and never against `lo`.
//!
//! A `grimble:effects` claim on a boundary where inference cannot reach (FFI, generated,
//! reflective) lets its callers resolve as conditional answers: the class is computed as if the
//! claim held and the premise travels with it ([`Inferred::assumed`], reason `assumed:<claim>`).
//! The claim itself is judged by [`claim_status`] and stays Unverified unless the body is
//! analysable (Theorem 3: a claim is a premise, never a proof).

// frob:ticket 01M4CXT1GFPWZAMV0BCBH3WC4G

use std::collections::BTreeSet;

use tracing::{debug, trace};

use crate::answer::Answer;
use crate::defuse::DefUseEdge;
use crate::scope::Status;

/// The inferred class of a unit; the derived order is the badness order (`Pure` best).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum EffectClass {
    /// No effect at all (`none`).
    Pure,
    /// Touches the outside world only through its parameters.
    Honest,
    /// The call closure is not fully resolvable; nothing is proven either way.
    Unknown,
    /// A provable ambient effect or global write.
    Impure,
}

impl EffectClass {
    /// Stable lowercase spelling for reports and messages.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Pure => "pure",
            Self::Honest => "honest",
            Self::Unknown => "unknown",
            Self::Impure => "impure",
        }
    }

    /// True when `self` is a strictly worse class than `base` (the NEAT037 ratchet).
    pub fn is_worse_than(self, base: Self) -> bool {
        self > base
    }
}

/// What a unit does to the outside world: one side (`lo` or `hi`) of an effects answer.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct EffectFacts {
    /// Ambient atoms performed (`clock`, `rng`, `env`, `fs`, `net`, `stdio`, `exit`, ...).
    pub ambient: BTreeSet<String>,
    /// Writes storage that is not reachable from a parameter (a global, a singleton).
    pub globals: bool,
    /// Writes storage reachable from a parameter.
    pub param_writes: bool,
    /// An unresolved call, opaque body or dynamic site may add anything (`hi` is `any`).
    pub open: bool,
}

impl EffectFacts {
    /// True when the facts are an effect no claim short of `any` excuses: ambient or a global write.
    pub fn is_ambient(&self) -> bool {
        !self.ambient.is_empty() || self.globals
    }

    /// True when every effect in `self` is allowed by `claim` (an open `self` is never within).
    pub fn within(&self, claim: &Self) -> bool {
        !self.open
            && self.ambient.is_subset(&claim.ambient)
            && (!self.globals || claim.globals)
            && (!self.param_writes || claim.param_writes)
    }

    fn absorb(&mut self, other: &Self) {
        self.ambient.extend(other.ambient.iter().cloned());
        self.globals |= other.globals;
        self.param_writes |= other.param_writes;
        self.open |= other.open;
    }
}

/// Where a write lands, relative to the unit's parameters.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WriteTarget {
    /// A fresh local that nothing else can alias: not an effect.
    Local,
    /// Storage reachable from a parameter.
    Param,
    /// Storage outside the unit and its parameters.
    Global,
    /// A name with a May def-use edge: it may be a parameter's storage or a global.
    MayAlias,
}

/// Place a write to `var` of a unit with parameters `params` and `locals`, given its def-use edges.
///
/// A parameter is `Param`; a name declared nowhere in the unit is `Global`; a local with any
/// `May` edge (attribute, kwargs, closure or mutation alias) is `MayAlias`, because inference
/// cannot tell which storage it names; any other local is `Local`.
pub fn write_target(
    var: &str,
    params: &BTreeSet<String>,
    locals: &BTreeSet<String>,
    edges: &[DefUseEdge],
) -> WriteTarget {
    let root = var.split('.').next().unwrap_or(var);
    if params.contains(root) {
        return WriteTarget::Param;
    }
    if !locals.contains(root) {
        return WriteTarget::Global;
    }
    let aliased = edges
        .iter()
        .any(|e| e.strength == Status::May && e.var.split('.').next() == Some(root));
    if aliased {
        WriteTarget::MayAlias
    } else {
        WriteTarget::Local
    }
}

/// A `grimble:effects` claim on a boundary, with the label that travels as a premise.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EffectClaim {
    /// Where the claim was made and what it says (`ffi.c:3 effects none`).
    pub label: String,
    /// The effects the claim allows (`none` is the default, empty facts).
    pub allows: EffectFacts,
}

/// How a call site's callee contributes to the caller's effects.
#[derive(Debug, Clone, Copy)]
pub enum Callee<'a> {
    /// The callee's body was analysed.
    Resolved(&'a Answer<EffectFacts>),
    /// The callee is a boundary inference cannot reach, carrying a claim.
    Claimed(&'a EffectClaim),
    /// An unresolved call or opaque body with no claim: widens `hi` to `any`.
    Opaque,
}

/// A unit's effects answer, its conditional premises and the call sites that widened it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Inferred {
    /// The `effects(unit)` answer: Exact when fully resolved, else Bounds.
    pub effects: Answer<EffectFacts>,
    /// Claims this answer is conditional on (reason `assumed:<claim>`), sorted.
    pub assumed: Vec<String>,
    /// The call sites that left the answer open, in source order.
    pub witnesses: Vec<String>,
}

impl Inferred {
    /// The inferred class: Impure when `lo` is ambient, Unknown when `hi` is open or ambient,
    /// Honest when only parameters are written, Pure otherwise.
    pub fn class(&self) -> EffectClass {
        let class = classify(&self.effects);
        trace!(class = class.as_str(), assumed = ?self.assumed, "classified effects answer");
        class
    }

    /// True when the class holds only assuming at least one unverified claim.
    pub fn is_conditional(&self) -> bool {
        !self.assumed.is_empty()
    }

    /// The reasons of a conditional answer, one `assumed:<claim>` per premise.
    pub fn reasons(&self) -> Vec<String> {
        self.assumed
            .iter()
            .map(|c| format!("assumed:{c}"))
            .collect()
    }
}

/// The class of an effects answer (see [`Inferred::class`]).
pub fn classify(effects: &Answer<EffectFacts>) -> EffectClass {
    match effects {
        Answer::Unknown | Answer::NotApplicable => EffectClass::Unknown,
        Answer::Exact(f) => {
            if f.is_ambient() {
                EffectClass::Impure
            } else if f.open {
                EffectClass::Unknown
            } else if f.param_writes {
                EffectClass::Honest
            } else {
                EffectClass::Pure
            }
        }
        Answer::Bounds { lo, hi } => {
            if lo.is_ambient() {
                EffectClass::Impure
            } else if hi.open || hi.is_ambient() {
                EffectClass::Unknown
            } else if hi.param_writes || lo.param_writes {
                EffectClass::Honest
            } else {
                EffectClass::Pure
            }
        }
    }
}

/// Builds a unit's effects answer one fact at a time: `lo` is what the body provably does, `hi`
/// the closure over everything it may do.
#[derive(Debug, Default)]
pub struct EffectCollector {
    lo: EffectFacts,
    hi: EffectFacts,
    assumed: BTreeSet<String>,
    witnesses: Vec<String>,
}

impl EffectCollector {
    /// A collector for a body with no effects so far.
    pub fn new() -> Self {
        Self::default()
    }

    /// The body provably performs the ambient `atom` (a vocabulary callee such as the clock).
    pub fn ambient(&mut self, atom: &str) {
        self.lo.ambient.insert(atom.to_owned());
        self.hi.ambient.insert(atom.to_owned());
    }

    /// The body writes `target`; a `MayAlias` write only widens `hi`.
    pub fn write(&mut self, target: WriteTarget) {
        match target {
            WriteTarget::Local => {}
            WriteTarget::Param => {
                self.lo.param_writes = true;
                self.hi.param_writes = true;
            }
            WriteTarget::Global => {
                self.lo.globals = true;
                self.hi.globals = true;
            }
            WriteTarget::MayAlias => {
                self.hi.param_writes = true;
                self.hi.globals = true;
            }
        }
    }

    /// The body calls `callee` at `site`, passing the storage in `args` to its parameters.
    ///
    /// A resolved callee's ambient effects and global writes carry over; its parameter writes
    /// land on the argument targets (and only in `hi`, since which argument is written is not
    /// known). An Unknown or `NotApplicable` answer, an unclaimed opaque callee, and a callee that
    /// writes parameters with no argument to land on, leave `hi` open with `site` as witness.
    pub fn call(&mut self, site: &str, callee: Callee<'_>, args: &[WriteTarget]) {
        match callee {
            Callee::Resolved(answer) => self.resolved(site, answer, args),
            Callee::Claimed(claim) => {
                debug!(site, claim = %claim.label, "callee resolved by an unverified claim");
                self.assumed.insert(claim.label.clone());
                self.lo.absorb(&claim.allows);
                self.hi.absorb(&claim.allows);
            }
            Callee::Opaque => self.widen(site),
        }
    }

    fn resolved(&mut self, site: &str, answer: &Answer<EffectFacts>, args: &[WriteTarget]) {
        let (Some(lo), Some(hi)) = (answer.lo(), answer.hi()) else {
            return self.widen(site);
        };
        self.lo.ambient.extend(lo.ambient.iter().cloned());
        self.lo.globals |= lo.globals;
        self.hi.ambient.extend(hi.ambient.iter().cloned());
        self.hi.globals |= hi.globals;
        if hi.param_writes || lo.param_writes {
            if args.is_empty() {
                self.hi.open = true;
                self.witnesses.push(site.to_owned());
            }
            for &arg in args {
                self.hi_write(arg);
            }
        }
        if hi.open {
            self.widen(site);
        }
    }

    fn hi_write(&mut self, target: WriteTarget) {
        match target {
            WriteTarget::Local => {}
            WriteTarget::Param => self.hi.param_writes = true,
            WriteTarget::Global | WriteTarget::MayAlias => {
                self.hi.globals = true;
                self.hi.param_writes = true;
            }
        }
    }

    /// An unresolved call, opaque body or dynamic site at `site` may add anything.
    pub fn widen(&mut self, site: &str) {
        self.hi.open = true;
        self.witnesses.push(site.to_owned());
    }

    /// The finished answer: Exact when `lo` and `hi` agree, Bounds otherwise.
    pub fn finish(self) -> Inferred {
        let effects = if self.lo == self.hi {
            Answer::Exact(self.lo)
        } else {
            Answer::Bounds {
                lo: self.lo,
                hi: self.hi,
            }
        };
        let inferred = Inferred {
            effects,
            assumed: self.assumed.into_iter().collect(),
            witnesses: self.witnesses,
        };
        debug!(
            class = inferred.class().as_str(),
            assumed = inferred.assumed.len(),
            "inferred effects"
        );
        inferred
    }
}

/// The verdict on a `grimble:effects` claim (neatness.md 3).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ClaimStatus {
    /// The body is analysed and its `hi` is within the claim.
    Verified,
    /// The body provably does more than the claim allows (an Error).
    Contradicted,
    /// Between: the body is opaque, open or only possibly outside the claim. Never clean.
    Unverified,
}

/// Judge `claim` against the body's own answer; a body inference cannot reach is Unverified.
pub fn claim_status(claim: &EffectClaim, body: &Answer<EffectFacts>) -> ClaimStatus {
    let status = match (body.lo(), body.hi()) {
        (Some(lo), Some(hi)) => {
            if !lo.within(&claim.allows) {
                ClaimStatus::Contradicted
            } else if hi.within(&claim.allows) {
                ClaimStatus::Verified
            } else {
                ClaimStatus::Unverified
            }
        }
        _ => ClaimStatus::Unverified,
    };
    debug!(claim = %claim.label, ?status, "judged effects claim");
    status
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::defuse::MayCause;
    use crate::term::NodeId;

    fn set(names: &[&str]) -> BTreeSet<String> {
        names.iter().map(|s| (*s).to_owned()).collect()
    }

    fn edge(var: &str, strength: Status) -> DefUseEdge {
        let cause = (strength == Status::May).then_some(MayCause::Mutation);
        DefUseEdge {
            var: var.to_owned(),
            def: NodeId(0),
            use_site: NodeId(1),
            strength,
            cause,
        }
    }

    // frob:tests crates/gob-ir/src/effect_class.rs::write_target
    #[test]
    fn write_targets_follow_params_locals_and_may_alias_edges() {
        let (params, locals) = (set(&["acc"]), set(&["tmp", "alias"]));
        let edges = [edge("alias", Status::May), edge("tmp", Status::Must)];
        let at = |v: &str| write_target(v, &params, &locals, &edges);
        assert_eq!(at("acc"), WriteTarget::Param);
        assert_eq!(at("acc.field"), WriteTarget::Param);
        assert_eq!(at("tmp"), WriteTarget::Local);
        assert_eq!(at("alias.x"), WriteTarget::MayAlias);
        assert_eq!(at("COUNTER"), WriteTarget::Global);
    }
}
