//! The one mapping from the three language vocabularies to [`Lang`] (D107).
//!
//! The vocabularies are [`gob_languages::Language`] (grammar detection), [`LanguageHint`]
//! (the walker's extension guess) and an adapter tag ([`crate::Adapter::language`]). All three
//! reduce to a tag, and [`lang_of_tag`] is the single table.

// frob:ticket 01M48R002DA5FKCXDP8HQ6B02X

use gob_caps::Lang;
use gob_languages::Language;
use gob_walk::LanguageHint;

/// Maps a tag to its [`Lang`]: a canonical name or alias, else a file extension; `None` if unknown.
pub fn lang_of_tag(tag: &str) -> Option<Lang> {
    let found = Lang::from_tag(tag).or_else(|| {
        let ext = tag.trim_start_matches('.').to_ascii_lowercase();
        Language::detect(format!("x.{ext}")).map(lang_of_language)
    });
    tracing::trace!(tag, ?found, "lang_of_tag");
    found
}

/// Maps a grammar [`Language`] to its [`Lang`] (tsx, jsx and javascript fold into TypeScript).
pub fn lang_of_language(language: Language) -> Lang {
    match language {
        Language::Rust => Lang::Rust,
        Language::Markdown => Lang::Markdown,
        Language::Toml => Lang::Toml,
        Language::Yaml => Lang::Yaml,
        Language::Python => Lang::Python,
        Language::CSharp => Lang::CSharp,
        Language::TypeScript | Language::Tsx | Language::JavaScript | Language::Jsx => {
            Lang::TypeScript
        }
        Language::Css => Lang::Css,
        Language::Html => Lang::Html,
    }
}

/// Maps a walker [`LanguageHint`] to its [`Lang`]; `None` for an unknown extension.
pub fn lang_of_hint(hint: &LanguageHint) -> Option<Lang> {
    lang_of_tag(hint.tag())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{adapters, opaque_adapter};

    #[test]
    // frob:tests crates/gob-symbols/src/lang.rs::lang_of_language
    fn every_grammar_language_maps() {
        for l in Language::ALL {
            let lang = lang_of_language(l);
            let want = match l {
                Language::Rust => Lang::Rust,
                Language::Markdown => Lang::Markdown,
                Language::Toml => Lang::Toml,
                Language::Yaml => Lang::Yaml,
                Language::Python => Lang::Python,
                Language::CSharp => Lang::CSharp,
                Language::TypeScript | Language::Tsx | Language::JavaScript | Language::Jsx => {
                    Lang::TypeScript
                }
                Language::Css => Lang::Css,
                Language::Html => Lang::Html,
            };
            assert_eq!(lang, want, "{l:?}");
        }
    }

    #[test]
    // frob:tests crates/gob-symbols/src/lang.rs::lang_of_hint
    fn walker_hints_map() {
        assert_eq!(lang_of_hint(&LanguageHint::Rust), Some(Lang::Rust));
        assert_eq!(lang_of_hint(&LanguageHint::Markdown), Some(Lang::Markdown));
        assert_eq!(lang_of_hint(&LanguageHint::Toml), Some(Lang::Toml));
        for (ext, want) in [
            ("py", Lang::Python),
            ("ts", Lang::TypeScript),
            ("jsx", Lang::TypeScript),
            ("css", Lang::Css),
            ("yml", Lang::Yaml),
            ("cs", Lang::CSharp),
            ("htm", Lang::Html),
        ] {
            assert_eq!(
                lang_of_hint(&LanguageHint::from_path(&format!("a.{ext}"))),
                Some(want),
                "{ext}"
            );
        }
        assert_eq!(lang_of_hint(&LanguageHint::from_path("Makefile")), None);
        assert_eq!(lang_of_hint(&LanguageHint::from_path("a.zzz")), None);
    }

    #[test]
    // frob:tests crates/gob-symbols/src/lang.rs::lang_of_tag
    fn adapter_tags_map_and_pseudo_tags_resolve() {
        for a in adapters().into_iter().chain([opaque_adapter()]) {
            assert!(lang_of_tag(a.language()).is_some(), "{}", a.language());
        }
        assert_eq!(lang_of_tag("grmb"), Some(Lang::Grmb));
        assert_eq!(lang_of_tag("opaque"), Some(Lang::OpaqueText));
        assert_eq!(lang_of_tag("opaque-text"), Some(Lang::OpaqueText));
        assert_eq!(lang_of_tag("binary"), Some(Lang::Binary));
        assert_eq!(lang_of_tag("cobol"), None);
    }

    #[test]
    // frob:tests crates/gob-symbols/src/adapter.rs::CapabilityDecl.for_lang
    fn each_adapter_declares_exactly_its_matrix_row() {
        for a in adapters().into_iter().chain([opaque_adapter()]) {
            let lang = lang_of_tag(a.language()).expect("adapter tag maps");
            let row = gob_caps::row(lang);
            assert_eq!(a.fidelity(), row.fidelity, "{}", a.language());
            let decl = a.capabilities();
            for c in gob_caps::Capability::ALL {
                assert_eq!(
                    decl.precision(c),
                    row.cell(c),
                    "{} {}",
                    a.language(),
                    c.name()
                );
            }
        }
    }
}
