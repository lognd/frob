//! The words a rule may name, with their types: the compiler's view of the relation catalog.
//!
//! Web-engine kinds come from [`crate::catalog`]; the core kinds, flags, verbs, side relations
//! and built-in functions of grl-spec.md section 6 are listed here until the full catalog
//! (~CDMAECH) absorbs them. Every lookup goes through this module so that swap is one place.

use crate::catalog::{self, FieldType};
use crate::grl::ast::{LiteralKind, TypeKind};

/// The static type of a GRL term, as far as the checker can tell.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) enum Ty {
    /// Text.
    Str,
    /// A whole number.
    Int,
    /// A decimal.
    Float,
    /// A boolean.
    Bool,
    /// A compiled regular expression.
    Regex,
    /// A glob pattern.
    Glob,
    /// A `const_value` answer (may be Unknown).
    Const,
    /// A `class_tokens` answer.
    Tokens,
    /// A list of one element type.
    List(Box<Ty>),
    /// A node of a kind (`None` when the kind is not known statically).
    Node(Option<&'static str>),
    /// A node-valued field such as `.callee` or `.target`: text as written plus parts.
    Ref,
    /// A row of a side relation, a vocabulary or anything the checker does not model.
    Any,
}

impl Ty {
    /// The type as a phrase for a message ("a string", "an integer").
    pub(super) fn phrase(&self) -> &'static str {
        match self {
            Self::Str => "a string",
            Self::Int => "an integer",
            Self::Float => "a decimal number",
            Self::Bool => "a boolean",
            Self::Regex => "a regex",
            Self::Glob => "a glob",
            Self::List(_) => "a list",
            Self::Const => "a constant answer",
            Self::Tokens => "a class-token answer",
            Self::Node(_) | Self::Ref => "a node",
            Self::Any => "a value",
        }
    }

    /// Whether the type is one the checker can contradict (others are never a mismatch).
    pub(super) fn is_concrete(&self) -> bool {
        matches!(
            self,
            Self::Str
                | Self::Int
                | Self::Float
                | Self::Bool
                | Self::Regex
                | Self::Glob
                | Self::List(_)
        )
    }

    /// Whether the type is a number.
    pub(super) fn is_numeric(&self) -> bool {
        matches!(self, Self::Int | Self::Float)
    }

    /// Whether values of the two types may be compared or matched.
    pub(super) fn compatible(&self, other: &Self) -> bool {
        if !self.is_concrete() || !other.is_concrete() {
            return true;
        }
        match (self, other) {
            (Self::List(a), Self::List(b)) => a.compatible(b),
            (a, b) => a == b || (a.is_numeric() && b.is_numeric()),
        }
    }
}

/// The type of a knob declared `knob n: TYPE`.
pub(super) fn knob_ty(ty: &TypeKind) -> Ty {
    match ty {
        TypeKind::Int => Ty::Int,
        TypeKind::Float => Ty::Float,
        TypeKind::String => Ty::Str,
        TypeKind::Bool => Ty::Bool,
        TypeKind::Glob => Ty::Glob,
        TypeKind::Regex => Ty::Regex,
        TypeKind::Vocab => Ty::Any,
        TypeKind::List(inner) => Ty::List(Box::new(knob_ty(&inner.node))),
    }
}

/// The type of a literal.
pub(super) fn literal_ty(lit: &LiteralKind) -> Ty {
    match lit {
        LiteralKind::Int(_) => Ty::Int,
        LiteralKind::Decimal(_) => Ty::Float,
        LiteralKind::Str(_) => Ty::Str,
        LiteralKind::Regex(_) => Ty::Regex,
        LiteralKind::Bool(_) => Ty::Bool,
        LiteralKind::List(items) => Ty::List(Box::new(
            items
                .first()
                .map_or(Ty::Any, |first| literal_ty(&first.node)),
        )),
        LiteralKind::Call { .. } => Ty::Any,
    }
}

