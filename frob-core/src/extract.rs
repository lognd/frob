// frob:waive INV006 preset="split-carried-prose"
//! Python-only tree-extraction kernel (T-1220, EPIC B candidate #1's first
//! landed portion): source bytes in, spans/tokens/identifiers out, computed
//! natively via `tree-sitter`/`tree-sitter-python` instead of `frob.lang`'s
//! per-node Python recursion (`_extract.py`, `_walk_python.py`,
//! `frob.vet._capability_core`'s pre-T-1223 walk). This module owns ONLY
//! the python grammar today -- cpp/rust/typescript kernels and the
//! consumer-side rewiring (perf/clones/deprecated/dead_symbols/opaque/sys)
//! are follow-up tickets (T-1220's own acceptance criteria; this is the
//! foundation, not the full migration).
//!
//! Mirrors two existing Python-side contracts exactly, verified by a
//! golden-test comparison script (not committed -- run ad hoc against this
//! repo's own `.py` corpus per the ticket's own acceptance gate):
//! - `frob.lang._common._span_of`'s 1-based inclusive (start_line, end_line)
//!   fold for a tree-sitter node whose `end_point` lands at column 0 of the
//!   following line (a lexer artifact, not real content on that line).
//! - `frob.vet._capability_core._PY_DOCSTRING_QUERY_SRC` /
//!   `_PY_DOC_CAPTURE_FILTER` (T-1223's own fix for the `expression_statement`
//!   supertype false positive on an `ErrorSet`-style `NAME = "value"` first
//!   body statement) -- same query source, same post-capture parent-type
//!   filter, reimplemented here rather than re-derived, so both language
//!   bindings agree on what counts as a docstring.
//!
//! Never raises across the FFI boundary (this crate's whole-file
//! convention, `docs/modules/gates.md#ffi001-ffi002-t-0690`): a source
//! buffer tree-sitter cannot parse at all returns four empty collections
//! rather than a `PyErr` -- malformed input is a Python-side validation
//! concern, not something this kernel defends against.

use pyo3::prelude::*;
use tree_sitter::{Node, Parser, Query, QueryCursor, StreamingIterator};

/// 1-based inclusive `(start_line, end_line)` span for `node`, folding the
/// same trailing-newline lexer artifact `frob.lang._common._span_of` folds
/// (a comment/string node whose `end_point` lands at column 0 of the
/// FOLLOWING line is reporting no real content on that line).
fn span_of(node: Node) -> (usize, usize) {
    let start_row = node.start_position().row;
    let mut end_row = node.end_position().row;
    if node.end_position().column == 0 && end_row > start_row {
        end_row -= 1;
    }
    (start_row + 1, end_row + 1)
}

/// Depth-first collect every leaf ("no named/anonymous children") node
/// under `root`, in source order -- the same traversal shape
/// `frob.lang._common._leaf_tokens` and `_extract._collect_comment_nodes`
/// both walk, reimplemented once here so every collector below (comments,
/// identifiers, the token stream) shares one recursion instead of three.
fn walk_leaves<'a>(node: Node<'a>, out: &mut Vec<Node<'a>>) {
    if node.child_count() == 0 {
        out.push(node);
        return;
    }
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        walk_leaves(child, out);
    }
}

/// Three of `_PY_DOCSTRING_QUERY_SRC`'s six anchored patterns
/// (`frob.vet._capability_core`) -- module/class/function-body first
/// statement, `expression_statement`-wrapped only. The other three
/// (bare-string, unwrapped) patterns from the Python-side source are
/// DELIBERATELY dropped here, not an oversight: `frob.lang`'s python parse
/// path runs through `tree_sitter_language_pack.get_language("python")`
/// (ABI 14, an older grammar generation) where a first-statement string
/// CAN appear as a bare `(string)` child with no wrapping
/// `expression_statement`; the `tree-sitter-python` 0.25.0 Rust crate
/// pinned in `Cargo.toml` targets a newer grammar generation that always
/// wraps every top-level string in `expression_statement` -- verified by
/// probing both grammars directly (`tree.root_node` for a bare-docstring
/// source always shows `(expression_statement (string ...))` on the newer
/// grammar, never a bare `(string ...)`). Compiling any of the three
/// bare-string patterns against the newer grammar raises
/// `tree-sitter::QueryError` (`kind: Structure`) at construction time --
/// they describe a shape the newer grammar can never produce, so
/// `Query::new` correctly rejects them as unsatisfiable rather than
/// silently no-op matching. Dropping them changes nothing observable:
/// every docstring span this python-side grammar generation could ever
/// have found the OLD unwrapped way is still found by the wrapped
/// pattern, since this grammar has already wrapped it. This is the one
/// documented, justified delta between the Rust and Python extraction
/// paths this ticket's golden test allows (rest of the surface is
/// byte-identical) -- a follow-up ticket to pin an ABI-14-compatible
/// `tree-sitter-python` crate version (if one still builds against a
/// current `tree-sitter` core) would let this list match the Python
/// source verbatim again; not attempted here since it is out of this
/// portion's scope.
const PY_DOCSTRING_QUERY_SRC: &str = "
(module . (expression_statement (string) @doc))
(function_definition body: (block . (expression_statement (string) @doc)))
(class_definition body: (block . (expression_statement (string) @doc)))
";

