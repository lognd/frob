//! The GRL relation catalog: every word a rule can name, with its fields, the
//! universal query that answers it and the languages that implement that query
//! (grl-spec.md section 6, language-engines.md section 5).
//!
//! This milestone lists the web-engine kinds (`element`, `attribute`,
//! `style_rule`, `declaration`, `custom_property`) and the derived
//! `class_tokens` query; the core kinds join as their adapters land. The
//! catalog is data, so [`render`] generates the reference page from the same
//! table the compiler reads.

use std::fmt::Write as _;

/// The type of a field, as the catalog page shows it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FieldType {
    /// Text.
    Str,
    /// A boolean flag.
    Bool,
    /// A `const_value` answer: Known, `OneOf`, Fragments or Unknown.
    Const,
    /// A `class_tokens` answer: Known tokens plus a dynamic remainder.
    Tokens,
}

impl FieldType {
    /// The type's name on the catalog page.
    pub const fn name(self) -> &'static str {
        match self {
            Self::Str => "string",
            Self::Bool => "bool",
            Self::Const => "const_value",
            Self::Tokens => "class_tokens",
        }
    }
}

/// One field of a kind.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Field {
    /// The field name without the leading dot.
    pub name: &'static str,
    /// Its type.
    pub ty: FieldType,
    /// One example value, as written in a rule.
    pub example: &'static str,
    /// Whether the answer can be Unknown (a dynamic value, a spread).
    pub may_be_unknown: bool,
}

/// One kind a rule can name.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Kind {
    /// The kind word.
    pub word: &'static str,
    /// The universal query that answers it (universal-model.md 5.1).
    pub query: &'static str,
    /// The language ids whose adapters implement the query.
    pub languages: &'static [&'static str],
    /// A one-line summary.
    pub summary: &'static str,
    /// The fields, in catalog order.
    pub fields: &'static [Field],
}

impl Kind {
    /// The field called `name`.
    pub fn field(&self, name: &str) -> Option<&'static Field> {
        self.fields.iter().find(|f| f.name == name)
    }

    /// Whether the language `lang` answers this kind.
    pub fn answered_in(&self, lang: &str) -> bool {
        self.languages.contains(&lang)
    }
}

const fn field(
    name: &'static str,
    ty: FieldType,
    example: &'static str,
    may_be_unknown: bool,
) -> Field {
    Field {
        name,
        ty,
        example,
        may_be_unknown,
    }
}

/// Languages whose adapters lower markup (language-engines.md section 2).
const MARKUP_LANGS: &[&str] = &["tsx", "jsx", "html"];
/// Languages whose adapters lower stylesheets.
const STYLE_LANGS: &[&str] = &["css", "scss"];
/// Languages that also lower inline style objects.
const DECL_LANGS: &[&str] = &["css", "scss", "tsx", "jsx"];

/// The kinds of the catalog, sorted by word.
pub const KINDS: &[Kind] = &[
    Kind {
        word: "attribute",
        query: "Q48 markup",
        languages: MARKUP_LANGS,
        summary: "an attribute of an element; a spread is an attribute at status May",
        fields: &[
            field("name", FieldType::Str, "\"alt\"", false),
            field("value", FieldType::Const, "\"logo\"", true),
            field("spread", FieldType::Bool, "true", false),
            field("tokens", FieldType::Tokens, "class_tokens", true),
        ],
    },
    Kind {
        word: "custom_property",
        query: "Q49 style",
        languages: STYLE_LANGS,
        summary: "a custom property definition such as `--gap: 8px`",
        fields: &[
            field("name", FieldType::Str, "\"--gap\"", false),
            field("value", FieldType::Str, "\"8px\"", false),
        ],
    },
    Kind {
        word: "declaration",
        query: "Q49 style",
        languages: DECL_LANGS,
        summary: "a declaration `property: value`, also from inline style objects",
        fields: &[
            field("property", FieldType::Str, "\"margin\"", false),
            field("value", FieldType::Str, "\"0 auto\"", false),
            field("important", FieldType::Bool, "true", false),
        ],
    },
    Kind {
        word: "element",
        query: "Q48 markup",
        languages: MARKUP_LANGS,
        summary: "a markup element: tag, attributes, children",
        fields: &[
            field("tag", FieldType::Str, "\"img\"", true),
            field("kind", FieldType::Str, "\"component\"", false),
            field("tokens", FieldType::Tokens, "class_tokens", true),
        ],
    },
    Kind {
        word: "style_rule",
        query: "Q49 style",
        languages: STYLE_LANGS,
        summary: "a style rule with its selector",
        fields: &[field("selector", FieldType::Str, "\".card\"", false)],
    },
];

/// The kind named `word`, if the catalog has it.
pub fn kind(word: &str) -> Option<&'static Kind> {
    KINDS.iter().find(|k| k.word == word)
}

/// The catalog page (markdown), generated from [`KINDS`].
pub fn render() -> String {
    let mut out = String::from("# GRL relation catalog: web-engine kinds\n");
    for k in KINDS {
        let _ = write!(
            out,
            "\n## `{}`\n\n{}.\n\nQuery: {}. Languages: {}.\n\n| Field | Type | Example | Unknown |\n|---|---|---|---|\n",
            k.word,
            k.summary,
            k.query,
            k.languages.join(", ")
        );
        for f in k.fields {
            let _ = writeln!(
                out,
                "| `.{}` | {} | `{}` | {} |",
                f.name,
                f.ty.name(),
                f.example,
                if f.may_be_unknown { "may" } else { "never" }
            );
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn catalog_is_sorted_and_names_query_and_languages() {
        assert!(KINDS.windows(2).all(|w| w[0].word < w[1].word));
        for k in KINDS {
            assert!(!k.query.is_empty() && !k.languages.is_empty(), "{}", k.word);
            assert!(!k.fields.is_empty(), "{}", k.word);
        }
        for w in [
            "element",
            "attribute",
            "style_rule",
            "declaration",
            "custom_property",
        ] {
            assert!(kind(w).is_some(), "{w}");
        }
        assert!(kind("tset").is_none());
    }

    #[test]
    fn render_lists_every_kind_and_field() {
        let page = render();
        for k in KINDS {
            assert!(page.contains(&format!("## `{}`", k.word)));
            for f in k.fields {
                assert!(page.contains(&format!("| `.{}` |", f.name)));
            }
        }
        assert!(page.is_ascii());
    }
}
