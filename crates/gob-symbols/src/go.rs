//! The Go adapter (fidelity F1): tree-sitter tree to a U term of top-level declarations.
//!
//! # Mapping (rho)
//!
//! - The file is a `unit(file, impl)`. Each top-level declaration is one unit spanning the whole
//!   declaration: `func` is `unit(function)`, a method is `unit(method)` named `Recv.name`, each
//!   `type` spec is `unit(struct | interface | type)`, each `const` / `var` name is
//!   `unit(const | static)`. A unit's body is one `lit` of its source text.
//! - Exported names (leading upper-case letter) are `public`, the rest `private`.
//! - Imports are not units; they are read by the import-resolved capability scanner
//!   ([`crate::go_uses`]), not folded into the term.
//! - Syntax errors become `hole(parse-error)` nodes, so the file reads as a partial parse.

// frob:ticket 01M64VBRCNYQ3WC895EYXR6GME

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

/// The Go adapter.
#[derive(Debug, Clone, Copy, Default)]
pub struct GoAdapter;

impl Adapter for GoAdapter {
    fn language(&self) -> &'static str {
        "go"
    }

    fn identity(&self) -> String {
        format!(
            "gob-symbols/v{EXTRACTOR_VERSION}/{}",
            grammar_identity(Language::Go)
        )
    }

    fn fidelity(&self) -> Fidelity {
        gob_caps::lang_fidelity(Lang::Go)
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::for_lang(Lang::Go)
    }

    fn parse(&self, text: &str, limits: &ParseLimits) -> ConcreteTree {
        match parse(Language::Go, text, limits) {
            ParseResult::Parsed(t) => ConcreteTree::Parsed(t),
            ParseResult::Unresolved(u) => ConcreteTree::Unparsed(u.reason),
        }
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        match tree {
            ConcreteTree::Parsed(t) => fold_tree(&t.text, t.root(), input),
            ConcreteTree::Unparsed(reason) => failed_file(input, "go", *reason),
            ConcreteTree::Leaf | ConcreteTree::Source(_) => failed_file(
                input,
                "go",
                gob_languages::UnresolvedReason::GrammarUnavailable,
            ),
        }
    }
}

/// True when `path` is a Go source file (`.go`, any case).
pub fn is_go_path(path: &str) -> bool {
    std::path::Path::new(path)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("go"))
}

/// Folds a parsed Go file into one unit per top-level declaration.
fn fold_tree(text: &str, root: Node<'_>, input: &FileInput<'_>) -> Result<Folded, FoldError> {
    let mut cx = Cx::new(input.path, "go", text);
    let mut kids = Vec::new();
    for n in children(root) {
        kids.extend(top_level(&mut cx, text, n)?);
    }
    let spec = file_root_spec(&cx, input.size as usize);
    let root_id = cx.add(spec, &kids)?;
    let term = cx.b.finish(root_id)?;
    let scopes = ScopeGraph::from_term(&term);
    let v = view::build(&term, input.path, Naming::Model);
    let mut file = base_file(input, "go");
    file.fidelity = Fidelity::F1;
    file.parse_status = view::parse_status_of(&term);
    file.symbols = v.symbols;
    file.extras = v.extras;
    tracing::debug!(
        path = input.path,
        symbols = file.symbols.len(),
        "go file folded"
    );
    Ok(Folded { term, scopes, file })
}

