//! Token naming on top of `crunk_spec::naming`: companion names, bare (JSON) names, `var()`
//! references and the Tailwind theme key of a scale step.
//!
//! The per-family custom-property names themselves (`--color-ink`, `--space-8`) stay in
//! `crunk_spec::naming`, parameterized by `[tokens.prefixes]`; this module only derives the
//! names that are functions of those.

// frob:ticket 01M43ARZAJ8NJ3F38157ERAKR5

/// Suffix of the alpha-channel companion of a color token.
pub const CHANNELS_SUFFIX: &str = "-rgb";

/// The `-rgb` companion name of the color token `color_name` (`--color-ink` to
/// `--color-ink-rgb`).
pub fn channels_name(color_name: &str) -> String {
    format!("{color_name}{CHANNELS_SUFFIX}")
}

/// A custom-property name without its leading `--` (the flat-JSON and namespaced-Tailwind key).
pub fn bare_name(name: &str) -> &str {
    name.strip_prefix("--").unwrap_or(name)
}

/// The `var(--...)` reference to the custom property `name`.
pub fn var_ref(name: &str) -> String {
    format!("var({name})")
}

/// The Tailwind theme key of a scale step: the full token name without `--` when `namespaced`,
/// else the bare formatted step (`8`, `6_5`).
pub fn scale_key(step_key: &str, token_name: &str, namespaced: bool) -> String {
    if namespaced {
        bare_name(token_name).to_owned()
    } else {
        step_key.to_owned()
    }
}
