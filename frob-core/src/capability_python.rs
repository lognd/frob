//! T-1221: rust capability-scan resolver -- import table, position-aware
//! scope shadowing, scope-local alias copy-propagation, and call/
//! attribute/subscript candidate resolution for python source, mirroring
//! `frob.vet._capability_python`'s resolution semantics (T-0328/T-0337/
//! T-0468/T-1626 lineage) in the native kernel. Extraction only, same
//! design line T-1222 states explicitly for the arch walk: RULE evaluation
//! (matching a resolved target against the `DANGEROUS_OPERATIONS` needle
//! registry) stays entirely in Python -- `frob.vet._capability_registry`
//! is data a security reviewer edits and audits directly; a needle rule
//! compiled into this crate would be unreadable and unwaivable from the
//! Python side that owns it. This kernel only answers "what does this
//! call/attribute/subscript site's callee resolve to", the same question
//! `_python_resolved_candidates` answers today.
//!
//! ## The UNRESOLVED requirement
//!
//! A resolver that silently treats "I could not follow this" the same as
//! "there is nothing dangerous here" turns a missed capability into a
//! security claim the design makes and the code silently violates -- the
//! one failure mode with no external symptom. `scan_python_capabilities`
//! therefore returns THREE collections, not the two the ticket's own
//! acceptance criterion names as a floor: `candidates` (definitely-
//! resolved call/attribute/subscript targets, the criterion's own
//! surface), `unresolved` (call sites this resolver can SEE are a dynamic-
//! dispatch shape -- today, specifically a subscript-call keyed by a
//! non-literal expression, `handlers[computed_key](x)` -- but cannot
//! identify the callee for), and `spans` (comment+docstring byte spans, so
//! a caller can exclude prose the same way the Python path does). A site
//! that is not a call/attribute/subscript at all contributes to NEITHER
//! `candidates` NOR `unresolved` -- that is the genuinely uninteresting
//! case (an ordinary expression), not a missed resolution.
//!
//! ## Disclosed deviations from `frob.vet._capability_python`
//!
//! Three, all narrowing recall in a specific, named, non-silent way (never
//! a behavior this module claims parity with and then quietly drops):
//!
//! 1. **No dangerous-priority import tie-break (T-0659).** The Python
//!    resolver's `_bind_py_name` keeps the MORE DANGEROUS of two
//!    conflicting bindings for the same name (a `try`/`except ImportError`
//!    fallback binding one name to a dangerous import in one branch, a
//!    benign one in the other) -- but deciding "more dangerous" needs the
//!    needle registry, which this extraction-only kernel deliberately does
//!    not consume (see module docstring above). This kernel's import table
//!    is plain last-import-wins instead. Concretely narrower: the exact
//!    try/except-fallback-hides-a-dangerous-import shape T-0659 fixed on
//!    the Python side can still evade detection via this kernel alone,
//!    until a consumer either widens the FFI contract to return every
//!    conflicting binding (letting Python's needle match decide, sound but
//!    a larger change) or keeps running the Python resolver as a fallback
//!    for this one shape. Not attempted here -- this is T-1221's own
//!    scope, not T-1219's consumer-wiring scope.
//! 2. **No `from X import *` wildcard fallback (T-0659).** `_bind_import_
//!    from_statement`'s wildcard branch offers a best-effort `module.name`
//!    resolution for a bare name when a REGISTRY-tracked module was star-
//!    imported -- again registry-dependent, so left out here. A star
//!    import of a dangerous module is simply not modeled by this kernel;
//!    the Python resolver still catches it when it runs.
//! 3. **No tuple/list destructuring alias (T-0659, `f, g = subprocess.run,
//!    os.system`).** Implementable without the registry, but a lower-
//!    value, narrower-recall shape than the two evasions this ticket's
//!    own dispatch named explicitly (`functools.partial` and literal-
//!    keyed dict/list dispatch, both implemented below, T-1626) -- left
//!    as documented future work rather than expanding this portion's
//!    scope further.
//!
//! Everything else mirrors the Python resolver: position-aware scope
//! shadowing (T-0468), scope-local alias copy-propagation including
//! attribute rebinds (T-0659) and default-parameter aliasing (T-0659),
//! `functools.partial` first-positional-argument resolution (T-1626), and
//! literal-string/integer-keyed dict/list container-alias resolution
//! (T-1626).

