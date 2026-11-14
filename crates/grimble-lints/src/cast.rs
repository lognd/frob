//! `TYPING004`: network or file data cast to a declared type without validation.
//!
//! `await res.json() as User` tells the compiler a shape the runtime never checked. The scan reads
//! the tree of a TypeScript or TSX file and reports an `as T` whose operand is untyped boundary
//! data: a `.json()` call, a `JSON.parse(..)` call, or a name bound from one of those that no
//! validator call (`schema.parse(x)`, `safeParse`, `assert`, `validate`, `decode`) ever receives.
//! `as unknown`, `as any` and `as const` declare no shape and are not reported.

// frob:ticket 01M4D95Q9WWPDZH86CMBMAZEDQ

use std::collections::BTreeSet;

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use gob_text::TextRange;
use tree_sitter::Node;

use crate::res::{ScanError, text};

/// Method names that validate the value they are given (never `JSON.parse`).
const VALIDATORS: &[&str] = &[
    "parse",
    "safeParse",
    "parseAsync",
    "safeParseAsync",
    "assert",
    "validate",
    "validateSync",
    "decode",
    "cast",
];

/// Cast targets that declare no shape.
const SHAPELESS: &[&str] = &["unknown", "any", "const", "never"];

/// How the cast operand was recognised as unvalidated boundary data.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Origin {
    /// The operand is a `.json()` call (a `fetch` body).
    Json,
    /// The operand is a `JSON.parse(..)` call.
    JsonParse,
    /// The operand is a name bound from one of those and never passed to a validator.
    Binding,
}

/// One `as T` cast of unvalidated boundary data.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Site {
    /// The whole `as` expression, as byte offsets in the scanned text.
    pub range: TextRange,
    /// How the operand was recognised.
    pub origin: Origin,
    /// The declared target type, as written.
    pub target: String,
}

/// True for the languages the scan reads (those with `as` casts).
pub fn judged(language: Language) -> bool {
    matches!(language, Language::TypeScript | Language::Tsx)
}

/// Strip parentheses, `await` and `!` wrappers from an expression node.
fn unwrap(mut n: Node<'_>) -> Node<'_> {
    while matches!(
        n.kind(),
        "parenthesized_expression" | "await_expression" | "non_null_expression"
    ) {
        match n.named_child(0) {
            Some(c) => n = c,
            None => break,
        }
    }
    n
}

/// The [`Origin`] of a call expression that yields unvalidated data, if it is one.
fn source_of(n: Node<'_>, src: &str) -> Option<Origin> {
    let n = unwrap(n);
    if n.kind() != "call_expression" {
        return None;
    }
    let f = n.child_by_field_name("function")?;
    if f.kind() != "member_expression" {
        return None;
    }
    let prop = text(f.child_by_field_name("property")?, src);
    let obj = text(f.child_by_field_name("object")?, src);
    match prop {
        "json" => Some(Origin::Json),
        "parse" if obj == "JSON" => Some(Origin::JsonParse),
        _ => None,
    }
}

/// True when `call` is a validator invocation (`schema.parse(x)`, `assert(x)`), not `JSON.parse`.
fn is_validator(call: Node<'_>, src: &str) -> bool {
    let Some(f) = call.child_by_field_name("function") else {
        return false;
    };
    match f.kind() {
        "member_expression" => {
            let prop = f
                .child_by_field_name("property")
                .map(|p| text(p, src))
                .unwrap_or_default();
            let obj = f
                .child_by_field_name("object")
                .map(|o| text(o, src))
                .unwrap_or_default();
            VALIDATORS.contains(&prop) && obj != "JSON"
        }
        "identifier" => VALIDATORS.contains(&text(f, src)),
        _ => false,
    }
}

/// Everything one walk of the tree gathers.
#[derive(Default)]
struct Gathered<'t> {
    /// Names bound from a boundary source.
    bound: BTreeSet<String>,
    /// Names passed as a direct argument to a validator.
    validated: BTreeSet<String>,
    /// Every `as` expression.
    casts: Vec<Node<'t>>,
}

