//! Rule metadata, findings, the global rule registry and exception data types.
//!
//! Declare a rule with `#[gob_rules::rule(..)]` (D107: every field required, `applies` checked
//! against the capability matrix, a colocated `.md` page); [`RuleDef`] is its static description.
//! The older `#[derive(gob_rules::Rule)]` is superseded by it; it registers itself via `inventory` and
//! appears in [`Registry::global`].
//!
//! ```
//! use gob_rules::{RuleId, Severity};
//! let id: RuleId = "COV006".parse().unwrap();
//! assert_eq!(id.family(), "COV");
//! assert!(Severity::Error > Severity::Unresolved);
//! ```

// Lets the `#[rule]` expansion name `::gob_rules` from inside this crate (~N88H9SY).
extern crate self as gob_rules;

mod baseline;
mod decl;
mod exception;
mod finding;
mod fix;
mod gate;
mod id;
mod index;
pub mod indexgen;
mod meta;
mod nature;
mod precision;
mod product_registry;
mod reason;
mod redirects;
mod registry;
mod required;
pub mod rules;
mod settings;
mod unresolved;

pub use baseline::{
    BASELINE_FILE, BASELINE_VERSION, Baseline, BaselineError, BaselineHost, Growth, PruneInput,
    PruneReport, RATCHET_LOCK_FILE, RuleTable, TicketLife, dead_tables, growth,
    migrate_ratchet_lock,
};
pub use decl::{
    Applies, Emitted, FileCx, FileRule, Measured, Out, RelayRule, RepoRule, RuleDecl, RuleDef,
    run_file, run_relay, run_repo,
};
pub use exception::{
    BoundException, Exception, ExceptionCtx, ExceptionKind, Resolved, apply_exceptions,
};
pub use finding::{Finding, Fingerprint, Fix, TextEdit};
pub use fix::{FixDrop, PluginEdit, PluginFix, cap_applicability};
pub use gate::{ALL_GATES, Gate, check_gate_override, gates_of, rule_in_gate};
pub use gob_caps as caps;
pub use gob_macros::{Rule, rule};
pub use gob_text::FileInterner;
pub use id::{ParseRuleIdError, RuleId};
pub use index::{
    Body, BoundRule, FileFn, InapplicableFn, RelayFn, RepoFn, RuleIndex, SubjectsFn, assert_unique,
};
pub use inventory;
pub use meta::{
    Applicability, FixKind, Needs, Polarity, Provenance, RuleEntry, RuleMeta, Scope, Severity, Tier,
};
pub use nature::{AGENT_INSTRUCTION, Audience, HEURISTIC_PREFIX, HeuristicNote, Nature};
pub use precision::{Demotion, MIN_DECIDED, PrecisionLedger, PrecisionRow, RuleTally};
pub use product_registry::{
    PRODUCT_CRATES, ProductCrates, ProductRegistryError, check_registry, crate_of_module,
};
pub use reason::{BannedPattern, ReasonPolicy, ReasonRejected, check_reason};
pub use redirects::{RENAMED_IDS, RENAMED_SLUGS, RETIRED_IDS, RedirectError, Redirects};
pub use registry::{Registry, RegistryError, RuleRow, RuleSettings};
pub use required::{PackFailure, RequiredReason};
pub use settings::{drop_disabled_product_findings, shipped_in};
pub use unresolved::{RuleReport, UnknownClass, UnresolvedReason};

/// A declared rule; implemented by `#[derive(Rule)]`. Object safe.
pub trait Rule {
    /// The static metadata for this rule.
    fn meta(&self) -> &'static RuleMeta;
}
