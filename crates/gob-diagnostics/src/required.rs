//! The `required` mark on Unresolved findings and the gate policy (cli.md section 2).

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// Which Unresolved findings fail the gate (`[check] fail_on_unresolved`).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum UnresolvedPolicy {
    /// Only Unresolved findings carrying a required reason fail.
    #[default]
    Required,
    /// No Unresolved finding fails.
    Never,
    /// Every Unresolved finding fails.
    All,
}

impl UnresolvedPolicy {
    /// The config spelling (`required`, `never`, `all`).
    pub const fn name(self) -> &'static str {
        match self {
            Self::Required => "required",
            Self::Never => "never",
            Self::All => "all",
        }
    }
}
