//! Default-theme key tables for Tailwind v3 and v4.
//!
//! The v3 tables are ported verbatim from crunk's Python `tw_defaults`. v4 has no JS theme: its
//! defaults are CSS variables, so the v4 tables list the variable suffixes (`--radius-md` is
//! key `md`). v4 has no default z-index scale and its spacing is a numeric multiplier rather
//! than a key table, hence [`V4_Z_INDEX_KEYS`] is empty and [`is_v4_spacing_key`] is a predicate.

pub use crate::v3_data::{
    V3_BORDER_RADIUS_KEYS, V3_COLOR_HEXES, V3_COLOR_NAMES, V3_FONT_SIZE_KEYS, V3_SPACING_KEYS,
    V3_Z_INDEX_KEYS,
};

/// Tailwind v4 default `--radius-*` keys.
pub const V4_BORDER_RADIUS_KEYS: &[&str] = &["2xl", "3xl", "4xl", "lg", "md", "sm", "xl", "xs"];

/// Tailwind v4 default `--text-*` (font size) keys.
pub const V4_FONT_SIZE_KEYS: &[&str] = &[
    "2xl", "3xl", "4xl", "5xl", "6xl", "7xl", "8xl", "9xl", "base", "lg", "sm", "xl", "xs",
];

/// Tailwind v4 has no default z-index scale; any integer is accepted by the utility itself.
pub const V4_Z_INDEX_KEYS: &[&str] = &[];

/// Tailwind v4 default color names: the same 22 ramp families and `black`/`white` as v3 (v4
/// redefines the values in oklch, not the names).
pub const V4_COLOR_NAMES: &[&str] = V3_COLOR_NAMES;

/// Whether `key` is a v4 default spacing key: `px` or a non-negative multiple of 0.25 written
/// as a plain decimal (v4 computes `calc(var(--spacing) * key)`).
pub fn is_v4_spacing_key(key: &str) -> bool {
    if key == "px" {
        return true;
    }
    let well_formed = !key.is_empty()
        && key.chars().all(|c| c.is_ascii_digit() || c == '.')
        && key.matches('.').count() <= 1
        && !key.starts_with('.')
        && !key.ends_with('.');
    if !well_formed {
        return false;
    }
    key.parse::<f64>().is_ok_and(|n| (n * 4.0).fract() == 0.0)
}

/// Whether `table` (a sorted or unsorted key slice from this module) contains `key`.
pub fn has_key(table: &[&str], key: &str) -> bool {
    table.contains(&key)
}
