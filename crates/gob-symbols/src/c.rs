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
//! - Every `call_expression` and (C++) `new_expression` inside a function is a [`CallSite`] (caller =
//!   that unit, byte span of the call expression); a plain or `::`-qualified callee (`printf`,
//!   `std::print`) keeps its `qual_path`, a member call (`a.f()`) is a method call. C++ `using
//!   namespace std;` becomes a `*` [`UseBinding`] and `using std::cout;` a binding of `cout`
//!   (targets keep `::`).
//! - Syntax errors become `hole(parse-error)` nodes, so the file reads as a partial parse.
//!
//! One adapter type serves both languages, as two registered tags: `c` (`.c`, `.h`) and `cpp`
//! (`.cc`, `.cpp`, `.cxx`, `.hpp`, `.hh`, `.hxx`). Both share the capability row of [`Lang::C`].

// frob:ticket 01M64VBRHX20P2EJGQ2S1VG0FG

use gob_ir::{NodeId, Operator, ScopeGraph, TermError};
use gob_languages::{Language, ParseLimits, ParseResult, grammar_identity, parse};
use tree_sitter::Node;

use crate::adapter::{
    Adapter, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded, Lang,
};
use crate::fold::{
    Cx, base_file, call_text, children, failed_file, file_root_spec, line_of, span_of, text_of,
    text_unit,
};
use crate::model::{CallSite, LocalBinding, Receiver, UseBinding};
use crate::pipeline::EXTRACTOR_VERSION;
use crate::symref::Symref;
use crate::view::{self, HOLE_MISSING, HOLE_PARSE_ERROR, Naming};

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
    let mut raw_calls: Vec<(NodeId, CallSite)> = Vec::new();
    collect(&mut cx, text, root, "", &mut kids, &mut raw_calls)?;
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
    for (node, mut site) in raw_calls {
        if let Some(caller) = v.by_node.get(&node) {
            site.caller = caller.clone();
            file.calls.push(site);
        }
    }
    file.uses = using_uses(text, root, input.path);
    tracing::debug!(
        path = input.path,
        calls = file.calls.len(),
        uses = file.uses.len(),
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
    calls: &mut Vec<(NodeId, CallSite)>,
) -> R<()> {
    for n in children(node) {
        match n.kind() {
            "function_definition" => {
                if let Some(name) = n
                    .child_by_field_name("declarator")
                    .and_then(|d| declared_name(text, d))
                {
                    let id = unit(cx, text, n, "function", &join(prefix, &name))?;
                    let mut found = Vec::new();
                    if let Some(body) = n.child_by_field_name("body") {
                        collect_calls(text, body, &declared_names(text, n), &mut found);
                    }
                    found.sort_by_key(|c| c.start);
                    calls.extend(found.into_iter().map(|c| (id, c)));
                    out.push(id);
                }
            }
            "namespace_definition"
            | "linkage_specification"
            | "template_declaration"
            | "declaration_list" => collect(cx, text, n, prefix, out, calls)?,
            "declaration" | "type_definition" | "field_declaration" => {
                for t in children(n) {
                    type_unit(cx, text, t, prefix, out, calls)?;
                }
            }
            "ERROR" => out.push(hole(cx, n)?),
            _ if n.is_missing() => out.push(hole(cx, n)?),
            _ => type_unit(cx, text, n, prefix, out, calls)?,
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
    calls: &mut Vec<(NodeId, CallSite)>,
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
    collect(cx, text, body, &full, out, calls)
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
    text_unit(cx, text, n, kind, name, !is_static(text, n))
}

/// The names a parameter or local declaration under `n` declares (they shadow callees).
fn declared_names(text: &str, n: Node<'_>) -> Vec<String> {
    let mut out = Vec::new();
    let mut stack = vec![n];
    while let Some(x) = stack.pop() {
        if matches!(
            x.kind(),
            "parameter_declaration"
                | "init_declarator"
                | "declaration"
                | "optional_parameter_declaration"
        ) && let Some(d) = x.child_by_field_name("declarator")
            && let Some(name) = declared_name(text, d)
        {
            out.push(name);
        }
        stack.extend(children(x));
    }
    out
}

/// The `::`-separated identifiers of a callee name (`std::print`, `n::f<int>`), template args dropped.
fn callee_path(text: &str, f: Node<'_>) -> Option<Vec<String>> {
    match f.kind() {
        "identifier" | "qualified_identifier" | "field_identifier" | "type_identifier" => Some(
            text_of(text, f)
                .split("::")
                .map(|s| s.trim().to_owned())
                .filter(|s| !s.is_empty())
                .collect(),
        ),
        "template_function" | "template_type" => callee_path(text, f.child_by_field_name("name")?),
        _ => None,
    }
}

/// Every call and `new` expression under `body`, as caller-less call sites.
fn collect_calls(text: &str, body: Node<'_>, bound: &[String], out: &mut Vec<CallSite>) {
    let mut stack = vec![body];
    while let Some(x) = stack.pop() {
        let (callee_node, ty) = match x.kind() {
            "call_expression" => (x.child_by_field_name("function"), None),
            "new_expression" => (x.child_by_field_name("type"), Some("new")),
            _ => (None, None),
        };
        if let Some(f) = callee_node {
            let member = f.kind() == "field_expression";
            let path = if member {
                f.child_by_field_name("field")
                    .and_then(|n| callee_path(text, n))
            } else {
                callee_path(text, f)
            };
            if let Some(mut path) = path
                && let Some(callee) = path.pop()
            {
                let (start, end) = span_of(x);
                let local = if !member && path.is_empty() && bound.contains(&callee) {
                    LocalBinding::Value
                } else {
                    LocalBinding::None
                };
                out.push(CallSite {
                    caller: Symref::file(""),
                    callee,
                    qualifier: ty.map(str::to_owned),
                    method: member,
                    local,
                    in_macro: false,
                    receiver: member.then_some(Receiver::Expr),
                    opaque_qualifier: false,
                    macro_exact: None,
                    args: x
                        .child_by_field_name("arguments")
                        .map(|a| children(a).iter().filter(|c| c.is_named()).count()),
                    qual_path: if member { Vec::new() } else { path },
                    bound: Vec::new(),
                    line: line_of(x),
                    text: call_text(text_of(text, f)),
                    start,
                    end,
                });
            }
        }
        stack.extend(children(x));
    }
}

/// C++ `using` directives and declarations as use bindings (`using namespace std;` as `*`).
fn using_uses(text: &str, root: Node<'_>, path: &str) -> Vec<UseBinding> {
    let mut out = Vec::new();
    let mut stack = vec![root];
    while let Some(x) = stack.pop() {
        if x.kind() == "using_declaration" {
            let raw: String = text_of(text, x)
                .split_whitespace()
                .collect::<Vec<_>>()
                .join(" ");
            let body = raw
                .trim_start_matches("using")
                .trim()
                .trim_end_matches(';')
                .trim();
            let (glob, target) = match body.strip_prefix("namespace ") {
                Some(ns) => (true, ns.trim()),
                None => (false, body),
            };
            let target = target.strip_prefix("::").unwrap_or(target).to_owned();
            let local = if glob {
                "*".to_owned()
            } else {
                target.rsplit("::").next().unwrap_or_default().to_owned()
            };
            if !target.is_empty() {
                out.push(UseBinding {
                    from_file: path.to_owned(),
                    local,
                    target,
                    public: false,
                    container: None,
                    kind: crate::UseKind::default(),
                });
            }
        } else {
            stack.extend(children(x).into_iter().rev());
        }
    }
    out
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

    // frob:tests crates/gob-symbols/src/c.rs::collect_calls
    // frob:tests crates/gob-symbols/src/c.rs::using_uses
    #[test]
    fn records_calls_with_byte_spans_and_using_uses() {
        let src = "using namespace std;\nusing std::cout;\nint f(int p) {\n  printf(\"a\");\n  std::print(\"b\");\n  p(1);\n  v.push(2);\n  new Foo(3);\n  return 0;\n}\n";
        let f = fold_src(CAdapter::cpp(), "a.cpp", src);
        let calls = &f.file.calls;
        let c = calls.iter().find(|c| c.callee == "printf").expect("printf");
        assert_eq!(&src[c.start..c.end], "printf(\"a\")");
        assert_eq!(c.line, 4);
        assert_eq!(c.caller.to_string(), "a.cpp::f");
        assert!(c.qual_path.is_empty() && !c.method);
        let pr = calls.iter().find(|c| c.callee == "print").expect("print");
        assert_eq!(pr.qual_path, ["std"]);
        let p = calls.iter().find(|c| c.callee == "p").expect("p");
        assert_eq!(p.local, LocalBinding::Value);
        assert!(calls.iter().any(|c| c.callee == "push" && c.method));
        assert!(
            calls
                .iter()
                .any(|c| c.callee == "Foo" && c.qualifier.as_deref() == Some("new"))
        );
        let uses: Vec<(&str, &str)> = f
            .file
            .uses
            .iter()
            .map(|u| (u.local.as_str(), u.target.as_str()))
            .collect();
        assert_eq!(uses, [("*", "std"), ("cout", "std::cout")]);
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
