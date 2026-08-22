//! R3: canonicalization/hashing rung, split out of lib.rs by T-2846.
//! frob:ticket T-2846

use crate::hash_str;
use pyo3::prelude::*;

/// True iff `tok` is shaped like a numeric literal (optional leading `-`,
/// digits, at most one `.`) -- e.g. `1`, `-3`, `2.5`. Deliberately
/// conservative: anything ambiguous (an identifier, a keyword) is left
/// alone rather than risk collapsing two DIFFERENT non-literal tokens
/// into the same placeholder (T-0447).
pub(crate) fn is_numeric_literal(tok: &str) -> bool {
    let body = tok.strip_prefix('-').unwrap_or(tok);
    if body.is_empty() {
        return false;
    }
    let mut seen_dot = false;
    let mut seen_digit = false;
    for c in body.chars() {
        if c == '.' {
            if seen_dot {
                return false;
            }
            seen_dot = true;
        } else if c.is_ascii_digit() {
            seen_digit = true;
        } else {
            return false;
        }
    }
    seen_digit
}

/// True iff `tok` is a quoted string literal (starts and ends with the
/// same quote character, `'` or `"`, and is at least two characters --
/// i.e. the quotes are not the same single character counted twice).
pub(crate) fn is_string_literal(tok: &str) -> bool {
    let mut chars = tok.chars();
    let Some(first) = chars.next() else {
        return false;
    };
    if first != '\'' && first != '"' {
        return false;
    }
    tok.len() >= 2 && tok.ends_with(first) && tok.chars().count() >= 2
}

/// R3 canonicalization pass: literal abstraction + control-flow desugar,
/// applied to an already alpha-renamed (R2) token stream before folding.
///
/// WHY here and not in Python: `docs/modules/dup.md`'s R3 row promises
/// "canonicalized-AST subtree hash: alpha-rename, literal abstraction, ...
/// control-flow normalization", but until T-0447 `r3_canonical_hash` only
/// folded the raw R2 stream -- literally indistinguishable from R2 (T-0199
/// finding). Two real, tractable-without-an-AST transforms close that gap:
///
/// - literal abstraction: every numeric-literal-shaped or quoted-string-
///   literal-shaped token collapses to one canonical placeholder per kind
///   (`_lit_num` / `_lit_str`), so two bodies differing only in a constant
///   value hash identically.
/// - control-flow desugar: `elif` is real syntactic sugar for `else: if`
///   (true in every grammar frob.lang parses that has an `elif` keyword,
///   Python's included) -- expanding it to the three tokens
///   `["else", ":", "if"]` before folding makes an `if/elif/else` chain
///   and its manually-nested `if/else: if/else` equivalent hash the same,
///   without needing real AST restructuring.
///
/// Anything beyond these two (commutative-operand reordering, real
/// for/while loop-shape desugaring) needs actual AST structure, not a
/// token fold, and is intentionally NOT attempted here -- see
/// `docs/modules/dup.md`'s R3 deviations note and `frob:todo T-0001`.
fn r3_canonicalize(tokens: &[String]) -> Vec<String> {
    let mut out = Vec::with_capacity(tokens.len());
    for tok in tokens {
        if tok == "elif" {
            out.push("else".to_string());
            out.push(":".to_string());
            out.push("if".to_string());
        } else if is_numeric_literal(tok) {
            out.push("_lit_num".to_string());
        } else if is_string_literal(tok) {
            out.push("_lit_str".to_string());
        } else {
            out.push(tok.clone());
        }
    }
    out
}

/// R3: canonicalized-AST subtree hash.
///
/// WHY: the caller (frob.dup._pipeline) has already alpha-renamed locals
/// via `frob.lang` (R2 normalization) -- this function's job is to finish
/// canonicalizing the resulting token sequence (literal abstraction,
/// `elif` control-flow desugar -- `r3_canonicalize`, T-0447) and fold it
/// into one stable hex digest, so equal-shape bodies collide regardless of
/// source length, constant values, or `elif`-vs-nested-`if/else` spelling.
/// Kept as a pure fold (not a crate like blake3) to keep the dependency
/// surface at just pyo3.
#[pyfunction]
pub fn r3_canonical_hash(tokens: Vec<String>) -> String {
    // frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
    let canonical = r3_canonicalize(&tokens);
    let mut acc: u64 = 0xcbf29ce484222325; // FNV offset basis, arbitrary seed
    for tok in &canonical {
        let h = hash_str(tok);
        acc = acc.rotate_left(5) ^ h;
    }
    format!("{:016x}", acc)
}

