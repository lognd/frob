//! The Java adapter (fidelity F1): tree-sitter tree to a U term of type and method declarations.
//!
//! # Mapping (rho)
//!
//! - The file is a `unit(file, impl)`. Each top-level `class`, `interface`, `enum`, `record` and
//!   `@interface` is one unit spanning the declaration; each method and constructor directly in
//!   its body is a `unit(method)` named `Type.name`. A unit's body is one `lit` of its source text.
//! - A unit is `public` when its modifiers say `public` or `protected`, else `private`.
//! - Imports are not units; they are read by the import-resolved capability scanner
//!   ([`crate::java_uses`]), not folded into the term.
//! - Syntax errors become `hole(parse-error)` nodes, so the file reads as a partial parse.

// frob:ticket 01M64VBRFWT0EKCG800ANRZDTE

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

/// The Java adapter.
#[derive(Debug, Clone, Copy, Default)]
pub struct JavaAdapter;

impl Adapter for JavaAdapter {
    fn language(&self) -> &'static str {
        "java"
    }

    fn identity(&self) -> String {
        format!(
            "gob-symbols/v{EXTRACTOR_VERSION}/{}",
            grammar_identity(Language::Java)
        )
    }

    fn fidelity(&self) -> Fidelity {
        gob_caps::lang_fidelity(Lang::Java)
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::for_lang(Lang::Java)
    }

    fn parse(&self, text: &str, limits: &ParseLimits) -> ConcreteTree {
        match parse(Language::Java, text, limits) {
            ParseResult::Parsed(t) => ConcreteTree::Parsed(t),
            ParseResult::Unresolved(u) => ConcreteTree::Unparsed(u.reason),
        }
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        match tree {
            ConcreteTree::Parsed(t) => fold_tree(&t.text, t.root(), input),
            ConcreteTree::Unparsed(reason) => failed_file(input, "java", *reason),
            ConcreteTree::Leaf | ConcreteTree::Source(_) => failed_file(
                input,
                "java",
                gob_languages::UnresolvedReason::GrammarUnavailable,
            ),
        }
    }
}

/// True when `path` is a Java source file (`.java`, any case).
pub fn is_java_path(path: &str) -> bool {
    std::path::Path::new(path)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("java"))
}

/// Folds a parsed Java file into one unit per type and per method.
fn fold_tree(text: &str, root: Node<'_>, input: &FileInput<'_>) -> Result<Folded, FoldError> {
    let mut cx = Cx::new(input.path, "java", text);
    let mut kids = Vec::new();
    for n in children(root) {
        kids.extend(top_level(&mut cx, text, n)?);
    }
    let spec = file_root_spec(&cx, input.size as usize);
    let root_id = cx.add(spec, &kids)?;
    let term = cx.b.finish(root_id)?;
    let scopes = ScopeGraph::from_term(&term);
    let v = view::build(&term, input.path, Naming::Model);
    let mut file = base_file(input, "java");
    file.fidelity = Fidelity::F1;
    file.parse_status = view::parse_status_of(&term);
    file.symbols = v.symbols;
    file.extras = v.extras;
    tracing::debug!(
        path = input.path,
        symbols = file.symbols.len(),
        "java file folded"
    );
    Ok(Folded { term, scopes, file })
}

/// The unit kind of a type declaration node, if it is one.
fn type_kind(kind: &str) -> Option<&'static str> {
    match kind {
        "class_declaration" => Some("class"),
        "interface_declaration" | "annotation_type_declaration" => Some("interface"),
        "enum_declaration" => Some("enum"),
        "record_declaration" => Some("record"),
        _ => None,
    }
}

/// The units one top-level node contributes (none for package and import clauses).
fn top_level(cx: &mut Cx<'_>, text: &str, n: Node<'_>) -> R<Vec<NodeId>> {
    let mut out = Vec::new();
    if let Some(kind) = type_kind(n.kind()) {
        if let Some(name) = n.child_by_field_name("name") {
            let name = text_of(text, name).to_owned();
            out.push(unit(cx, text, n, kind, &name)?);
            if let Some(body) = n.child_by_field_name("body") {
                for m in children(body) {
                    if matches!(m.kind(), "method_declaration" | "constructor_declaration")
                        && let Some(mn) = m.child_by_field_name("name")
                    {
                        let full = format!("{name}.{}", text_of(text, mn));
                        out.push(unit(cx, text, m, "method", &full)?);
                    }
                }
            }
        }
    } else if n.kind() == "ERROR" || n.is_missing() {
        out.push(hole(cx, n)?);
    }
    Ok(out)
}

/// True when the declaration's modifiers include `public` or `protected`.
fn is_visible(n: Node<'_>) -> bool {
    children(n).into_iter().any(|m| {
        m.kind() == "modifiers"
            && children(m)
                .into_iter()
                .any(|k| matches!(k.kind(), "public" | "protected"))
    })
}

/// One named unit spanning `n` whose body is its source text.
fn unit(cx: &mut Cx<'_>, text: &str, n: Node<'_>, kind: &str, name: &str) -> R<NodeId> {
    let body = cx.lit("text", text_of(text, n), n)?;
    let vis = if is_visible(n) { "public" } else { "private" };
    let spec = NodeSpec::new(Operator::unit(kind, "impl"), cx.node_loc(n))
        .named(name)
        .attr(ATTR_VISIBILITY, vis);
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
    use crate::adapter::FileInput;

    fn fold_src(src: &str) -> Folded {
        let a = JavaAdapter;
        let tree = a.parse(src, &ParseLimits::default());
        let input = FileInput {
            path: "A.java",
            digest: "d",
            size: u32::try_from(src.len()).expect("small"),
        };
        a.fold(&tree, &input).expect("fold")
    }

    // frob:tests crates/gob-symbols/src/java.rs::JavaAdapter
    #[test]
    fn folds_types_and_methods() {
        let f = fold_src(
            "package p;\nimport java.io.File;\npublic class A {\n  public void run() {}\n  private void helper() {}\n  A() {}\n}\ninterface I { void f(); }\nenum E { X }\nrecord R(int a) {}\n",
        );
        let names: Vec<String> = f
            .file
            .symbols
            .iter()
            .map(|s| s.symref.to_string())
            .collect();
        for want in [
            "A.java::A",
            "A.java::A.run",
            "A.java::A.helper",
            "A.java::I",
            "A.java::E",
            "A.java::R",
        ] {
            assert!(names.iter().any(|n| n == want), "{want} in {names:?}");
        }
        assert_eq!(f.file.language, "java");
    }

    // frob:tests crates/gob-symbols/src/java.rs::is_java_path
    #[test]
    fn claims_java_files() {
        assert!(is_java_path("a/B.java"));
        assert!(is_java_path("A.JAVA"));
        assert!(!is_java_path("a.javascript"));
    }
}
