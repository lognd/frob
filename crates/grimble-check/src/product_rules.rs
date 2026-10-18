//! The rule crates grimble runs (D107, rule-authoring.md section 4): one line per crate.
//!
//! `grimble-model` (MDL) and `grimble-bind` (SYS) declare their rules with `#[rule]`; the model
//! check and the binding step run as pipeline stages, so the product registers the declarations
//! as stage entries rather than binding their bodies. `gob-dev` lists every product's
//! `RULE_INDEXES` so ids stay unique across products.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P
use crate::GrimbleHost;

gob_check::product_rules! {
    product = Grimble;
    host = dyn GrimbleHost;
    crates = [grimble_model, grimble_bind];
}
