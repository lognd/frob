//! Bakes the build identity into `FROB_BUILD_VERSION` (the string `frob --version` prints).
//!
//! A release build (release profile, HEAD exactly on tag `v<version>`) and any build without a
//! git checkout (a packaged source tree) report the bare release version; every other build
//! reports `<version>-dev+<short sha>`, so two builds from different commits never share an
//! identity (~821FN00).

#![allow(
    clippy::print_stdout,
    reason = "cargo build-script protocol: directives are printed to stdout"
)]

use std::process::Command;

/// Stdout of `git <args>` when it succeeds and is non-empty.
fn git(args: &[&str]) -> Option<String> {
    let out = Command::new("git").args(args).output().ok()?;
    let text = String::from_utf8(out.stdout).ok()?;
    let text = text.trim();
    (out.status.success() && !text.is_empty()).then(|| text.to_owned())
}

/// Ask cargo to rerun when HEAD or the branch it points at moves.
fn watch_head() {
    for spec in ["HEAD"] {
        if let Some(p) = git(&["rev-parse", "--git-path", spec]) {
            println!("cargo:rerun-if-changed={p}");
        }
    }
    if let Some(r) = git(&["symbolic-ref", "-q", "HEAD"])
        && let Some(p) = git(&["rev-parse", "--git-path", &r])
    {
        println!("cargo:rerun-if-changed={p}");
    }
    println!("cargo:rerun-if-env-changed=FROB_BUILD_ID");
}

fn main() {
    let version = std::env::var("CARGO_PKG_VERSION").unwrap_or_default();
    watch_head();
    // An explicit override (packagers without .git) wins.
    let sha = std::env::var("FROB_BUILD_ID")
        .ok()
        .filter(|s| !s.is_empty())
        .or_else(|| git(&["rev-parse", "--short=9", "HEAD"]));
    let release_profile = std::env::var("PROFILE").is_ok_and(|p| p == "release");
    let on_tag = git(&["describe", "--exact-match", "--tags", "HEAD"])
        .is_some_and(|t| t == format!("v{version}"));
    let full = match sha {
        Some(sha) if !(release_profile && on_tag) => format!("{version}-dev+{sha}"),
        _ => version,
    };
    println!("cargo:rustc-env=FROB_BUILD_VERSION={full}");
}
