//! T-1222: rust arch python metrics single-pass walk export. Extraction
//! only -- rule evaluation (long-function/god-class/deep-nesting
//! thresholds, the T-0332 pattern detectors in `frob.arch._patterns`,
//! `_lock_ordering.py`/`_async_hazards.py`/`_shared_state_race.py`/
//! `_concurrency_model.py`) stays entirely in Python, same design line
//! T-1221's capability resolver states explicitly. This kernel answers
//! only "what does this function's body contain" -- the same question
//! `frob.arch._python`'s `_py_max_nesting`/`_py_cyclomatic`/`_py_collect_
//! body_events` answer today, computed natively via `tree-sitter` in one
//! pass per function instead of three separate Python recursions.
//!
//! Deliberately narrower than `NormalizedFunction`: no `name`/`params`/
//! `return_type`/`is_method`/`overrides` -- those are O(1) per function to
//! read off the node directly and stay Python-side (`_py_build_function`
//! still owns assembling the full model; this kernel replaces only its
//! expensive body-walk portion, matching the ticket's own "extraction-only
//! portion of `_py_build_function`/`_py_build_module`" framing).
//!
//! ## One disclosed deviation from `frob.arch._python`
//!
//! **No `declared_raises` (T-0689's `# frob:callee-raises` comment
//! parsing).** `NormalizedCall.declared_raises` is populated by regex-
//! matching a call site's OWN source line against a `# frob:callee-raises
//! A, B` comment -- a raw-text convention layered on top of the tree walk,
//! not a tree-sitter extraction concern. Every `calls` entry this kernel
//! returns therefore carries no declared-raises information; a consumer
//! that needs it re-derives it Python-side from `(call_line, source_text)`
//! after the fact (`_frob_raises_declaration` is a five-line pure function
//! over already-available source lines -- cheap to keep running post-hoc,
//! not worth threading through the FFI boundary as a second input). This
//! is the one place this kernel's output is not a complete substitute for
//! `_py_collect_body_events`'s own `NormalizedCall.declared_raises` field;
//! every other event field matches byte-for-byte.

use pyo3::prelude::*;
use tree_sitter::{Node, Parser};

/// Node kinds that count toward `_py_max_nesting`'s depth -- matches
/// `_NESTING_TYPES` exactly.
// frob:ticket T-1222
const NESTING_TYPES: [&str; 5] = [
    "if_statement",
    "for_statement",
    "while_statement",
    "try_statement",
    "with_statement",
];

/// Node kinds that count toward `_py_cyclomatic`'s proxy count -- matches
/// `_BRANCH_NODE_TYPES` exactly (match/case deliberately excluded, see the
/// Python original's own module-level comment for why).
// frob:ticket T-1222
const BRANCH_NODE_TYPES: [&str; 6] = [
    "if_statement",
    "for_statement",
    "while_statement",
    "except_clause",
    "boolean_operator",
    "conditional_expression",
];

/// Node kinds that emit a `NormalizedBranch` event -- matches
/// `_BRANCH_EVENT_TYPES` (a DIFFERENT, narrower set than
/// `BRANCH_NODE_TYPES` above: `for`/`while`/`except_clause` are decision
/// points for the cyclomatic proxy but not `NormalizedBranch` events --
/// they get their own `NormalizedLoop`/`NormalizedCatch` events instead).
// frob:ticket T-1222
const BRANCH_EVENT_TYPES: [&str; 3] =
    ["if_statement", "boolean_operator", "conditional_expression"];

/// `node`'s source text, or `""` on a UTF-8 boundary failure.
// frob:ticket T-1222
fn text<'a>(node: Node, source: &'a [u8]) -> &'a str {
    node.utf8_text(source).unwrap_or("")
}

/// 1-based source line of `node`'s start -- matches every `NormalizedX`
/// event's `line = c.start_point[0] + 1` convention.
// frob:ticket T-1222
fn line_of(node: Node) -> usize {
    node.start_position().row + 1
}

