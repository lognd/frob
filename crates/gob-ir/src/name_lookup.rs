//! Name-computed lookups: the one place a literal name becomes an origin symbol.
//!
//! A language can reach a symbol by a name it computes at run time: Python `getattr(os, n)`,
//! `__import__(n)`, `importlib.import_module(n)`, `vars(m)[n]`, `m.__dict__[n]`, `sys.modules[n]`;
//! JavaScript `require(n)`, `import(n)`, `obj[n]`; C# `Type.GetType(n)`. Each is a *lookup
//! primitive*: a callee (or index form) plus the position of its name argument. [`primitive`]
//! names the table; [`resolve_name`] turns the bounded static value of the name argument
//! ([`ConstValue`], see `const_value`) into either a literal, which resolves to the origin symbol
//! exactly as the direct form would, or an [`NameGap`], which a consumer must report as
//! Unresolved. Adapters fold the argument into a [`ConstValue`] with their own syntax and call
//! this module; no adapter decides what counts as a literal itself.

// frob:ticket 01M6422ZFEPZJYJQDDM6CV37RW

use crate::const_value::{ConstValue, Fragment, Value};

/// What a lookup primitive does with its name argument.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LookupKind {
    /// Reads attribute `name` of the object argument (`getattr(obj, name)`).
    Attribute,
    /// Imports or loads the module or type called `name` (`__import__`, `require`, `GetType`).
    Import,
    /// Indexes a namespace by `name` (`obj["k"]`, `vars(m)[k]`, `sys.modules[k]`).
    Index,
}

/// One lookup primitive of a language.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Primitive {
    /// The adapter language tag (`python`, `typescript`, `csharp`).
    pub lang: &'static str,
    /// The callee as written; a leading `.` is a method matched on any receiver.
    pub callee: &'static str,
    /// What the primitive does.
    pub kind: LookupKind,
    /// Position of the name argument among the call arguments.
    pub name_arg: usize,
    /// Position of the object argument, when the primitive takes one.
    pub object_arg: Option<usize>,
}

const fn p(
    lang: &'static str,
    callee: &'static str,
    kind: LookupKind,
    name_arg: usize,
    object_arg: Option<usize>,
) -> Primitive {
    Primitive {
        lang,
        callee,
        kind,
        name_arg,
        object_arg,
    }
}

/// Every lookup primitive, by language. Rust has none: its paths are all static.
pub const PRIMITIVES: &[Primitive] = &[
    p("python", "getattr", LookupKind::Attribute, 1, Some(0)),
    p("python", "__import__", LookupKind::Import, 0, None),
    p(
        "python",
        "importlib.import_module",
        LookupKind::Import,
        0,
        None,
    ),
    p("python", "sys.modules", LookupKind::Index, 0, None),
    p("python", "__dict__", LookupKind::Index, 0, None),
    p("python", "vars", LookupKind::Index, 0, None),
    p("python", "globals", LookupKind::Index, 0, None),
    p("python", "locals", LookupKind::Index, 0, None),
    p("typescript", "require", LookupKind::Import, 0, None),
    p("typescript", "import", LookupKind::Import, 0, None),
    p(
        "typescript",
        "Reflect.get",
        LookupKind::Attribute,
        1,
        Some(0),
    ),
    p("csharp", "Type.GetType", LookupKind::Import, 0, None),
    p("csharp", "Assembly.GetType", LookupKind::Import, 0, None),
    p("csharp", "Assembly.Load", LookupKind::Import, 0, None),
    p("csharp", ".GetType", LookupKind::Import, 0, None),
    p("csharp", ".GetMethod", LookupKind::Attribute, 0, None),
    p("csharp", ".GetProperty", LookupKind::Attribute, 0, None),
    p("csharp", ".GetField", LookupKind::Attribute, 0, None),
];

/// The language tag the table is keyed by: `javascript`, `tsx` and `jsx` share `typescript`.
pub fn table_lang(lang: &str) -> &str {
    match lang {
        "javascript" | "tsx" | "jsx" => "typescript",
        other => other,
    }
}

/// The primitive `callee` names in `lang`, if any.
pub fn primitive(lang: &str, callee: &str) -> Option<&'static Primitive> {
    let lang = table_lang(lang);
    PRIMITIVES
        .iter()
        .find(|p| p.lang == lang && p.callee == callee)
}

/// True when `src` mentions any lookup primitive of `lang`; consumers use it to avoid skipping a
/// file whose lookups cannot be matched by a vocabulary name.
pub fn mentions_lookup(lang: &str, src: &str) -> bool {
    let lang = table_lang(lang);
    PRIMITIVES
        .iter()
        .filter(|p| p.lang == lang)
        .any(|p| src.contains(p.callee.trim_start_matches('.')))
}

