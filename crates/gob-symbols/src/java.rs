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
//! - Every `method_invocation` and `object_creation_expression` inside a method or constructor is a
//!   [`CallSite`] (caller = that unit, byte span of the call expression); a receiver that is a plain
//!   name chain (`System.out`) becomes `qual_path`, any other receiver makes it a method call.
//!   Imports become [`UseBinding`]s (`java.io.File` as `File`, `java.io.*` as `*`, a static import
//!   as its member) so the universal model can resolve a call through them.
//! - Syntax errors become `hole(parse-error)` nodes, so the file reads as a partial parse.

// frob:ticket 01M64VBRFWT0EKCG800ANRZDTE

use gob_ir::{NodeId, NodeSpec, Operator, ScopeGraph, TermError};
use gob_languages::{Language, ParseLimits, ParseResult, grammar_identity, parse};
use tree_sitter::Node;

use crate::adapter::{
    Adapter, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded, Lang,
};
use crate::fold::{Cx, base_file, children, failed_file, file_root_spec, text_of};
use crate::model::{CallSite, LocalBinding, Receiver, UseBinding};
use crate::pipeline::EXTRACTOR_VERSION;
use crate::symref::Symref;
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
    let mut raw_calls: Vec<(NodeId, CallSite)> = Vec::new();
    for n in children(root) {
        kids.extend(top_level(&mut cx, text, n, &mut raw_calls)?);
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
    for (node, mut site) in raw_calls {
        if let Some(caller) = v.by_node.get(&node) {
            site.caller = caller.clone();
            file.calls.push(site);
        }
    }
    file.uses = import_uses(text, root, input.path);
    tracing::debug!(
        path = input.path,
        calls = file.calls.len(),
        uses = file.uses.len(),
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
fn top_level(
    cx: &mut Cx<'_>,
    text: &str,
    n: Node<'_>,
    calls: &mut Vec<(NodeId, CallSite)>,
) -> R<Vec<NodeId>> {
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
                        let id = unit(cx, text, m, "method", &full)?;
                        let mut found = Vec::new();
                        let mut bound = declared_names(text, m);
                        if let Some(body) = n.child_by_field_name("body") {
                            for f in children(body)
                                .into_iter()
                                .filter(|f| f.kind() == "field_declaration")
                            {
                                bound.extend(declared_names(text, f));
                            }
                        }
                        collect_calls(text, m, &bound, &mut found);
                        found.sort_by_key(|c| c.start);
                        calls.extend(found.into_iter().map(|c| (id, c)));
                        out.push(id);
                    }
                }
            }
        }
    } else if n.kind() == "ERROR" || n.is_missing() {
        out.push(hole(cx, n)?);
    }
    Ok(out)
}

/// The identifiers of a plain name chain (`a`, `a.b.c`), or `None` when it is anything else.
fn name_chain(text: &str, n: Node<'_>) -> Option<Vec<String>> {
    match n.kind() {
        "identifier" => Some(vec![text_of(text, n).to_owned()]),
        "field_access" => {
            let mut head = name_chain(text, n.child_by_field_name("object")?)?;
            head.push(text_of(text, n.child_by_field_name("field")?).to_owned());
            Some(head)
        }
        "scoped_identifier" => Some(
            text_of(text, n)
                .split('.')
                .map(|s| s.trim().to_owned())
                .collect(),
        ),
        _ => None,
    }
}

/// The names a parameter, local, catch, loop or lambda variable under `n` declares (they shadow types).
fn declared_names(text: &str, n: Node<'_>) -> Vec<String> {
    let mut out = Vec::new();
    let mut stack = vec![n];
    while let Some(x) = stack.pop() {
        match x.kind() {
            "formal_parameter"
            | "spread_parameter"
            | "variable_declarator"
            | "catch_formal_parameter"
            | "enhanced_for_statement"
            | "resource" => {
                if let Some(name) = x.child_by_field_name("name") {
                    out.push(text_of(text, name).to_owned());
                }
            }
            "inferred_parameters" => {
                for c in children(x).into_iter().filter(|c| c.kind() == "identifier") {
                    out.push(text_of(text, c).to_owned());
                }
            }
            "lambda_expression" => {
                if let Some(p) = x.child_by_field_name("parameters")
                    && p.kind() == "identifier"
                {
                    out.push(text_of(text, p).to_owned());
                }
            }
            _ => {}
        }
        stack.extend(children(x));
    }
    out
}