/// Deepest control-flow nesting depth inside `func_body_node` -- matches
/// `_py_max_nesting` exactly (a pure recursive max, no early return).
// frob:invariant terminates reason="each recursive call descends strictly into a \
// child of node in tree-sitter's own finite parse tree" measure="remaining depth from \
// node to its deepest leaf in the parse tree"
// frob:ticket T-1222
fn max_nesting(node: Node, current: usize) -> usize {
    let mut best = current;
    let mut cursor = node.walk();
    for c in node.children(&mut cursor) {
        let nxt = if NESTING_TYPES.contains(&c.kind()) {
            current + 1
        } else {
            current
        };
        best = best.max(max_nesting(c, nxt));
    }
    best
}

/// Cheap cyclomatic-complexity proxy: count of `BRANCH_NODE_TYPES` nodes
/// in `node`'s subtree -- matches `_py_cyclomatic` exactly.
// frob:invariant terminates reason="each recursive call descends strictly into a \
// child of node in tree-sitter's own finite parse tree" measure="remaining depth from \
// node to its deepest leaf in the parse tree"
// frob:ticket T-1222
fn cyclomatic(node: Node) -> usize {
    let mut count = if BRANCH_NODE_TYPES.contains(&node.kind()) { 1 } else { 0 };
    let mut cursor = node.walk();
    for c in node.children(&mut cursor) {
        count += cyclomatic(c);
    }
    count
}

/// A branch's condition text -- matches `_py_branch_condition_text`: an
/// `if_statement` reads its `condition` field; a `boolean_operator`/
/// `conditional_expression` has no separate condition field, so its own
/// text stands for it.
// frob:ticket T-1222
// frob:waive DUP001 reason="the r2 structural match is against unrelated short \
// predicate/lookup functions across this crate (is_dynamic_dispatch_subscript, \
// collect_candidates, walk_leaves, collect_comment_nodes, anti_unify_core) and four \
// strata-core recursive-descent parser methods -- none share this function's actual \
// logic (a two-branch field-lookup-with-text-fallback); the r2 rung matches on \
// generic short-function control-flow shape only, a coincidental match class this \
// size of function is prone to, not a real duplication to extract a helper from"
fn branch_condition_text<'a>(node: Node, source: &'a [u8]) -> &'a str {
    if node.kind() == "if_statement" {
        if let Some(cond) = node.child_by_field_name("condition") {
            return text(cond, source);
        }
    }
    text(node, source)
}

/// A `call` node's callee text -- matches `_py_call_callee_text`: the
/// `function` field's text (a bare identifier or `obj.method` chain), or
/// the whole node's own text as a fallback.
// frob:ticket T-1222
fn call_callee_text<'a>(node: Node, source: &'a [u8]) -> &'a str {
    match node.child_by_field_name("function") {
        Some(func) => text(func, source),
        None => text(node, source),
    }
}

/// One call argument: `(index, keyword, ident)`, exactly one of `index`/
/// `keyword` set -- matches `NormalizedCallArg`/`_py_call_args`.
// frob:ticket T-1222
type CallArg = (Option<i64>, Option<String>, Option<String>);

/// `NormalizedCallArg`s for a `call` node's `arguments` list, in source
/// order -- matches `_py_call_args` exactly.
// frob:ticket T-1222
fn call_args(node: Node, source: &[u8]) -> Vec<CallArg> {
    let Some(args_node) = node.child_by_field_name("arguments") else {
        return Vec::new();
    };
    let mut out: Vec<CallArg> = Vec::new();
    let mut position: i64 = 0;
    let mut cursor = args_node.walk();
    for a in args_node.named_children(&mut cursor) {
        if a.kind() == "keyword_argument" {
            let val = a.child_by_field_name("value");
            let name_node = a.child_by_field_name("name");
            let keyword = name_node.map(|n| text(n, source).to_string()).unwrap_or_else(|| "?".to_string());
            let ident = val.filter(|v| v.kind() == "identifier").map(|v| text(v, source).to_string());
            out.push((None, Some(keyword), ident));
            continue;
        }
        let ident = if a.kind() == "identifier" { Some(text(a, source).to_string()) } else { None };
        out.push((Some(position), None, ident));
        position += 1;
    }
    out
}

