//! DUP004: a function whose statement shapes match another function's, in any order.
//!
//! The token windows of DUP001/DUP002 need the copy to keep its statement order. This pass
//! fingerprints each function by its multiset of statement shapes instead: the body is split into
//! statements, each statement is hashed with identifiers and literals abstracted to their kind,
//! and the sorted statement hashes are hashed again. A copy that renamed everything and reordered
//! its statements has the same fingerprint. Only functions with a changed file are reported, so the
//! check costs a land only what the land touches.

// frob:ticket 01M4P0SXFYYD9TE4F53NQ5SB96

use std::collections::{BTreeMap, BTreeSet};

use gob_rules::Severity;
use gob_symbols::{SymbolGraph, SymbolKind, SymbolRecord};

use crate::dup::fnv;
use crate::dup_lex::{Kind, Tok, tokens};
use crate::{DUP_SCAN, DUP_STRUCT, Verdict};

/// Statements a function needs before its shape means anything; fewer is idiom, not a design.
const MIN_STATEMENTS: usize = 4;
/// Sites listed in a message before it says "and N more".
const LISTED_SITES: usize = 12;
/// Adapter language tags whose functions are fingerprinted (every gob-symbols language with functions).
const LANGUAGES: &[&str] = &[
    "rust",
    "python",
    "typescript",
    "csharp",
    "java",
    "c",
    "cpp",
    "go",
    "shell",
];
/// Language tags whose comments start with `#` and whose statements end at a line break.
const HASH_STYLE: &[&str] = &["python", "shell"];

/// One fingerprinted function.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Unit {
    /// Repo-relative file path.
    pub path: String,
    /// The symbol's address, for messages.
    pub name: String,
    /// Byte range of the function in its file.
    pub range: (usize, usize),
    /// Hash of the sorted statement shapes: equal for a renamed and reordered copy.
    pub shape: u128,
    /// Hash of the statement shapes in order: equal only when the order is kept too.
    pub ordered: u128,
}

/// Fold 64-bit parts into one 128-bit hash.
fn fold(parts: impl IntoIterator<Item = u64>) -> u128 {
    let (mut a, mut b) = (0_u64, 0x9e37_79b9_7f4a_7c15_u64);
    for v in parts {
        a = (a.rotate_left(5) ^ v).wrapping_mul(0x517c_c1b7_2722_0a95);
        b = (b ^ v).wrapping_mul(0x0100_0000_01b3).rotate_left(17);
    }
    (u128::from(a) << 64) | u128::from(b)
}

