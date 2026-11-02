//! The shell adapter (fidelity F1): tree-sitter tree to a U term of function units.
//!
//! # Mapping (rho)
//!
//! - The file is a `unit(file, impl)`. Each function definition (`f() { ... }` or
//!   `function f { ... }`) is one `unit(function)` named after the function; its body is one `lit`
//!   of its source text. Every function is `public`: a script has no visibility.
//! - Commands, aliases and redirections are not units; they are read by the command-word scanner
//!   ([`crate::shell_uses`]), not folded into the term.
//! - Syntax errors become `hole(parse-error)` nodes, so the file reads as a partial parse.

// frob:ticket 01M6CN4WNECMHQ1T65JT6CSE34

use gob_ir::{NodeId, NodeSpec, Operator, ScopeGraph, TermError};
use gob_languages::{Language, ParseLimits, ParseResult, grammar_identity, parse};
use tree_sitter::Node;

use crate::adapter::{
    Adapter, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded, Lang,
};
use crate::fold::{Cx, base_file, children, failed_file, file_root_spec, text_of};
use crate::pipeline::EXTRACTOR_VERSION;
use crate::view::{self, ATTR_VISIBILITY, HOLE_MISSING, HOLE_PARSE_ERROR, Naming};

type R<T> = Result<T, TermError>;

/// The adapter tag (`shell`), as `path_uses` and the binder spell it.
const TAG: &str = "shell";

/// The shell adapter.
#[derive(Debug, Clone, Copy, Default)]
pub struct ShellAdapter;

impl Adapter for ShellAdapter {
    fn language(&self) -> &'static str {
        TAG
    }

    fn identity(&self) -> String {
        format!(
            "gob-symbols/v{EXTRACTOR_VERSION}/{}",
            grammar_identity(Language::Shell)
        )
    }

    fn fidelity(&self) -> Fidelity {
        gob_caps::lang_fidelity(Lang::Shell)
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::for_lang(Lang::Shell)
    }

    fn parse(&self, text: &str, limits: &ParseLimits) -> ConcreteTree {
        match parse(Language::Shell, text, limits) {
            ParseResult::Parsed(t) => ConcreteTree::Parsed(t),
            ParseResult::Unresolved(u) => {
                tracing::debug!(reason = ?u.reason, "shell file not parsed");
                ConcreteTree::Unparsed(u.reason)
            }
        }
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        match tree {
            ConcreteTree::Parsed(t) => fold_tree(&t.text, t.root(), input),
            ConcreteTree::Unparsed(reason) => failed_file(input, TAG, *reason),
            ConcreteTree::Leaf | ConcreteTree::Source(_) => failed_file(
                input,
                TAG,
                gob_languages::UnresolvedReason::GrammarUnavailable,
            ),
        }
    }
}

/// True when `path` is a shell script (`.sh` or `.bash`, any case).
pub fn is_shell_path(path: &str) -> bool {
    std::path::Path::new(path)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("sh") || e.eq_ignore_ascii_case("bash"))
}

/// Folds a parsed shell file into one unit per function definition.
fn fold_tree(text: &str, root: Node<'_>, input: &FileInput<'_>) -> Result<Folded, FoldError> {
    let mut cx = Cx::new(input.path, TAG, text);
    let mut kids = Vec::new();
    for n in children(root) {
        match n.kind() {
            "function_definition" => {
                if let Some(name) = n.child_by_field_name("name") {
                    kids.push(unit(&mut cx, text, n, text_of(text, name))?);
                }
            }
            "ERROR" => kids.push(hole(&mut cx, n)?),
            _ if n.is_missing() => kids.push(hole(&mut cx, n)?),
            _ => {}
        }
    }
    let spec = file_root_spec(&cx, input.size as usize);
    let root_id = cx.add(spec, &kids)?;
    let term = cx.b.finish(root_id)?;
    let scopes = ScopeGraph::from_term(&term);
    let v = view::build(&term, input.path, Naming::Model);
    let mut file = base_file(input, TAG);
    file.fidelity = Fidelity::F1;
    file.parse_status = view::parse_status_of(&term);
    file.symbols = v.symbols;
    file.extras = v.extras;
    tracing::debug!(
        path = input.path,
        symbols = file.symbols.len(),
        "shell file folded"
    );
    Ok(Folded { term, scopes, file })
}

/// One function unit spanning `n` whose body is its source text.
fn unit(cx: &mut Cx<'_>, text: &str, n: Node<'_>, name: &str) -> R<NodeId> {
    let body = cx.lit("text", text_of(text, n), n)?;
    let spec = NodeSpec::new(Operator::unit("function", "impl"), cx.node_loc(n))
        .named(name)
        .attr(ATTR_VISIBILITY, "public");
    cx.add(spec, &[body])
}

/// A hole for a syntax error or missing token.
fn hole(cx: &mut Cx<'_>, n: Node<'_>) -> R<NodeId> {
    let kind = if n.is_missing() {
        HOLE_MISSING
    } else {
        HOLE_PARSE_ERROR
    };
    cx.op(Operator::hole(kind), n, &[])
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fold_src(src: &str) -> Folded {
        let a = ShellAdapter;
        let tree = a.parse(src, &ParseLimits::default());
        let input = FileInput {
            path: "run.sh",
            digest: "d",
            size: u32::try_from(src.len()).expect("small"),
        };
        a.fold(&tree, &input).expect("fold")
    }

    // frob:tests crates/gob-symbols/src/shell.rs::ShellAdapter
    #[test]
    fn folds_function_definitions() {
        let f = fold_src("#!/bin/sh\nrun() { rm -rf x; }\nfunction go { echo hi; }\necho top\n");
        let names: Vec<String> = f
            .file
            .symbols
            .iter()
            .map(|s| s.symref.to_string())
            .collect();
        for want in ["run.sh::run", "run.sh::go"] {
            assert!(names.iter().any(|n| n == want), "{want} in {names:?}");
        }
        assert_eq!(f.file.language, "shell");
    }

    // frob:tests crates/gob-symbols/src/shell.rs::is_shell_path
    #[test]
    fn claims_shell_files() {
        assert!(is_shell_path("a/b.sh"));
        assert!(is_shell_path("A.BASH"));
        assert!(!is_shell_path("a.shx"));
    }
}