/// Whether an `attribute` node is a genuine `self.<field>` read/write --
/// matches `_py_is_self_attribute` exactly: object half is bare `self`,
/// AND it is not itself a call's own callee (`self.method(...)` is a
/// method invocation, already covered by `calls`, not a field access).
// frob:ticket T-1222
fn is_self_attribute(node: Node, source: &[u8]) -> bool {
    let Some(obj) = node.child_by_field_name("object") else {
        return false;
    };
    if obj.kind() != "identifier" || text(obj, source) != "self" {
        return false;
    }
    if let Some(parent) = node.parent() {
        if parent.kind() == "call" {
            if let Some(func) = parent.child_by_field_name("function") {
                if func.id() == node.id() {
                    return false;
                }
            }
        }
    }
    true
}

/// Whether an `attribute` node (`self.x`) is an assignment TARGET (a
/// write) -- matches `_py_is_field_write` exactly.
// frob:ticket T-1222
fn is_field_write(node: Node) -> bool {
    let Some(parent) = node.parent() else {
        return false;
    };
    if parent.kind() != "assignment" {
        return false;
    }
    match parent.child_by_field_name("left") {
        Some(target) => target.id() == node.id(),
        None => false,
    }
}

/// The exception type name of a `raise` statement where statically
/// determinable -- matches `_py_raise_exception_type` exactly.
// frob:ticket T-1222
// frob:waive DUP001 reason="the r2 structural match is against capability_python.rs's \
// first_positional_arg (an unrelated argument-list scan with a different payload and \
// no named-children iteration) -- the r2 rung matches on the generic 'iterate named \
// children, return on first match of a kind check' shape every small tree-sitter \
// lookup helper in this crate necessarily has, not a real duplication to extract a \
// helper from"
fn raise_exception_type(node: Node, source: &[u8]) -> Option<String> {
    let mut cursor = node.walk();
    for c in node.named_children(&mut cursor) {
        if c.kind() == "call" {
            if let Some(func) = c.child_by_field_name("function") {
                if func.kind() == "identifier" {
                    return Some(text(func, source).to_string());
                }
            }
        } else if c.kind() == "identifier" {
            return Some(text(c, source).to_string());
        }
    }
    None
}

/// The caught exception type name of an `except_clause` -- matches
/// `_py_except_exception_type` exactly.
// frob:ticket T-1222
// frob:waive DUP001 reason="the r2 structural match is against capability_python.rs's \
// first_positional_arg (an unrelated argument-list scan) -- same coincidental \
// generic-shape match as raise_exception_type immediately above, not a real \
// duplication to extract a helper from"
fn except_exception_type(node: Node, source: &[u8]) -> Option<String> {
    let mut cursor = node.walk();
    for c in node.named_children(&mut cursor) {
        if c.kind() == "identifier" || c.kind() == "attribute" {
            return Some(text(c, source).to_string());
        }
        if c.kind() == "tuple" {
            let mut inner_cursor = c.walk();
            let first = c.named_children(&mut inner_cursor).next();
            if let Some(first) = first {
                return Some(text(first, source).to_string());
            }
        }
    }
    None
}

/// One function's flattened body events -- the eight parallel lists
/// `_py_collect_body_events` mutates, bundled as a struct so the walk can
/// pass one `&mut` instead of eight.
#[derive(Default)]
// frob:ticket T-1222
struct BodyEvents {
    branches: Vec<(usize, String)>,
    loops: Vec<(usize, String)>,
    calls: Vec<(String, usize, Vec<CallArg>)>,
    field_accesses: Vec<(String, usize, bool)>,
    returns: Vec<(usize, Option<String>)>,
    raises: Vec<(usize, Option<String>)>,
    catches: Vec<(usize, Option<String>)>,
    subscripts: Vec<usize>,
}

