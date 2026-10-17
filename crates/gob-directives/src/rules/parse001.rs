//! PARSE001: A `frob:` directive is malformed: unterminated quote, bad key, missing or invalid argument.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD

use gob_rules::{FileCx, FileRule, Out, rule};

use crate::host::DirectiveHost;

/// A `frob:` directive is malformed: unterminated quote, bad key, missing or invalid argument.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PARSE001",
    slug = "malformed-directive",
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
pub struct Parse001;

gob_rules::list_in_registry!(Parse001, "frob");

impl<P: ?Sized + DirectiveHost> FileRule<P> for Parse001 {
    /// The verdict is computed by the directive scanner (`crate::scan`); see the module doc.
    fn check(&self, _cx: &FileCx<'_, P>, _out: &mut Out<'_, Self>) {}
}