use std::collections::HashMap;

use pyo3::prelude::*;
use tree_sitter::{Node, Parser};

use crate::extract::python_non_executable_byte_spans;

/// Node kinds that open a new python scope for shadowing purposes --
/// matches `frob.vet._capability_python._PY_SCOPE_TYPES` exactly.
// frob:ticket T-1221
const PY_SCOPE_TYPES: [&str; 3] = ["function_definition", "class_definition", "module"];

/// Sentinel "always shadows" position -- matches `_PY_ALWAYS_SHADOWS`
/// (parameters and nested `def`/`class` names are in scope for the WHOLE
/// enclosing body, regardless of call-site byte position).
// frob:ticket T-1221
const ALWAYS_SHADOWS: i64 = -1;

// frob:ticket T-1221
type ImportTable = HashMap<String, String>;
/// scope node id -> (bound name -> byte position it starts shadowing from)
// frob:ticket T-1221
type ScopeBound = HashMap<usize, HashMap<String, i64>>;
/// scope node id -> (alias key -> resolved dangerous-candidate target)
// frob:ticket T-1221
type AliasTable = HashMap<usize, HashMap<String, String>>;

/// `node`'s source text, or `""` on a UTF-8 boundary failure (never
/// panics) -- this kernel's whole-file never-raises convention applied at
/// the node-text level too.
// frob:ticket T-1221
fn text<'a>(node: Node, source: &'a [u8]) -> &'a str {
    node.utf8_text(source).unwrap_or("")
}

// --------------------------------------------------------------- import table

/// `import X` / `import X as Y` -- matches `_bind_import_statement`.
// frob:ticket T-1221
fn bind_import_statement(node: Node, source: &[u8], table: &mut ImportTable) {
    let mut cursor = node.walk();
    for name_node in node.children_by_field_name("name", &mut cursor) {
        match name_node.kind() {
            "dotted_name" => {
                let full = text(name_node, source);
                let first = full.split('.').next().unwrap_or(full).to_string();
                table.entry(first.clone()).or_insert(first);
            }
            "aliased_import" => {
                let dotted = name_node.child_by_field_name("name");
                let alias = name_node.child_by_field_name("alias");
                if let (Some(d), Some(a)) = (dotted, alias) {
                    table.insert(text(a, source).to_string(), text(d, source).to_string());
                }
            }
            _ => {}
        }
    }
}

/// `from X import Z` / `from X import Z as W` -- matches `_bind_import_
/// from_statement`, MINUS the wildcard-import registry fallback (module
/// docstring, deviation 2).
// frob:ticket T-1221
fn bind_import_from_statement(node: Node, source: &[u8], table: &mut ImportTable) {
    let module_field = node.child_by_field_name("module_name");
    let module_text = module_field.map(|n| text(n, source)).unwrap_or("");
    let mut cursor = node.walk();
    for name_node in node.children_by_field_name("name", &mut cursor) {
        match name_node.kind() {
            "dotted_name" => {
                let imported = text(name_node, source);
                let target = if module_text.is_empty() {
                    imported.to_string()
                } else {
                    format!("{module_text}.{imported}")
                };
                table.insert(imported.to_string(), target);
            }
            "aliased_import" => {
                let dotted = name_node.child_by_field_name("name");
                let alias = name_node.child_by_field_name("alias");
                if let (Some(d), Some(a)) = (dotted, alias) {
                    let imported = text(d, source);
                    let target = if module_text.is_empty() {
                        imported.to_string()
                    } else {
                        format!("{module_text}.{imported}")
                    };
                    table.insert(text(a, source).to_string(), target);
                }
            }
            _ => {}
        }
    }
}

/// The file-wide local-name -> resolved-dotted-target binding table
/// (T-0328) -- matches `_py_import_table`: walks the WHOLE tree, not just
/// top-level statements, so a function-scoped import still contributes.
// frob:ticket T-1221
fn py_import_table(module_node: Node, source: &[u8]) -> ImportTable {
    let mut table = ImportTable::new();
    fn visit(node: Node, source: &[u8], table: &mut ImportTable) {
        match node.kind() {
            "import_statement" => bind_import_statement(node, source, table),
            "import_from_statement" => bind_import_from_statement(node, source, table),
            _ => {}
        }
        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            visit(child, source, table);
        }
    }
    visit(module_node, source, &mut table);
    table
}

