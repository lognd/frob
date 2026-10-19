//! [`Figure`]: a measured value, or Unresolved with the sample count when history is too short.
// frob:ticket 01M48Q2AQXY69YKK3D2DC05ZWR

use schemars::JsonSchema;
use serde::Serialize;

/// A figure that is either a value or Unresolved because there are too few samples.
#[derive(Debug, Clone, PartialEq, Serialize, JsonSchema)]
#[serde(tag = "status", rename_all = "snake_case")]
pub enum Figure<T> {
    /// Enough samples: the value.
    Value {
        /// The computed value.
        value: T,
    },
    /// Too few samples: no number is reported.
    Unresolved {
        /// Samples that exist.
        samples: u32,
        /// Samples needed (`[pm] min_history`, or the fit's own floor).
        need: u32,
    },
}

impl<T> Figure<T> {
    /// `Value` when `samples >= need`, else `Unresolved`; `compute` only runs when resolved.
    pub fn gate(samples: usize, need: u32, compute: impl FnOnce() -> T) -> Self {
        let have = u32::try_from(samples).unwrap_or(u32::MAX);
        if have >= need {
            Self::Value { value: compute() }
        } else {
            tracing::debug!(have, need, "figure unresolved: too few samples");
            Self::Unresolved {
                samples: have,
                need,
            }
        }
    }

    /// The value, `None` when Unresolved.
    pub const fn value(&self) -> Option<&T> {
        match self {
            Self::Value { value } => Some(value),
            Self::Unresolved { .. } => None,
        }
    }
}
