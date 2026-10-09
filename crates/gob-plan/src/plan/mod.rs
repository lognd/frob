//! The plan format: one typed IR for every declarative rule (plugins.md section 3).
//!
//! Std rules are compiled to the same form that disk packs are, and one executor
//! runs both. A [`Plan`] carries pack provenance, polarity, needs, the prefilter
//! kind set and the cost class. Bytes from disk are untrusted (security.md 2.2):
//! [`Plan::load`] decodes and fully validates them and returns a [`PlanError`]
//! naming the reason on any defect; it never panics and never yields an invalid
//! plan. Only plans embedded with `include_bytes!` may use [`Plan::load_embedded`].
//!
//! # Wire form
//!
//! `FROBPLAN`, a `u16` version, then fixed-width little-endian fields (see
//! `codec`). The encoding is canonical: accepted bytes re-encode to themselves.
//!
//! # Shape
//!
//! Ops live in one arena; an op refers only to earlier ops and has exactly one
//! referrer, so a plan is a bounded tree that cannot cycle. See [`Op`] and [`PlanParts`].

mod codec;
mod error;
mod ir;
mod limits;
mod validate;

#[cfg(test)]
mod tests;

pub use error::PlanError;
pub use ir::{
    Certainty, CmpOp, CostClass, Def, Langs, Limit, Need, NeedSet, Op, OpId, Operand, PlanParts,
    Polarity, Position, Provenance, Quant, Report, StrId, VarId,
};
pub use limits::{MAX_BYTES, MAX_DEFS, MAX_DEPTH, MAX_OPS, MAX_STR_LEN, MAX_STRINGS};

/// A validated plan: the only form the executor accepts.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Plan(PlanParts);

impl Plan {
    /// Validates `parts` and wraps them, or names the first defect.
    ///
    /// # Errors
    /// Returns the [`PlanError`] for the first violated invariant.
    pub fn new(parts: PlanParts) -> Result<Plan, PlanError> {
        match validate::validate(&parts) {
            Ok(()) => {
                tracing::debug!(rule = %parts.rule, ops = parts.ops.len(), "plan validated");
                Ok(Plan(parts))
            }
            Err(e) => {
                tracing::warn!(rule = %parts.rule, error = %e, "plan rejected");
                Err(e)
            }
        }
    }

    /// Decodes and fully validates untrusted plan bytes (from disk or a cache).
    ///
    /// # Errors
    /// Returns the [`PlanError`] naming why the bytes are not a valid plan.
    pub fn load(bytes: &[u8]) -> Result<Plan, PlanError> {
        let parts = codec::decode(bytes).inspect_err(|e| {
            tracing::warn!(error = %e, len = bytes.len(), "plan bytes rejected while decoding");
        })?;
        Plan::new(parts)
    }

    /// Decodes a plan embedded with `include_bytes!`, skipping semantic validation.
    ///
    /// Structure is still checked (the decoder is memory safe on any input) but the
    /// semantic pass is only run in debug builds; never use this for bytes that did
    /// not come from this binary's own build.
    ///
    /// # Errors
    /// Returns a [`PlanError`] if the embedded bytes are structurally malformed.
    pub fn load_embedded(bytes: &'static [u8]) -> Result<Plan, PlanError> {
        let parts = codec::decode(bytes)?;
        debug_assert!(
            validate::validate(&parts).is_ok(),
            "embedded plan is invalid"
        );
        Ok(Plan(parts))
    }

    /// The canonical bytes of this plan.
    pub fn to_bytes(&self) -> Vec<u8> {
        codec::encode(&self.0)
    }

    /// The validated fields.
    pub fn parts(&self) -> &PlanParts {
        &self.0
    }

    /// The rule id, for example `TODO001`.
    pub fn rule(&self) -> &str {
        &self.0.rule
    }

    /// Where the rule came from.
    pub fn provenance(&self) -> &Provenance {
        &self.0.provenance
    }

    /// The rule's polarity.
    pub fn polarity(&self) -> Polarity {
        self.0.polarity
    }

    /// The declared side relations.
    pub fn needs(&self) -> NeedSet {
        self.0.needs
    }

    /// The cost class.
    pub fn cost(&self) -> CostClass {
        self.0.cost
    }

    /// The prefilter node kinds, resolved to names.
    pub fn prefilter_kinds(&self) -> impl Iterator<Item = &str> {
        self.0
            .prefilter
            .iter()
            .filter_map(|&i| self.0.strings.get(i as usize).map(String::as_str))
    }
}