/// The shape hash of every statement of `toks`, in order.
///
/// Statements end at `;` and at braces (nesting is flattened); for hash-style languages also at a
/// line break outside brackets.
fn statement_shapes(toks: &[Tok<'_>], hash_style: bool) -> Vec<u64> {
    let mut out = Vec::new();
    let mut cur: Vec<u64> = Vec::new();
    let (mut depth, mut line) = (0_i32, toks.first().map_or(0, |t| t.line));
    let mut flush = |cur: &mut Vec<u64>| {
        if !cur.is_empty() {
            out.push(u64::try_from(fold(cur.drain(..)) >> 64).unwrap_or_default());
        }
    };
    for t in toks {
        if hash_style && depth == 0 && t.line != line {
            flush(&mut cur);
        }
        line = t.line;
        match (t.kind, t.text) {
            (Kind::Punct, ";" | "{" | "}") => flush(&mut cur),
            (Kind::Punct, "(" | "[") => {
                depth += 1;
                cur.push(fnv(t.text));
            }
            (Kind::Punct, ")" | "]") => {
                depth -= 1;
                cur.push(fnv(t.text));
            }
            (Kind::Ident, _) => cur.push(0x2000_0000_0000_0001),
            (Kind::Number | Kind::Str, _) => cur.push(0x2000_0000_0000_0002),
            _ => cur.push(fnv(t.text)),
        }
    }
    flush(&mut cur);
    out
}

/// The `(shape, ordered)` fingerprint of a function body, `None` when it has too few statements.
pub(crate) fn fingerprint(toks: &[Tok<'_>], hash_style: bool) -> Option<(u128, u128)> {
    let stmts = statement_shapes(toks, hash_style);
    if stmts.len() < MIN_STATEMENTS {
        return None;
    }
    let ordered = fold(stmts.iter().copied());
    let mut sorted = stmts;
    sorted.sort_unstable();
    Some((fold(sorted), ordered))
}

/// True for the symbols whose body is fingerprinted: non-test functions and methods.
fn is_callable(rec: &SymbolRecord) -> bool {
    matches!(rec.kind, SymbolKind::Function | SymbolKind::Method) && !rec.test
}

/// The fingerprinted functions of the walk (those with at least `min_tokens` tokens), and the files lexed.
fn units(
    graph: &SymbolGraph,
    read: &dyn Fn(&str) -> Option<String>,
    min_tokens: usize,
) -> (Vec<Unit>, usize) {
    let mut by_file: BTreeMap<&str, Vec<&SymbolRecord>> = BTreeMap::new();
    for rec in graph.records().filter(|r| is_callable(r)) {
        by_file.entry(rec.symref.path()).or_default().push(rec);
    }
    let (mut out, mut lexed) = (Vec::new(), 0);
    for (path, recs) in by_file {
        let Some(info) = graph.file_info(path) else {
            continue;
        };
        let lang = info.language.as_str();
        if !LANGUAGES.contains(&lang) || grimble_bind::eval::is_test_unit(path) {
            continue;
        }
        let Some(text) = read(path) else {
            tracing::warn!(path, "DUP004 skipped an unreadable file");
            continue;
        };
        lexed += 1;
        let hash_style = HASH_STYLE.contains(&lang);
        let toks = tokens(&text, hash_style);
        for rec in recs {
            let start = usize::try_from(u32::from(rec.span.start())).unwrap_or(usize::MAX);
            let end = usize::try_from(u32::from(rec.span.end())).unwrap_or(usize::MAX);
            let lo = toks.partition_point(|t| t.start < start);
            let hi = toks.partition_point(|t| t.end <= end);
            if hi <= lo || hi - lo < min_tokens {
                continue;
            }
            if let Some((shape, ordered)) = fingerprint(&toks[lo..hi], hash_style) {
                out.push(Unit {
                    path: path.to_owned(),
                    name: rec.symref.to_string(),
                    range: (start, end),
                    shape,
                    ordered,
                });
            }
        }
    }
    (out, lexed)
}

/// The findings for `units` that share a shape with at least one unit in a changed file.
///
/// A class whose members all keep the statement order and number `min_occurrences` or more is the
/// token-window rules' (`DUP002`) and is left to them.
pub(crate) fn clones(
    units: &[Unit],
    changed: &BTreeSet<String>,
    min_occurrences: usize,
    rule: &'static str,
) -> Vec<Verdict> {
    let mut classes: BTreeMap<u128, Vec<&Unit>> = BTreeMap::new();
    for u in units {
        classes.entry(u.shape).or_default().push(u);
    }
    let mut found = Vec::new();
    for (shape, members) in classes {
        if members.len() < 2 || !members.iter().any(|u| changed.contains(&u.path)) {
            continue;
        }
        let same_order = members.iter().all(|u| u.ordered == members[0].ordered);
        if same_order && members.len() >= min_occurrences {
            tracing::debug!(copies = members.len(), "DUP004 class left to DUP002");
            continue;
        }
        let Some(head) = members.iter().find(|u| changed.contains(&u.path)) else {
            continue;
        };
        let mut listed: Vec<String> = members
            .iter()
            .filter(|u| u.name != head.name)
            .take(LISTED_SITES)
            .map(|u| u.name.clone())
            .collect();
        if members.len() - 1 > LISTED_SITES {
            listed.push(format!("and {} more", members.len() - 1 - LISTED_SITES));
        }
        tracing::debug!(unit = %head.name, copies = members.len(), rule, "structural clone");
        found.push(Verdict::fire(
            rule,
            Severity::Error,
            (&head.path, head.range),
            format!(
                "`{}` has the same statement shapes as {}, up to renamed identifiers and statement order",
                head.name,
                listed.join(", ")
            ),
            format!("S:{shape:032x}"),
        ));
    }
    found
}

/// Findings for changed functions that structurally clone another function, and the files examined.
///
/// A `min_tokens` of 0 turns the check off.
pub(crate) fn check(
    graph: &SymbolGraph,
    read: &dyn Fn(&str) -> Option<String>,
    min_tokens: usize,
    min_occurrences: usize,
    changed: &BTreeSet<String>,
) -> (Vec<Verdict>, usize) {
    if min_tokens == 0 || changed.is_empty() {
        tracing::debug!(min_tokens, "DUP004 off or nothing changed");
        return (Vec::new(), 0);
    }
    let (units, lexed) = units(graph, read, min_tokens);
    (clones(&units, changed, min_occurrences, DUP_STRUCT), lexed)
}

/// Findings for every structural clone class in the walk (`DUP005`), and the files examined.
///
/// The whole-repo form of [`check`]: every file counts as changed, so each class is reported once,
/// anchored at its first member. A `min_tokens` of 0 turns the scan off.
pub(crate) fn scan(
    graph: &SymbolGraph,
    read: &dyn Fn(&str) -> Option<String>,
    min_tokens: usize,
    min_occurrences: usize,
) -> (Vec<Verdict>, usize) {
    if min_tokens == 0 {
        tracing::debug!("DUP005 off: dup_min_tokens is 0");
        return (Vec::new(), 0);
    }
    let started = std::time::Instant::now();
    let (units, lexed) = units(graph, read, min_tokens);
    let everything: BTreeSet<String> = units.iter().map(|u| u.path.clone()).collect();
    let found = clones(&units, &everything, min_occurrences, DUP_SCAN);
    tracing::info!(
        files = lexed,
        functions = units.len(),
        clusters = found.len(),
        elapsed_ms = u64::try_from(started.elapsed().as_millis()).unwrap_or(u64::MAX),
        "DUP005 whole-repo scan finished"
    );
    (found, lexed)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The fingerprint of brace-style `src`.
    fn fp(src: &str) -> Option<(u128, u128)> {
        fingerprint(&tokens(src, false), false)
    }

    // frob:tests crates/grimble-arch/src/dup_struct.rs::fingerprint
    #[test]
    fn renamed_and_reordered_bodies_share_a_shape_but_not_an_order() {
        let a = "x = f(1); y = g(x); z = h(y, 2); w = k(z); return w;";
        let renamed = "m = f(1); n = g(m); o = h(n, 2); t = k(o); return t;";
        let reordered = "y = g(x); x = f(1); w = k(z); z = h(y, 2); return w;";
        let (sa, oa) = fp(a).expect("a");
        assert_eq!(fp(renamed).expect("renamed"), (sa, oa));
        let (sr, or) = fp(reordered).expect("reordered");
        assert_eq!(sa, sr);
        assert_ne!(oa, or);
    }

    // frob:tests crates/grimble-arch/src/dup_struct.rs::fingerprint
    #[test]
    fn different_shapes_and_short_bodies_do_not_match() {
        let a = "x = f(1); y = g(x); z = h(y, 2); w = k(z);";
        let c = "x = f(1); y = g(x); z = h(y, 2); w = k(z) + 1;";
        assert_ne!(fp(a).expect("a").0, fp(c).expect("c").0);
        assert!(fp("x = f(1); y = g(x);").is_none());
    }

    // frob:tests crates/grimble-arch/src/dup_struct.rs::fingerprint
    #[test]
    fn hash_style_statements_end_at_line_breaks() {
        let src = "a = f(1)\nb = g(a)\nc = h(b,\n 2)\nd = k(c)\n";
        let toks = tokens(src, true);
        assert_eq!(statement_shapes(&toks, true).len(), 4);
    }

    /// A unit in `path` with the given fingerprints.
    fn unit(path: &str, name: &str, shape: u128, ordered: u128) -> Unit {
        Unit {
            path: path.to_owned(),
            name: name.to_owned(),
            range: (0, 1),
            shape,
            ordered,
        }
    }

    // frob:tests crates/grimble-arch/src/dup_struct.rs::clones
    #[test]
    fn only_classes_touching_a_changed_file_are_reported() {
        let units = [unit("a.rs", "a", 1, 1), unit("b.rs", "b", 1, 2)];
        let none = BTreeSet::new();
        assert!(clones(&units, &none, 3, DUP_STRUCT).is_empty());
        let changed: BTreeSet<String> = ["b.rs".to_owned()].into();
        let found = clones(&units, &changed, 3, DUP_STRUCT);
        assert_eq!(found.len(), 1);
        assert_eq!(found[0].file, "b.rs");
        assert!(found[0].message.contains('a'), "{}", found[0].message);
    }

    // frob:tests crates/grimble-arch/src/dup_struct.rs::clones
    #[test]
    fn order_preserving_copies_in_quantity_are_left_to_dup002() {
        let units = [
            unit("a.rs", "a", 1, 1),
            unit("b.rs", "b", 1, 1),
            unit("c.rs", "c", 1, 1),
        ];
        let changed: BTreeSet<String> = ["c.rs".to_owned()].into();
        assert!(clones(&units, &changed, 3, DUP_STRUCT).is_empty());
        assert_eq!(clones(&units, &changed, 4, DUP_STRUCT).len(), 1);
    }

    // frob:tests crates/grimble-arch/src/dup_struct.rs::clones
    #[test]
    fn the_scan_form_reports_a_class_once_under_its_own_rule() {
        let units = [
            unit("a.rs", "a", 1, 1),
            unit("b.rs", "b", 1, 2),
            unit("c.rs", "c", 2, 3),
        ];
        let everything: BTreeSet<String> = units.iter().map(|u| u.path.clone()).collect();
        let found = clones(&units, &everything, 3, DUP_SCAN);
        assert_eq!(found.len(), 1);
        assert_eq!(found[0].rule, DUP_SCAN);
        assert_eq!(found[0].file, "a.rs");
    }
}