// --------------------------------------------------------------- scope shadowing

// frob:ticket T-1221
fn record_binding(bound: &mut HashMap<String, i64>, name: &str, position: i64) {
    match bound.get(name) {
        Some(&existing) => {
            bound.insert(name.to_string(), existing.min(position));
        }
        None => {
            bound.insert(name.to_string(), position);
        }
    }
}

/// Every plain-`identifier` name a `parameters`/`lambda_parameters` child
/// binds, at `ALWAYS_SHADOWS` -- matches `_collect_param_name`.
// frob:ticket T-1221
fn collect_param_name(node: Node, source: &[u8], bound: &mut HashMap<String, i64>) {
    match node.kind() {
        "identifier" => record_binding(bound, text(node, source), ALWAYS_SHADOWS),
        "typed_parameter" | "default_parameter" | "typed_default_parameter"
        | "list_splat_pattern" | "dictionary_splat_pattern" => {
            let mut cursor = node.walk();
            for child in node.children(&mut cursor) {
                if child.kind() == "identifier" {
                    record_binding(bound, text(child, source), ALWAYS_SHADOWS);
                    return;
                }
            }
        }
        _ => {}
    }
}

/// Every name an assignment-style TARGET pattern binds, at `position` --
/// matches `_collect_target_names`: recurses through tuple/list patterns
/// and `as`-pattern wrappers, never through `attribute`/`subscript`
/// targets (those mutate an existing object, they bind no new name).
// frob:ticket T-1221
fn collect_target_names(node: Node, source: &[u8], position: i64, bound: &mut HashMap<String, i64>) {
    match node.kind() {
        "identifier" => {
            record_binding(bound, text(node, source), position);
        }
        "attribute" | "subscript" => {}
        _ => {
            let mut cursor = node.walk();
            for child in node.children(&mut cursor) {
                collect_target_names(child, source, position, bound);
            }
        }
    }
}

/// Every name bound DIRECTLY within `scope_node`, at the byte position it
/// starts shadowing an enclosing import binding from -- matches
/// `_py_scope_bound_names` (T-0468 position-aware fix included: an
/// assignment/`for`/`as`-pattern/walrus target binds at its own node's
/// `start_byte`, never hoisted).
// frob:ticket T-1221
fn py_scope_bound_names(scope_node: Node, source: &[u8]) -> HashMap<String, i64> {
    let mut bound: HashMap<String, i64> = HashMap::new();

    fn walk(node: Node, source: &[u8], is_top: bool, bound: &mut HashMap<String, i64>) {
        let kind = node.kind();
        if !is_top && (kind == "function_definition" || kind == "class_definition") {
            if let Some(name_node) = node.child_by_field_name("name") {
                record_binding(bound, text(name_node, source), ALWAYS_SHADOWS);
            }
            return;
        }
        if !is_top && kind == "lambda" {
            return;
        }
        if kind == "parameters" || kind == "lambda_parameters" {
            let mut cursor = node.walk();
            for child in node.children(&mut cursor) {
                collect_param_name(child, source, bound);
            }
            return;
        }
        if kind == "assignment" || kind == "augmented_assignment" || kind == "for_statement" {
            if let Some(left) = node.child_by_field_name("left") {
                collect_target_names(left, source, node.start_byte() as i64, bound);
            }
        } else if kind == "as_pattern_target" {
            collect_target_names(node, source, node.start_byte() as i64, bound);
        } else if kind == "named_expression" {
            if let Some(name_node) = node.child_by_field_name("name") {
                record_binding(bound, text(name_node, source), node.start_byte() as i64);
            }
        }
        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            walk(child, source, false, bound);
        }
    }

    walk(scope_node, source, true, &mut bound);
    bound
}

