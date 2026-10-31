//! The C and C++ adapter (fidelity F1): tree-sitter tree to a U term of function and type units.
//!
//! # Mapping (rho)
//!
//! - The file is a `unit(file, impl)`. Each function definition is one `unit(function)`, each
//!   `struct`, `union`, `enum` and (C++) `class` with a body is one `unit` of that kind, and a
//!   member function defined in a class body is `Type.name`. C++ `namespace` blocks, `extern "C"`
//!   blocks and templates are looked through. A unit's body is one `lit` of its source text.
//! - A unit is `private` when declared `static`, else `public`.
//! - `#include` lines and macros are not units; they are read by the include-resolved capability
//!   scanner ([`crate::c_uses`]), not folded into the term.
//! - Syntax errors become `hole(parse-error)` nodes, so the file reads as a partial parse.
//!
//! One adapter type serves both languages, as two registered tags: `c` (`.c`, `.h`) and `cpp`
//! (`.cc`, `.cpp`, `.cxx`, `.hpp`, `.hh`, `.hxx`). Both share the capability row of [`Lang::C`].

// frob:ticket 01M64VBRHX20P2EJGQ2S1VG0FG

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

/// The C or C++ adapter (`c` and `cpp` tags).
#[derive(Debug, Clone, Copy)]
pub struct CAdapter {
    cpp: bool,
}

impl CAdapter {
    /// The adapter for C (`.c`, `.h`).
    pub const fn c() -> Self {
        Self { cpp: false }
    }

    /// The adapter for C++ (`.cc`, `.cpp`, `.cxx`, `.hpp`, `.hh`, `.hxx`).
    pub const fn cpp() -> Self {
        Self { cpp: true }
    }

    fn grammar(self) -> Language {
        if self.cpp { Language::Cpp } else { Language::C }
    }
}

impl Adapter for CAdapter {
    fn language(&self) -> &'static str {
        if self.cpp { "cpp" } else { "c" }
    }

    fn identity(&self) -> String {
        format!(
            "gob-symbols/v{EXTRACTOR_VERSION}/{}",
            grammar_identity(self.grammar())
        )
    }

    fn fidelity(&self) -> Fidelity {
        gob_caps::lang_fidelity(Lang::C)
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::for_lang(Lang::C)
    }

    fn parse(&self, text: &str, limits: &ParseLimits) -> ConcreteTree {
        match parse(self.grammar(), text, limits) {
            ParseResult::Parsed(t) => ConcreteTree::Parsed(t),
            ParseResult::Unresolved(u) => ConcreteTree::Unparsed(u.reason),
        }
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        let tag = self.language();
        match tree {
            ConcreteTree::Parsed(t) => fold_tree(tag, &t.text, t.root(), input),
            ConcreteTree::Unparsed(reason) => failed_file(input, tag, *reason),
            ConcreteTree::Leaf | ConcreteTree::Source(_) => failed_file(
                input,
                tag,
                gob_languages::UnresolvedReason::GrammarUnavailable,
            ),
        }
    }
}

/// True when `path` is a C source or header (`.c`, `.h`, any case).
pub fn is_c_path(path: &str) -> bool {
    has_extension(path, &["c", "h"])
}

/// True when `path` is a C++ source or header (`.cc`, `.cpp`, `.cxx`, `.hpp`, `.hh`, `.hxx`).
pub fn is_cpp_path(path: &str) -> bool {
    has_extension(path, &["cc", "cpp", "cxx", "hpp", "hh", "hxx"])
}

/// True when `path` ends in one of `exts`, ignoring case.
fn has_extension(path: &str, exts: &[&str]) -> bool {
    std::path::Path::new(path)
        .extension()
        .is_some_and(|e| exts.iter().any(|x| e.eq_ignore_ascii_case(x)))
}

/// Folds a parsed C or C++ file into one unit per function and per type.
fn fold_tree(
    tag: &'static str,
    text: &str,
    root: Node<'_>,
    input: &FileInput<'_>,
) -> Result<Folded, FoldError> {
    let mut cx = Cx::new(input.path, tag, text);
    let mut kids = Vec::new();
    collect(&mut cx, text, root, "", &mut kids)?;
    let spec = file_root_spec(&cx, input.size as usize);
    let root_id = cx.add(spec, &kids)?;
    let term = cx.b.finish(root_id)?;
    let scopes = ScopeGraph::from_term(&term);
    let v = view::build(&term, input.path, Naming::Model);
    let mut file = base_file(input, tag);
    file.fidelity = Fidelity::F1;
    file.parse_status = view::parse_status_of(&term);
    file.symbols = v.symbols;
    file.extras = v.extras;
    tracing::debug!(
        path = input.path,
        symbols = file.symbols.len(),
        "{tag} file folded"
    );
    Ok(Folded { term, scopes, file })
}

/// The unit kind of a type specifier node, if it is one.
fn type_kind(kind: &str) -> Option<&'static str> {
    match kind {
        "struct_specifier" => Some("struct"),
        "union_specifier" => Some("union"),
        "enum_specifier" => Some("enum"),
        "class_specifier" => Some("class"),
        _ => None,
    }
}