/// Every method invocation and object creation under `m`, as caller-less call sites.
fn collect_calls(text: &str, m: Node<'_>, bound: &[String], out: &mut Vec<CallSite>) {
    let mut stack = children(m);
    while let Some(x) = stack.pop() {
        let site = |callee: String, qual_path: Vec<String>, method: bool| {
            let mut t: String = text_of(text, x)
                .split_whitespace()
                .collect::<Vec<_>>()
                .join(" ");
            if t.len() > 96 {
                let mut cut = 96;
                while !t.is_char_boundary(cut) {
                    cut -= 1;
                }
                t.truncate(cut);
            }
            CallSite {
                caller: Symref::file(""),
                callee,
                qualifier: None,
                method,
                local: LocalBinding::None,
                in_macro: false,
                receiver: method.then_some(Receiver::Expr),
                opaque_qualifier: false,
                macro_exact: None,
                args: x
                    .child_by_field_name("arguments")
                    .map(|a| children(a).iter().filter(|c| c.is_named()).count()),
                qual_path,
                bound: Vec::new(),
                line: u32::try_from(x.start_position().row + 1).unwrap_or(u32::MAX),
                text: t,
                start: x.start_byte(),
                end: x.end_byte(),
            }
        };
        match x.kind() {
            "method_invocation" => {
                if let Some(name) = x.child_by_field_name("name") {
                    let callee = text_of(text, name).to_owned();
                    let mut call = match x.child_by_field_name("object") {
                        None => site(callee, Vec::new(), false),
                        Some(o) => match name_chain(text, o) {
                            Some(path) => site(callee, path, false),
                            None => site(callee, Vec::new(), true),
                        },
                    };
                    if call.qual_path.first().is_some_and(|h| bound.contains(h)) {
                        call.local = LocalBinding::Value;
                    }
                    out.push(call);
                }
            }
            "object_creation_expression" => {
                if let Some(t) = x.child_by_field_name("type") {
                    let mut chain: Vec<String> = text_of(text, t)
                        .split('<')
                        .next()
                        .unwrap_or_default()
                        .split('.')
                        .map(|s| s.trim().to_owned())
                        .collect();
                    let callee = chain.pop().unwrap_or_default();
                    let mut c = site(callee, chain, false);
                    c.qualifier = Some("new".to_owned());
                    out.push(c);
                }
            }
            _ => {}
        }
        stack.extend(children(x));
    }
}

/// The `import` declarations of a file as use bindings (single type, static member, wildcard `*`).
fn import_uses(text: &str, root: Node<'_>, path: &str) -> Vec<UseBinding> {
    let mut out = Vec::new();
    for n in children(root) {
        if n.kind() != "import_declaration" {
            continue;
        }
        let kids = children(n);
        let wild = kids.iter().any(|k| k.kind() == "asterisk");
        let Some(name) = kids
            .iter()
            .find(|k| matches!(k.kind(), "scoped_identifier" | "identifier"))
        else {
            continue;
        };
        let target: String = text_of(text, *name).split_whitespace().collect();
        let local = if wild {
            "*".to_owned()
        } else {
            target.rsplit('.').next().unwrap_or_default().to_owned()
        };
        out.push(UseBinding {
            from_file: path.to_owned(),
            local,
            target,
            public: false,
            container: None,
            kind: crate::UseKind::default(),
        });
    }
    out
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

    // frob:tests crates/gob-symbols/src/java.rs::collect_calls
    // frob:tests crates/gob-symbols/src/java.rs::import_uses
    #[test]
    fn records_calls_with_byte_spans_and_import_uses() {
        let src = "import java.io.File;\nimport java.io.*;\nimport static java.lang.System.getenv;\nclass A {\n  void run() {\n    System.out.println(1);\n    new File(\"x\");\n    getenv(\"H\");\n    foo().bar();\n  }\n}\n";
        let f = fold_src(src);
        let calls = &f.file.calls;
        let c = calls
            .iter()
            .find(|c| c.callee == "println")
            .expect("println");
        assert_eq!(c.qual_path, ["System", "out"]);
        assert!(!c.method);
        assert_eq!(&src[c.start..c.end], "System.out.println(1)");
        assert_eq!(c.line, 6);
        assert_eq!(c.caller.to_string(), "A.java::A.run");
        assert!(
            calls
                .iter()
                .any(|c| c.callee == "File" && c.qualifier.as_deref() == Some("new"))
        );
        assert!(
            calls
                .iter()
                .any(|c| c.callee == "getenv" && c.qual_path.is_empty())
        );
        assert!(calls.iter().any(|c| c.callee == "bar" && c.method));
        let uses: Vec<(&str, &str)> = f
            .file
            .uses
            .iter()
            .map(|u| (u.local.as_str(), u.target.as_str()))
            .collect();
        assert_eq!(
            uses,
            [
                ("File", "java.io.File"),
                ("*", "java.io"),
                ("getenv", "java.lang.System.getenv")
            ]
        );
    }

    // frob:tests crates/gob-symbols/src/java.rs::is_java_path
    #[test]
    fn claims_java_files() {
        assert!(is_java_path("a/B.java"));
        assert!(is_java_path("A.JAVA"));
        assert!(!is_java_path("a.javascript"));
    }
}
