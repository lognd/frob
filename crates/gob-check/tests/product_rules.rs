//! `product_rules!` over two generated fixture rule crates (~PBJ6GPZ, D107 section 4).
//!
//! `tests/product_rules/{alpha,beta}/src/rules/` are rule crates in miniature: rule files plus the
//! generated `mod.rs`, included here as the `rules` module of a stand-in crate module. Compile-fail
//! cases (duplicates) are under `tests/ui_product` and run in `ui_product.rs`.

use gob_check::__rules::{Body, indexgen};

/// The host trait both fixture rules evaluate against (stands in for a product host).
pub trait Host {
    /// True when the repository is bad.
    fn bad_repo(&self) -> bool;
}

/// A host whose repository badness is fixed.
struct Fake(bool);

impl Host for Fake {
    fn bad_repo(&self) -> bool {
        self.0
    }
}

#[path = "product_rules/alpha/src/rules/mod.rs"]
pub mod alpha_rules;

#[path = "product_rules/beta/src/rules/mod.rs"]
pub mod beta_rules;

/// Stand-in rule crates: `alpha::rules` is what `product_rules!` reads from a real crate.
mod alpha {
    pub use super::alpha_rules as rules;
}

/// Stand-in rule crate, see `alpha`.
mod beta {
    pub use super::beta_rules as rules;
}

mod demo {
    use super::{Host, alpha, beta};

    gob_check::product_rules! {
        product = Demo;
        host = dyn Host;
        crates = [alpha, beta];
    }
}

fn fixture(name: &str) -> std::path::PathBuf {
    std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/product_rules")
        .join(name)
}

#[test]
fn the_list_names_every_listed_crates_rules() {
    let ids: Vec<&str> = demo::RULE_INDEXES
        .iter()
        .flat_map(|ix| ix.metas.iter().map(|d| d.id))
        .collect();
    assert_eq!(ids, ["ALP001", "BET001"]);
}

#[test]
fn rules_binds_every_listed_rule_and_runs_it() {
    let host: &dyn Host = &Fake(true);
    let bound = demo::rules();
    assert_eq!(bound.len(), 2);
    let mut fired = Vec::new();
    for rule in &bound {
        let found = match &rule.body {
            Body::File(run) => run(host, "a bad word"),
            Body::Repo(run) => run(host),
        };
        fired.push((rule.def.id, found.len()));
    }
    assert_eq!(fired, [("ALP001", 1), ("BET001", 1)]);
}

#[test]
fn a_clean_host_and_text_fire_nothing() {
    let host: &dyn Host = &Fake(false);
    for rule in demo::rules() {
        let found = match &rule.body {
            Body::File(run) => run(host, "all fine"),
            Body::Repo(run) => run(host),
        };
        assert!(found.is_empty(), "{} fired on a clean input", rule.def.id);
    }
}

#[test]
fn fixture_indexes_are_fresh() {
    for name in ["alpha", "beta"] {
        indexgen::assert_fresh(fixture(name)).expect("fixture index is fresh");
    }
}
