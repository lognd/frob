//! Grammar table (feature gated) and grammar identity strings.

use crate::Language;

/// The pinned `tree-sitter` core version (checked against `Cargo.toml`).
pub(crate) const CORE_VERSION: &str = "0.27.0";

/// Returns the tree-sitter language for `language`, or `None` when its
/// cargo feature is disabled.
pub(crate) fn ts_language(language: Language) -> Option<tree_sitter::Language> {
    match language {
        #[cfg(feature = "rust")]
        Language::Rust => Some(tree_sitter_rust::LANGUAGE.into()),
        #[cfg(feature = "markdown")]
        Language::Markdown => Some(tree_sitter_md::LANGUAGE.into()),
        #[cfg(feature = "toml")]
        Language::Toml => Some(tree_sitter_toml_ng::LANGUAGE.into()),
        #[allow(unreachable_patterns)]
        _ => None,
    }
}

/// Returns `(grammar crate name, exact pinned version)` for `language`.
pub(crate) const fn pin(language: Language) -> (&'static str, &'static str) {
    match language {
        Language::Rust => ("tree-sitter-rust", "0.24.2"),
        Language::Markdown => ("tree-sitter-md", "0.5.3"),
        Language::Toml => ("tree-sitter-toml-ng", "0.7.0"),
    }
}

/// Identity string for the grammar of `language`, for cache keys.
///
/// Combines the language name, grammar crate and version, the grammar ABI
/// version and the tree-sitter core version, so any grammar or core change
/// invalidates caches. A disabled feature yields an `unavailable` identity.
pub fn grammar_identity(language: Language) -> String {
    let (krate, version) = pin(language);
    match ts_language(language) {
        Some(ts) => format!(
            "{}:{krate}@{version}:abi{}:ts{CORE_VERSION}",
            language.name(),
            ts.abi_version()
        ),
        None => format!("{}:{krate}@{version}:unavailable", language.name()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn identity_is_stable_and_distinct() {
        for l in Language::ALL {
            assert_eq!(grammar_identity(l), grammar_identity(l));
        }
        assert_ne!(
            grammar_identity(Language::Rust),
            grammar_identity(Language::Toml)
        );
    }

    #[cfg(feature = "rust")]
    #[test]
    fn identity_names_crate_version_and_abi() {
        let id = grammar_identity(Language::Rust);
        assert!(id.contains("tree-sitter-rust@0.24.2"), "{id}");
        assert!(id.contains(":abi"), "{id}");
        assert!(id.ends_with(&format!(":ts{CORE_VERSION}")), "{id}");
    }

    /// The hard-coded pins must match the exact requirements in Cargo.toml,
    /// so a version bump cannot silently keep the old identity.
    #[test]
    fn pins_match_cargo_toml() {
        let manifest = include_str!("../Cargo.toml");
        let mut expected = vec![format!("tree-sitter = \"={CORE_VERSION}\"")];
        for l in Language::ALL {
            let (krate, ver) = pin(l);
            expected.push(format!("{krate} = {{ version = \"={ver}\""));
        }
        for e in expected {
            assert!(manifest.contains(&e), "Cargo.toml missing `{e}`");
        }
    }
}