/// Flatten every structural event inside `node`'s subtree into `events`,
/// stopping descent at a nested `function_definition`/`class_definition`
/// boundary -- matches `_py_collect_body_events` exactly (module
/// docstring's one disclosed deviation: no `declared_raises` populated
/// here, see above). Nested function bodies are walked separately by the
/// caller (`collect_function_metrics`), one call per function, matching
/// `_py_build_function`'s own per-function recursion.
// frob:invariant terminates reason="each recursive call descends strictly into a \
// child of node in tree-sitter's own finite parse tree; a function_definition/ \
// class_definition child stops descent entirely rather than recursing" \
// measure="remaining depth from node to its deepest leaf in the parse tree"
// frob:ticket T-1222
fn collect_body_events(node: Node, source: &[u8], events: &mut BodyEvents) {
    let mut cursor = node.walk();
    for c in node.children(&mut cursor) {
        let kind = c.kind();
        if kind == "function_definition" || kind == "class_definition" {
            continue;
        }
        if BRANCH_EVENT_TYPES.contains(&kind) {
            events.branches.push((line_of(c), branch_condition_text(c, source).to_string()));
        }
        match kind {
            "for_statement" => events.loops.push((line_of(c), "for".to_string())),
            "while_statement" => events.loops.push((line_of(c), "while".to_string())),
            _ => {}
        }
        if kind == "call" {
            events.calls.push((call_callee_text(c, source).to_string(), line_of(c), call_args(c, source)));
        }
        if kind == "attribute" && is_self_attribute(c, source) {
            if let Some(field_name_node) = c.child_by_field_name("attribute") {
                events.field_accesses.push((
                    text(field_name_node, source).to_string(),
                    line_of(c),
                    is_field_write(c),
                ));
            }
        }
        if kind == "return_statement" {
            let mut inner_cursor = c.walk();
            let value = c.named_children(&mut inner_cursor).next();
            events.returns.push((line_of(c), value.map(|v| text(v, source).to_string())));
        }
        if kind == "raise_statement" {
            events.raises.push((line_of(c), raise_exception_type(c, source)));
        }
        if kind == "except_clause" {
            events.catches.push((line_of(c), except_exception_type(c, source)));
        }
        if kind == "subscript" {
            events.subscripts.push(line_of(c));
        }
        collect_body_events(c, source, events);
    }
}

/// One function's full metrics tuple: `((start_line, end_line), nesting,
/// cyclomatic, (branches, loops, calls, field_accesses, returns, raises,
/// catches, subscripts))` -- the FFI entry point's per-function payload
/// shape (module docstring).
// frob:ticket T-1222
type FunctionMetrics = (
    (usize, usize),
    usize,
    usize,
    (
        Vec<(usize, String)>,
        Vec<(usize, String)>,
        Vec<(String, usize, Vec<CallArg>)>,
        Vec<(String, usize, bool)>,
        Vec<(usize, Option<String>)>,
        Vec<(usize, Option<String>)>,
        Vec<(usize, Option<String>)>,
        Vec<usize>,
    ),
);

