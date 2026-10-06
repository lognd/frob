//! [`Lang`]: the closed list of built-in languages and pseudo-languages.

/// A built-in language or pseudo-language; one row of the [`crate::MATRIX`].
///
/// Discriminants are the row indexes of the matrix, so keep declaration order in step with it
/// (a const assertion in `matrix.rs` enforces this).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Lang {
    /// Rust.
    Rust,
    /// Python.
    Python,
    /// C#.
    CSharp,
    /// TypeScript, covering `.ts`, `.tsx`, `.js` and `.jsx`.
    TypeScript,
    /// CSS.
    Css,
    /// HTML.
    Html,
    /// Markdown.
    Markdown,
    /// YAML.
    Yaml,
    /// TOML.
    Toml,
    /// The grimble model language (`.grmb`).
    Grmb,
    /// Pseudo-language: text with no adapter.
    OpaqueText,
    /// Pseudo-language: bytes that are not text (every cell not-applicable).
    Binary,
}

impl Lang {
    /// Every language, in matrix row order.
    pub const ALL: [Self; 12] = [
        Self::Rust,
        Self::Python,
        Self::CSharp,
        Self::TypeScript,
        Self::Css,
        Self::Html,
        Self::Markdown,
        Self::Yaml,
        Self::Toml,
        Self::Grmb,
        Self::OpaqueText,
        Self::Binary,
    ];

    /// The canonical lowercase tag (`rust`, `opaque-text`), as GRL `lang` and packs spell it.
    pub const fn name(self) -> &'static str {
        match self {
            Self::Rust => "rust",
            Self::Python => "python",
            Self::CSharp => "csharp",
            Self::TypeScript => "typescript",
            Self::Css => "css",
            Self::Html => "html",
            Self::Markdown => "markdown",
            Self::Yaml => "yaml",
            Self::Toml => "toml",
            Self::Grmb => "grmb",
            Self::OpaqueText => "opaque-text",
            Self::Binary => "binary",
        }
    }

    /// Parses a canonical name or a known alias (`opaque`, `tsx`, `jsx`, `javascript`); `None`
    /// for anything else (extension spellings are resolved by the caller's own vocabulary).
    pub fn from_tag(tag: &str) -> Option<Self> {
        Self::ALL
            .into_iter()
            .find(|l| l.name() == tag)
            .or(match tag {
                "opaque" => Some(Self::OpaqueText),
                "tsx" | "jsx" | "javascript" => Some(Self::TypeScript),
                _ => None,
            })
    }
}
