//! Why an Unresolved finding is required (`cli.md` section 2, the one gate mechanism).

use std::fmt;

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// Why an Unresolved finding is required, so the gate fails on it (exit 1).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum RequiredReason {
    /// A configured sibling product is absent or incompatible.
    SiblingMissing {
        /// The product or program that could not be used.
        product: String,
    },
    /// An opaque needs an `annotation-required` declaration.
    AnnotationRequired {
        /// The annotation code the declaration must carry.
        code: String,
        /// True when the opaque sits on the public surface.
        public_surface: bool,
    },
    /// A `must_measure` rule examined zero subjects.
    ZeroSubjects {
        /// The rule id that measured nothing.
        rule: String,
    },
    /// A rule could not be evaluated (unreadable ledger, config or milestones), so its silence is not a pass.
    EvaluationFailed {
        /// The rule that was not evaluated.
        rule: String,
        /// The underlying error, as text.
        error: String,
    },
    /// A configured tool stage could not run, exited abnormally or printed unreadable output.
    ToolFailed {
        /// The name of the tool stage that did not produce evidence.
        stage: String,
    },
    /// A required pack was not trusted, so its rules did not run.
    Untrusted {
        /// The pack that was not trusted.
        pack: String,
    },
    /// A required pack changed in this change and so is not trusted for it.
    UntrustedInChange {
        /// The pack that changed.
        pack: String,
    },
    /// A required pack exhausted its compute budget.
    Budget {
        /// The pack that ran out of budget.
        pack: String,
    },
    /// A required pack trapped while running.
    Trap {
        /// The pack that trapped.
        pack: String,
    },
    /// A required pack attempted an effect its grants deny.
    EffectDenied {
        /// The pack that was denied.
        pack: String,
    },
    /// A required pack could not be loaded or found.
    PackUnavailable {
        /// The pack that was unavailable.
        pack: String,
    },
}

/// How an enabled pack failed to finish (security.md section 2.7).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum PackFailure {
    /// The pack is not trusted.
    Untrusted,
    /// The pack changed in this change.
    UntrustedInChange,
    /// The pack ran out of budget.
    Budget,
    /// The pack trapped.
    Trap,
    /// The pack attempted a denied effect.
    EffectDenied,
    /// The pack could not be loaded.
    PackUnavailable,
}

impl RequiredReason {
    /// The required reason for a pack failure, or `None` when the pack is not marked required.
    #[must_use]
    pub fn for_pack(required: bool, pack: &str, failure: PackFailure) -> Option<Self> {
        if !required {
            tracing::debug!(pack, ?failure, "pack failure is not required");
            return None;
        }
        let pack = pack.to_owned();
        tracing::debug!(pack, ?failure, "pack failure is required");
        Some(match failure {
            PackFailure::Untrusted => Self::Untrusted { pack },
            PackFailure::UntrustedInChange => Self::UntrustedInChange { pack },
            PackFailure::Budget => Self::Budget { pack },
            PackFailure::Trap => Self::Trap { pack },
            PackFailure::EffectDenied => Self::EffectDenied { pack },
            PackFailure::PackUnavailable => Self::PackUnavailable { pack },
        })
    }
}

impl fmt::Display for RequiredReason {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::SiblingMissing { product } => write!(f, "sibling-missing: {product}"),
            Self::AnnotationRequired {
                code,
                public_surface,
            } => write!(
                f,
                "annotation-required: {code}{}",
                if *public_surface { " (public)" } else { "" }
            ),
            Self::ZeroSubjects { rule } => write!(f, "zero-subjects: {rule}"),
            Self::EvaluationFailed { rule, error } => {
                write!(f, "evaluation-failed: {rule}: {error}")
            }
            Self::ToolFailed { stage } => write!(f, "tool-failed: {stage}"),
            Self::Untrusted { pack } => write!(f, "untrusted: {pack}"),
            Self::UntrustedInChange { pack } => write!(f, "untrusted-in-change: {pack}"),
            Self::Budget { pack } => write!(f, "budget: {pack}"),
            Self::Trap { pack } => write!(f, "trap: {pack}"),
            Self::EffectDenied { pack } => write!(f, "effect-denied: {pack}"),
            Self::PackUnavailable { pack } => write!(f, "pack-unavailable: {pack}"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests for_pack
    #[test]
    fn required_pack_failure_maps_to_matching_variant() {
        let r = RequiredReason::for_pack(true, "core", PackFailure::Trap);
        assert_eq!(
            r,
            Some(RequiredReason::Trap {
                pack: "core".into()
            })
        );
        assert_eq!(r.unwrap().to_string(), "trap: core");
    }

    // frob:tests for_pack
    #[test]
    fn unmarked_pack_failure_is_not_required() {
        assert_eq!(
            RequiredReason::for_pack(false, "core", PackFailure::Trap),
            None
        );
    }
}
