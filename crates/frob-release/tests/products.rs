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

// frob:ticket 01M43ARVS24254G85TMFYH8FGQ
/// Products whose binary package exists but whose release wiring (dist opt-in, smoke, workflows) does
/// not yet; ~8CRC1ZH folds each entry into [`PRODUCTS`] when it registers the product.
const UNWIRED_PRODUCTS: [(&str, &str); 1] = [("crunk", "crunk")];

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
            let expected = PRODUCTS
                .iter()
                .chain(&UNWIRED_PRODUCTS)
                .find(|(b, _)| *b == bin)
                .map(|(_, p)| *p);
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
        .chain(&UNWIRED_PRODUCTS)
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

// frob:ticket 01M421FB3B2P9EMNKPDTPHS84G

/// The `[[product]]` tables of the `PyPI` product list.
fn pypi_products() -> Vec<toml::Table> {
    let table: toml::Table = read("packaging/pypi/products.toml").parse().unwrap();
    table["product"]
        .as_array()
        .unwrap()
        .iter()
        .map(|p| p.as_table().unwrap().clone())
        .collect()
}

/// Binds: the `PyPI` product list is the product list, and each entry points at its package's manifest.
#[test]
fn the_pypi_product_list_is_the_product_list() {
    let listed: Vec<(String, String)> = pypi_products()
        .iter()
        .map(|p| {
            let name = p["name"].as_str().unwrap().to_owned();
            let package = p["package"].as_str().unwrap().to_owned();
            let manifest = read(p["manifest"].as_str().unwrap());
            assert!(
                manifest.contains(&format!("name = \"{package}\"")),
                "{name}: manifest does not declare package {package}"
            );
            (name, package)
        })
        .collect();
    let want: Vec<(String, String)> = PRODUCTS
        .iter()
        .map(|(b, p)| ((*b).to_owned(), (*p).to_owned()))
        .collect();
    assert_eq!(listed, want);
}

/// Binds: frob's wheel depends on grimble at its own version; grimble's depends on nothing.
#[test]
fn frob_depends_on_grimble_at_the_same_version_and_grimble_on_nothing() {
    for p in pypi_products() {
        let deps: Vec<&str> = p["depends"]
            .as_array()
            .unwrap()
            .iter()
            .map(|d| d.as_str().unwrap())
            .collect();
        match p["name"].as_str().unwrap() {
            "frob" => assert_eq!(deps, ["grimble"]),
            "grimble" => assert!(deps.is_empty()),
            other => panic!("unexpected product {other}"),
        }
    }
    // One template, rendered per product: the dependency is pinned `==` the wheel's own version.
    let render = read("packaging/pypi/render.py");
    assert!(
        render.contains("f\"{d}=={version}\""),
        "pin is the wheel version"
    );
    let template = read("packaging/pypi/pyproject.template.toml");
    assert!(template.contains("version = \"@VERSION@\""));
    assert!(template.contains("dependencies = @DEPENDENCIES@"));
    assert!(
        !std::path::Path::new(&root().join("packaging/pypi/pyproject.toml")).exists(),
        "no per-product pyproject is checked in; the version is the Cargo lockstep version"
    );
    let build = read("packaging/pypi/build-wheel.sh");
    assert!(
        build.contains("render.py\" list"),
        "build-wheel.sh builds every listed product"
    );
    assert!(
        !build.contains("data/scripts"),
        "no wheel bundles another product's binary"
    );
}

/// Binds: the smoke installs from the local wheels only and covers the three scenarios.
#[test]
fn the_wheel_smoke_installs_from_local_wheels_only_in_three_scenarios() {
    let smoke = read("packaging/pypi/smoke.sh");
    assert!(smoke.contains("--no-index --find-links"));
    let installs: Vec<&str> = smoke
        .lines()
        .filter(|l| !l.trim_start().starts_with('#'))
        .filter(|l| l.starts_with("uv pip install") || l.starts_with("uv tool install"))
        .collect();
    assert_eq!(installs.len(), 3, "{installs:?}");
    for l in &installs {
        assert!(
            l.contains("${install_args[@]}"),
            "install without --no-index: {l}"
        );
    }
    for scenario in [
        "# a. grimble alone",
        "# b. frob alone",
        "# c. uv tool install frob",
    ] {
        assert!(smoke.contains(scenario), "smoke lacks `{scenario}`");
    }
    assert!(
        smoke.contains("beside-frob"),
        "scenario c asserts sibling discovery"
    );
    assert!(smoke.is_ascii());
}

/// Binds: the workflows name every `PyPI` product in the per-product wheel count checks.
#[test]
fn the_workflows_count_wheels_for_every_pypi_product() {
    let names: Vec<String> = pypi_products()
        .iter()
        .map(|p| p["name"].as_str().unwrap().to_owned())
        .collect();
    let loop_line = format!("for product in {}; do", names.join(" "));
    for wf in [
        ".github/workflows/build-smoke.yml",
        ".github/workflows/release.yml",
    ] {
        assert!(read(wf).contains(&loop_line), "{wf} lacks `{loop_line}`");
    }
}
