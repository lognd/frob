//! Bakes the short git sha of the build into `GOB_BUILD_ID` (see `gob_check::build_id`).
//!
//! `FROB_BUILD_ID` overrides it for packagers without a `.git`; with neither, no id is baked
//! and the sibling document simply omits `build_id` (~RP9EDXC).

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
    if let Some(p) = git(&["rev-parse", "--git-path", "HEAD"]) {
        println!("cargo:rerun-if-changed={p}");
    }
    if let Some(r) = git(&["symbolic-ref", "-q", "HEAD"])
        && let Some(p) = git(&["rev-parse", "--git-path", &r])
    {
        println!("cargo:rerun-if-changed={p}");
    }
    println!("cargo:rerun-if-env-changed=FROB_BUILD_ID");
}

fn main() {
    watch_head();
    let id = std::env::var("FROB_BUILD_ID")
        .ok()
        .filter(|s| !s.is_empty())
        .or_else(|| git(&["rev-parse", "--short=9", "HEAD"]));
    if let Some(id) = id {
        println!("cargo:rustc-env=GOB_BUILD_ID={id}");
    }
}
