//! What a `frob check` run was asked to do: the generic options plus frob's own.

use std::path::PathBuf;
use std::sync::Arc;

use frob_lease::LeaseConfig;
use frob_ledger::LedgerConfig;
use gob_check::{FailOn, FileCheck, RunOptions};

use crate::product::Frob;

/// Which findings `check --teach [RULE]` prints the full explain text for.
// frob:ticket 01M3ZX81N4AFEA0W55R756T5RD
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TeachSelect {
    /// Every rule that fired in this run (`--teach`, alias `--explain-all`).
    All,
    /// Only this rule id or slug (`--teach SYS003`).
    Rule(String),
}

impl TeachSelect {
    /// Parse the flag value: empty means every rule, anything else names one rule.
    pub fn from_flag(value: &str) -> Self {
        let v = value.trim();
        if v.is_empty() {
            Self::All
        } else {
            Self::Rule(v.to_owned())
        }
    }

    /// True when a finding of rule `id` (with kebab-case `slug`) is printed in full.
    pub fn selects(&self, id: &str, slug: &str) -> bool {
        match self {
            Self::All => true,
            Self::Rule(r) => r.eq_ignore_ascii_case(id) || r == slug,
        }
    }
}

/// Inputs of [`crate::run`] besides the repository root; `Default` is a plain full check.
#[expect(
    clippy::struct_excessive_bools,
    reason = "independent caller switches, each one flag of the run"
)]
#[derive(Clone, Default)]
pub struct CheckOptions {
    /// Ticket reference (`~handle`, ULID or alias) that scopes the run.
    pub ticket: Option<String>,
    /// Rule families or rule ids to keep; empty keeps everything.
    pub only: Vec<String>,
    /// Apply Deterministic fixes and re-run once.
    pub fix: bool,
    /// Overrides the `[check] fail_on` of `frob.toml` when deciding the exit code.
    pub fail_on: Option<FailOn>,
    /// Scope the run to what the tree changed since this ref or oid (plus dependents), with no
    /// ticket: SCOPE001, TICK002 and REL003 are skipped. Ignored when `ticket` is set.
    pub diff_base: Option<String>,
    /// Overrides `[check] base` for the diff of a `--ticket` run.
    pub base: Option<String>,
    /// Ledger settings (the `[tickets]` and `[git]` tables live in the binary); defaults when absent.
    pub ledger: Option<LedgerConfig>,
    /// Lease settings (`[lease]`); loaded from `frob.toml` when absent.
    pub lease: Option<LeaseConfig>,
    /// Extra per-file checks run next to the built-in ones (tests, embedders).
    pub extra_checks: Vec<Arc<dyn FileCheck<Frob>>>,
    /// With `ticket`: run only the `ticket`-tier tool stages (`--quick`).
    pub quick: bool,
    /// Skip the `[[check.tool]]` stages (frob-land runs them itself).
    pub skip_tools: bool,
    /// Run this executable for a sibling product instead of resolving it next to frob or on `PATH`
    /// (`(product, path)` pairs; tests and embedders).
    pub sibling_programs: Vec<(String, PathBuf)>,
    /// Do not write `.frob/telemetry.jsonl` even when `[check] telemetry` is true.
    pub skip_telemetry: bool,
    /// The command's clock; when absent the run pins the system clock once at its start.
    pub clock: Option<Arc<dyn gob_time::Clock>>,
    /// Treat the `--ticket` ticket as exempt from the changelog fragment (`land --no-changelog --reason`, not yet recorded).
    pub changelog_exempt: bool,
    /// `--trust-from REF`: trust only the pack lock at this ref (security.md 2.3); the only CI trust flag.
    pub trust_from: Option<String>,
    /// `--teach [RULE]`: print the full explain text for the selected findings of this run.
    pub teach: Option<TeachSelect>,
}

/// Repo-relative path of frob's pack lock, read at the `--trust-from` ref.
pub(crate) const TRUST_LOCK_PATH: &str = "frob.packs.lock";

impl CheckOptions {
    /// The tool tier of this run: `ticket` under `--quick`, `train` for a ticket run, else every tier.
    pub(crate) fn tool_tier(&self) -> Option<gob_check::ToolTier> {
        match (&self.ticket, self.quick) {
            (Some(_), true) => Some(gob_check::ToolTier::Ticket),
            (Some(_), false) => Some(gob_check::ToolTier::Train),
            (None, _) => None,
        }
    }

    /// The product-neutral half of these options, as [`gob_check::run`] takes them.
    pub(crate) fn run_options(&self) -> RunOptions {
        RunOptions {
            scope: self.ticket.clone().or_else(|| {
                self.diff_base
                    .as_ref()
                    .map(|_| crate::scope::DIFF_SCOPE_REF.to_owned())
            }),
            only: self.only.clone(),
            fix: self.fix,
            fail_on: self.fail_on,
            tool_tier: self.tool_tier(),
            skip_tools: self.skip_tools,
            skip_telemetry: self.skip_telemetry,
            clock: self.clock.clone(),
            tool_memo: None,
            tool_trust: None,
            trust_from: self.trust_from.as_ref().map(|base_ref| {
                gob_check::TrustFromSpec {
                    base_ref: base_ref.clone(),
                    lock_path: TRUST_LOCK_PATH.to_owned(),
                    // frob loads no repository packs yet, so no live pack can be untrusted.
                    packs: Vec::new(),
                }
            }),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{CheckOptions, TeachSelect};
    use gob_check::ToolTier;

    // frob:tests crates/frob-check/src/options.rs::CheckOptions.tool_tier
    #[test]
    fn quick_ticket_runs_only_the_ticket_tier() {
        let mut o = CheckOptions::default();
        assert_eq!(o.tool_tier(), None);
        o.ticket = Some("~X".to_owned());
        assert_eq!(o.tool_tier(), Some(ToolTier::Train));
        o.quick = true;
        assert_eq!(o.tool_tier(), Some(ToolTier::Ticket));
    }

    // frob:tests crates/frob-check/src/options.rs::TeachSelect.selects
    #[test]
    fn teach_selects_one_rule_or_all() {
        assert_eq!(TeachSelect::from_flag(""), TeachSelect::All);
        assert!(TeachSelect::All.selects("DOC001", "x"));
        let one = TeachSelect::from_flag("sys003");
        assert!(one.selects("SYS003", "slug"));
        assert!(!one.selects("DOC001", "other"));
    }
}
