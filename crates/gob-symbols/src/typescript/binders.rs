//! Scope helpers of the TypeScript adapter: the names a pattern, a parameter list or a function body binds.
//!
//! A function scope binds its parameters, every `var` anywhere in its body (hoisted, outside nested
//! functions) and the `let` and `const` names declared directly in its statement list. A block, a `for`
//! head, a `catch` clause and a `switch` body are scopes of their own and bind the `let` and `const` names
//! declared directly in them, so a block-scoped name shadows an outer one only inside its block.
//! Declarations are not ordered: a use before the declaration (the temporal dead zone) still binds to the
//! block binder, as it does at run time.

// frob:ticket 01M43ARXMH7RJ63G8096KKJF80
// frob:ticket 01M4828JQJKETWWCRQGJCXJ4VH

use std::collections::HashSet;

use tree_sitter::Node;

use crate::fold::{children, text_of};

/// Kinds that start a new function scope: the walk of a body does not enter them.
const SCOPE_KINDS: [&str; 9] = [
    "function_declaration",
    "generator_function_declaration",
    "function_expression",
    "function",
    "generator_function",
    "arrow_function",
    "method_definition",
    "class_body",
    "class_static_block",
];

/// Appends every identifier the binding pattern `n` declares (not defaults, keys or type annotations).
pub(super) fn pattern_names(n: Node<'_>, text: &str, out: &mut Vec<String>) {
    match n.kind() {
        "identifier" | "shorthand_property_identifier_pattern" => {
            out.push(text_of(text, n).to_owned());
        }
        "pair_pattern" => {
            if let Some(v) = n.child_by_field_name("value") {
                pattern_names(v, text, out);
            }
        }
        "assignment_pattern" | "object_assignment_pattern" => {
            if let Some(l) = n.child_by_field_name("left") {
                pattern_names(l, text, out);
            }
        }
        "required_parameter" | "optional_parameter" => {
            if let Some(p) = n.child_by_field_name("pattern") {
                pattern_names(p, text, out);
            }
        }
        "formal_parameters" | "object_pattern" | "array_pattern" | "rest_pattern" => {
            for c in children(n) {
                pattern_names(c, text, out);
            }
        }
        _ => {}
    }
}

/// The parameter names of function-like `f` (an arrow's lone `parameter`, or its `parameters`).
pub(super) fn param_names(f: Node<'_>, text: &str) -> Vec<String> {
    let mut out = Vec::new();
    if let Some(p) = f.child_by_field_name("parameters") {
        pattern_names(p, text, &mut out);
    }
    if let Some(p) = f.child_by_field_name("parameter") {
        pattern_names(p, text, &mut out);
    }
    out
}

/// True when declarator `d` binds the result of `require("m")`, `import("m")` or a member of one: an import binding.
pub(super) fn is_module_binding(d: Node<'_>, text: &str) -> bool {
    let Some(mut value) = d.child_by_field_name("value") else {
        return false;
    };
    loop {
        match value.kind() {
            "await_expression" | "parenthesized_expression" => {
                let Some(i) = children(value)
                    .into_iter()
                    .find(|c| c.is_named() && c.kind() != "comment")
                else {
                    return false;
                };
                value = i;
            }
            "member_expression" => {
                let Some(o) = value.child_by_field_name("object") else {
                    return false;
                };
                value = o;
            }
            "call_expression" => {
                return value.child_by_field_name("function").is_some_and(|f| {
                    f.kind() == "import"
                        || (f.kind() == "identifier" && text_of(text, f) == "require")
                });
            }
            _ => return false,
        }
    }
}

/// Appends the declarator names of lexical declaration `d` that are not in `skip` or module bindings.
fn declarator_names(d: Node<'_>, text: &str, skip: &HashSet<usize>, out: &mut Vec<String>) {
    for c in children(d) {
        if c.kind() == "variable_declarator"
            && !skip.contains(&c.id())
            && !is_module_binding(c, text)
            && let Some(name) = c.child_by_field_name("name")
        {
            pattern_names(name, text, out);
        }
    }
}

/// True when `n` is the `let`/`const` kind of a `for ... in/of` head (`var` and a bare target are not).
fn is_lexical_for_in(n: Node<'_>, text: &str) -> bool {
    n.child_by_field_name("kind")
        .is_some_and(|k| matches!(text_of(text, k), "let" | "const"))
}

/// Appends the names the statements under `n` declare in the enclosing function scope.
///
/// `var` names are collected at any depth; `let` and `const` names only when `lexical` (`n` is a statement
/// of the scope itself, not of a nested block). Declarators whose node id is in `skip` are units
/// (module-level functions and constants), not binders.
fn walk_binders(
    n: Node<'_>,
    text: &str,
    skip: &HashSet<usize>,
    lexical: bool,
    out: &mut Vec<String>,
) {
    match n.kind() {
        k if SCOPE_KINDS.contains(&k) => return,
        "class_declaration" | "abstract_class_declaration" | "class" => {
            // A nested class is a unit; its heritage runs in this scope but binds nothing.
            return;
        }
        "variable_declaration" => declarator_names(n, text, skip, out),
        "lexical_declaration" if lexical => declarator_names(n, text, skip, out),
        "for_in_statement" => {
            if n.child_by_field_name("kind").is_some()
                && !is_lexical_for_in(n, text)
                && let Some(l) = n.child_by_field_name("left")
            {
                pattern_names(l, text, out);
            }
        }
        _ => {}
    }
    // Only an `export` wrapper keeps its child a statement of the same scope.
    let keep = lexical && n.kind() == "export_statement";
    for c in children(n) {
        walk_binders(c, text, skip, keep, out);
    }
}

/// The sorted, unique binder names of a scope with `seed` (its parameters) and statements `body`.
pub(super) fn scope_binders(
    seed: Vec<String>,
    body: &[Node<'_>],
    text: &str,
    skip: &HashSet<usize>,
) -> Vec<String> {
    let mut names = seed;
    for s in body {
        walk_binders(*s, text, skip, true, &mut names);
    }
    names.sort();
    names.dedup();
    names
}

/// The names the block-level scope node `n` binds (empty when `n` opens no scope or binds nothing).
///
/// Covers a `statement_block`, a `for` head, a `catch` clause and a `switch` body. A function body is
/// not one: its statements are the function scope's own.
pub(super) fn block_scope_names(n: Node<'_>, text: &str) -> Vec<String> {
    let mut names = Vec::new();
    let none = HashSet::new();
    let mut lexical_in = |stmts: &[Node<'_>]| {
        for s in stmts {
            let decl = if s.kind() == "export_statement" {
                s.child_by_field_name("declaration")
            } else {
                Some(*s)
            };
            if let Some(d) = decl.filter(|d| d.kind() == "lexical_declaration") {
                declarator_names(d, text, &none, &mut names);
            }
        }
    };
    match n.kind() {
        "statement_block" => lexical_in(&children(n)),
        "switch_body" => {
            for case in children(n) {
                lexical_in(&children(case));
            }
        }
        "for_statement" => {
            if let Some(i) = n.child_by_field_name("initializer") {
                lexical_in(&[i]);
            }
        }
        "for_in_statement" => {
            if is_lexical_for_in(n, text)
                && let Some(l) = n.child_by_field_name("left")
            {
                pattern_names(l, text, &mut names);
            }
        }
        "catch_clause" => {
            if let Some(p) = n.child_by_field_name("parameter") {
                pattern_names(p, text, &mut names);
            }
        }
        _ => {}
    }
    names.sort();
    names.dedup();
    names
}