/// The nearest LOCAL scope enclosing `site` that binds `name` AT OR BEFORE
/// `site`'s own `start_byte`, or `None` -- matches `_shadowing_scope`
/// (T-0468 position-aware). Returns the scope node ITSELF (not a bare
/// bool) so a caller can look up that scope's alias-table entry.
// frob:ticket T-1221
fn shadowing_scope<'a>(
    name: &str,
    site: Node<'a>,
    source: &[u8],
    scope_cache: &mut HashMap<usize, HashMap<String, i64>>,
) -> Option<Node<'a>> {
    let mut cur = site.parent();
    while let Some(node) = cur {
        if PY_SCOPE_TYPES.contains(&node.kind()) {
            let key = node.id();
            if !scope_cache.contains_key(&key) {
                let bound = py_scope_bound_names(node, source);
                scope_cache.insert(key, bound);
            }
            let position = scope_cache.get(&key).and_then(|b| b.get(name).copied());
            if let Some(pos) = position {
                if site.start_byte() as i64 >= pos {
                    return Some(node);
                }
            }
            if node.kind() == "module" {
                break;
            }
        }
        cur = node.parent();
    }
    None
}

// --------------------------------------------------------------- expression resolution

/// Resolve one expression node (`identifier`/`attribute`/`subscript`/
/// `call`/`assignment`) to its fully-qualified import-bound target, or
/// `None` -- matches `_resolve_py_expr`'s dispatch exactly.
// frob:ticket T-1221
fn resolve_expr(
    node: Node,
    source: &[u8],
    import_table: &ImportTable,
    scope_cache: &mut HashMap<usize, HashMap<String, i64>>,
    alias_table: &AliasTable,
) -> Option<String> {
    match node.kind() {
        "identifier" => resolve_identifier(node, source, import_table, scope_cache, alias_table),
        "attribute" => resolve_attribute(node, source, import_table, scope_cache, alias_table),
        "subscript" => resolve_subscript(node, source, alias_table),
        "call" => resolve_partial_call(node, source, import_table, scope_cache, alias_table),
        "assignment" => {
            let right = node.child_by_field_name("right")?;
            resolve_expr(right, source, import_table, scope_cache, alias_table)
        }
        _ => None,
    }
}

// frob:ticket T-1221
fn resolve_identifier(
    node: Node,
    source: &[u8],
    import_table: &ImportTable,
    scope_cache: &mut HashMap<usize, HashMap<String, i64>>,
    alias_table: &AliasTable,
) -> Option<String> {
    let name = text(node, source);
    if let Some(scope) = shadowing_scope(name, node, source, scope_cache) {
        return alias_table.get(&scope.id()).and_then(|a| a.get(name)).cloned();
    }
    import_table.get(name).cloned()
}

// frob:ticket T-1221
fn resolve_attribute(
    node: Node,
    source: &[u8],
    import_table: &ImportTable,
    scope_cache: &mut HashMap<usize, HashMap<String, i64>>,
    alias_table: &AliasTable,
) -> Option<String> {
    let obj = node.child_by_field_name("object")?;
    let attr = node.child_by_field_name("attribute")?;
    if let Some(resolved_obj) = resolve_expr(obj, source, import_table, scope_cache, alias_table) {
        return Some(format!("{resolved_obj}.{}", text(attr, source)));
    }
    if obj.kind() == "identifier" {
        let key = format!("{}.{}", text(obj, source), text(attr, source));
        return scope_alias_lookup(&key, node, source, alias_table);
    }
    None
}

/// `functools.partial(dangerous, ...)` resolution (T-1626) -- matches
/// `_resolve_py_partial_call`: resolve the callee, and if it is (an alias
/// of) `functools.partial` itself, resolve through its first positional
/// argument.
// frob:ticket T-1221
fn resolve_partial_call(
    node: Node,
    source: &[u8],
    import_table: &ImportTable,
    scope_cache: &mut HashMap<usize, HashMap<String, i64>>,
    alias_table: &AliasTable,
) -> Option<String> {
    let func = node.child_by_field_name("function")?;
    let resolved_func = resolve_expr(func, source, import_table, scope_cache, alias_table)?;
    if resolved_func != "functools.partial" {
        return None;
    }
    let arguments = node.child_by_field_name("arguments")?;
    let target = first_positional_arg(arguments)?;
    resolve_expr(target, source, import_table, scope_cache, alias_table)
}

