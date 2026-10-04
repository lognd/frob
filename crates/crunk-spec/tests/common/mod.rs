#![allow(
    dead_code,
    reason = "each test binary uses a different subset of the helpers"
)]

//! Shared helpers for the crunk-spec integration tests.

use std::path::Path;

use crunk_spec::{DesignSpec, SpecError, parse_spec, presets};

/// Project root every test spec is rooted at.
pub const ROOT: &str = "/proj";

/// The documented full example (the `default` preset).
pub fn full() -> &'static str {
    presets::DEFAULT
}

/// Parse `text` as `crunk.toml` rooted at [`ROOT`].
pub fn load(text: &str) -> Result<DesignSpec, SpecError> {
    parse_spec(text, Path::new("crunk.toml"), Path::new(ROOT))
}

/// Parse `text`, panicking with the error when it is invalid.
pub fn ok(text: &str) -> DesignSpec {
    load(text).unwrap_or_else(|e| panic!("expected a valid spec, got: {e}"))
}

/// Parse `text`, panicking when it is valid, and return the error.
pub fn err(text: &str) -> SpecError {
    load(text).expect_err("expected an invalid spec")
}

/// The full example with `extra` appended.
pub fn with(extra: &str) -> String {
    format!("{}\n{extra}\n", full())
}

/// The full example with `from` replaced by `to`.
pub fn swap(from: &str, to: &str) -> String {
    assert!(full().contains(from), "fixture lacks {from:?}");
    full().replacen(from, to, 1)
}

/// The detail text of an invalid-spec error.
pub fn detail(e: &SpecError) -> String {
    match e {
        SpecError::Invalid { detail, .. } => detail.clone(),
        other => panic!("expected Invalid, got {other:?}"),
    }
}

/// 1-based line of the first line of `text` containing `needle`.
pub fn line_of(text: &str, needle: &str) -> usize {
    text.lines()
        .position(|l| l.contains(needle))
        .unwrap_or_else(|| panic!("no line contains {needle:?}"))
        + 1
}