/// The languages whose adapters answer a kind.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(super) enum Langs {
    /// Every language.
    All,
    /// Programming languages: everything except data, prose and style files.
    Code,
    /// Exactly these language ids.
    Only(&'static [&'static str]),
}

/// Language ids that are data, prose or style rather than code.
const NON_CODE: &[&str] = &[
    "css", "scss", "html", "markdown", "toml", "json", "yaml", "text",
];

impl Langs {
    /// Whether the language `lang` answers the kind (unknown ids count as code).
    pub(super) fn answers(self, lang: &str) -> bool {
        match self {
            Self::All => true,
            Self::Code => !NON_CODE.contains(&lang),
            Self::Only(ids) => ids.contains(&lang),
        }
    }

    /// Where the kind is answered, as a phrase for help text.
    pub(super) fn describe(self) -> String {
        match self {
            Self::All => "every language".into(),
            Self::Code => "code languages (not data, prose or style files)".into(),
            Self::Only(ids) => ids.join(", "),
        }
    }
}

/// A kind a rule can name: its extra fields beyond the common ones, and where it is answered.
#[derive(Debug, Clone)]
pub(super) struct KindInfo {
    /// The kind word.
    pub(super) word: &'static str,
    /// Fields specific to the kind.
    pub(super) extra: Vec<(&'static str, Ty)>,
    /// The languages that answer it.
    pub(super) langs: Langs,
}

/// Fields every kind has (grl-spec.md section 6).
const COMMON: &[(&str, Ty)] = &[
    ("name", Ty::Str),
    ("text", Ty::Str),
    ("line", Ty::Int),
    ("file", Ty::Ref),
    ("path", Ty::Str),
    ("kind", Ty::Str),
    ("role", Ty::Str),
    ("unit", Ty::Ref),
    ("doc", Ty::Str),
];

/// Fields of a node-valued field (`.callee.name`, `.target.anchor`, `.file.path`).
const REF_FIELDS: &[(&str, Ty)] = &[
    ("name", Ty::Str),
    ("text", Ty::Str),
    ("path", Ty::Str),
    ("anchor", Ty::Str),
    ("scheme", Ty::Str),
    ("kind", Ty::Str),
    ("line", Ty::Int),
    ("file", Ty::Ref),
    ("lang", Ty::Str),
];

/// Core kinds: (word, extra fields, languages). Sorted by word.
fn core_kinds() -> Vec<KindInfo> {
    let k = |word, extra: Vec<(&'static str, Ty)>, langs| KindInfo { word, extra, langs };
    vec![
        k("artifact", vec![], Langs::All),
        k("assignment", vec![], Langs::Code),
        k("branch", vec![], Langs::Code),
        k(
            "call",
            vec![("callee", Ty::Ref), ("args", Ty::Any)],
            Langs::Code,
        ),
        k(
            "cell",
            vec![
                ("node", Ty::Ref),
                ("atom", Ty::Str),
                ("observed", Ty::Bool),
                ("granted", Ty::Bool),
                ("excused", Ty::Bool),
            ],
            Langs::All,
        ),
        k("comment", vec![], Langs::All),
        k("directive", vec![], Langs::All),
        k("effect_use", vec![], Langs::All),
        k("excuse", vec![], Langs::All),
        k("fence", vec![], Langs::Only(&["markdown"])),
        k("field", vec![], Langs::Code),
        k("file", vec![], Langs::All),
        k(
            "function",
            vec![("params", Ty::Any), ("returns", Ty::Ref)],
            Langs::Code,
        ),
        k("grant", vec![], Langs::All),
        k(
            "heading",
            vec![("level", Ty::Int), ("slug", Ty::Str)],
            Langs::Only(&["markdown"]),
        ),
        k("import", vec![("target", Ty::Ref)], Langs::Code),
        k(
            "key",
            vec![("value", Ty::Const)],
            Langs::Only(&["toml", "json", "yaml"]),
        ),
        k(
            "link",
            vec![("target", Ty::Ref)],
            Langs::Only(&["markdown"]),
        ),
        k("literal", vec![("value", Ty::Const)], Langs::All),
        k("loop", vec![], Langs::Code),
        k(
            "method",
            vec![("params", Ty::Any), ("returns", Ty::Ref)],
            Langs::Code,
        ),
        k("module", vec![], Langs::Code),
        k("node", vec![], Langs::All),
        k("param", vec![], Langs::Code),
        k("stmt", vec![], Langs::Code),
        k("table", vec![], Langs::Only(&["markdown"])),
        k("test", vec![], Langs::Code),
        k("type", vec![], Langs::Code),
        k("unit", vec![], Langs::Code),
    ]
}

/// Every kind a rule can name: the core kinds plus the catalog's web-engine kinds.
pub(super) fn kinds() -> Vec<KindInfo> {
    let mut all = core_kinds();
    for k in catalog::KINDS {
        all.push(KindInfo {
            word: k.word,
            extra: k
                .fields
                .iter()
                .map(|f| {
                    (
                        f.name,
                        match f.ty {
                            FieldType::Str => Ty::Str,
                            FieldType::Bool => Ty::Bool,
                            FieldType::Const => Ty::Const,
                            FieldType::Tokens => Ty::Tokens,
                        },
                    )
                })
                .collect(),
            langs: Langs::Only(k.languages),
        });
    }
    all.sort_by_key(|k| k.word);
    all
}

/// The kind named `word`.
pub(super) fn kind(word: &str) -> Option<KindInfo> {
    kinds().into_iter().find(|k| k.word == word)
}

/// The type of field `name` on a node of `kind` (`None` kind: any kind has it); `None` if no such field.
pub(super) fn field(kind: Option<&str>, name: &str) -> Option<Ty> {
    let from = |k: &KindInfo| k.extra.iter().find(|f| f.0 == name).map(|f| f.1.clone());
    let specific = match kind {
        Some(w) => self::kind(w).and_then(|k| from(&k)),
        None => kinds().iter().find_map(from),
    };
    specific.or_else(|| COMMON.iter().find(|f| f.0 == name).map(|f| f.1.clone()))
}

/// The field names of a kind (kind-specific first, then the common ones).
pub(super) fn field_names(kind: Option<&str>) -> Vec<&'static str> {
    let mut names: Vec<&'static str> = match kind {
        Some(w) => self::kind(w)
            .map(|k| k.extra.iter().map(|f| f.0).collect())
            .unwrap_or_default(),
        None => kinds()
            .iter()
            .flat_map(|k| k.extra.iter().map(|f| f.0))
            .collect(),
    };
    names.extend(COMMON.iter().map(|f| f.0));
    names.dedup();
    names
}

