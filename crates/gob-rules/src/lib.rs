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
//! assert!(Severity::Error > Severity::Warn);
//! ```

// Lets the `#[rule]` expansion name `::gob_rules` from inside this crate (~N88H9SY).
extern crate self as gob_rules;

mod decl;
mod exception;
mod finding;
mod id;
mod index;
pub mod indexgen;
mod meta;
mod reason;
mod registry;
mod required;

pub use decl::{
    Applies, Emitted, FileCx, FileRule, Measured, Out, RepoRule, RuleDecl, RuleDef, run_file,
    run_repo,
};
pub use exception::{
    BoundException, Exception, ExceptionCtx, ExceptionKind, Resolved, apply_exceptions,
};
pub use finding::{Finding, Fingerprint, Fix, TextEdit};
pub use gob_caps as caps;
pub use gob_macros::{Rule, rule};
pub use id::{ParseRuleIdError, RuleId};
pub use index::{
    Body, BoundRule, FileFn, InapplicableFn, RepoFn, RuleIndex, SubjectsFn, assert_unique,
};
pub use inventory;
pub use meta::{FixKind, Polarity, RuleEntry, RuleMeta, Scope, Severity, Tier};
pub use reason::{BannedPattern, ReasonPolicy, ReasonRejected, check_reason};
pub use registry::{Registry, RegistryError};
pub use required::RequiredReason;

/// A declared rule; implemented by `#[derive(Rule)]`. Object safe.
pub trait Rule {
    /// The static metadata for this rule.
    fn meta(&self) -> &'static RuleMeta;
}
