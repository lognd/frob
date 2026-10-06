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
        #[cfg(feature = "python")]
        Language::Python => Some(tree_sitter_python::LANGUAGE.into()),
        #[cfg(feature = "csharp")]
        Language::CSharp => Some(tree_sitter_c_sharp::LANGUAGE.into()),
        #[cfg(feature = "typescript")]
        Language::TypeScript => Some(tree_sitter_typescript::LANGUAGE_TYPESCRIPT.into()),
        #[cfg(feature = "tsx")]
        Language::Tsx => Some(tree_sitter_typescript::LANGUAGE_TSX.into()),
        #[cfg(feature = "javascript")]
        Language::JavaScript => Some(tree_sitter_javascript::LANGUAGE.into()),
        #[cfg(feature = "jsx")]
        Language::Jsx => Some(tree_sitter_javascript::LANGUAGE.into()),
        #[cfg(feature = "css")]
        Language::Css => Some(tree_sitter_css::LANGUAGE.into()),
        #[cfg(feature = "html")]
        Language::Html => Some(tree_sitter_html::LANGUAGE.into()),
        #[allow(unreachable_patterns)]
        _ => None,
    }
}

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
/// Returns `(grammar crate name, exact pinned version)` for `language`, or
/// `None` for a language scanned without a grammar (YAML).
pub(crate) const fn pin(language: Language) -> Option<(&'static str, &'static str)> {
    match language {
        Language::Rust => Some(("tree-sitter-rust", "0.24.2")),
        Language::Markdown => Some(("tree-sitter-md", "0.5.3")),
        Language::Toml => Some(("tree-sitter-toml-ng", "0.7.0")),
        Language::Yaml => None,
        Language::Python => Some(("tree-sitter-python", "0.25.0")),
        Language::CSharp => Some(("tree-sitter-c-sharp", "0.23.5")),
        Language::TypeScript | Language::Tsx => Some(("tree-sitter-typescript", "0.23.2")),
        Language::JavaScript | Language::Jsx => Some(("tree-sitter-javascript", "0.25.0")),
        Language::Css => Some(("tree-sitter-css", "0.25.0")),
        Language::Html => Some(("tree-sitter-html", "0.23.2")),
    }
}

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
/// Identity string for the grammar of `language`, for cache keys.
///
/// Combines the language name, grammar crate and version, the grammar ABI
/// version and the tree-sitter core version, so any grammar or core change
/// invalidates caches. A disabled feature yields an `unavailable` identity.
pub fn grammar_identity(language: Language) -> String {
    let Some((krate, version)) = pin(language) else {
        return format!("{}:line-scanner", language.name());
    };
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

    #[cfg(all(feature = "typescript", feature = "tsx"))]
    #[test]
    fn typescript_and_tsx_share_a_crate_but_not_an_identity() {
        let (ts, tsx) = (
            grammar_identity(Language::TypeScript),
            grammar_identity(Language::Tsx),
        );
        assert!(ts.contains("tree-sitter-typescript@0.23.2"), "{ts}");
        assert!(tsx.contains("tree-sitter-typescript@0.23.2"), "{tsx}");
        assert_ne!(ts, tsx);
    }

    /// The hard-coded pins must match the exact requirements in Cargo.toml,
    /// so a version bump cannot silently keep the old identity.
    #[test]
    fn pins_match_cargo_toml() {
        let manifest = include_str!("../Cargo.toml");
        let mut expected = vec![format!("tree-sitter = \"={CORE_VERSION}\"")];
        for l in Language::ALL {
            let Some((krate, ver)) = pin(l) else {
                continue;
            };
            expected.push(format!("{krate} = {{ version = \"={ver}\""));
        }
        for e in expected {
            assert!(manifest.contains(&e), "Cargo.toml missing `{e}`");
        }
    }
}