/// The type of field `name` of a node-valued field.
pub(super) fn ref_field(name: &str) -> Option<Ty> {
    REF_FIELDS.iter().find(|f| f.0 == name).map(|f| f.1.clone())
}

/// The field names of a node-valued field.
pub(super) fn ref_field_names() -> Vec<&'static str> {
    REF_FIELDS.iter().map(|f| f.0).collect()
}

/// Words that follow `is` besides kinds: boolean fields and checks.
pub(super) const FLAGS: &[&str] = &["async", "exported", "public", "relative", "valid_glob"];

/// The edge verbs of the catalog (multi-word verbs with single spaces).
pub(super) const VERBS: &[&str] = &[
    "calls",
    "extends",
    "imports",
    "instantiates",
    "owned by",
    "peer of",
    "references",
    "resolves to",
    "tests",
];

/// Roots of side-relation paths.
pub(super) const SIDE_ROOTS: &[&str] = &["config", "diff", "lease", "model"];

/// The fixed side relations (config tables are typed later from the config schema, ~CDMAECH).
pub(super) const SIDE_RELATIONS: &[&str] = &[
    "diff.added",
    "diff.changed",
    "lease.globs",
    "lease.ticket",
    "model.nodes",
    "model.selectors",
];

/// Built-in function names.
pub(super) const FUNCTIONS: &[&str] = &["glob", "resolve", "slug", "valid_glob", "vocab"];