/// The first POSITIONAL argument node of a `call`'s `arguments` field --
/// matches `_first_py_positional_arg`.
// frob:ticket T-1221
fn first_positional_arg(arguments_node: Node) -> Option<Node> {
    let mut cursor = arguments_node.walk();
    for child in arguments_node.children(&mut cursor) {
        if !child.is_named() {
            continue;
        }
        if matches!(child.kind(), "keyword_argument" | "dictionary_splat" | "list_splat") {
            continue;
        }
        return Some(child);
    }
    None
}

/// Literal text a dict `pair`'s `key` (or list-element position) can be
/// looked up by (T-1626) -- a `string` node's decoded content, or an
/// `integer` node's digit text verbatim. `None` for any computed key
/// (OPAQUE001's job, not this resolver's) -- matches `_py_literal_key_text`.
// frob:ticket T-1221
fn literal_key_text(node: Node, source: &[u8]) -> Option<String> {
    match node.kind() {
        "string" => {
            let mut content = String::new();
            let mut cursor = node.walk();
            for child in node.children(&mut cursor) {
                if child.kind() == "string_content" {
                    content.push_str(text(child, source));
                }
            }
            Some(content)
        }
        "integer" => Some(text(node, source).to_string()),
        _ => None,
    }
}

/// Walk `site`'s enclosing scope chain looking up `key` in each scope's
/// alias-table entry -- matches `_py_scope_alias_lookup`.
// frob:ticket T-1221
fn scope_alias_lookup(key: &str, site: Node, _source: &[u8], alias_table: &AliasTable) -> Option<String> {
    let mut cur = site.parent();
    while let Some(node) = cur {
        if PY_SCOPE_TYPES.contains(&node.kind()) {
            if let Some(found) = alias_table.get(&node.id()).and_then(|a| a.get(key)) {
                return Some(found.clone());
            }
            if node.kind() == "module" {
                break;
            }
        }
        cur = node.parent();
    }
    None
}

/// Resolve a `subscript` node (`d["run"]`/`lst[0]`) through the dict/list
/// container-alias entries `record_container_aliases` recorded (T-1626) --
/// matches `_resolve_py_subscript`. `is_dynamic_dispatch_site` is this
/// module's own addition (not in the Python original): a caller uses it to
/// tell "not a capability site" apart from "a real dispatch we could not
/// resolve" (module docstring's UNRESOLVED requirement).
// frob:ticket T-1221
fn resolve_subscript(node: Node, source: &[u8], alias_table: &AliasTable) -> Option<String> {
    let value = node.child_by_field_name("value")?;
    let key_node = node.child_by_field_name("subscript")?;
    if value.kind() != "identifier" {
        return None;
    }
    let key_text = literal_key_text(key_node, source)?;
    let key = format!("{}[{key_text}]", text(value, source));
    scope_alias_lookup(&key, node, source, alias_table)
}

/// True iff `node` (a `call`'s `function` field, or a `subscript` node
/// generally) is a subscript whose key is NOT a literal string/integer --
/// the shape `resolve_subscript` structurally cannot resolve, distinct
/// from "not a dispatch site at all". This is exactly the shape
/// `frob.gates._opaque`'s OPAQUE001 already treats fail-closed on the
/// Python side (`_subscript_key_looks_literal`) -- this kernel surfaces
/// the SAME judgment as an explicit UNRESOLVED candidate instead of
/// silently omitting it, per the module docstring's UNRESOLVED
/// requirement.
// frob:waive DUP001 reason="the r2 structural match is against \
// walk_leaves/collect_comment_nodes (this same crate, unrelated shape: an \
// early-return-on-node-kind tree walk), anti_unify_core (a lockstep two-tree \
// Plotkin-lgg walk), and four strata-core recursive-descent parser methods -- none \
// share this function's actual logic (an is-a-non-literal-subscript-key predicate \
// with no recursion at all); the r2 rung matches on generic Option-chaining \
// control-flow shape only, a coincidental match class this size of function is prone \
// to, not a real code duplication to extract a helper from"
// frob:ticket T-1221
fn is_dynamic_dispatch_subscript(node: Node, source: &[u8]) -> bool {
    if node.kind() != "subscript" {
        return false;
    }
    let Some(value) = node.child_by_field_name("value") else {
        return false;
    };
    if value.kind() != "identifier" {
        return false;
    }
    let Some(key_node) = node.child_by_field_name("subscript") else {
        return false;
    };
    literal_key_text(key_node, source).is_none()
}