fn gather<'t>(n: Node<'t>, src: &str, g: &mut Gathered<'t>) {
    match n.kind() {
        "variable_declarator" => {
            if let (Some(name), Some(value)) = (
                n.child_by_field_name("name"),
                n.child_by_field_name("value"),
            ) && name.kind() == "identifier"
                && source_of(value, src).is_some()
            {
                g.bound.insert(text(name, src).to_owned());
            }
        }
        "call_expression" if is_validator(n, src) => {
            if let Some(args) = n.child_by_field_name("arguments") {
                let mut cur = args.walk();
                for a in args.named_children(&mut cur) {
                    let a = unwrap(a);
                    if a.kind() == "identifier" {
                        g.validated.insert(text(a, src).to_owned());
                    }
                }
            }
        }
        "as_expression" => g.casts.push(n),
        _ => {}
    }
    let mut cur = n.walk();
    for c in n.children(&mut cur) {
        gather(c, src, g);
    }
}

/// Find unvalidated boundary casts in one file.
///
/// # Errors
/// [`ScanError::Parse`] when the file does not parse within the limits.
pub fn scan(language: Language, src: &str) -> Result<Vec<Site>, ScanError> {
    if !judged(language) {
        return Ok(Vec::new());
    }
    let tree = match parse(language, src, &ParseLimits::default()) {
        ParseResult::Parsed(tree) => tree,
        ParseResult::Unresolved(u) => return Err(ScanError::Parse(u.reason.to_string())),
    };
    let mut g = Gathered::default();
    gather(tree.root(), src, &mut g);
    let sites = g
        .casts
        .iter()
        .filter_map(|cast| judge_cast(*cast, src, &g, &tree))
        .collect();
    Ok(sites)
}

/// Judge one `as` cast: a site when it casts unvalidated boundary data to a shaped type.
fn judge_cast(
    cast: Node<'_>,
    src: &str,
    g: &Gathered<'_>,
    tree: &gob_languages::ParsedTree,
) -> Option<Site> {
    let (operand, ty) = (cast.named_child(0)?, cast.named_child(1)?);
    let target = text(ty, src).trim();
    if SHAPELESS.contains(&target) {
        return None;
    }
    let inner = unwrap(operand);
    let origin = match source_of(inner, src) {
        Some(o) => o,
        None if inner.kind() == "identifier" => {
            let name = text(inner, src);
            if g.bound.contains(name) && !g.validated.contains(name) {
                Origin::Binding
            } else {
                return None;
            }
        }
        None => return None,
    };
    tracing::debug!(?origin, target, "typing004 unvalidated boundary cast");
    Some(Site {
        range: tree.node_range(&cast),
        origin,
        target: target.to_owned(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sites(src: &str) -> Vec<Site> {
        scan(Language::TypeScript, src).expect("scan")
    }

    /// An awaited `.json()` cast to a type fires.
    // frob:tests crates/grimble-lints/src/cast.rs::scan
    #[test]
    fn json_cast_fires() {
        let s = sites("async function f() { const u = (await res.json()) as User; }");
        assert_eq!(s.len(), 1);
        assert_eq!(s[0].origin, Origin::Json);
        assert_eq!(s[0].target, "User");
    }

    /// A schema parse of the body is not a cast and is clean.
    // frob:tests crates/grimble-lints/src/cast.rs::scan
    #[test]
    fn schema_parse_is_clean() {
        assert!(
            sites("async function f() { const u = schema.parse(await res.json()); }").is_empty()
        );
    }

    /// A bound body cast fires unless a validator receives the name.
    // frob:tests crates/grimble-lints/src/cast.rs::scan
    #[test]
    fn binding_cast_needs_validator() {
        let bad = "async function f() { const b = await res.json(); return b as User; }";
        assert_eq!(sites(bad)[0].origin, Origin::Binding);
        let ok =
            "async function f() { const b = await res.json(); schema.parse(b); return b as User; }";
        assert!(sites(ok).is_empty());
    }

    /// `JSON.parse(..) as T` fires; `as unknown` and non-TS files do not.
    // frob:tests crates/grimble-lints/src/cast.rs::scan
    #[test]
    fn json_parse_and_exemptions() {
        assert_eq!(
            sites("const c = JSON.parse(raw) as Config;")[0].origin,
            Origin::JsonParse
        );
        assert!(sites("const c = JSON.parse(raw) as unknown;").is_empty());
        assert!(
            scan(Language::JavaScript, "const c = JSON.parse(raw);")
                .unwrap()
                .is_empty()
        );
    }
}
