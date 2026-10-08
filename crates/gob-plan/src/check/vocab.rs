//! The words a rule may name, with their types: the compiler's view of the relation catalog.
//!
//! The words themselves live in [`crate::catalog`]; this module adapts them to the checker's
//! types and holds the typo-suggestion helpers.

use std::rc::Rc;

use crate::catalog::{self, Column, FieldType, Kind, SideRelation};
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
    /// A row of a side relation whose columns are known.
    Row(Rc<Vec<Column>>),
    /// A vocabulary or anything the checker does not model.
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
            Self::Row(_) => "a row",
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

/// The checker's type for a catalog field type.
pub(super) fn ty_of(t: FieldType) -> Ty {
    match t {
        FieldType::Str => Ty::Str,
        FieldType::Int => Ty::Int,
        FieldType::Float => Ty::Float,
        FieldType::Bool => Ty::Bool,
        FieldType::Glob => Ty::Glob,
        FieldType::Const => Ty::Const,
        FieldType::Tokens => Ty::Tokens,
        FieldType::Ref => Ty::Ref,
        FieldType::Any => Ty::Any,
    }
}

/// The kind named `word`.
pub(super) fn kind(word: &str) -> Option<&'static Kind> {
    catalog::kind(word)
}

/// Every kind a rule can name, sorted by word.
pub(super) fn kinds() -> &'static [Kind] {
    catalog::KINDS
}

fn common(name: &str) -> Option<Ty> {
    catalog::COMMON_FIELDS
        .iter()
        .find(|f| f.name == name)
        .map(|f| ty_of(f.ty))
}

/// The type of field `name` on a node of `kind` (`None` kind: any kind has it); `None` if no such field.
pub(super) fn field(kind: Option<&str>, name: &str) -> Option<Ty> {
    let from = |k: &Kind| k.field(name).map(|f| ty_of(f.ty));
    let specific = match kind {
        Some(w) => self::kind(w).and_then(from),
        None => kinds().iter().find_map(from),
    };
    specific.or_else(|| common(name))
}

/// The field names of a kind (kind-specific first, then the common ones).
pub(super) fn field_names(kind: Option<&str>) -> Vec<&'static str> {
    let mut names: Vec<&'static str> = match kind {
        Some(w) => self::kind(w)
            .map(|k| k.fields.iter().map(|f| f.name).collect())
            .unwrap_or_default(),
        None => kinds()
            .iter()
            .flat_map(|k| k.fields.iter().map(|f| f.name))
            .collect(),
    };
    names.extend(catalog::COMMON_FIELDS.iter().map(|f| f.name));
    names.dedup();
    names
}

/// The type of field `name` of a node-valued field.
pub(super) fn ref_field(name: &str) -> Option<Ty> {
    catalog::REF_FIELDS
        .iter()
        .find(|f| f.name == name)
        .map(|f| ty_of(f.ty))
}

/// The field names of a node-valued field.
pub(super) fn ref_field_names() -> Vec<&'static str> {
    catalog::REF_FIELDS.iter().map(|f| f.name).collect()
}

/// Whether `word` is a flag that follows `is`.
pub(super) fn is_flag(word: &str) -> bool {
    catalog::FLAGS.iter().any(|f| f.word == word)
}

/// The flag words, for suggestions.
pub(super) fn flag_names() -> impl Iterator<Item = &'static str> {
    catalog::FLAGS.iter().map(|f| f.word)
}

/// Whether `word` is an edge verb.
pub(super) fn is_verb(word: &str) -> bool {
    catalog::verb(word).is_some()
}

/// The verb words, for suggestions.
pub(super) fn verb_names() -> impl Iterator<Item = &'static str> {
    catalog::VERBS.iter().map(|v| v.word)
}

/// Whether `word` is the root of a side-relation path.
pub(super) fn is_side_root(word: &str) -> bool {
    catalog::SIDE_ROOTS.contains(&word)
}

/// The fixed side-relation names, for suggestions.
pub(super) fn side_relation_names() -> impl Iterator<Item = &'static str> {
    catalog::SIDE_RELATIONS.iter().map(|s| s.name)
}

/// The built-in function names.
pub(super) fn function_names() -> impl Iterator<Item = &'static str> {
    catalog::FUNCTIONS.iter().map(|f| f.name)
}

/// The result type of the built-in function `name`.
pub(super) fn function_ty(name: &str) -> Option<Ty> {
    catalog::function(name).map(|f| ty_of(f.returns))
}

/// The side relation a path of up to two segments names (`diff.changed`), if it is a fixed one.
pub(super) fn fixed_side(segments: &[&str]) -> Option<&'static SideRelation> {
    match segments {
        [root, second] => catalog::side_relation(&format!("{root}.{second}")),
        _ => None,
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
        assert!(kinds().windows(2).all(|w| w[0].word < w[1].word));
        assert_eq!(field(Some("function"), "name"), Some(Ty::Str));
        assert_eq!(field(Some("function"), "line"), Some(Ty::Int));
        assert_eq!(field(Some("function"), "callee"), None);
        assert_eq!(field(None, "callee"), Some(Ty::Ref));
        assert_eq!(field(Some("element"), "tag"), Some(Ty::Str));
    }
}
