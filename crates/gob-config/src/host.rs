//! The host the rule of this crate judges; it needs nothing from the product.

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

/// A product that can bind `CFG001`; every host qualifies.
pub trait ConfigHost {}

impl<T: ?Sized> ConfigHost for T {}
