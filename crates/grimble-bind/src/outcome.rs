//! Impl outcome-map planning (D121): consume `ErrorFacts` resolution as an opaque-cone Unresolved.
//!
//! [`plan_outcome_map`] takes the error facts of the code an impl realizes and, optionally, an
//! outcome-map declaration on the impl. A set that is not Exact is a gap and is reported through the
//! existing Unresolved path (an `Unresolved` binding finding, no new severity). An outcome-map claim
//! resolves the gap conditionally: the plan is Conditional on `assumed:<claim>` and the premise
//! travels with it. Nothing here reads source text; the facts are already symbolic.

// frob:ticket 01M68WWE14NTX7QGN0T0W79F8B

use gob_ir::error_flow::{ErrorFacts, ErrorResolution, OutcomeMapClaim};

use crate::types::{BindFinding, Reason};

/// The rule an unmodeled boundary failure of an impl is reported under (PLAN011).
pub const OUTCOME_RULE: &str = "PLAN011";

/// The planned outcome map of one impl: how its error set resolved, and any Unresolved finding.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OutcomePlan {
    /// The impl anchor (`impl/S.sc.o.step`).
    pub anchor: String,
    /// Closed, Conditional on claims (`assumed:<claim>` premises), or Unresolved with reasons.
    pub resolution: ErrorResolution,
    /// The Unresolved findings; empty unless the resolution is Unresolved.
    pub findings: Vec<BindFinding>,
}

/// Plan the outcome map of impl `anchor` from its `facts`, resolved conditionally by `claim` if given.
pub fn plan_outcome_map(
    anchor: &str,
    facts: ErrorFacts,
    claim: Option<&OutcomeMapClaim>,
) -> OutcomePlan {
    let facts = match claim {
        Some(c) => {
            tracing::debug!(anchor, claim = %c.label, "applying outcome-map claim to impl");
            facts.with_outcome_map(c)
        }
        None => facts,
    };
    let resolution = facts.resolution();
    let findings = match &resolution {
        ErrorResolution::Unresolved(reasons) => {
            tracing::debug!(anchor, ?reasons, "impl error set is an opaque cone");
            vec![BindFinding::unresolved(
                OUTCOME_RULE,
                Reason::UnseenRemainder,
                &format!(
                    "impl error set is not known and no outcome map resolves it: {}",
                    reasons.join("; ")
                ),
                anchor,
                None,
            )]
        }
        ErrorResolution::Conditional(claims) => {
            tracing::info!(
                anchor,
                ?claims,
                "impl error set holds only under outcome-map claims"
            );
            Vec::new()
        }
        ErrorResolution::Closed => {
            tracing::trace!(anchor, "impl error set is closed");
            Vec::new()
        }
    };
    OutcomePlan {
        anchor: anchor.to_owned(),
        resolution,
        findings,
    }
}
