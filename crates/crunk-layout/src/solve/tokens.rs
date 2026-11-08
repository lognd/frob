//! Computed token bindings: which `var(--token)` each property of a node uses.

// frob:ticket 01M5XCWYB9M2YSJ5EGABMREX1B

use std::collections::BTreeMap;

/// Property name to the first token name (without `--`) its value references.
pub(crate) fn token_bindings(decls: &[(String, String)]) -> BTreeMap<String, String> {
    decls
        .iter()
        .filter_map(|(prop, value)| {
            first_token(value).map(|t| (prop.trim().to_ascii_lowercase(), t.to_owned()))
        })
        .collect()
}

/// The name of the first `var(--name` in `value`, without the dashes.
fn first_token(value: &str) -> Option<&str> {
    let rest = &value[value.find("var(")? + 4..];
    let rest = rest.trim_start().strip_prefix("--")?;
    let end = rest.find([',', ')']).unwrap_or(rest.len());
    let name = rest[..end].trim();
    (!name.is_empty()).then_some(name)
}