/// The units `node`'s children contribute, looking through namespaces, linkage blocks and templates.
fn collect(
    cx: &mut Cx<'_>,
    text: &str,
    node: Node<'_>,
    prefix: &str,
    out: &mut Vec<NodeId>,
) -> R<()> {
    for n in children(node) {
        match n.kind() {
            "function_definition" => {
                if let Some(name) = n
                    .child_by_field_name("declarator")
                    .and_then(|d| declared_name(text, d))
                {
                    out.push(unit(cx, text, n, "function", &join(prefix, &name))?);
                }
            }
            "namespace_definition"
            | "linkage_specification"
            | "template_declaration"
            | "declaration_list" => collect(cx, text, n, prefix, out)?,
            "declaration" | "type_definition" | "field_declaration" => {
                for t in children(n) {
                    type_unit(cx, text, t, prefix, out)?;
                }
            }
            "ERROR" => out.push(hole(cx, n)?),
            _ if n.is_missing() => out.push(hole(cx, n)?),
            _ => type_unit(cx, text, n, prefix, out)?,
        }
    }
    Ok(())
}

/// A unit for `n` when it is a type specifier with a body, plus the members defined inside it.
fn type_unit(
    cx: &mut Cx<'_>,
    text: &str,
    n: Node<'_>,
    prefix: &str,
    out: &mut Vec<NodeId>,
) -> R<()> {
    let Some(kind) = type_kind(n.kind()) else {
        return Ok(());
    };
    let (Some(name), Some(body)) = (n.child_by_field_name("name"), n.child_by_field_name("body"))
    else {
        return Ok(());
    };
    let full = join(prefix, text_of(text, name));
    out.push(unit(cx, text, n, kind, &full)?);
    collect(cx, text, body, &full, out)
}

/// `prefix.name`, or `name` at the top level.
fn join(prefix: &str, name: &str) -> String {
    if prefix.is_empty() {
        name.to_owned()
    } else {
        format!("{prefix}.{name}")
    }
}

/// The name a declarator declares (`A::f` becomes `A.f`), looking through pointers and parentheses.
fn declared_name(text: &str, d: Node<'_>) -> Option<String> {
    let mut cur = d;
    loop {
        match cur.kind() {
            "identifier"
            | "field_identifier"
            | "qualified_identifier"
            | "destructor_name"
            | "operator_name" => return Some(text_of(text, cur).replace("::", ".")),
            _ => {
                cur = cur
                    .child_by_field_name("declarator")
                    .or_else(|| cur.named_child(0))?;
            }
        }
    }
}

/// True when the definition or declaration has a `static` storage class.
fn is_static(text: &str, n: Node<'_>) -> bool {
    children(n)
        .into_iter()
        .any(|m| m.kind() == "storage_class_specifier" && text_of(text, m) == "static")
}

/// One named unit spanning `n` whose body is its source text.
fn unit(cx: &mut Cx<'_>, text: &str, n: Node<'_>, kind: &str, name: &str) -> R<NodeId> {
    let body = cx.lit("text", text_of(text, n), n)?;
    let vis = if is_static(text, n) {
        "private"
    } else {
        "public"
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

    fn fold_src(a: CAdapter, path: &str, src: &str) -> Folded {
        let tree = a.parse(src, &ParseLimits::default());
        let input = FileInput {
            path,
            digest: "d",
            size: u32::try_from(src.len()).expect("small"),
        };
        a.fold(&tree, &input).expect("fold")
    }

    fn names(f: &Folded) -> Vec<String> {
        f.file
            .symbols
            .iter()
            .map(|s| s.symref.to_string())
            .collect()
    }

    // frob:tests crates/gob-symbols/src/c.rs::CAdapter
    #[test]
    fn folds_c_functions_and_types() {
        let f = fold_src(
            CAdapter::c(),
            "a.c",
            "#include <stdio.h>\nstruct P { int x; };\nenum E { A };\nstatic int helper(void) { return 1; }\nint main(void) { return helper(); }\n",
        );
        let got = names(&f);
        for want in ["a.c::P", "a.c::E", "a.c::helper", "a.c::main"] {
            assert!(got.iter().any(|n| n == want), "{want} in {got:?}");
        }
        assert_eq!(f.file.language, "c");
    }

    // frob:tests crates/gob-symbols/src/c.rs::CAdapter
    #[test]
    fn folds_cpp_classes_namespaces_and_members() {
        let f = fold_src(
            CAdapter::cpp(),
            "a.cpp",
            "namespace n { class A { public: void run() {} }; int f() { return 0; } }\nint A::g() { return 1; }\n",
        );
        let got = names(&f);
        for want in ["a.cpp::A", "a.cpp::A.run", "a.cpp::f", "a.cpp::A.g"] {
            assert!(got.iter().any(|n| n == want), "{want} in {got:?}");
        }
        assert_eq!(f.file.language, "cpp");
    }

    // frob:tests crates/gob-symbols/src/c.rs::is_c_path
    // frob:tests crates/gob-symbols/src/c.rs::is_cpp_path
    #[test]
    fn claims_c_and_cpp_files() {
        assert!(is_c_path("a/b.c") && is_c_path("A.H"));
        assert!(!is_c_path("a.cc") && !is_c_path("a.cs"));
        assert!(is_cpp_path("a.cpp") && is_cpp_path("x.HPP") && is_cpp_path("y.cc"));
        assert!(!is_cpp_path("a.c"));
    }
}
