//! The host trait the check-owned `#[rule]` declarations evaluate against.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD

/// Marker for products that run the check pipeline; the verdicts come from the pipeline, the tool binders and the PROC001 scan.
pub trait CheckHost {}
