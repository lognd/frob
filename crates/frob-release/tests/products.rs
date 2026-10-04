//! The product list (D87, docs/design/products.md 6) is the only thing that ships: published
//! packages declare exactly the product binaries, dist archives exactly the product packages,
//! and the smoke and upload steps name every product archive explicitly.
// frob:ticket 01M422D5YRH5TG4499Z24K7SMT

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};
use std::process::Command;

use serde_json::Value;

/// The products: binary name to the package that carries it (and names its archive).
const PRODUCTS: [(&str, &str); 2] = [("frob", "frob-cli"), ("grimble", "grimble")];

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn read(rel: &str) -> String {
    std::fs::read_to_string(root().join(rel)).unwrap_or_else(|e| panic!("{rel}: {e}"))
}

/// `cargo metadata --no-deps` of this workspace.
fn metadata() -> Value {
    let cargo = std::env::var_os("CARGO").unwrap_or_else(|| "cargo".into());
    let out = Command::new(cargo)
        .current_dir(root())
        .args(["metadata", "--no-deps", "--format-version", "1"])
        .output()
        .expect("run cargo metadata");
    assert!(out.status.success(), "cargo metadata failed");
    serde_json::from_slice(&out.stdout).expect("metadata json")
}

/// Packages cargo would publish (`publish` is not the empty list).
fn publishable(meta: &Value) -> Vec<&Value> {
    meta["packages"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|p| p["publish"].as_array().is_none_or(|r| !r.is_empty()))
        .collect()
}

fn bins(pkg: &Value) -> BTreeSet<String> {
    pkg["targets"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|t| t["kind"].as_array().unwrap().iter().any(|k| k == "bin"))
        .map(|t| t["name"].as_str().unwrap().to_owned())
        .collect()
}

/// Binds: every publishable package's bin targets are exactly the product binaries.
#[test]
fn published_packages_declare_only_product_binaries() {
    let meta = metadata();
    let mut found: BTreeMap<String, String> = BTreeMap::new();
    for pkg in publishable(&meta) {
        let name = pkg["name"].as_str().unwrap();
        for bin in bins(pkg) {
            let expected = PRODUCTS.iter().find(|(b, _)| *b == bin).map(|(_, p)| *p);
            assert_eq!(
                expected,
                Some(name),
                "publishable package {name} declares non-product binary {bin}"
            );
            found.insert(bin, name.to_owned());
        }
    }
    let want: BTreeMap<String, String> = PRODUCTS
        .iter()
        .map(|(b, p)| ((*b).to_owned(), (*p).to_owned()))
        .collect();
    assert_eq!(found, want, "every product binary ships from its package");
}

/// Binds: the test-support crate that holds fake-sibling is never published.
#[test]
fn the_fake_sibling_helper_lives_in_an_unpublished_crate() {
    let meta = metadata();
    let owner = meta["packages"]
        .as_array()
        .unwrap()
        .iter()
        .find(|p| bins(p).contains("fake-sibling"))
        .expect("some package declares fake-sibling");
    assert_eq!(owner["name"], "gob-testsupport");
    assert_eq!(owner["publish"].as_array().map(Vec::len), Some(0));
}

/// Binds: the dist package set equals the product list (workspace default off, products opt in).
#[test]
fn dist_distributes_exactly_the_product_packages() {
    let cfg: toml::Table = read("dist-workspace.toml").parse().unwrap();
    assert_eq!(
        cfg["dist"]["dist"].as_bool(),
        Some(false),
        "[dist] dist = false is the workspace default"
    );
    let meta = metadata();
    let opted_in: BTreeSet<&str> = meta["packages"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|p| p["metadata"]["dist"]["dist"].as_bool() == Some(true))
        .map(|p| p["name"].as_str().unwrap())
        .collect();
    let products: BTreeSet<&str> = PRODUCTS.iter().map(|(_, p)| *p).collect();
    assert_eq!(opted_in, products, "dist opt-ins are the product list");
}

/// Binds: the smoke step names each product archive and runs each binary.
#[test]
fn the_smoke_steps_name_each_product_archive_and_run_each_binary() {
    let wf = read(".github/workflows/build-smoke.yml");
    for (bin, pkg) in PRODUCTS {
        let call = format!("archive-smoke.sh {bin} \"target/distrib/{pkg}-$TARGET.$ext\"");
        assert!(wf.contains(&call), "build smoke lacks: {call}");
        let fresh = format!("archive-smoke.sh {bin} \"archives/{pkg}-$TARGET.$ext\"");
        assert!(wf.contains(&fresh), "fresh-runner smoke lacks: {fresh}");
        for ext in ["tar.xz", "zip"] {
            for sum in ["", ".sha256"] {
                let up = format!("target/distrib/{pkg}-${{{{ matrix.target }}}}.{ext}{sum}");
                assert!(wf.contains(&up), "upload lacks {up}");
            }
        }
    }
    assert!(
        !wf.contains("target/distrib/*"),
        "no globbed archive path may remain"
    );
    let script = read("packaging/smoke/archive-smoke.sh");
    assert!(script.contains("fixture-loop.sh"), "frob runs the loop");
    assert!(script.contains("--version"), "grimble runs its binary");
    assert!(script.is_ascii());
}

/// Binds: the dev publish and the release job upload only the named product archives.
#[test]
fn publish_jobs_accept_only_product_archives() {
    let ci = read(".github/workflows/ci.yml");
    assert!(ci.contains("frob-cli-*|grimble-*) ;; *) echo \"unexpected file"));
    let rel = read(".github/workflows/release.yml");
    assert!(rel.contains("for product in frob-cli grimble; do"));
    assert!(rel.contains("archives/frob-cli-x86_64-unknown-linux-gnu.tar.xz"));
    assert!(!rel.contains("archives/*"), "no globbed asset list");
}
