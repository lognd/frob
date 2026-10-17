//! The rule crates frob runs (D107, rule-authoring.md section 4): one line per crate.
//!
//! The migrated rule crates are listed here; later migration tickets add theirs (and to
//! `Cargo.toml`; `unused_crate_dependencies` catches one without the other). `gob-dev` lists
//! every product's `RULE_INDEXES` so ids stay unique across products.

// frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3

use crate::host::FrobHost;

gob_check::product_rules! {
    product = Frob;
    host = dyn FrobHost;
    crates = [
        frob_tests,
        frob_ack,
        frob_obligations,
        frob_ledger,
        frob_pm,
        frob_release,
        frob_lease,
        gob_config,
    ];
}
