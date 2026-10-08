//! The GRL relation catalog: everything a rule can name, in one place (grl-spec.md section 6,
//! language-engines.md section 5).
//!
//! Kinds carry their fields, universal query, an Unknown-capable flag per field and the languages
//! that answer them, keyed on the `gob_caps` matrix ([`Answers`]); verbs, flags, built-in
//! functions, fixed side relations ([`SIDE_RELATIONS`]) and per-language comment markers
//! ([`comment_markers`]) sit beside them, and `config.<table>` is typed from the config JSON
//! schema ([`ConfigSchema`]). The compiler's checks read this module and nothing else, and
//! [`render`] generates the reference page from the same tables.

mod answer;
mod config;
mod words;

use std::fmt::Write as _;

use gob_caps::{Capability, Lang};

pub use answer::{Answers, comment_markers, lang_of};
pub use config::{ConfigNode, ConfigSchema};
pub use words::{
    Column, FLAGS, FUNCTIONS, Flag, Function, SIDE_RELATIONS, SIDE_ROOTS, SideRelation, VERBS,
    Verb, function, side_relation, verb,
};

/// The type of a field, as the catalog page shows it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FieldType {
    /// Text.
    Str,
    /// A whole number.
    Int,
    /// A decimal number.
    Float,
    /// A boolean flag.
    Bool,
    /// A glob pattern.
    Glob,
    /// A `const_value` answer: Known, `OneOf`, Fragments or Unknown.
    Const,
    /// A `class_tokens` answer: Known tokens plus a dynamic remainder.
    Tokens,
    /// A node-valued field: the text as written plus its parts (`.callee.name`).
    Ref,
    /// A list, table or vocabulary the checker does not look into.
    Any,
}

impl FieldType {
    /// The type's name on the catalog page.
    pub const fn name(self) -> &'static str {
        match self {
            Self::Str => "string",
            Self::Int => "int",
            Self::Float => "float",
            Self::Bool => "bool",
            Self::Glob => "glob",
            Self::Const => "const_value",
            Self::Tokens => "class_tokens",
            Self::Ref => "node",
            Self::Any => "any",
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
    /// Where the kind is answered, keyed on the `gob_caps` matrix.
    pub answers: Answers,
    /// A one-line summary.
    pub summary: &'static str,
    /// The fields beyond the common ones, in catalog order.
    pub fields: &'static [Field],
}

impl Kind {
    /// The field called `name` among the kind's own fields.
    pub fn field(&self, name: &str) -> Option<&'static Field> {
        self.fields.iter().find(|f| f.name == name)
    }

    /// Whether the language id `lang` (as written after `lang` in a rule) answers this kind.
    pub fn answered_in(&self, lang: &str) -> bool {
        self.answers.answered_in(lang)
    }