/// The result type of the built-in function `name`.
pub(super) fn function_ty(name: &str) -> Option<Ty> {
    match name {
        "glob" => Some(Ty::Glob),
        "resolve" | "slug" => Some(Ty::Str),
        "valid_glob" => Some(Ty::Bool),
        "vocab" => Some(Ty::Any),
        _ => None,
    }
}

/// Whether `path` (dotted) names a known side relation; `config.*` accepts any table.
pub(super) fn side_relation_known(segments: &[&str]) -> bool {
    match segments {
        ["config", _, ..] => true,
        [root, second] => SIDE_RELATIONS.contains(&format!("{root}.{second}").as_str()),
        _ => false,
    }
}

/// The closest candidate to `word` (Damerau-Levenshtein within a third of its length), if any.
pub(super) fn suggest<'a>(
    word: &str,
    candidates: impl IntoIterator<Item = &'a str>,
) -> Option<&'a str> {
    if word.len() < 3 {
        return None;
    }
    let limit = (word.len() / 3).max(1);
    candidates
        .into_iter()
        .filter(|c| *c != word)
        .map(|c| (distance(word, c), c))
        .filter(|(d, _)| *d <= limit)
        .min_by_key(|(d, _)| *d)
        .map(|(_, c)| c)
}

/// Optimal-string-alignment distance: edits are insert, delete, substitute, adjacent swap.
fn distance(a: &str, b: &str) -> usize {
    let (a, b): (Vec<char>, Vec<char>) = (a.chars().collect(), b.chars().collect());
    let mut d = vec![vec![0usize; b.len() + 1]; a.len() + 1];
    for (i, row) in d.iter_mut().enumerate() {
        row[0] = i;
    }
    for (j, cell) in d[0].iter_mut().enumerate() {
        *cell = j;
    }
    for i in 1..=a.len() {
        for j in 1..=b.len() {
            let cost = usize::from(a[i - 1] != b[j - 1]);
            d[i][j] = (d[i - 1][j] + 1)
                .min(d[i][j - 1] + 1)
                .min(d[i - 1][j - 1] + cost);
            if i > 1 && j > 1 && a[i - 1] == b[j - 2] && a[i - 2] == b[j - 1] {
                d[i][j] = d[i][j].min(d[i - 2][j - 2] + 1);
            }
        }
    }
    d[a.len()][b.len()]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn suggestions_catch_swaps_and_ignore_short_words() {
        let words: Vec<&str> = kinds().iter().map(|k| k.word).collect();
        assert_eq!(suggest("tset", words.iter().copied()), Some("test"));
        assert_eq!(suggest("g", words.iter().copied()), None);
        assert_eq!(suggest("zzzzzz", words.iter().copied()), None);
    }

    #[test]
    fn kinds_are_sorted_unique_and_fields_resolve() {
        let all = kinds();
        assert!(all.windows(2).all(|w| w[0].word < w[1].word));
        assert_eq!(field(Some("function"), "name"), Some(Ty::Str));
        assert_eq!(field(Some("function"), "line"), Some(Ty::Int));
        assert_eq!(field(Some("function"), "callee"), None);
        assert_eq!(field(None, "callee"), Some(Ty::Ref));
        assert_eq!(field(Some("element"), "tag"), Some(Ty::Str));
    }

    #[test]
    fn language_answers() {
        assert!(!Langs::Code.answers("css"));
        assert!(Langs::Code.answers("rust"));
        assert!(Langs::Only(&["markdown"]).answers("markdown"));
    }
}
