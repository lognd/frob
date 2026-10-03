//! The [`Language`] enum and path detection.

use std::path::Path;

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
/// A language this crate can (feature permitting) parse.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Language {
    /// Rust source (`.rs`).
    Rust,
    /// Markdown block structure (`.md`, `.markdown`).
    Markdown,
    /// TOML (`.toml`).
    Toml,
    /// YAML (`.yml`, `.yaml`); comments and keys only, no tree-sitter grammar.
    Yaml,
}

impl Language {
    /// Every variant, regardless of enabled features.
    pub const ALL: [Language; 4] = [
        Language::Rust,
        Language::Markdown,
        Language::Toml,
        Language::Yaml,
    ];

    /// Detects the language from the file extension (case-insensitive).
    pub fn detect(path: impl AsRef<Path>) -> Option<Language> {
        let ext = path.as_ref().extension()?.to_str()?.to_ascii_lowercase();
        let found = match ext.as_str() {
            "rs" => Some(Language::Rust),
            "md" | "markdown" => Some(Language::Markdown),
            "toml" => Some(Language::Toml),
            "yml" | "yaml" => Some(Language::Yaml),
            _ => None,
        };
        tracing::trace!(path = %path.as_ref().display(), ?found, "language detect");
        found
    }

    /// Stable lowercase name, used in cache keys and diagnostics.
    pub const fn name(self) -> &'static str {
        match self {
            Language::Rust => "rust",
            Language::Markdown => "markdown",
            Language::Toml => "toml",
            Language::Yaml => "yaml",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_by_extension() {
        assert_eq!(Language::detect("a/b.rs"), Some(Language::Rust));
        assert_eq!(Language::detect("README.MD"), Some(Language::Markdown));
        assert_eq!(Language::detect("x.markdown"), Some(Language::Markdown));
        assert_eq!(Language::detect("frob.toml"), Some(Language::Toml));
        assert_eq!(Language::detect("a.py"), None);
        assert_eq!(Language::detect("Makefile"), None);
    }

    #[test]
    fn names_are_distinct() {
        assert_eq!(Language::Rust.name(), "rust");
        assert_eq!(Language::Markdown.name(), "markdown");
        assert_eq!(Language::Toml.name(), "toml");
    }
}
