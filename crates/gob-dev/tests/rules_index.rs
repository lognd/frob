//! `cargo dev gen rules-index`: crate discovery, family ownership and the explicit product list (~PBJ6GPZ).

use gob_dev::render::rules_index::{RulesIndexError, generate};

fn write_rule_crate(root: &std::path::Path, krate: &str, families: Option<&str>, id: &str) {
    let dir = root.join("crates").join(krate);
    std::fs::create_dir_all(dir.join("src/rules")).expect("mkdir");
    let meta = families.map_or(String::new(), |f| {
        format!("[package.metadata.gob]\nfamilies = [{f}]\n")
    });
    std::fs::write(
        dir.join("Cargo.toml"),
        format!("[package]\nname = \"{krate}\"\n{meta}"),
    )
    .expect("manifest");
    let lower = id.to_ascii_lowercase();
    std::fs::write(
        dir.join(format!("src/rules/{lower}.rs")),
        format!(
            "#[rule(\n    id = \"{id}\",\n    slug = \"s\",\n    scope = File,\n)]\n/// Doc.\npub struct R;\n"
        ),
    )
    .expect("rule");
}

#[test]
fn a_crate_with_attribute_rules_gets_a_generated_mod_rs_path() {
    let tmp = tempfile::tempdir().expect("tmp");
    write_rule_crate(tmp.path(), "cov-rules", Some("\"COV\""), "COV001");
    let files = generate(&tmp.path().join("crates")).expect("generate");
    assert_eq!(files.len(), 1);
    assert_eq!(files[0].path, "crates/cov-rules/src/rules/mod.rs");
    assert!(files[0].content.contains("pub mod cov001;"));
}

#[test]
fn a_crate_without_a_families_key_is_not_family_checked() {
    let tmp = tempfile::tempdir().expect("tmp");
    write_rule_crate(tmp.path(), "anywhere", None, "COV001");
    assert_eq!(
        generate(&tmp.path().join("crates"))
            .expect("generate")
            .len(),
        1
    );
}

#[test]
fn a_rule_in_a_crate_that_does_not_own_its_family_is_rejected() {
    let tmp = tempfile::tempdir().expect("tmp");
    write_rule_crate(tmp.path(), "neat-rules", Some("\"NEAT\""), "COV001");
    let err = generate(&tmp.path().join("crates")).expect_err("foreign family");
    assert!(
        matches!(err, RulesIndexError::ForeignFamily { .. }),
        "{err}"
    );
    assert!(err.to_string().contains("family `COV`"), "{err}");
}

#[test]
fn the_explicit_product_list_names_every_product_once() {
    let names: Vec<_> = gob_dev::products::PRODUCTS.iter().map(|p| p.0).collect();
    assert_eq!(names, ["frob", "grimble", "crunk"]);
}

#[test]
fn product_lists_hold_no_rule_ids_that_repeat() {
    let defs = gob_dev::products::all_defs();
    let mut ids: Vec<_> = defs.iter().map(|(_, d)| d.id).collect();
    ids.sort_unstable();
    let before = ids.len();
    ids.dedup();
    assert_eq!(before, ids.len());
}

#[test]
fn every_product_crate_denies_unused_dependencies_and_lists_its_rules() {
    // A rule crate that stays a dependency after leaving `product_rules!` is an unused crate
    // dependency; rustc reports it only because each product crate denies the lint.
    let crates = gob_dev::workspace_root()
        .expect("workspace root")
        .join("crates");
    for name in ["frob-check", "grimble-check", "crunk-check"] {
        let src = crates.join(name).join("src");
        let lib = std::fs::read_to_string(src.join("lib.rs")).expect("lib.rs");
        assert!(
            lib.contains("deny(unused_crate_dependencies)"),
            "{name} must deny unused_crate_dependencies"
        );
        let list = std::fs::read_to_string(src.join("product_rules.rs")).expect("product_rules.rs");
        assert!(
            list.contains("gob_check::product_rules!"),
            "{name} lists its rule crates"
        );
    }
}

#[test]
fn gob_dev_has_no_rule_link_anchor() {
    let lib = std::fs::read_to_string(
        gob_dev::workspace_root()
            .expect("workspace root")
            .join("crates/gob-dev/src/lib.rs"),
    )
    .expect("lib.rs");
    assert!(
        !lib.contains("Registry::global()"),
        "rules are listed in products.rs, not anchored through the inventory"
    );
}
