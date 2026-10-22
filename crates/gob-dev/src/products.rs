//! Every product's rule list, named explicitly (D107, rule-authoring.md section 4).
//!
//! The grimble and crunk lists are hand-written on purpose: dropping a product crate from
//! `Cargo.toml` makes this file stop compiling, so a product can never silently vanish from the
//! docs the way a missing link anchor once hid rules. frob's list cannot be named here (this crate
//! may not depend on a frob crate), so the frob-side generator binary registers it through
//! [`register_frob`] and carries the cross-product uniqueness check against [`OTHER_PRODUCTS`].

use std::sync::OnceLock;

use gob_rules::RuleIndex;

/// One product's name and the rule indexes of the crates it lists in `product_rules!`.
pub type ProductRules = (&'static str, &'static [&'static RuleIndex]);

/// The products this crate names itself, in generation order after frob.
pub const OTHER_PRODUCTS: &[ProductRules] = &[
    ("grimble", grimble_check::product_rules::RULE_INDEXES),
    ("crunk", crunk_check::product_rules::RULE_INDEXES),
];

/// What the frob side hands the generator: its rule indexes, its issue-projection schema and the
/// function that links its inventory registrations into the binary.
#[derive(Clone, Copy)]
pub struct FrobProduct {
    /// frob's `product_rules!` rule indexes.
    pub rules: &'static [&'static RuleIndex],
    /// The JSON schema of the tracker issue projection.
    pub issue_schema: fn() -> serde_json::Value,
    /// Touch every frob crate that submits inventory entries so the linker keeps them.
    pub link: fn(),
}

static FROB: OnceLock<FrobProduct> = OnceLock::new();

/// Register frob's side of the generator; the first registration wins and later ones are ignored.
pub fn register_frob(product: FrobProduct) {
    if FROB.set(product).is_err() {
        tracing::warn!("frob product already registered; keeping the first");
    } else {
        tracing::debug!(rules = product.rules.len(), "frob product registered");
    }
}

/// The registered frob product, or `None` when the binary never called [`register_frob`].
pub fn frob() -> Option<&'static FrobProduct> {
    FROB.get()
}

/// Every product, frob first, in a fixed order; frob is absent until [`register_frob`] runs.
pub fn products() -> Vec<ProductRules> {
    frob()
        .map(|f| ("frob", f.rules))
        .into_iter()
        .chain(OTHER_PRODUCTS.iter().copied())
        .collect()
}

/// Every `#[rule]` declaration of every product, with its product name, in product order.
pub fn all_defs() -> Vec<(&'static str, &'static gob_rules::RuleDef)> {
    let products = products();
    let defs: Vec<_> = products
        .iter()
        .flat_map(|(product, indexes)| {
            indexes
                .iter()
                .flat_map(move |ix| ix.metas.iter().map(move |d| (*product, *d)))
        })
        .collect();
    tracing::debug!(
        products = products.len(),
        rules = defs.len(),
        "product rule lists read"
    );
    defs
}