// --------------------------------------------------------------- alias table

/// `mod.run = subprocess.run` / `x = subprocess.run` / dict-and-list
/// container aliases (T-1626) / default-parameter aliases (T-0659) --
/// scope-local copy-propagation table matching `_build_py_alias_table`.
/// Sound for may-analysis by design (first resolution wins per scope, see
/// `_build_py_alias_table`'s own docstring for why a later benign
/// reassignment does not clear an earlier dangerous one).
// frob:ticket T-1221
fn build_alias_table(
    module_node: Node,
    source: &[u8],
    import_table: &ImportTable,
    scope_cache: &mut HashMap<usize, HashMap<String, i64>>,
) -> AliasTable {
    let mut alias_table: AliasTable = AliasTable::new();

    fn visit(
        node: Node,
        source: &[u8],
        import_table: &ImportTable,
        scope_cache: &mut HashMap<usize, HashMap<String, i64>>,
        alias_table: &mut AliasTable,
    ) {
        if node.kind() == "assignment" {
            record_alias(node, source, import_table, scope_cache, alias_table);
        } else if node.kind() == "function_definition" {
            record_default_param_aliases(node, source, import_table, scope_cache, alias_table);
        }
        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            visit(child, source, import_table, scope_cache, alias_table);
        }
    }

    visit(module_node, source, import_table, scope_cache, &mut alias_table);
    alias_table
}

// frob:ticket T-1221
fn record_default_param_aliases(
    func_node: Node,
    source: &[u8],
    import_table: &ImportTable,
    scope_cache: &mut HashMap<usize, HashMap<String, i64>>,
    alias_table: &mut AliasTable,
) {
    let Some(params) = func_node.child_by_field_name("parameters") else {
        return;
    };
    let mut cursor = params.walk();
    let mut pending: Vec<(String, String)> = Vec::new();
    for param in params.children(&mut cursor) {
        if !matches!(param.kind(), "default_parameter" | "typed_default_parameter") {
            continue;
        }
        let Some(name_node) = param.child_by_field_name("name") else {
            continue;
        };
        let Some(value_node) = param.child_by_field_name("value") else {
            continue;
        };
        // Read-only borrow of alias_table (snapshotted below) so the
        // resolve call and the eventual insert never alias-conflict --
        // matches the Python original resolving against the table as
        // built so far.
        if let Some(resolved) = resolve_expr(value_node, source, import_table, scope_cache, alias_table) {
            pending.push((text(name_node, source).to_string(), resolved));
        }
    }
    if pending.is_empty() {
        return;
    }
    let scope_aliases = alias_table.entry(func_node.id()).or_default();
    for (name, resolved) in pending {
        scope_aliases.entry(name).or_insert(resolved);
    }
}

// frob:ticket T-1221
fn enclosing_scope(node: Node) -> Option<Node> {
    let mut cur = node.parent();
    while let Some(n) = cur {
        if PY_SCOPE_TYPES.contains(&n.kind()) {
            return Some(n);
        }
        cur = n.parent();
    }
    None
}

// frob:ticket T-1221
fn record_alias(
    node: Node,
    source: &[u8],
    import_table: &ImportTable,
    scope_cache: &mut HashMap<usize, HashMap<String, i64>>,
    alias_table: &mut AliasTable,
) {
    let Some(left) = node.child_by_field_name("left") else {
        return;
    };
    let Some(right) = node.child_by_field_name("right") else {
        return;
    };
    let Some(scope) = enclosing_scope(node) else {
        return;
    };
    let scope_id = scope.id();

    if left.kind() == "attribute" {
        // T-0659: attribute-target rebind (`mod.run = subprocess.run`).
        let (Some(obj), Some(attr)) =
            (left.child_by_field_name("object"), left.child_by_field_name("attribute"))
        else {
            return;
        };
        if obj.kind() != "identifier" {
            return;
        }
        if let Some(resolved) = resolve_expr(right, source, import_table, scope_cache, alias_table) {
            let key = format!("{}.{}", text(obj, source), text(attr, source));
            alias_table.entry(scope_id).or_default().entry(key).or_insert(resolved);
        }
        return;
    }
    if left.kind() == "identifier" && right.kind() == "dictionary" {
        record_dict_container_alias(left, right, source, import_table, scope_cache, alias_table, scope_id);
        return;
    }
    if left.kind() == "identifier" && right.kind() == "list" {
        record_list_container_alias(left, right, source, import_table, scope_cache, alias_table, scope_id);
        return;
    }
    if left.kind() != "identifier" {
        return;
    }
    if let Some(resolved) = resolve_expr(right, source, import_table, scope_cache, alias_table) {
        alias_table
            .entry(scope_id)
            .or_default()
            .entry(text(left, source).to_string())
            .or_insert(resolved);
    }
}

