//! The host trait the MDL `#[rule]` declarations evaluate against.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

/// What an MDL rule may ask of its product: nothing yet, the model is checked as a whole.
///
/// `check_model` judges every MDL rule in one pass over the model files, so the declared rules are
/// staged (never run one by one); the trait exists so the rules bind to the product's host type.
pub trait MdlHost {}
