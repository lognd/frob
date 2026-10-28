//! COH003 as a registered rule: layers from the model and from module depth through `grimble check`.

// frob:ticket 01M5M1TVT09K4YPK17S62Y1A18

#![allow(unused_crate_dependencies)]

use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

const TOP: &str = "def f(order, raw):\n    total = price_order(order)\n    head = raw[2:5]\n    return total, head\n";
const PRICE: &str = "def price_order(order):\n    return order\n";
const HELPER: &str = "def helper():\n    return 1\n";
const MODELED: &str = "[grimble]\nmodels = [\"m.grmb\"]\n";
const MODEL: &str = "grimble = \"2\";\nmodule m;\nnode hi : trusted { owns \"top.py\"; attr layer = 4; }\nnode lo : trusted { owns \"low/**\"; attr layer = 1; }\n";

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

/// The COH003 findings of a repo made of `files`.
fn findings(files: &[(&str, &str)]) -> Vec<serde_json::Value> {
    let dir = tempfile::tempdir().unwrap();
    for (rel, text) in files {
        write(dir.path(), rel, text);
    }
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["rule"] == "COH003")
        .cloned()
        .collect()
}

// frob:tests crates/grimble-check/src/coh_pass.rs::analyze
// frob:tests crates/grimble-check/src/rules/coh003.rs::Coh003
#[test]
fn module_depth_layers_make_coh003_fire_through_the_product() {
    let found = findings(&[
        ("grimble.toml", "[check]\n"),
        ("top.py", TOP),
        ("price.py", PRICE),
        ("a/b/h.py", HELPER),
    ]);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0]["severity"], "error", "{found:?}");
}

// frob:tests crates/grimble-check/src/coh_pass.rs::analyze
// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn model_layers_make_coh003_fire_through_the_product() {
    let found = findings(&[
        ("grimble.toml", MODELED),
        ("m.grmb", MODEL),
        ("top.py", TOP),
        ("price.py", PRICE),
        ("low/h.py", HELPER),
    ]);
    // price.py is owned by no layered node, so its callee stays unplaced next to the model.
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0]["severity"], "unresolved", "{found:?}");
    let placed = findings(&[
        ("grimble.toml", MODELED),
        ("m.grmb", MODEL),
        ("top.py", &format!("{TOP}{PRICE}")),
        ("low/h.py", HELPER),
    ]);
    assert_eq!(placed.len(), 1, "{placed:?}");
    assert_eq!(placed[0]["severity"], "error", "{placed:?}");
    let message = placed[0]["message"].as_str().unwrap();
    assert!(message.contains("4 layers apart"), "{message}");
}

// frob:tests crates/grimble-check/src/coh_pass.rs::analyze
#[test]
fn a_single_depth_repo_is_unresolved_not_clean() {
    let found = findings(&[
        ("grimble.toml", "[check]\n"),
        ("top.py", TOP),
        ("price.py", PRICE),
    ]);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0]["severity"], "unresolved", "{found:?}");
}

// frob:tests crates/grimble-check/src/config.rs::CohTable
#[test]
fn max_level_spread_in_the_coh_table_widens_the_allowance() {
    let files = |cfg: &'static str| {
        findings(&[
            ("grimble.toml", cfg),
            ("top.py", TOP),
            ("price.py", PRICE),
            ("a/b/h.py", HELPER),
        ])
    };
    assert_eq!(files("[coh]\nmax_level_spread = 1\n").len(), 1);
    assert!(files("[coh]\nmax_level_spread = 9\n").is_empty());
}