/// `d = {"run": subprocess.run}` -- matches `_record_py_dict_container_alias`.
// frob:ticket T-1221
fn record_dict_container_alias(
    left: Node,
    right: Node,
    source: &[u8],
    import_table: &ImportTable,
    scope_cache: &mut HashMap<usize, HashMap<String, i64>>,
    alias_table: &mut AliasTable,
    scope_id: usize,
) {
    let name = text(left, source).to_string();
    let mut cursor = right.walk();
    let mut pending: Vec<(String, String)> = Vec::new();
    for pair in right.children(&mut cursor) {
        if pair.kind() != "pair" {
            continue;
        }
        let (Some(key_node), Some(value_node)) =
            (pair.child_by_field_name("key"), pair.child_by_field_name("value"))
        else {
            continue;
        };
        let Some(key_text) = literal_key_text(key_node, source) else {
            continue;
        };
        if let Some(resolved) = resolve_expr(value_node, source, import_table, scope_cache, alias_table) {
            pending.push((format!("{name}[{key_text}]"), resolved));
        }
    }
    let scope_aliases = alias_table.entry(scope_id).or_default();
    for (key, resolved) in pending {
        scope_aliases.entry(key).or_insert(resolved);
    }
}

/// `lst = [subprocess.run]` -- matches `_record_py_list_container_alias`.
// frob:ticket T-1221
fn record_list_container_alias(
    left: Node,
    right: Node,
    source: &[u8],
    import_table: &ImportTable,
    scope_cache: &mut HashMap<usize, HashMap<String, i64>>,
    alias_table: &mut AliasTable,
    scope_id: usize,
) {
    let name = text(left, source).to_string();
    let mut cursor = right.walk();
    let mut index: usize = 0;
    let mut pending: Vec<(String, String)> = Vec::new();
    for element in right.children(&mut cursor) {
        if !element.is_named() {
            continue;
        }
        if let Some(resolved) = resolve_expr(element, source, import_table, scope_cache, alias_table) {
            pending.push((format!("{name}[{index}]"), resolved));
        }
        index += 1;
    }
    let scope_aliases = alias_table.entry(scope_id).or_default();
    for (key, resolved) in pending {
        scope_aliases.entry(key).or_insert(resolved);
    }
}

// --------------------------------------------------------------- candidate walk

/// Recursively walk `node`, appending `(resolved, start_byte, end_byte)`
/// to `candidates` for every call/attribute/subscript site that resolves,
/// and `(start_byte, end_byte)` to `unresolved` for every call site whose
/// callee is a dynamic-dispatch subscript this resolver cannot follow
/// (module docstring's UNRESOLVED requirement) -- matches
/// `_collect_py_candidates`'s recursion shape, extended with the
/// unresolved branch that has no Python-side counterpart.
// frob:waive DUP001 reason="the r2 structural match is against \
// walk_leaves/collect_comment_nodes (this same crate's generic child-recursion shape, \
// a different traversal with a different payload), anti_unify_core (a lockstep \
// two-tree walk over TWO trees, not one), and four strata-core recursive-descent \
// parser methods (grammar productions, an unrelated domain) -- none share this \
// function's actual per-node dispatch logic (call/attribute/subscript \
// candidate-vs-unresolved classification against import/alias tables); the r2 rung \
// matches on the generic 'match on node.kind(), recurse into children' shape every \
// tree-sitter walker in this crate necessarily has, not a real duplication to extract \
// a helper from"
// frob:ticket T-1221
fn collect_candidates(
    node: Node,
    source: &[u8],
    import_table: &ImportTable,
    scope_cache: &mut HashMap<usize, HashMap<String, i64>>,
    alias_table: &AliasTable,
    candidates: &mut Vec<(String, usize, usize)>,
    unresolved: &mut Vec<(usize, usize)>,
) {
    if node.kind() == "call" {
        if let Some(func) = node.child_by_field_name("function") {
            if matches!(func.kind(), "identifier" | "attribute" | "subscript") {
                match resolve_expr(func, source, import_table, scope_cache, alias_table) {
                    Some(resolved) => {
                        candidates.push((resolved, node.start_byte(), node.end_byte()));
                    }
                    None => {
                        if is_dynamic_dispatch_subscript(func, source) {
                            unresolved.push((node.start_byte(), node.end_byte()));
                        }
                    }
                }
            }
        }
    } else if matches!(node.kind(), "attribute" | "subscript") {
        if let Some(resolved) = resolve_expr(node, source, import_table, scope_cache, alias_table) {
            candidates.push((resolved, node.start_byte(), node.end_byte()));
        }
    }
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        collect_candidates(
            child, source, import_table, scope_cache, alias_table, candidates, unresolved,
        );
    }
}

