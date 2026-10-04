//! Checked-in `crunk.toml` preset payloads for `crunk init`.
//!
//! Each preset is literally a `crunk.toml` file's text, so it can never diverge from the
//! schema: [`crate::parse_spec`] is the only validator and the tests run it over these strings.

// frob:ticket 01M43ARX764095Q4VWABWXXV5H

/// The `default` preset: Inter, a small palette, kebab-case buckets.
pub const DEFAULT: &str = include_str!("presets/default.toml");

/// The `mono` preset: a monospace, near-black-and-white palette.
pub const MONO: &str = include_str!("presets/mono.toml");

/// Every preset as `(name, crunk.toml text)`, in listing order.
pub const PRESETS: &[(&str, &str)] = &[("default", DEFAULT), ("mono", MONO)];

/// The text of the preset called `name`, if there is one.
pub fn preset(name: &str) -> Option<&'static str> {
    PRESETS.iter().find(|(n, _)| *n == name).map(|(_, t)| *t)
}

/// The preset names, in listing order.
pub fn preset_names() -> Vec<&'static str> {
    PRESETS.iter().map(|(n, _)| *n).collect()
}
