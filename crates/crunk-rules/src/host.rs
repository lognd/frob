//! The host trait crunk's `#[rule]` declarations evaluate against.

// frob:ticket 01M43ATASM383KB9130JY79XVV

/// What a crunk rule may ask of its product. The file rules so far read only their file's text,
/// so the trait is empty; a rule that needs the spec adds its accessor here, once, for all rules.
pub trait CrunkHost {}