/// Recursively collect one `FunctionMetrics` entry per `function_
/// definition` node under `node` (module-level, method, or nested --
/// FLATTENED into one output list, matching how `_py_build_function`
/// recurses into `nested_functions` but exposing every level at the same
/// depth here since this kernel does not itself assemble the nested
/// `NormalizedFunction` tree, module docstring). `span` is the WHOLE
/// `function_definition` node's own 1-based inclusive line range
/// (signature through closing body line), not just the body -- the
/// caller's existing `body_line_count`/`func.line` fields remain the
/// authoritative per-field source; `span` here is a convenience locator.
// frob:invariant terminates reason="each recursive call descends strictly into a \
// child of node in tree-sitter's own finite parse tree" measure="remaining depth from \
// node to its deepest leaf in the parse tree"
// frob:ticket T-1222
// frob:waive DUP001 reason="the r2 structural match is against capability_python.rs's \
// first_positional_arg (an unrelated, non-recursive argument-list scan with a \
// completely different signature and payload) -- the r2 rung matches on generic \
// control-flow shape only, not this function's actual per-node dispatch/recursion \
// logic; not a real duplication to extract a helper from"
fn collect_function_metrics(node: Node, source: &[u8], out: &mut Vec<FunctionMetrics>) {
    let mut cursor = node.walk();
    for c in node.children(&mut cursor) {
        if c.kind() == "function_definition" {
            let span = (c.start_position().row + 1, c.end_position().row + 1);
            let nesting = c.child_by_field_name("body").map(|b| max_nesting(b, 0)).unwrap_or(0);
            let cyc = c.child_by_field_name("body").map(cyclomatic).unwrap_or(0);
            let mut events = BodyEvents::default();
            if let Some(body) = c.child_by_field_name("body") {
                collect_body_events(body, source, &mut events);
            }
            out.push((
                span,
                nesting,
                cyc,
                (
                    events.branches,
                    events.loops,
                    events.calls,
                    events.field_accesses,
                    events.returns,
                    events.raises,
                    events.catches,
                    events.subscripts,
                ),
            ));
            // Recurse into the function's OWN body for nested function
            // definitions -- `_py_build_function`'s own recursion target
            // (`for c in body.named_children: if c.type ==
            // "function_definition"`), flattened into this same output
            // list rather than a separate `nested_functions` tree.
            if let Some(body) = c.child_by_field_name("body") {
                collect_function_metrics(body, source, out);
            }
            continue;
        }
        // A class body's direct function_definition children are methods
        // -- `_py_methods`/`_py_build_class` walk the SAME node kind, so
        // recursing through a class_definition's body here (rather than
        // skipping it, unlike collect_body_events which stops at a class
        // boundary) reaches them too, matching `_py_build_module`'s own
        // top-level dispatch (classes contribute their methods'
        // functions to the same overall per-file metrics set).
        collect_function_metrics(c, source, out);
    }
}

/// Pure compute: every function's metrics in one python source buffer --
/// empty (never a panic) if `source` fails to parse, or parses as a
/// language other than python.
// frob:ticket T-1222
fn py_function_metrics_source(source: &[u8]) -> Vec<FunctionMetrics> {
    let mut parser = Parser::new();
    let language = tree_sitter_python::LANGUAGE.into();
    if parser.set_language(&language).is_err() {
        return Vec::new();
    }
    let Some(tree) = parser.parse(source, None) else {
        return Vec::new();
    };
    let mut out: Vec<FunctionMetrics> = Vec::new();
    collect_function_metrics(tree.root_node(), source, &mut out);
    out
}

/// FFI entry point (T-1222): rust arch python metrics single-pass walk,
/// extraction only (module docstring). `source` is the raw file bytes;
/// returns one `FunctionMetrics` tuple per function (module-level,
/// method, or nested, flattened) found in `source`:
/// `((start_line, end_line), max_nesting_depth, cyclomatic, (branches,
/// loops, calls, field_accesses, returns, raises, catches, subscripts))`
/// -- matching `_py_max_nesting`/`_py_cyclomatic`/`_py_collect_body_
/// events`'s output exactly, MINUS `NormalizedCall.declared_raises`
/// (module docstring's one disclosed deviation).
///
/// Never raises (this crate's whole-file convention): a buffer tree-
/// sitter cannot parse, or one that does not parse as python, yields an
/// empty list rather than a `PyErr`.
// frob:doc docs/modules/arch.md#normalized-code-model
// frob:ticket T-1222
#[pyfunction]
pub fn py_function_metrics(source: Vec<u8>) -> Vec<FunctionMetrics> {
    py_function_metrics_source(&source)
}
