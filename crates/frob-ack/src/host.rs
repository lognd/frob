//! The host trait frob-ack's `#[rule]` declarations evaluate against.

// frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3

use crate::inputs::Inputs;

/// What the DRIFT and AFFECT rules may ask of their product: the ack input bundle.
pub trait AckHost {
    /// The graph, lock, `frob:doc` directives and interner the rules read.
    fn inputs(&self) -> &Inputs;
}
