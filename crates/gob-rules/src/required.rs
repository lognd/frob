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
        }
    }
}
