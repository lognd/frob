//! The rule crates crunk runs (D107, rule-authoring.md section 4): one line per crate.
//!
//! `crunk-rules` holds WAIVE001, COLOR001-002 and CONTRAST001. A new crunk rule crate is one more name in `crates` here and a dependency
//! in `Cargo.toml` (`unused_crate_dependencies` catches one without the other). `gob-dev` lists
//! every product's `RULE_INDEXES` so ids stay unique across products.

// frob:ticket 01M43ATASM383KB9130JY79XVV

use crunk_rules::CrunkHost;

gob_check::product_rules! {
    product = Crunk;
    host = dyn CrunkHost;
    crates = [crunk_rules];
}

// frob:ticket 01M43ANVJYA7GHN0Y8GX0SN72M
gob_config::inventory::submit! {
    gob_config::ArtifactEntry {
        path: "docs/crunk/rules/README.md",
        family: gob_config::ArtifactFamily::Config,
        render: || gob_config::ArtifactBody::Markdown(
            crunk_rules::registry::render_markdown(RULE_INDEXES),
        ),
    }
}
