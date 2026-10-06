//! Scope helpers of the TypeScript adapter: the names a pattern, a parameter list or a function body binds.
//!
//! Scoping is function-level: every `let`, `const`, `var`, class and catch name declared anywhere in a
//! function body (outside nested functions) is one binder of that function. A block-scoped name that shadows
//! an outer one therefore hides it for the whole function, which can only turn a resolved call into an
//! Unknown local-value call, never into a wrong target.

// frob:ticket 01M43ARXMH7RJ63G8096KKJF80

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

/// Appends the names the statements under `n` declare in the enclosing function scope.
///
/// Declarators whose node id is in `skip` are units (module-level functions and constants), not binders.
pub(super) fn walk_binders(n: Node<'_>, text: &str, skip: &HashSet<usize>, out: &mut Vec<String>) {
    match n.kind() {
        k if SCOPE_KINDS.contains(&k) => return,
        "class_declaration" | "abstract_class_declaration" | "class" => {
            // A nested class is a unit; its heritage runs in this scope but binds nothing.
            return;
        }
        "variable_declarator" => {
            if !skip.contains(&n.id())
                && !is_module_binding(n, text)
                && let Some(name) = n.child_by_field_name("name")
            {
                pattern_names(name, text, out);
            }
        }
        "catch_clause" => {
            if let Some(p) = n.child_by_field_name("parameter") {
                pattern_names(p, text, out);
            }
        }
        "for_in_statement" => {
            if n.child_by_field_name("kind").is_some()
                && let Some(l) = n.child_by_field_name("left")
            {
                pattern_names(l, text, out);
            }
        }
        _ => {}
    }
    for c in children(n) {
        walk_binders(c, text, skip, out);
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
        walk_binders(*s, text, skip, &mut names);
    }
    names.sort();
    names.dedup();
    names
}
