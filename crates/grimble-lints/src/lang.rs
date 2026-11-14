//! Language families shared by the grimble passes, so no pass drops a language silently.
//!
//! Every pass gates on the same two questions: is this file in the TypeScript/JavaScript family
//! (one adapter, one rule table), and is it a programming language at all (so a language the pass
//! cannot judge must be reported Unresolved rather than skipped).

// frob:ticket 01M7AV38AAVKP80JZ6XEW8J39T

use gob_languages::Language;

/// True for the TypeScript family: TypeScript, TSX, JavaScript and JSX share one adapter.
pub fn script_family(language: Language) -> bool {
    matches!(
        language,
        Language::TypeScript | Language::Tsx | Language::JavaScript | Language::Jsx
    )
}

/// True when `language` is a programming language whose code a rule pass should account for.
pub fn is_code(language: Language) -> bool {
    script_family(language)
        || matches!(
            language,
            Language::Rust
                | Language::Python
                | Language::CSharp
                | Language::Go
                | Language::Java
                | Language::C
                | Language::Cpp
                | Language::Zig
                | Language::Cuda
        )
}

/// The language tag the symbol and effects tables use: the whole script family is `typescript`.
pub fn tag(language: Language) -> &'static str {
    if script_family(language) {
        Language::TypeScript.name()
    } else {
        language.name()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/grimble-lints/src/lang.rs::script_family
    #[test]
    fn family_covers_ts_tsx_js_jsx_only() {
        for l in Language::ALL {
            let want = matches!(
                l,
                Language::TypeScript | Language::Tsx | Language::JavaScript | Language::Jsx
            );
            assert_eq!(script_family(l), want, "{l:?}");
        }
    }

    // frob:tests crates/grimble-lints/src/lang.rs::is_code
    #[test]
    fn code_excludes_data_and_markup() {
        assert!(is_code(Language::Go) && is_code(Language::Jsx) && is_code(Language::Cpp));
        assert!(
            !is_code(Language::Markdown) && !is_code(Language::Toml) && !is_code(Language::Css)
        );
    }

    // frob:tests crates/grimble-lints/src/lang.rs::tag
    #[test]
    fn family_shares_the_typescript_tag() {
        assert_eq!(tag(Language::Tsx), "typescript");
        assert_eq!(tag(Language::Jsx), "typescript");
        assert_eq!(tag(Language::Go), "go");
    }
}
