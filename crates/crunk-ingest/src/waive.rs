//! The `crunk:waive` comment directive, registered in the `crunk` namespace so the shared
//! directive scanner finds it in CSS comments.

// frob:ticket 01M43ARY91XZ35DN9SCHRHS033

use gob_directives::Directive;

/// Waive one crunk rule at the declaration this comment attaches to.
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "crunk", verb = "waive")]
pub struct Waive {
    /// The waived rule id, for example `COLOR001`.
    #[arg(positional)]
    pub rule: String,
    /// Why the waiver exists.
    #[arg(key = "reason", optional)]
    pub reason: Option<String>,
}
