//! The [`Language`] enum and path detection.

use std::path::Path;

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
// frob:ticket 01M43A5DJT8XBQYEK36F0KSGKF
// frob:ticket 01M5HW48KRXEE8ARBE3N2JPRYH
/// A language this crate can (feature permitting) parse.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Language {
    /// Rust source (`.rs`).
    Rust,
    /// Markdown block structure (`.md`, `.markdown`).
    Markdown,
    /// TOML (`.toml`).
    Toml,
    /// YAML (`.yml`, `.yaml`, and Unity `.prefab`); comments and keys only, no tree-sitter grammar.
    Yaml,
    /// Python source (`.py`, `.pyi`).
    Python,
    /// C# source (`.cs`; `.csx` scripts are not C# files).
    CSharp,
    /// TypeScript source (`.ts`, `.mts`, `.cts`).
    TypeScript,
    /// TypeScript with JSX (`.tsx`).
    Tsx,
    /// JavaScript source (`.js`, `.mjs`, `.cjs`).
    JavaScript,
    /// JavaScript with JSX (`.jsx`).
    Jsx,
    /// CSS stylesheets (`.css`, and Unity `.uss` / `.tss`).
    Css,
    /// HTML documents (`.html`, `.htm`, and Unity `.uxml`).
    Html,
    /// `.grmb` design models (`.grmb`); hand-written parser, no tree-sitter grammar.
    Grmb,
}

impl Language {
    /// Every variant, regardless of enabled features.
    pub const ALL: [Language; 13] = [
        Language::Rust,
        Language::Markdown,
        Language::Toml,
        Language::Yaml,
        Language::Python,
        Language::CSharp,
        Language::TypeScript,
        Language::Tsx,
        Language::JavaScript,
        Language::Jsx,
        Language::Css,
        Language::Html,
        Language::Grmb,
    ];

    /// Detects the language from the file extension (case-insensitive).
    pub fn detect(path: impl AsRef<Path>) -> Option<Language> {
        let ext = path
            .as_ref()
            .extension()
            .and_then(gob_path::exact_text)?
            .to_ascii_lowercase();
        let found = match ext.as_str() {
            "rs" => Some(Language::Rust),
            "md" | "markdown" => Some(Language::Markdown),
            "toml" => Some(Language::Toml),
            "yml" | "yaml" | "prefab" => Some(Language::Yaml),
            "py" | "pyi" => Some(Language::Python),
            "cs" => Some(Language::CSharp),
            "ts" | "mts" | "cts" => Some(Language::TypeScript),
            "tsx" => Some(Language::Tsx),
            "js" | "mjs" | "cjs" => Some(Language::JavaScript),
            "jsx" => Some(Language::Jsx),
            "css" | "uss" | "tss" => Some(Language::Css),
            "html" | "htm" | "uxml" => Some(Language::Html),
            "grmb" => Some(Language::Grmb),
            _ => None,
        };
        tracing::trace!(path = ?path.as_ref(), ?found, "language detect");
        found
    }

    /// Stable lowercase name, used in cache keys and diagnostics.
    pub const fn name(self) -> &'static str {
        match self {
            Language::Rust => "rust",
            Language::Markdown => "markdown",
            Language::Toml => "toml",
            Language::Yaml => "yaml",
            Language::Python => "python",
            Language::CSharp => "csharp",
            Language::TypeScript => "typescript",
            Language::Tsx => "tsx",
            Language::JavaScript => "javascript",
            Language::Jsx => "jsx",
            Language::Css => "css",
            Language::Html => "html",
            Language::Grmb => crate::grmb::NAME,
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
        assert_eq!(Language::detect("a.py"), Some(Language::Python));
        assert_eq!(Language::detect("a.PYI"), Some(Language::Python));
        assert_eq!(Language::detect("Player.cs"), Some(Language::CSharp));
        assert_eq!(Language::detect("Player.CS"), Some(Language::CSharp));
        assert_eq!(Language::detect("script.csx"), None);
        assert_eq!(Language::detect("a.ts"), Some(Language::TypeScript));
        assert_eq!(Language::detect("a.d.mts"), Some(Language::TypeScript));
        assert_eq!(Language::detect("App.TSX"), Some(Language::Tsx));
        assert_eq!(Language::detect("a.mjs"), Some(Language::JavaScript));
        assert_eq!(Language::detect("a.jsx"), Some(Language::Jsx));
        assert_eq!(Language::detect("site.css"), Some(Language::Css));
        assert_eq!(Language::detect("index.HTML"), Some(Language::Html));
        assert_eq!(Language::detect("a.htm"), Some(Language::Html));
        assert_eq!(Language::detect("ui/Main.USS"), Some(Language::Css));
        assert_eq!(Language::detect("theme.tss"), Some(Language::Css));
        assert_eq!(Language::detect("ui/Main.uxml"), Some(Language::Html));
        assert_eq!(Language::detect("design/frob.grmb"), Some(Language::Grmb));
        assert_eq!(Language::detect("X.GRMB"), Some(Language::Grmb));
        assert_eq!(Language::Grmb.name(), "grmb");
        assert_eq!(Language::detect("ui/Hud.prefab"), Some(Language::Yaml));
        assert_eq!(Language::detect("Hud.PREFAB"), Some(Language::Yaml));
        assert_eq!(Language::detect("a.scss"), None);
        assert_eq!(Language::detect("a.pyc"), None);
        assert_eq!(Language::detect("Makefile"), None);
    }

    // frob:tests crates/gob-languages/src/language.rs::Language
    #[test]
    fn prefab_files_are_detected_as_yaml() {
        assert_eq!(Language::detect("Assets/Hud.prefab"), Some(Language::Yaml));
        assert_eq!(Language::detect("Hud.Prefab"), Some(Language::Yaml));
        assert_eq!(Language::detect("Hud.prefab.meta"), None);
    }

    #[test]
    fn names_are_distinct() {
        assert_eq!(Language::Rust.name(), "rust");
        assert_eq!(Language::Markdown.name(), "markdown");
        assert_eq!(Language::Toml.name(), "toml");
        assert_eq!(Language::Python.name(), "python");
        let mut names: Vec<_> = Language::ALL.iter().map(|l| l.name()).collect();
        names.sort_unstable();
        names.dedup();
        assert_eq!(names.len(), Language::ALL.len());
    }
}