/// Same `_PY_DOC_CAPTURE_FILTER` (`frob.vet._capability_core`, T-1223): a
/// capture only counts as a real docstring if its immediate parent's own
/// `.kind()` is literally one of these -- never a supertype-conforming
/// concrete kind like `assignment` (the `ErrorSet`-style `NAME = "value"`
/// false-positive T-1223 closed).
fn is_real_docstring_parent(kind: &str) -> bool {
    matches!(kind, "module" | "block" | "expression_statement")
}

/// One parsed extraction result for a python source buffer -- the four
/// collections `extract_tree_python` computes, bundled so the FFI boundary
/// returns one tuple rather than four independently-ordered ones.
struct PythonExtraction {
    comment_spans: Vec<(usize, usize)>,
    docstring_spans: Vec<(usize, usize)>,
    identifiers: Vec<(String, usize)>,
    tokens: Vec<String>,
}

/// Pure compute: parse `source` as python and collect comment spans,
/// docstring spans, identifier `(name, line)` pairs, and the whole-file
/// leaf-token stream (comments excluded, matching `_leaf_tokens(root,
/// {"comment"})`'s filter) -- empty result (never a panic) if `source`
/// fails to parse at all.
fn extract_python_source(source: &[u8]) -> PythonExtraction {
    let empty = PythonExtraction {
        comment_spans: Vec::new(),
        docstring_spans: Vec::new(),
        identifiers: Vec::new(),
        tokens: Vec::new(),
    };
    let mut parser = Parser::new();
    let language = tree_sitter_python::LANGUAGE.into();
    if parser.set_language(&language).is_err() {
        return empty;
    }
    let Some(tree) = parser.parse(source, None) else {
        return empty;
    };
    let root = tree.root_node();

    let mut leaves: Vec<Node> = Vec::new();
    walk_leaves(root, &mut leaves);

    let mut comment_spans: Vec<(usize, usize)> = Vec::new();
    let mut identifiers: Vec<(String, usize)> = Vec::new();
    let mut tokens: Vec<String> = Vec::new();
    for leaf in &leaves {
        let text = match leaf.utf8_text(source) {
            Ok(t) => t,
            Err(_) => continue,
        };
        if leaf.kind() == "comment" {
            comment_spans.push(span_of(*leaf));
            continue;
        }
        if leaf.kind() == "identifier" {
            identifiers.push((text.to_string(), leaf.start_position().row + 1));
        }
        tokens.push(text.to_string());
    }

    let mut docstring_spans: Vec<(usize, usize)> = Vec::new();
    if let Ok(query) = Query::new(&language, PY_DOCSTRING_QUERY_SRC) {
        let mut cursor = QueryCursor::new();
        let mut matches = cursor.matches(&query, root, source);
        while let Some(m) = matches.next() {
            for cap in m.captures {
                let parent_kind = cap.node.parent().map(|p| p.kind());
                let is_real = match parent_kind {
                    None => true,
                    Some(k) => is_real_docstring_parent(k),
                };
                if is_real {
                    docstring_spans.push(span_of(cap.node));
                }
            }
        }
    }
    docstring_spans.sort_unstable();
    docstring_spans.dedup();

    PythonExtraction {
        comment_spans,
        docstring_spans,
        identifiers,
        tokens,
    }
}

/// FFI entry point (T-1220): python-only tree-extraction kernel. `source`
/// is the raw file bytes; returns `(comment_spans, docstring_spans,
/// identifiers, tokens)` where spans are 1-based inclusive
/// `(start_line, end_line)` pairs matching `frob.lang._common._span_of`,
/// identifiers are `(name, 1-based line)` pairs matching
/// `frob.lang._extract.iter_identifiers`'s python output, and `tokens` is
/// the whole-file leaf-token stream with comments excluded, matching
/// `frob.lang._common._leaf_tokens(root, {"comment"})`.
///
/// Never raises (see module docstring): a buffer tree-sitter cannot parse
/// yields four empty lists rather than a `PyErr`.
// frob:doc docs/modules/lang.md#extraction-api
#[pyfunction]
pub fn extract_tree_python(
    source: Vec<u8>,
) -> (
    Vec<(usize, usize)>,
    Vec<(usize, usize)>,
    Vec<(String, usize)>,
    Vec<String>,
) {
    let result = extract_python_source(&source);
    (
        result.comment_spans,
        result.docstring_spans,
        result.identifiers,
        result.tokens,
    )
}
