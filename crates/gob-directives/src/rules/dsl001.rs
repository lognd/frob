//! DSL001: A directive names a verb its namespace does not declare.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD

use gob_rules::{FileCx, FileRule, Out, rule};

use crate::host::DirectiveHost;

/// A directive names a verb its namespace does not declare.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "DSL001",
    slug = "unknown-directive-verb",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = File,
    fix = Manual,
    applies = project,
    host = DirectiveHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Dsl001;

gob_rules::list_in_registry!(Dsl001, "frob");

impl<P: ?Sized + DirectiveHost> FileRule<P> for Dsl001 {
    /// The verdict is computed by the directive scanner (`crate::scan`); see the module doc.
    fn check(&self, _cx: &FileCx<'_, P>, _out: &mut Out<'_, Self>) {}
}
