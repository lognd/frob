//! Attributes: doc comments and outer attributes are attr children and feed Sig.

/// Documented.
#[deprecated(note = "use other")]
#[inline]
pub fn old() {}
