//! `frob --version` build identity (~821FN00).

// frob:ticket 01M1T07NX1SZYZBZYYW821FN00

use std::process::Command;

/// First line of `frob --version` for the test binary.
fn version_line() -> String {
    let exe = assert_cmd::cargo::cargo_bin("frob");
    let out = Command::new(exe).arg("--version").output().expect("run frob");
    String::from_utf8(out.stdout).expect("utf8").lines().next().unwrap_or_default().to_owned()
}

#[test]
fn a_dev_build_reports_release_plus_dev_and_sha() {
    let line = version_line();
    let release = env!("CARGO_PKG_VERSION");
    // Test builds use the debug profile, so never the bare release version.
    assert!(line.contains(&format!("{release}-dev+")), "{line}");
}

#[test]
fn the_baked_identity_is_the_build_version_constant() {
    let baked = env!("FROB_BUILD_VERSION");
    assert!(version_line().ends_with(baked), "{baked}");
    assert!(baked.starts_with(env!("CARGO_PKG_VERSION")));
}
