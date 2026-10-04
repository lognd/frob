//! Token naming: the one home of every custom-property name crunk emits, parameterized by the
//! spec's `[tokens]` prefix configuration.

// frob:ticket 01M43ARX764095Q4VWABWXXV5H

use crate::model::TokensConfig;

/// Lowercase `name` and collapse runs of CSS-ident-illegal characters to `-`.
///
/// The spec guarantees palette and layer names are TOML-key-safe, which is not the same as
/// CSS-ident-safe (spaces, dots); this is the fallback for a name that would otherwise produce
/// an invalid custom property.
pub fn sanitize_ident(name: &str) -> String {
    let mut out = String::with_capacity(name.len());
    let mut in_run = false;
    for ch in name.to_lowercase().chars() {
        if ch.is_ascii_alphanumeric() || ch == '_' || ch == '-' {
            out.push(ch);
            in_run = false;
        } else if !in_run {
            out.push('-');
            in_run = true;
        }
    }
    out
}

/// Render a scale step as a CSS-ident-safe name segment (`6.5` becomes `6_5`).
///
/// Whole steps drop the fraction (`16.0` becomes `16`). Rust never prints an exponent, so a
/// step below `1e-4` renders positionally where Python would print `1e-05`.
#[allow(
    clippy::float_cmp,
    reason = "a step is whole exactly when it equals its truncation"
)]
pub fn format_step(value: f64) -> String {
    if value == 0.0 {
        "0".to_owned()
    } else if value == value.trunc() && value.abs() < 1e15 {
        format!("{value:.0}")
    } else {
        value.to_string().replace('.', "_")
    }
}

fn prefixed(prefix: &str, ident: &str) -> String {
    if prefix.is_empty() {
        format!("--{ident}")
    } else {
        format!("--{prefix}-{ident}")
    }
}

/// Full `--...` custom property name for palette entry `name`.
pub fn color_token(cfg: &TokensConfig, name: &str) -> String {
    prefixed(&cfg.color, &sanitize_ident(name))
}

/// Full `--...` custom property name for a spacing scale step.
pub fn space_token(cfg: &TokensConfig, step: f64) -> String {
    prefixed(&cfg.space, &format_step(step))
}

/// Full `--...` custom property name for a font-size scale step.
pub fn font_size_token(cfg: &TokensConfig, step: f64) -> String {
    prefixed(&cfg.font_size, &format_step(step))
}

/// Full `--...` custom property name for a radius scale step.
pub fn radius_token(cfg: &TokensConfig, step: f64) -> String {
    prefixed(&cfg.radius, &format_step(step))
}

/// Full `--...` custom property name for a sizes scale step (naming only, for SIZE001's
/// suggestions; `sizes` do not join the tokens export).
pub fn size_token(cfg: &TokensConfig, step: f64) -> String {
    prefixed(&cfg.size, &format_step(step))
}

/// Full `--...` custom property name for layer entry `name`.
pub fn layer_token(cfg: &TokensConfig, name: &str) -> String {
    prefixed(&cfg.layer, &sanitize_ident(name))
}

/// Full `--...` custom property name for the single `base` font-family stack.
pub fn font_family_token(cfg: &TokensConfig) -> String {
    prefixed(&cfg.font_family, "base")
}

/// Full `--...` name for one declared `[typography.stacks]` entry.
pub fn font_family_stack_token(cfg: &TokensConfig, stack_name: &str) -> String {
    prefixed(&cfg.font_family, &sanitize_ident(stack_name))
}

/// The `var(--...)` namespace prefixes COLOR002 recognizes as token-shaped.
///
/// Ordinarily one `--<prefix>-` string per configured family. Any empty prefix makes namespace
/// boundaries ambiguous (an empty-prefix token is just `--<ident>`), so the set collapses to the
/// single umbrella namespace `--`.
pub fn token_namespaces(cfg: &TokensConfig) -> Vec<String> {
    let prefixes = [
        &cfg.color,
        &cfg.space,
        &cfg.font_size,
        &cfg.radius,
        &cfg.layer,
        &cfg.font_family,
    ];
    if prefixes.iter().any(|p| p.is_empty()) {
        return vec!["--".to_owned()];
    }
    prefixes.iter().map(|p| format!("--{p}-")).collect()
}
