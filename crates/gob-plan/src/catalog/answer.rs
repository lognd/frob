//! Which languages answer a catalog word, keyed on the `gob_caps` matrix.
//!
//! A word is answered by every language, by code languages, by the languages that provide one
//! capability (markup, style), or by an explicit list. Whether a (word, language) pair is
//! answerable is therefore a static fact (formal review 2026-10-08, sections 2.3 and 3), which
//! GRL018 reads instead of a table of its own.

// frob:ticket 01M3ZX7DMYNTWB3AP04CDMAECH
use gob_caps::{Capability, Lang};

/// Language ids the matrix does not model, with the language whose row answers for them.
const ALIASES: &[(&str, Lang)] = &[
    ("scss", Lang::Css),
    ("sass", Lang::Css),
    ("less", Lang::Css),
    ("text", Lang::OpaqueText),
    ("c#", Lang::CSharp),
    ("ts", Lang::TypeScript),
    ("js", Lang::TypeScript),
];

/// Language ids that are data files the matrix has no row for; they are not code.
const UNMODELLED_DATA: &[&str] = &["json"];

/// The matrix language a rule's `lang` id names, if the matrix models it.
pub fn lang_of(id: &str) -> Option<Lang> {
    Lang::from_tag(id).or_else(|| ALIASES.iter().find(|(a, _)| *a == id).map(|(_, l)| *l))
}

/// The comment introducers of a language, longest-lived first (`//~ warn`, `#~ error`).
pub const fn comment_markers(lang: Lang) -> &'static [&'static str] {
    match lang {
        Lang::Rust | Lang::CSharp | Lang::TypeScript | Lang::Grmb => &["//", "/*"],
        Lang::Python | Lang::Yaml | Lang::Toml => &["#"],
        Lang::Css => &["/*"],
        Lang::Html | Lang::Markdown => &["<!--"],
        Lang::OpaqueText | Lang::Binary => &[],
    }
}

/// Where a catalog word is answered.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Answers {
    /// Every language.
    Everywhere,
    /// Programming languages: not data, prose, style or model files.
    Code,
    /// Languages whose matrix row provides the capability.
    Capability(Capability),
    /// These languages, plus ids the matrix does not model.
    Langs(&'static [Lang], &'static [&'static str]),
}

impl Answers {
    /// Whether the matrix language `lang` answers the word.
    pub fn answered_by(self, lang: Lang) -> bool {
        match self {
            Self::Everywhere => true,
            Self::Code => matches!(
                lang,
                Lang::Rust | Lang::Python | Lang::CSharp | Lang::TypeScript
            ),
            Self::Capability(cap) => gob_caps::provides(lang, cap),
            Self::Langs(langs, _) => langs.contains(&lang),
        }
    }

    /// Whether the language id `id` (as written after `lang`) answers the word.
    ///
    /// Ids the matrix does not model count as code unless they are known data files.
    pub fn answered_in(self, id: &str) -> bool {
        match lang_of(id) {
            Some(l) => self.answered_by(l),
            None => match self {
                Self::Everywhere => true,
                Self::Code => !UNMODELLED_DATA.contains(&id),
                Self::Capability(_) => false,
                Self::Langs(_, ids) => ids.contains(&id),
            },
        }
    }

    /// Where the word is answered, as a phrase for help text.
    pub fn describe(self) -> String {
        match self {
            Self::Everywhere => "every language".into(),
            Self::Code => "code languages (not data, prose or style files)".into(),
            Self::Capability(cap) => {
                let names: Vec<&str> = Lang::ALL
                    .into_iter()
                    .filter(|l| gob_caps::provides(*l, cap))
                    .map(Lang::name)
                    .collect();
                format!(
                    "{} (languages providing `{}`)",
                    names.join(", "),
                    cap.name()
                )
            }
            Self::Langs(langs, ids) => langs
                .iter()
                .map(|l| l.name())
                .chain(ids.iter().copied())
                .collect::<Vec<_>>()
                .join(", "),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn capability_words_follow_the_matrix() {
        let markup = Answers::Capability(Capability::Markup);
        assert!(markup.answered_in("tsx") && markup.answered_in("html"));
        assert!(!markup.answered_in("rust") && !markup.answered_in("css"));
        let style = Answers::Capability(Capability::Style);
        assert!(style.answered_in("scss") && !style.answered_in("markdown"));
    }

    #[test]
    fn code_excludes_data_prose_and_style() {
        assert!(Answers::Code.answered_in("rust") && Answers::Code.answered_in("go"));
        for id in [
            "css", "html", "markdown", "toml", "yaml", "json", "text", "binary",
        ] {
            assert!(!Answers::Code.answered_in(id), "{id}");
        }
    }

    #[test]
    fn explicit_lists_include_unmodelled_ids() {
        let key = Answers::Langs(&[Lang::Yaml, Lang::Toml], &["json"]);
        assert!(key.answered_in("json") && key.answered_in("toml"));
        assert!(!key.answered_in("rust"));
        assert_eq!(key.describe(), "yaml, toml, json");
    }

    #[test]
    fn every_language_has_comment_markers_or_none() {
        assert_eq!(comment_markers(Lang::Python), &["#"]);
        assert!(comment_markers(Lang::Binary).is_empty());
    }
}
