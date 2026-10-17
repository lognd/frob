//! DSL002: A directive carries an abbreviated ticket id instead of a full 26-char ULID.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD

use gob_rules::{FileCx, FileRule, Out, rule};

use crate::host::DirectiveHost;

/// A directive carries an abbreviated ticket id instead of a full 26-char ULID.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "DSL002",
    slug = "abbreviated-ticket-id",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = File,
    fix = Deterministic,
    applies = project,
    host = DirectiveHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Dsl002;

gob_rules::list_in_registry!(Dsl002, "frob");

impl<P: ?Sized + DirectiveHost> FileRule<P> for Dsl002 {
    /// The verdict is computed by the directive scanner (`crate::scan`); see the module doc.
    fn check(&self, _cx: &FileCx<'_, P>, _out: &mut Out<'_, Self>) {}
}
