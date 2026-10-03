//! Tool versions pinned in `.github/workflows/ci.yml` must equal the ones the repository's
//! source of truth uses: `frob.toml` for zizmor and actionlint, `rust-toolchain.toml` for Rust,
//! `dist-workspace.toml` for cargo-dist (pinned in `build-smoke.yml`).
// frob:ticket 01M41PEAN0RE8DBEKQ1RBF6057

use std::fs;
use std::path::Path;

fn read(rel: &str) -> String {
    fs::read_to_string(
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../..")
            .join(rel),
    )
    .unwrap()
}

fn toml_of(rel: &str) -> toml::Table {
    read(rel).parse().unwrap()
}

/// The `[[check.tool]]` entry named `name` in `frob.toml`.
fn frob_tool(name: &str) -> toml::Table {
    let frob = toml_of("frob.toml");
    frob["check"]["tool"]
        .as_array()
        .unwrap()
        .iter()
        .map(|t| t.as_table().unwrap().clone())
        .find(|t| t["name"].as_str() == Some(name))
        .unwrap_or_else(|| panic!("no [[check.tool]] named {name}"))
}

fn strings(v: &toml::Value) -> Vec<String> {
    v.as_array()
        .unwrap()
        .iter()
        .map(|s| s.as_str().unwrap().to_owned())
        .collect()
}

/// Non-comment lines of ci.yml (prose comments may mention versions).
fn ci_code() -> String {
    read(".github/workflows/ci.yml")
        .lines()
        .filter(|l| !l.trim_start().starts_with('#'))
        .collect::<Vec<_>>()
        .join("\n")
}

/// Every whitespace-delimited token in ci.yml that starts with `prefix`.
fn ci_tokens(prefix: &str) -> Vec<String> {
    ci_code()
        .split_whitespace()
        .filter(|t| t.starts_with(prefix))
        .map(str::to_owned)
        .collect()
}

// frob:tests crates/frob-release/tests/ci_pins.rs::ci_zizmor_pin_matches_frob_toml
#[test]
fn ci_zizmor_pin_matches_frob_toml() {
    let tool = frob_tool("zizmor");
    let spec = strings(&tool["args"])
        .into_iter()
        .find(|a| a.starts_with("zizmor@"))
        .expect("frob.toml zizmor args carry a pinned spec");
    assert!(spec.contains('@') && !spec.ends_with('@'));
    assert!(strings(&tool["version_args"]).contains(&spec));
    let in_ci = ci_tokens("zizmor@");
    // The pin lives only in frob.toml; ci.yml runs `cargo dev ci --step zizmor`, which reads it
    // (gob-dev ci::tests::pins_come_from_frob_toml), so a hand-typed copy here is a second source.
    // frob:ticket 01M41T8KP0769YYXP8CAHBKXAZ
    assert!(
        in_ci.is_empty(),
        "ci.yml carries its own zizmor pin {in_ci:?} (want {spec}); use cargo dev ci --step zizmor"
    );
    assert!(ci_code().contains("cargo dev ci --step zizmor"));
}

// frob:tests crates/frob-release/tests/ci_pins.rs::ci_actionlint_pin_matches_frob_toml
#[test]
fn ci_actionlint_pin_matches_frob_toml() {
    let tool = frob_tool("actionlint");
    let spec = strings(&tool["args"])
        .into_iter()
        .find(|a| a.starts_with("actionlint-py=="))
        .expect("frob.toml actionlint args carry a pinned spec");
    assert!(strings(&tool["version_args"]).contains(&spec));
    let in_ci = ci_tokens("actionlint-py");
    // frob:ticket 01M41T8KP0769YYXP8CAHBKXAZ
    assert!(
        in_ci.is_empty(),
        "ci.yml carries its own actionlint pin {in_ci:?} (want {spec}); use cargo dev ci --step actionlint"
    );
    assert!(ci_code().contains("cargo dev ci --step actionlint"));
}

// frob:tests crates/frob-release/tests/ci_pins.rs::ci_rust_toolchain_comes_from_rust_toolchain_toml
#[test]
fn ci_rust_toolchain_comes_from_rust_toolchain_toml() {
    let code = ci_code();
    assert!(
        code.contains("rust-toolchain.toml"),
        "ci.yml must read the pinned channel"
    );
    assert!(
        code.contains("sed -n 's/^channel"),
        "ci.yml must derive the channel from the file"
    );
    let channel = toml_of("rust-toolchain.toml")["toolchain"]["channel"]
        .as_str()
        .unwrap()
        .to_owned();
    assert!(!channel.is_empty());
    // No second, hand-typed toolchain pin in ci.yml.
    for forbidden in ["toolchain: ", "dtolnay/rust-toolchain", "rustup default 1."] {
        assert!(
            !code.contains(forbidden),
            "ci.yml hand-pins a toolchain: {forbidden}"
        );
    }
}

// frob:tests crates/frob-release/tests/ci_pins.rs::ci_installs_no_unpinned_cargo_tools_beyond_nextest
#[test]
fn ci_installs_no_unpinned_cargo_tools_beyond_nextest() {
    // nextest is installed by sha-pinned taiki-e/install-action at its latest release; no other
    // file pins a nextest version, so there is nothing to equal. Any other `tool:` is new and
    // needs a source of truth plus an assertion here.
    let tools: Vec<String> = ci_code()
        .lines()
        .filter_map(|l| l.trim().strip_prefix("tool:").map(|v| v.trim().to_owned()))
        .collect();
    assert_eq!(tools, vec!["nextest".to_owned()]);
}

// frob:tests crates/frob-release/tests/ci_pins.rs::dist_pin_matches_dist_workspace
#[test]
fn dist_pin_matches_dist_workspace() {
    let want = toml_of("dist-workspace.toml")["dist"]["cargo-dist-version"]
        .as_str()
        .unwrap()
        .to_owned();
    let smoke = read(".github/workflows/build-smoke.yml");
    let got = smoke
        .lines()
        .find_map(|l| l.trim().strip_prefix("DIST_VERSION:"))
        .map(|v| v.trim().trim_matches('"').to_owned())
        .expect("build-smoke.yml pins DIST_VERSION");
    assert_eq!(got, want);
    assert!(
        !ci_code().contains("cargo-dist"),
        "ci.yml must not carry its own dist pin"
    );
}
