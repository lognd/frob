//! Design-token lookup and `var(--x, fallback)` substitution.

// frob:ticket 01M5XCWXYNXW0RW8VRDQPY31M6

use std::collections::BTreeMap;

/// How deep token-in-token substitution may nest before it counts as a cycle.
const MAX_DEPTH: usize = 32;

/// The resolved design tokens: custom-property name (with `--`) to its value text.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct TokenMap(BTreeMap<String, String>);

impl TokenMap {
    /// An empty token map.
    pub fn new() -> Self {
        Self::default()
    }

    /// Add or replace one token; `name` is the custom property with its leading `--`.
    pub fn insert(&mut self, name: impl Into<String>, value: impl Into<String>) {
        self.0.insert(name.into(), value.into());
    }

    /// The raw value of a token, when defined.
    pub fn get(&self, name: &str) -> Option<&str> {
        self.0.get(name).map(String::as_str)
    }

    /// Build a map from `(name, value)` pairs.
    pub fn from_pairs<N: Into<String>, V: Into<String>>(
        pairs: impl IntoIterator<Item = (N, V)>,
    ) -> Self {
        Self(
            pairs
                .into_iter()
                .map(|(n, v)| (n.into(), v.into()))
                .collect(),
        )
    }
}

/// Why a `var()` could not be substituted.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum VarError {
    /// The token is not defined and has no fallback.
    Undefined(String),
    /// Substitution revisits a token or nests past [`MAX_DEPTH`].
    Cycle(String),
    /// The `var(` call is not well formed.
    Malformed(String),
}

/// Replace every `var(--name[, fallback])` in `text` with the token's value (recursively).
pub(crate) fn resolve_vars(tokens: &TokenMap, text: &str) -> Result<String, VarError> {
    resolve(tokens, text, &mut Vec::new())
}

fn resolve(tokens: &TokenMap, text: &str, stack: &mut Vec<String>) -> Result<String, VarError> {
    let mut out = String::with_capacity(text.len());
    let mut rest = text;
    while let Some(pos) = rest.find("var(") {
        let boundary = rest[..pos]
            .chars()
            .last()
            .is_none_or(|c| !(c.is_ascii_alphanumeric() || c == '-' || c == '_'));
        if !boundary {
            out.push_str(&rest[..pos + 4]);
            rest = &rest[pos + 4..];
            continue;
        }
        out.push_str(&rest[..pos]);
        let args_start = pos + 4;
        let close = matching_paren(&rest[args_start..])
            .ok_or_else(|| VarError::Malformed(format!("unclosed var( in `{text}`")))?;
        let inner = &rest[args_start..args_start + close];
        let (name, fallback) = split_first_comma(inner);
        let name = name.trim();
        if !name.starts_with("--") || name.len() < 3 {
            return Err(VarError::Malformed(format!(
                "`{name}` is not a custom property name"
            )));
        }
        if stack.len() >= MAX_DEPTH || stack.iter().any(|s| s == name) {
            return Err(VarError::Cycle(name.to_owned()));
        }
        let replacement = if let Some(value) = tokens.get(name) {
            stack.push(name.to_owned());
            let r = resolve(tokens, value, stack);
            stack.pop();
            r?
        } else if let Some(fb) = fallback {
            resolve(tokens, fb.trim(), stack)?
        } else {
            return Err(VarError::Undefined(name.to_owned()));
        };
        out.push_str(&replacement);
        rest = &rest[args_start + close + 1..];
    }
    out.push_str(rest);
    Ok(out)
}

/// Byte index of the `)` closing an already-opened paren in `s`.
fn matching_paren(s: &str) -> Option<usize> {
    let mut depth = 0usize;
    for (i, c) in s.char_indices() {
        match c {
            '(' => depth += 1,
            ')' if depth == 0 => return Some(i),
            ')' => depth -= 1,
            _ => {}
        }
    }
    None
}

/// Split at the first comma outside nested parens.
fn split_first_comma(s: &str) -> (&str, Option<&str>) {
    let mut depth = 0usize;
    for (i, c) in s.char_indices() {
        match c {
            '(' => depth += 1,
            ')' => depth = depth.saturating_sub(1),
            ',' if depth == 0 => return (&s[..i], Some(&s[i + 1..])),
            _ => {}
        }
    }
    (s, None)
}
