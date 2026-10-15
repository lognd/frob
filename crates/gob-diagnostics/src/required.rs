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

#[cfg(test)]
mod tests {
    use gob_rules::{Finding, PackFailure, RequiredReason, Severity};

    use super::UnresolvedPolicy;
    use crate::{ExitCode, fail_on};

    fn trapped(required: bool) -> Finding {
        let mut f = Finding::new(
            "PACK006".parse().unwrap(),
            Severity::Unresolved,
            None,
            "pack trapped",
            "gob.toml",
        );
        f.required = RequiredReason::for_pack(required, "core", PackFailure::Trap);
        f
    }

    // frob:tests fail_on
    #[test]
    fn required_pack_trap_fails_the_gate() {
        let fs = [trapped(true)];
        assert_eq!(
            fail_on(&fs, None, UnresolvedPolicy::Required),
            ExitCode::Negative
        );
    }

    // frob:tests fail_on
    #[test]
    fn unmarked_pack_trap_does_not_fail_the_gate() {
        let fs = [trapped(false)];
        assert_eq!(fail_on(&fs, None, UnresolvedPolicy::Required), ExitCode::Ok);
    }
}
