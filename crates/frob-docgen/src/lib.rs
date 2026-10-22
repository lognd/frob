//! `frob-docgen`: the generator binary linked with frob.
//!
//! `gob-dev` renders every generated page but may not depend on a frob crate (SYS013), so this
//! crate sits above both: it hands frob's rule indexes, issue-projection schema and inventory
//! anchor to `gob-dev` through [`register`], and `cargo dev gen` delegates here.

use gob_dev::products::{FrobProduct, register_frob};

// Ids, slugs and renamed or retired ids may not repeat across the three products.
const _: () = gob_rules::assert_unique(
    "all products",
    &[
        frob_check::product_rules::RULE_INDEXES,
        grimble_check::product_rules::RULE_INDEXES,
        crunk_check::product_rules::RULE_INDEXES,
    ],
);

/// Touch the frob CLI so its inventory registrations stay linked into the binary.
fn link() {
    let verbs = frob_cli::cli();
    tracing::debug!(product = frob_cli::PRODUCT, "frob cli linked");
    drop(verbs);
}

/// Register frob's side of the generator with `gob-dev`; safe to call repeatedly.
pub fn register() {
    register_frob(FrobProduct {
        rules: frob_check::product_rules::RULE_INDEXES,
        issue_schema: frob_mirror::projection::issue_projection_schema,
        link,
    });
}
