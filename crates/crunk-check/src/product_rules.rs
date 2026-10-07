//! The rule crates crunk runs (D107, rule-authoring.md section 4): one line per crate.
//!
//! No rule crate has moved to `#[rule]` yet, so the list is empty; the migration tickets add
//! their crates here (and to `Cargo.toml`; `unused_crate_dependencies` catches one without the
//! other). `gob-dev` lists every product's `RULE_INDEXES` so ids stay unique across products.

gob_check::product_rules! {
    product = Crunk;
    host = ();
    crates = [];
}