/// Pure compute: the full T-1221 resolver pipeline over one python source
/// buffer -- import table, alias table, and the candidate/unresolved walk.
/// Empty everything (never a panic) if `source` fails to parse, or parses
/// as a language other than python.
// frob:ticket T-1221
fn scan_python_source(
    source: &[u8],
) -> (Vec<(String, usize, usize)>, Vec<(usize, usize)>, Vec<(usize, usize)>) {
    let mut parser = Parser::new();
    let language = tree_sitter_python::LANGUAGE.into();
    if parser.set_language(&language).is_err() {
        return (Vec::new(), Vec::new(), Vec::new());
    }
    let Some(tree) = parser.parse(source, None) else {
        return (Vec::new(), Vec::new(), Vec::new());
    };
    let root = tree.root_node();

    let import_table = py_import_table(root, source);
    let mut scope_cache: HashMap<usize, HashMap<String, i64>> = HashMap::new();
    let alias_table = build_alias_table(root, source, &import_table, &mut scope_cache);

    let mut candidates: Vec<(String, usize, usize)> = Vec::new();
    let mut unresolved: Vec<(usize, usize)> = Vec::new();
    collect_candidates(
        root,
        source,
        &import_table,
        &mut scope_cache,
        &alias_table,
        &mut candidates,
        &mut unresolved,
    );

    let spans = python_non_executable_byte_spans(source);
    (candidates, unresolved, spans)
}

/// FFI entry point (T-1221): rust capability-scan resolver for python
/// source. `source` is the raw file bytes; returns `(candidates,
/// unresolved, spans)`:
/// - `candidates`: `(resolved_dotted_target, start_byte, end_byte)` for
///   every call/attribute/subscript site this resolver could identify --
///   the caller (Python-side, T-1219 follow-up) matches each `resolved`
///   string against `frob.vet._capability_registry.DANGEROUS_OPERATIONS`'s
///   needles exactly as `_python_binding_capabilities`/`_python_binding_
///   operations` do today; this kernel makes no dangerous/benign judgment
///   itself (module docstring).
/// - `unresolved`: `(start_byte, end_byte)` for every call site this
///   resolver can see is a dynamic-dispatch shape (a subscript keyed by a
///   non-literal expression) but cannot identify the callee for -- a loud,
///   explicit "cannot resolve" outcome, never silently folded into "no
///   capability" (module docstring's UNRESOLVED requirement; a WIDER
///   contract than the ticket's own `(candidates, spans)` floor,
///   disclosed and intentional).
/// - `spans`: comment+docstring byte spans (T-0209/T-0769), matching
///   `frob.vet._capability_core._non_executable_byte_spans`'s contract,
///   so a caller can exclude prose exactly as the Python path does.
///
/// Never raises (this crate's whole-file convention): a buffer tree-
/// sitter cannot parse, or one that does not parse as python, yields three
/// empty lists rather than a `PyErr`.
// frob:doc docs/modules/vet.md#public-api
// frob:ticket T-1221
#[pyfunction]
pub fn scan_python_capabilities(
    source: Vec<u8>,
) -> (Vec<(String, usize, usize)>, Vec<(usize, usize)>, Vec<(usize, usize)>) {
    scan_python_source(&source)
}
