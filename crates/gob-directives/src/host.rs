//! The host trait the PARSE and DSL `#[rule]` declarations evaluate against.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD

/// Marker for products whose directives the scanner reads; the verdicts come from `crate::scan`.
pub trait DirectiveHost {}
