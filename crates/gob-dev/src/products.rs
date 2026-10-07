//! Every product's rule list, named explicitly (D107, rule-authoring.md section 4).
//!
//! The list is hand-written on purpose: dropping a product crate from `Cargo.toml` makes this file
//! stop compiling, so a product can never silently vanish from the docs the way a missing link
//! anchor once hid rules. The const check below fails the build when an id, slug, renamed id or
//! retired id repeats across products.

use gob_rules::RuleIndex;

/// One product's name and the rule indexes of the crates it lists in `product_rules!`.
pub type ProductRules = (&'static str, &'static [&'static RuleIndex]);

/// Every product, in a fixed order.
pub const PRODUCTS: &[ProductRules] = &[
    ("frob", frob_check::product_rules::RULE_INDEXES),
    ("grimble", grimble_check::product_rules::RULE_INDEXES),
    ("crunk", crunk_check::product_rules::RULE_INDEXES),
];

const _: () = gob_rules::assert_unique(
    "all products",
    &[
        frob_check::product_rules::RULE_INDEXES,
        grimble_check::product_rules::RULE_INDEXES,
        crunk_check::product_rules::RULE_INDEXES,
    ],
);

/// Every `#[rule]` declaration of every product, with its product name, in product order.
pub fn all_defs() -> Vec<(&'static str, &'static gob_rules::RuleDef)> {
    let defs: Vec<_> = PRODUCTS
        .iter()
        .flat_map(|(product, indexes)| {
            indexes
                .iter()
                .flat_map(move |ix| ix.metas.iter().map(move |d| (*product, *d)))
        })
        .collect();
    tracing::debug!(
        products = PRODUCTS.len(),
        rules = defs.len(),
        "product rule lists read"
    );
    defs
}
