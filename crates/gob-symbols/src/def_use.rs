//! Per-language [`DefUseSyntax`] tables and the entry point that runs the shared def-use engine
//! over a folded artifact (cohesion.md 1.1: the input of COH001).

// frob:ticket 01M4CXSPADQCCZ40KNYPAFVSV6

use gob_ir::{DefUseEdge, DefUseSyntax, NodeId};

use crate::adapter::Folded;

/// The Rust adapter's operator names.
pub const RUST_SYNTAX: DefUseSyntax = DefUseSyntax {
    assign: &[
        ("assignment_expression", false),
        ("compound_assignment_expr", true),
    ],
    declarators: &[],
    members: &["field_expression"],
    indexes: &["index_expression"],
    branches: &["if_expression", "match_expression"],
    alternatives: &["else_clause", "match_arm"],
    arm_containers: &["match_block"],
    else_ops: &["else_clause"],
    exhaustive: &["match_expression"],
    loops: &["for_expression", "while_expression", "loop_expression"],
    loop_binds: &["for"],
    arm_binds: &["pattern"],
    dynamic_setters: &[],
    splats: &[],
};

/// The Python adapter's operator names.
pub const PYTHON_SYNTAX: DefUseSyntax = DefUseSyntax {
    assign: &[("assignment", false), ("augmented_assignment", true)],
    declarators: &[],
    members: &["attribute"],
    indexes: &["subscript"],
    branches: &["if_statement", "match_statement", "try_statement"],
    alternatives: &[
        "block",
        "elif_clause",
        "else_clause",
        "except_clause",
        "case_clause",
    ],
    arm_containers: &[],
    else_ops: &["else_clause"],
    exhaustive: &[],
    loops: &["for_statement", "while_statement"],
    loop_binds: &[],
    arm_binds: &[],
    dynamic_setters: &["setattr"],
    splats: &["dictionary_splat", "list_splat"],
};

/// The TypeScript adapter's operator names.
pub const TYPESCRIPT_SYNTAX: DefUseSyntax = DefUseSyntax {
    assign: &[
        ("assignment_expression", false),
        ("augmented_assignment_expression", true),
    ],
    declarators: &["variable_declarator"],
    members: &["member_expression"],
    indexes: &["subscript_expression"],
    branches: &["if_statement", "switch_statement", "try_statement"],
    alternatives: &[
        "statement_block",
        "else_clause",
        "switch_case",
        "switch_default",
        "catch_clause",
    ],
    arm_containers: &["switch_body"],
    else_ops: &["else_clause", "switch_default"],
    exhaustive: &[],
    loops: &[
        "for_statement",
        "for_in_statement",
        "while_statement",
        "do_statement",
    ],
    loop_binds: &[],
    arm_binds: &[],
    dynamic_setters: &["setattr"],
    splats: &["spread_element"],
};

/// The syntax table for a language tag (`rust`, `python`, `typescript`), if def-use supports it.
pub fn syntax_for(lang: &str) -> Option<&'static DefUseSyntax> {
    match lang {
        "rust" => Some(&RUST_SYNTAX),
        "python" => Some(&PYTHON_SYNTAX),
        "typescript" => Some(&TYPESCRIPT_SYNTAX),
        _ => None,
    }
}

/// Def-use edges of `unit` in a folded artifact; `None` for a language without a syntax table.
pub fn def_use_of(folded: &Folded, lang: &str, unit: NodeId) -> Option<Vec<DefUseEdge>> {
    let syntax = syntax_for(lang)?;
    Some(gob_ir::def_use(&folded.term, &folded.scopes, unit, syntax))
}