    /// Whether the matrix language `lang` answers this kind.
    pub fn answered_by(&self, lang: Lang) -> bool {
        self.answers.answered_by(lang)
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

const fn kind_of(
    word: &'static str,
    query: &'static str,
    answers: Answers,
    summary: &'static str,
    fields: &'static [Field],
) -> Kind {
    Kind {
        word,
        query,
        answers,
        summary,
        fields,
    }
}

/// Fields every kind has (grl-spec.md section 6).
pub const COMMON_FIELDS: &[Field] = &[
    field("name", FieldType::Str, "\"main\"", false),
    field("text", FieldType::Str, "\"x\"", false),
    field("line", FieldType::Int, "12", false),
    field("file", FieldType::Ref, "f.file", false),
    field("path", FieldType::Str, "\"src/lib.rs\"", false),
    field("kind", FieldType::Str, "\"component\"", false),
    field("role", FieldType::Str, "\"function\"", false),
    field("unit", FieldType::Ref, "c.unit", false),
    field("doc", FieldType::Str, "\"Adds.\"", false),
];

/// Fields of a node-valued field (`.callee.name`, `.target.anchor`, `.file.path`).
pub const REF_FIELDS: &[Field] = &[
    field("name", FieldType::Str, "\"exit\"", false),
    field("text", FieldType::Str, "\"sys.exit\"", false),
    field("path", FieldType::Str, "\"docs/a.md\"", false),
    field("anchor", FieldType::Str, "\"intro\"", false),
    field("scheme", FieldType::Str, "\"https\"", false),
    field("kind", FieldType::Str, "\"file\"", false),
    field("line", FieldType::Int, "3", false),
    field("file", FieldType::Ref, "l.target.file", false),
    field("lang", FieldType::Str, "\"rust\"", false),
];

const MARKUP: Answers = Answers::Capability(Capability::Markup);
const STYLE: Answers = Answers::Capability(Capability::Style);
const PROSE: Answers = Answers::Langs(&[Lang::Markdown], &[]);
const DATA: Answers = Answers::Langs(&[Lang::Yaml, Lang::Toml], &["json"]);

const CALLABLE: &[Field] = &[
    field("params", FieldType::Any, "params", false),
    field("returns", FieldType::Ref, "returns", false),
];

/// The kinds of the catalog, sorted by word.
pub const KINDS: &[Kind] = &[
    kind_of(
        "artifact",
        "Q01",
        Answers::Everywhere,
        "a file or other artifact",
        &[],
    ),
    kind_of(
        "assignment",
        "Q16",
        Answers::Code,
        "an assignment statement",
        &[],
    ),
    kind_of(
        "attribute",
        "Q48 markup",
        MARKUP,
        "an attribute of an element; a spread is an attribute at status May",
        &[
            field("name", FieldType::Str, "\"alt\"", false),
            field("value", FieldType::Const, "\"logo\"", true),
            field("spread", FieldType::Bool, "true", false),
            field("tokens", FieldType::Tokens, "class_tokens", true),
        ],
    ),
    kind_of(
        "branch",
        "Q16",
        Answers::Code,
        "a branching construct (U role)",
        &[],
    ),
    kind_of(
        "call",
        "Q13, Q20",
        Answers::Code,
        "a call; `.callee` is the callee as written, `.callee.name` its last segment",
        &[
            field("callee", FieldType::Ref, "\"exit\"", false),
            field("args", FieldType::Any, "args", false),
        ],
    ),
    kind_of(
        "cell",
        "binding.md 7",
        Answers::Everywhere,
        "a cell of the capability matrix, computed by the engine",
        &[
            field("node", FieldType::Ref, "node", false),
            field("atom", FieldType::Str, "\"fs.read\"", false),
            field("observed", FieldType::Bool, "true", false),
            field("granted", FieldType::Bool, "true", false),
            field("excused", FieldType::Bool, "true", false),
        ],
    ),
    kind_of("comment", "Q10", Answers::Everywhere, "a comment", &[]),
    kind_of(
        "custom_property",
        "Q49 style",
        STYLE,
        "a custom property definition such as `--gap: 8px`",
        &[
            field("name", FieldType::Str, "\"--gap\"", false),
            field("value", FieldType::Str, "\"8px\"", false),
        ],
    ),
    kind_of(
        "declaration",
        "Q49 style",
        STYLE,
        "a declaration `property: value`, also from inline style objects",
        &[
            field("property", FieldType::Str, "\"margin\"", false),
            field("value", FieldType::Str, "\"0 auto\"", false),
            field("important", FieldType::Bool, "true", false),
        ],
    ),
    kind_of(
        "directive",
        "gob-directives",
        Answers::Everywhere,
        "a directive such as `directive \"todo\"`",
        &[],
    ),
    kind_of(
        "effect_use",
        "Q34",
        Answers::Everywhere,
        "a use of an effect atom",
        &[],
    ),
    kind_of(
        "element",
        "Q48 markup",
        MARKUP,
        "a markup element: tag, attributes, children",
        &[
            field("tag", FieldType::Str, "\"img\"", true),
            field("kind", FieldType::Str, "\"component\"", false),
            field("tokens", FieldType::Tokens, "class_tokens", true),
        ],
    ),
    kind_of(
        "excuse",
        "Q36",
        Answers::Everywhere,
        "an excuse for a capability",
        &[],
    ),
    kind_of("fence", "Q11", PROSE, "a fenced code block", &[]),
    kind_of("field", "Q15", Answers::Code, "a field of a type", &[]),
    kind_of(
        "file",
        "Q02",
        Answers::Everywhere,
        "an artifact with text",
        &[],
    ),
    kind_of(
        "function",
        "Q15",
        Answers::Code,
        "a function; `is public`, `is async` where the language has them",
        CALLABLE,
    ),
    kind_of(
        "grant",
        "Q36",
        Answers::Everywhere,
        "a capability grant",
        &[],
    ),
    kind_of(
        "heading",
        "Q11",
        PROSE,
        "a markdown heading",
        &[
            field("level", FieldType::Int, "2", false),
            field("slug", FieldType::Str, "\"intro\"", false),
        ],
    ),
    kind_of(
        "import",
        "Q12",
        Answers::Code,
        "an import",
        &[field("target", FieldType::Ref, "\"std::fs\"", false)],
    ),
    kind_of(
        "key",
        "Q19",
        DATA,
        "a TOML, JSON or YAML key; `key(path = \"/jobs/*\")` addresses by key path",
        &[field("value", FieldType::Const, "\"on\"", true)],
    ),
    kind_of(
        "link",
        "Q11",
        PROSE,
        "a link; `.target` is the destination as written",
        &[field("target", FieldType::Ref, "\"a.md#x\"", false)],
    ),
    kind_of(
        "literal",
        "Q14",
        Answers::Everywhere,
        "a literal",
        &[field("value", FieldType::Const, "\"x\"", true)],
    ),
    kind_of(
        "loop",
        "Q16",
        Answers::Code,
        "a loop construct (U role)",
        &[],
    ),
    kind_of("method", "Q15", Answers::Code, "a method", CALLABLE),
    kind_of("module", "Q15", Answers::Code, "a module", &[]),
    kind_of(
        "node",
        "Q36",
        Answers::Everywhere,
        "a grimble model node",
        &[],
    ),
    kind_of("param", "Q15", Answers::Code, "a parameter", &[]),
    kind_of("stmt", "Q16", Answers::Code, "a statement", &[]),
    kind_of(
        "style_rule",
        "Q49 style",
        STYLE,
        "a style rule with its selector",
        &[field("selector", FieldType::Str, "\".card\"", false)],
    ),
    kind_of("table", "Q11", PROSE, "a markdown table", &[]),
    kind_of(
        "test",
        "Q35",
        Answers::Code,
        "a test; NotApplicable where a language has no test convention",
        &[],
    ),
    kind_of("type", "Q15", Answers::Code, "a type declaration", &[]),
    kind_of("unit", "Q04", Answers::Code, "a unit of code", &[]),
];

/// The kind named `word`, if the catalog has it.
pub fn kind(word: &str) -> Option<&'static Kind> {
    KINDS.iter().find(|k| k.word == word)
}

/// The catalog page (markdown), generated from the tables.
pub fn render() -> String {
    let mut out = String::from("# GRL relation catalog\n");
    out.push_str("\n## Common fields\n\n");
    push_fields(&mut out, COMMON_FIELDS);
    for k in KINDS {
        let _ = write!(
            out,
            "\n## `{}`\n\n{}.\n\nQuery: {}. Languages: {}.\n\n",
            k.word,
            k.summary,
            k.query,
            k.answers.describe()
        );
        push_fields(&mut out, k.fields);
    }
    out.push_str("\n## Verbs\n\n| Verb | Query | Meaning |\n|---|---|---|\n");
    for v in VERBS {
        let _ = writeln!(out, "| `{}` | {} | {} |", v.word, v.query, v.summary);
    }
    out.push_str("\n## Flags\n\n| Flag | Query | Unknown |\n|---|---|---|\n");
    for f in FLAGS {
        let _ = writeln!(
            out,
            "| `is {}` | {} | {} |",
            f.word,
            f.query,
            if f.may_be_unknown { "may" } else { "never" }
        );
    }
    out.push_str("\n## Functions\n\n| Call | Returns |\n|---|---|\n");
    for f in FUNCTIONS {
        let _ = writeln!(out, "| `{}` | {} |", f.signature, f.ty_name());
    }
    out.push_str(
        "\n## Side relations\n\n| Relation | Reads | Source | Columns |\n|---|---|---|---|\n",
    );
    for s in SIDE_RELATIONS {
        let cols: Vec<String> = s
            .columns
            .iter()
            .map(|(n, t)| format!("{n}: {}", t.name()))
            .collect();
        let _ = writeln!(
            out,
            "| `{}` | `{}` | {} | {} |",
            s.name,
            s.reads,
            s.source,
            cols.join(", ")
        );
    }
    out.push_str("\n## Comment markers\n\n| Language | Markers |\n|---|---|\n");
    for l in Lang::ALL {
        let _ = writeln!(out, "| {} | {} |", l.name(), comment_markers(l).join(" "));
    }
    out
}

fn push_fields(out: &mut String, fields: &[Field]) {
    if fields.is_empty() {
        return;
    }
    out.push_str("| Field | Type | Example | Unknown |\n|---|---|---|---|\n");
    for f in fields {
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn catalog_is_sorted_and_every_kind_has_a_query() {
        assert!(KINDS.windows(2).all(|w| w[0].word < w[1].word));
        for k in KINDS {
            assert!(!k.query.is_empty(), "{}", k.word);
        }
        assert!(kind("tset").is_none());
    }

    #[test]
    fn every_word_of_spec_section_6_is_a_kind() {
        for w in [
            "artifact",
            "file",
            "unit",
            "function",
            "method",
            "type",
            "module",
            "field",
            "param",
            "test",
            "call",
            "import",
            "comment",
            "literal",
            "stmt",
            "branch",
            "loop",
            "assignment",
            "heading",
            "link",
            "fence",
            "table",
            "key",
            "element",
            "attribute",
            "style_rule",
            "declaration",
            "custom_property",
            "directive",
            "effect_use",
            "node",
            "grant",
            "excuse",
            "cell",
        ] {
            assert!(kind(w).is_some(), "{w}");
        }
    }

    #[test]
    fn answers_follow_the_capability_matrix() {
        assert!(kind("element").unwrap().answered_by(Lang::Html));
        assert!(!kind("element").unwrap().answered_by(Lang::Rust));
        assert!(!kind("test").unwrap().answered_in("css"));
        assert!(kind("test").unwrap().answered_in("rust"));
        assert!(kind("key").unwrap().answered_in("json"));
    }

    #[test]
    fn render_lists_every_kind_field_verb_and_side_relation() {
        let page = render();
        for k in KINDS {
            assert!(page.contains(&format!("## `{}`", k.word)));
            for f in k.fields {
                assert!(page.contains(&format!("| `.{}` |", f.name)));
            }
        }
        for v in VERBS {
            assert!(page.contains(&format!("| `{}` |", v.word)));
        }
        for s in SIDE_RELATIONS {
            assert!(page.contains(&format!("| `{}` |", s.name)));
        }
        assert!(page.is_ascii());
    }
}
