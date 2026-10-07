//! `product_rules!`: a product's one-line list of rule crates (D107, rule-authoring.md section 4).

/// Declare the rule crates a product runs; the pipeline runs exactly this list.
///
/// ```ignore
/// gob_check::product_rules! {
///     product = Frob;
///     host = dyn FrobHost;
///     crates = [frob_obligations, frob_ack];
/// }
/// ```
///
/// Expands to `RULE_INDEXES` (each listed crate's generated `rules::INDEX`), a const check that no
/// id, slug, renamed id or retired id repeats across the listed crates (a compile error naming both
/// declarations), and `rules()`, which binds every rule to `host`: a rule whose host trait the
/// product does not implement is an unsatisfied bound. A rule crate that is a Cargo dependency but
/// missing from the list is caught by `#![deny(unused_crate_dependencies)]` in the product crate.
#[macro_export]
macro_rules! product_rules {
    (
        product = $product:ident;
        host = $host:ty;
        crates = [$($krate:ident),* $(,)?] $(;)?
    ) => {
        /// The generated rule index of every crate this product lists.
        pub const RULE_INDEXES: &[&$crate::__rules::RuleIndex] = &[$(&$krate::rules::INDEX),*];

        const _: () = $crate::__rules::assert_unique(
            concat!("product ", stringify!($product)),
            &[RULE_INDEXES],
        );

        /// Every listed rule bound to this product's host; the pipeline runs exactly this list.
        #[allow(unused_mut, reason = "a product may list no rule crates yet")]
        pub fn rules() -> Vec<$crate::__rules::BoundRule<$host>> {
            let mut all = Vec::new();
            $( all.extend($krate::rules::bind::<$host>()); )*
            all
        }
    };
}
