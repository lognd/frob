//! Rule metadata, findings, the global rule registry and exception data types.
//!
//! Declare a rule with `#[derive(gob_rules::Rule)]`; it registers itself via
//! `inventory` and appears in [`Registry::global`].
//!
//! ```
//! use gob_rules::{RuleId, Severity};
//! let id: RuleId = "COV006".parse().unwrap();
//! assert_eq!(id.family(), "COV");
//! assert!(Severity::Error > Severity::Warn);
//! ```

mod exception;
mod finding;
mod id;
mod meta;
mod reason;
mod registry;
mod required;

pub use exception::{
    BoundException, Exception, ExceptionCtx, ExceptionKind, Resolved, apply_exceptions,
};
pub use finding::{Finding, Fingerprint, Fix, TextEdit};
pub use gob_macros::Rule;
pub use id::{ParseRuleIdError, RuleId};
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
