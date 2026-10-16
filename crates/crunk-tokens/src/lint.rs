//! Pure analyses over an authored [`TokenSet`] that the TOKEN lint rules report: naming, mode
//! completeness, tier skips, near-duplicate values, deprecated references and property scopes.
//!
//! Nothing here reads a file; the rules in `crunk-rules` feed in the compiled set and the
//! `var(--name)` references the stylesheets make.

// frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8

use std::collections::BTreeSet;

use crunk_values::Color;

use crate::model::{Scope, Tier, Token, TokenSet, TokenValue};

/// The tier a leading path segment names, when it names one.
fn tier_of_segment(segment: &str) -> Option<Tier> {
    match segment {
        "primitive" => Some(Tier::Primitive),
        "semantic" => Some(Tier::Semantic),
        "component" => Some(Tier::Component),
        _ => None,
    }
}

/// True for lowercase ASCII words joined by single hyphens (`ink`, `on-surface-2`).
pub fn is_kebab(segment: &str) -> bool {
    !segment.is_empty()
        && segment.split('-').all(|word| {
            !word.is_empty()
                && word
                    .chars()
                    .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit())
        })
}

/// Why `token`'s authored path breaks the naming convention (kebab-case segments; a leading
/// `primitive`, `semantic` or `component` segment must match the token's tier), if it does.
pub fn naming_issue(token: &Token) -> Option<String> {
    if let Some(bad) = token.key.split('.').find(|s| !is_kebab(s)) {
        return Some(format!("path segment `{bad}` is not kebab-case"));
    }
    let first = token.key.split('.').next().unwrap_or_default();
    let named = tier_of_segment(first)?;
    (named != token.tier).then(|| {
        format!(
            "the `{first}` prefix does not match its {:?} tier",
            token.tier
        )
        .to_lowercase()
    })
}

/// Every token with a naming issue, with the reason.
pub fn naming_issues(set: &TokenSet) -> Vec<(&Token, String)> {
    set.iter()
        .filter_map(|t| naming_issue(t).map(|why| (t, why)))
        .collect()
}

/// Tokens that override some mode but not every mode the set declares, with the modes they lack.
pub fn mode_gaps(set: &TokenSet) -> Vec<(&Token, Vec<String>)> {
    let all = set.mode_names();
    set.iter()
        .filter(|t| !t.modes.is_empty())
        .filter_map(|t| {
            let missing: Vec<String> = all
                .iter()
                .filter(|m| !t.modes.contains_key(**m))
                .map(|m| (*m).to_owned())
                .collect();
            (!missing.is_empty()).then_some((t, missing))
        })
        .collect()
}

/// The custom property names a value references, directly (an alias or a composite member).
fn alias_targets(value: &TokenValue) -> Vec<&str> {
    match value {
        TokenValue::Alias(t) => vec![t.as_str()],
        TokenValue::Composite(members) => members.values().flat_map(alias_targets).collect(),
        _ => Vec::new(),
    }
}

/// Every `(referrer, target)` alias edge of the set, over the default value and every mode.
pub fn alias_edges(set: &TokenSet) -> Vec<(&Token, &str)> {
    set.iter()
        .flat_map(|t| {
            std::iter::once(&t.value)
                .chain(t.modes.values())
                .flat_map(alias_targets)
                .map(move |target| (t, target))
        })
        .collect()
}

/// Component-tier tokens that alias a primitive directly, skipping the semantic layer.
pub fn tier_skips(set: &TokenSet) -> Vec<(&Token, &Token)> {
    alias_edges(set)
        .into_iter()
        .filter(|(from, _)| from.tier == Tier::Component)
        .filter_map(|(from, to)| set.get(to).map(|t| (from, t)))
        .filter(|(_, to)| to.tier == Tier::Primitive)
        .collect()
}

/// Tokens nothing refers to: not aliased by another token and not among `used` (the custom
/// properties the stylesheets read through `var()`).
pub fn unused<'a>(set: &'a TokenSet, used: &BTreeSet<String>) -> Vec<&'a Token> {
    let aliased: BTreeSet<&str> = alias_edges(set).into_iter().map(|(_, to)| to).collect();
    set.iter()
        .filter(|t| !aliased.contains(t.name.as_str()) && !used.contains(&t.name))
        .collect()
}

/// Pairs of tokens with different names and a near-identical literal value: colours within
/// `tolerance` of each other, and identical dimensions or durations. Aliases are skipped (they
/// repeat their target by design).
pub fn near_duplicates(set: &TokenSet, tolerance: f64) -> Vec<(&Token, &Token)> {
    let literals: Vec<&Token> = set
        .iter()
        .filter(|t| !matches!(t.value, TokenValue::Alias(_)))
        .collect();
    let mut found = Vec::new();
    for (i, a) in literals.iter().enumerate() {
        for b in &literals[i + 1..] {
            if values_alike(&a.value, &b.value, tolerance) {
                found.push((*a, *b));
            }
        }
    }
    found
}

fn values_alike(a: &TokenValue, b: &TokenValue, tolerance: f64) -> bool {
    match (a, b) {
        (TokenValue::Color(x), TokenValue::Color(y)) => Color::distance(*x, *y) <= tolerance,
        (TokenValue::Dimension { .. }, TokenValue::Dimension { .. })
        | (TokenValue::Duration(_), TokenValue::Duration(_)) => a == b,
        _ => false,
    }
}

/// The scope a CSS property binds (`margin` is spacing, `color` is color), when it is one the
/// model scopes.
pub fn scope_of_property(property: &str) -> Option<Scope> {
    let p = property.to_ascii_lowercase();
    if p == "color" || p == "fill" || p == "stroke" || p == "background" || p.ends_with("-color") {
        return Some(Scope::Color);
    }
    if p == "gap" || p.ends_with("-gap") || p.starts_with("margin") || p.starts_with("padding") {
        return Some(Scope::Spacing);
    }
    match p.as_str() {
        "font-size" => Some(Scope::FontSize),
        "font-family" => Some(Scope::FontFamily),
        "z-index" => Some(Scope::ZIndex),
        "width" | "height" | "min-width" | "min-height" | "max-width" | "max-height" => {
            Some(Scope::Size)
        }
        _ if p.ends_with("radius") => Some(Scope::Radius),
        _ => None,
    }
}

/// True when `token` may bind `scope`: it declares no scopes, or declares that one.
pub fn allows_scope(token: &Token, scope: Scope) -> bool {
    token.scopes.is_empty() || token.scopes.contains(&scope)
}

/// The byte offset of the line that introduces the token at dotted `key` in `text` (its table
/// header or its `name =` line), or 0 when it cannot be found.
pub fn offset_of(text: &str, key: &str) -> usize {
    let last = key.rsplit('.').next().unwrap_or(key);
    let mut at = 0;
    for line in text.split_inclusive('\n') {
        let trimmed = line.trim();
        let header = trimmed
            .strip_prefix('[')
            .and_then(|r| r.strip_suffix(']'))
            .map(|h| h.trim().replace('"', ""));
        let hit = header.as_deref() == Some(key)
            || (header.is_none()
                && trimmed
                    .strip_prefix(last)
                    .is_some_and(|rest| rest.trim_start().starts_with('=')));
        if hit {
            return at;
        }
        at += line.len();
    }
    0
}