/// The units one top-level node contributes (none for package and import clauses).
fn top_level(cx: &mut Cx<'_>, text: &str, n: Node<'_>) -> R<Vec<NodeId>> {
    let mut out = Vec::new();
    match n.kind() {
        "function_declaration" => {
            if let Some(name) = n.child_by_field_name("name") {
                out.push(unit(cx, text, n, "function", text_of(text, name))?);
            }
        }
        "method_declaration" => {
            if let Some(name) = n.child_by_field_name("name") {
                let recv = n
                    .child_by_field_name("receiver")
                    .map(|r| receiver_type(text_of(text, r)))
                    .unwrap_or_default();
                let full = if recv.is_empty() {
                    text_of(text, name).to_owned()
                } else {
                    format!("{recv}.{}", text_of(text, name))
                };
                out.push(unit(cx, text, n, "method", &full)?);
            }
        }
        "type_declaration" => {
            for spec in children(n) {
                if !matches!(spec.kind(), "type_spec" | "type_alias") {
                    continue;
                }
                let Some(name) = spec.child_by_field_name("name") else {
                    continue;
                };
                let kind = match spec.child_by_field_name("type").map(|t| t.kind()) {
                    Some("struct_type") => "struct",
                    Some("interface_type") => "interface",
                    _ => "type",
                };
                out.push(unit(cx, text, spec, kind, text_of(text, name))?);
            }
        }
        "const_declaration" | "var_declaration" => {
            let kind = if n.kind() == "const_declaration" {
                "const"
            } else {
                "static"
            };
            for spec in children(n) {
                if !matches!(spec.kind(), "const_spec" | "var_spec") {
                    continue;
                }
                let mut c = spec.walk();
                let names: Vec<String> = spec
                    .children_by_field_name("name", &mut c)
                    .map(|i| text_of(text, i).to_owned())
                    .collect();
                for name in names {
                    out.push(unit(cx, text, spec, kind, &name)?);
                }
            }
        }
        "ERROR" => out.push(hole(cx, n)?),
        _ if n.is_missing() => out.push(hole(cx, n)?),
        _ => {}
    }
    Ok(out)
}

/// The receiver base type of a method receiver list `(r *T)` as `T` (generics dropped).
fn receiver_type(recv: &str) -> String {
    let inner = recv.trim().trim_start_matches('(').trim_end_matches(')');
    let ty = inner.rsplit(char::is_whitespace).next().unwrap_or(inner);
    ty.trim_start_matches('*')
        .split('[')
        .next()
        .unwrap_or(ty)
        .to_owned()
}

/// True for an exported Go name (leading upper-case letter).
fn is_exported(name: &str) -> bool {
    name.rsplit('.')
        .next()
        .and_then(|s| s.chars().next())
        .is_some_and(char::is_uppercase)
}

/// One named unit spanning `n` whose body is its source text.
fn unit(cx: &mut Cx<'_>, text: &str, n: Node<'_>, kind: &str, name: &str) -> R<NodeId> {
    let body = cx.lit("text", text_of(text, n), n)?;
    let vis = if is_exported(name) {
        "public"
    } else {
        "private"
    };
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
        let a = GoAdapter;
        let tree = a.parse(src, &ParseLimits::default());
        let input = FileInput {
            path: "main.go",
            digest: "d",
            size: u32::try_from(src.len()).expect("small"),
        };
        a.fold(&tree, &input).expect("fold")
    }

    // frob:tests crates/gob-symbols/src/go.rs::GoAdapter
    #[test]
    fn folds_top_level_declarations() {
        let f = fold_src(
            "package main\nimport \"os\"\nfunc Run() {}\nfunc helper() {}\ntype S struct{}\nfunc (s *S) Go() {}\nconst K = 1\n",
        );
        let names: Vec<String> = f
            .file
            .symbols
            .iter()
            .map(|s| s.symref.to_string())
            .collect();
        for want in [
            "main.go::Run",
            "main.go::helper",
            "main.go::S",
            "main.go::S.Go",
            "main.go::K",
        ] {
            assert!(names.iter().any(|n| n == want), "{want} in {names:?}");
        }
        assert_eq!(f.file.language, "go");
    }

    // frob:tests crates/gob-symbols/src/go.rs::is_go_path
    #[test]
    fn claims_go_files() {
        assert!(is_go_path("a/b.go"));
        assert!(is_go_path("A.GO"));
        assert!(!is_go_path("a.gom"));
    }
}