/// Why a name argument is not a literal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NameGap {
    /// Nothing is known about the name (a parameter, a call result, an input).
    NotConstant,
    /// Part of the name is known, part is computed (an interpolated string).
    Partial,
    /// The name is one of several values (a conditional); each may be reached.
    Several(Vec<String>),
    /// The value is known but is not a string.
    NotString,
}

/// The outcome of a name lookup.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Resolved {
    /// The name is this exact string; the lookup denotes the same symbol as the direct form.
    Literal(String),
    /// The name is not a single literal; the lookup must be reported Unresolved.
    Unresolved(NameGap),
}

/// Classifies the static value of a name argument as a literal or a gap.
pub fn resolve_name(value: &ConstValue) -> Resolved {
    match value {
        ConstValue::Known(Value::Str(s)) => Resolved::Literal(s.clone()),
        ConstValue::Known(_) => Resolved::Unresolved(NameGap::NotString),
        ConstValue::OneOf(vs) => {
            let all: Vec<String> = vs
                .iter()
                .filter_map(|v| match v {
                    Value::Str(s) => Some(s.clone()),
                    _ => None,
                })
                .collect();
            if all.len() == vs.len() {
                Resolved::Unresolved(NameGap::Several(all))
            } else {
                Resolved::Unresolved(NameGap::NotString)
            }
        }
        ConstValue::Fragments(_) => Resolved::Unresolved(NameGap::Partial),
        ConstValue::Unknown => Resolved::Unresolved(NameGap::NotConstant),
    }
}

/// The value of `a + b` for two name parts: known when both are known strings, partial when one
/// is, unknown otherwise. This is the single concatenation rule adapters use for `+`.
pub fn concat(left: &ConstValue, right: &ConstValue) -> ConstValue {
    fn frags(v: &ConstValue) -> Option<Vec<Fragment>> {
        match v {
            ConstValue::Known(Value::Str(s)) => Some(vec![Fragment::Known(s.clone())]),
            ConstValue::Fragments(f) => Some(f.clone()),
            _ => None,
        }
    }
    if let (ConstValue::Known(Value::Str(head)), ConstValue::Known(Value::Str(tail))) =
        (left, right)
    {
        return ConstValue::Known(Value::Str(format!("{head}{tail}")));
    }
    let (Some(mut parts), Some(rest)) = (frags(left), frags(right)) else {
        return ConstValue::Unknown;
    };
    for frag in rest {
        match (parts.last_mut(), frag) {
            (Some(Fragment::Known(head)), Fragment::Known(tail)) => head.push_str(&tail),
            (_, frag) => parts.push(frag),
        }
    }
    ConstValue::Fragments(parts)
}

/// The value of a string literal.
pub fn literal(s: impl Into<String>) -> ConstValue {
    ConstValue::Known(Value::Str(s.into()))
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-ir/src/name_lookup.rs::resolve_name
    #[test]
    fn a_known_string_is_a_literal_and_anything_else_is_a_gap() {
        assert_eq!(resolve_name(&literal("os")), Resolved::Literal("os".into()));
        assert_eq!(
            resolve_name(&ConstValue::Unknown),
            Resolved::Unresolved(NameGap::NotConstant)
        );
        assert_eq!(
            resolve_name(&ConstValue::Known(Value::Int(1))),
            Resolved::Unresolved(NameGap::NotString)
        );
        assert_eq!(
            resolve_name(&ConstValue::Fragments(vec![
                Fragment::Known("o".into()),
                Fragment::Unknown
            ])),
            Resolved::Unresolved(NameGap::Partial)
        );
    }

    // frob:tests crates/gob-ir/src/name_lookup.rs::concat
    #[test]
    fn concatenation_is_literal_only_when_both_sides_are() {
        assert_eq!(concat(&literal("sys"), &literal("tem")), literal("system"));
        assert!(matches!(
            concat(&literal("sys"), &ConstValue::Unknown),
            ConstValue::Unknown
        ));
        let part = ConstValue::Fragments(vec![Fragment::Unknown]);
        assert_eq!(
            resolve_name(&concat(&literal("a"), &part)),
            Resolved::Unresolved(NameGap::Partial)
        );
    }

    // frob:tests crates/gob-ir/src/name_lookup.rs::primitive
    #[test]
    fn every_supported_language_has_primitives_and_rust_has_none() {
        assert!(primitive("python", "getattr").is_some());
        assert!(primitive("javascript", "require").is_some());
        assert!(primitive("csharp", "Type.GetType").is_some());
        assert!(PRIMITIVES.iter().all(|p| p.lang != "rust"));
    }

    // frob:tests crates/gob-ir/src/name_lookup.rs::mentions_lookup
    #[test]
    fn mentions_lookup_finds_primitives_per_language() {
        assert!(mentions_lookup("python", "x = vars(m)[n]"));
        assert!(mentions_lookup("javascript", "require(n)"));
        assert!(!mentions_lookup("rust", "getattr"));
        assert!(!mentions_lookup("python", "print(1)"));
    }
}
