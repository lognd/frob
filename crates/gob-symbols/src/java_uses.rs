//! Import-resolved Java uses: `ProcessBuilder`, `Runtime.getRuntime().exec`, `Files.readAllBytes`,
//! `System.getenv`, `HttpClient`, reflection and class loading, resolved to the fully qualified
//! name they denote.
//!
//! A path is the fully qualified name of the type plus the selected member chain, so
//! `import java.nio.file.Files; Files.delete(p)` is `java.nio.file.Files.delete`. Resolution is
//! symbolic, never textual:
//!
//! - a simple type name is bound by a single-type import, else by the implicit `java.lang`
//!   package; a type declared in the file hides both, so a local `ProcessBuilder` class names
//!   nothing and `import com.example.ProcessBuilder` resolves to a path outside the vocabulary;
//! - a wildcard import (`java.io.*`) may supply any other bare type: the use is emitted with the
//!   wildcard packages and the consumer decides (one known package is certain, an unknown one
//!   is not);
//! - a static import binds a bare member (`import static java.lang.System.getenv`), a static
//!   wildcard a bare member of a known class;
//! - a local, parameter or field resolves through its declared type (`Runtime rt` makes
//!   `rt.exec` a `java.lang.Runtime.exec`); a `var` local is an alias for its initialiser, and
//!   one that is reassigned may denote anything, so its uses are `maybe`;
//! - a fully qualified expression (`java.lang.Runtime.getRuntime()`) resolves to its own text;
//! - a call that is the receiver of a longer chain is a use of its own besides the chain's top
//!   (ticket 01M688121YPN90V6GKDTFZAPQN), so `Class.forName("java.lang.Runtime").getMethod(..)`
//!   still reports `java.lang.Class.forName`.

// frob:ticket 01M64VBRFWT0EKCG800ANRZDTE
// frob:ticket 01M688121YPN90V6GKDTFZAPQN
// frob:ticket 01M68B54QSJ9VSZ6S1SZYJNFX1

use std::collections::{BTreeMap, BTreeSet};

use tree_sitter::Node;

use crate::canon::PathUse;

/// Deepest alias chain followed (`var a = b; var b = c; ..`).
const MAX_ALIAS_DEPTH: usize = 8;

/// The `java.lang` types a file sees without importing them (the ones capabilities live in).
const JAVA_LANG: &[&str] = &[
    "ProcessBuilder",
    "Process",
    "ProcessHandle",
    "Runtime",
    "System",
    "Class",
    "ClassLoader",
    "Thread",
    "Module",
    "ModuleLayer",
];

/// Roots of a fully qualified name written inline.
const FQN_ROOTS: &[&str] = &["java", "javax", "jdk"];

/// What a name in scope denotes.
enum Res {
    /// A member path of a known type; `maybe` when a reassigned alias may hide it.
    Path { path: String, maybe: bool },
    /// A bare dotted name some wildcard (a package or a static class) may supply.
    Wild { path: String, from: Vec<String> },
    /// Nothing from an import (a local type, an unbound name).
    Nothing,
}

/// A local, parameter or field declaration nearest to a use.
struct Decl<'t> {
    /// Declared type (`None` for an untyped lambda parameter or a `var`).
    ty: Option<Node<'t>>,
    /// Initialiser, for a `var` alias.
    init: Option<Node<'t>>,
    /// Whether the name is assigned again somewhere in its scope.
    reassigned: bool,
}

struct Cx<'s> {
    src: &'s str,
    /// Simple name -> fully qualified type, for single-type imports.
    types: BTreeMap<String, String>,
    /// Packages of the on-demand imports (`import a.b.*`).
    packages: Vec<String>,
    /// Bare member -> `Class.member`, for single static imports.
    statics: BTreeMap<String, String>,
    /// Classes of the static on-demand imports.
    static_classes: Vec<String>,
    /// Types and methods declared in this file.
    declared_types: BTreeSet<String>,
    declared_methods: BTreeSet<String>,
    out: Vec<PathUse>,
}

/// Every import-resolved reference to a type member in a Java syntax tree.
pub(crate) fn scan(src: &str, root: Node<'_>) -> Vec<PathUse> {
    let mut cx = Cx {
        src,
        types: BTreeMap::new(),
        packages: Vec::new(),
        statics: BTreeMap::new(),
        static_classes: Vec::new(),
        declared_types: BTreeSet::new(),
        declared_methods: BTreeSet::new(),
        out: Vec::new(),
    };
    cx.collect(root);
    tracing::debug!(
        types = cx.types.len(),
        packages = cx.packages.len(),
        statics = cx.statics.len(),
        "java: imports bound"
    );
    cx.visit(root);
    cx.out
}

fn text<'a>(src: &'a str, n: Node<'_>) -> &'a str {
    &src[n.start_byte()..n.end_byte()]
}

/// A node's source text with all whitespace removed (a dotted name split over lines).
fn compact(src: &str, n: Node<'_>) -> String {
    text(src, n).split_whitespace().collect()
}

impl Cx<'_> {
    /// Bind imports and note the types and methods the file declares.
    fn collect(&mut self, root: Node<'_>) {
        let mut stack = vec![root];
        while let Some(n) = stack.pop() {
            match n.kind() {
                "import_declaration" => {
                    self.bind_import(n);
                    continue;
                }
                "class_declaration"
                | "interface_declaration"
                | "enum_declaration"
                | "record_declaration"
                | "annotation_type_declaration" => {
                    if let Some(name) = n.child_by_field_name("name") {
                        self.declared_types.insert(text(self.src, name).to_owned());
                    }
                }
                "method_declaration" => {
                    if let Some(name) = n.child_by_field_name("name") {
                        self.declared_methods
                            .insert(text(self.src, name).to_owned());
                    }
                }
                _ => {}
            }
            let mut c = n.walk();
            stack.extend(n.children(&mut c));
        }
    }

    fn bind_import(&mut self, decl: Node<'_>) {
        let mut c = decl.walk();
        let kids: Vec<Node<'_>> = decl.children(&mut c).collect();
        let is_static = kids.iter().any(|k| k.kind() == "static");
        let star = kids.iter().any(|k| k.kind() == "asterisk");
        let Some(name) = kids
            .iter()
            .find(|k| matches!(k.kind(), "scoped_identifier" | "identifier"))
        else {
            return;
        };
        let full = compact(self.src, *name);
        match (is_static, star) {
            (false, true) => self.packages.push(full),
            (false, false) => {
                let simple = full.rsplit('.').next().unwrap_or(&full).to_owned();
                self.types.insert(simple, full);
            }
            (true, true) => self.static_classes.push(full),
            (true, false) => {
                let simple = full.rsplit('.').next().unwrap_or(&full).to_owned();
                self.statics.insert(simple, full);
            }
        }
    }

    fn visit(&mut self, root: Node<'_>) {
        let mut stack = vec![root];
        while let Some(n) = stack.pop() {
            let mut c = n.walk();
            stack.extend(n.children(&mut c));
            match n.kind() {
                // a call whose result is chained on (`Class.forName("x").getMethod(..)`,
                // `System.getenv("K").trim()`) is itself a use: the longer path names no vocabulary
                "field_access" if !is_chain_object(n) => self.emit(n),
                "method_invocation" | "object_creation_expression" | "method_reference" => {
                    self.emit(n);
                }
                "scoped_type_identifier" if emits_type(n) => self.emit(n),
                // `Runtime.class` is the handle reflection starts from (ticket ZYJNFX1)
                "class_literal" => self.emit(n),
                _ => {}
            }
        }
    }

    fn emit(&mut self, at: Node<'_>) {
        let call = matches!(
            at.kind(),
            "method_invocation" | "object_creation_expression" | "method_reference"
        );
        match self.resolve(at, 0) {
            Res::Path { path, maybe } => self.push(at, path, call, maybe, Vec::new()),
            Res::Wild { path, from } => self.push(at, path, call, false, from),
            Res::Nothing => {}
        }
    }

    fn push(
        &mut self,
        at: Node<'_>,
        path: String,
        call: bool,
        maybe: bool,
        wildcards: Vec<String>,
    ) {
        tracing::debug!(%path, call, maybe, wild = wildcards.len(), "java: type member use");
        self.out.push(PathUse {
            offset: at.start_byte(),
            line: u32::try_from(at.start_position().row + 1).unwrap_or(u32::MAX),
            spelled: compact(self.src, at),
            path,
            call,
            dynamic: maybe,
            external_root: false,
            computed: false,
            wildcards,
            maybe,
        });
    }

    /// What expression or type `e` denotes: a member path, a wildcard name or nothing.
    fn resolve(&self, e: Node<'_>, depth: usize) -> Res {
        if depth > MAX_ALIAS_DEPTH {
            return Res::Nothing;
        }
        match e.kind() {
            "parenthesized_expression" => e
                .named_child(0)
                .map_or(Res::Nothing, |i| self.resolve(i, depth + 1)),
            "cast_expression" => e
                .child_by_field_name("value")
                .map_or(Res::Nothing, |v| self.resolve(v, depth + 1)),
            "identifier" => self.resolve_name(e, depth),
            "type_identifier" => self.resolve_type_name(text(self.src, e)),
            "generic_type" => e
                .named_child(0)
                .map_or(Res::Nothing, |t| self.resolve(t, depth + 1)),
            "array_type" => e
                .child_by_field_name("element")
                .map_or(Res::Nothing, |t| self.resolve(t, depth + 1)),
            "scoped_type_identifier" | "scoped_identifier" => self.resolve_dotted(e),
            "class_literal" => e.named_child(0).map_or(Res::Nothing, |t| {
                self.member(self.resolve(t, depth + 1), "class")
            }),
            "field_access" => {
                let (Some(obj), Some(f)) = (
                    e.child_by_field_name("object"),
                    e.child_by_field_name("field"),
                ) else {
                    return Res::Nothing;
                };
                self.member(self.resolve(obj, depth + 1), text(self.src, f))
            }
            "method_invocation" => {
                let Some(name) = e.child_by_field_name("name") else {
                    return Res::Nothing;
                };
                let name = text(self.src, name);
                match e.child_by_field_name("object") {
                    Some(obj) => self.member(self.resolve(obj, depth + 1), name),
                    None => self.resolve_bare_member(name),
                }
            }
            "object_creation_expression" => e
                .child_by_field_name("type")
                .map_or(Res::Nothing, |t| self.resolve(t, depth + 1)),
            "method_reference" => {
                let mut c = e.walk();
                let kids: Vec<Node<'_>> = e.children(&mut c).collect();
                let (Some(first), Some(last)) = (kids.first(), kids.last()) else {
                    return Res::Nothing;
                };
                if kids.len() < 3 {
                    return Res::Nothing;
                }
                self.member(self.resolve(*first, depth + 1), text(self.src, *last))
            }
            _ => Res::Nothing,
        }
    }

    /// Select member `name` of a resolved receiver.
    #[allow(clippy::unused_self)]
    fn member(&self, recv: Res, name: &str) -> Res {
        match recv {
            Res::Path { path, maybe } => Res::Path {
                path: format!("{path}.{name}"),
                maybe,
            },
            Res::Wild { path, from } => Res::Wild {
                path: format!("{path}.{name}"),
                from,
            },
            Res::Nothing => Res::Nothing,
        }
    }

    /// A bare call or name supplied by a static import, if any.
    fn resolve_bare_member(&self, name: &str) -> Res {
        if self.declared_methods.contains(name) {
            return Res::Nothing;
        }
        if let Some(full) = self.statics.get(name) {
            return Res::Path {
                path: full.clone(),
                maybe: false,
            };
        }
        if self.static_classes.is_empty() {
            return Res::Nothing;
        }
        Res::Wild {
            path: name.to_owned(),
            from: self.static_classes.clone(),
        }
    }

    /// A dotted type (`java.io.File`, `Runtime.Version`) with its first segment resolved.
    fn resolve_dotted(&self, e: Node<'_>) -> Res {
        let full = compact(self.src, e);
        let (first, rest) = full.split_once('.').unwrap_or((&full, ""));
        if FQN_ROOTS.contains(&first) || first.chars().next().is_some_and(char::is_lowercase) {
            return Res::Path {
                path: full,
                maybe: false,
            };
        }
        let head = self.resolve_type_name(first);
        if rest.is_empty() {
            return head;
        }
        rest.split('.').fold(head, |acc, seg| self.member(acc, seg))
    }

    /// What a bare simple type name denotes.
    fn resolve_type_name(&self, name: &str) -> Res {
        if self.declared_types.contains(name) {
            return Res::Nothing;
        }
        if let Some(full) = self.types.get(name) {
            return Res::Path {
                path: full.clone(),
                maybe: false,
            };
        }
        if JAVA_LANG.contains(&name) {
            return Res::Path {
                path: format!("java.lang.{name}"),
                maybe: false,
            };
        }
        if self.packages.is_empty() {
            return Res::Nothing;
        }
        Res::Wild {
            path: name.to_owned(),
            from: self.packages.clone(),
        }
    }

    fn resolve_name(&self, id: Node<'_>, depth: usize) -> Res {
        let name = text(self.src, id);
        if let Some(d) = self.declared(id, name) {
            return match (d.ty, d.init) {
                (Some(ty), _) if text(self.src, ty) != "var" => self.resolve(ty, depth + 1),
                (_, Some(init)) => match self.resolve(init, depth + 1) {
                    Res::Path { path, maybe } => Res::Path {
                        path,
                        maybe: maybe || d.reassigned,
                    },
                    other if d.reassigned => {
                        let _ = other;
                        Res::Nothing
                    }
                    other => other,
                },
                _ => Res::Nothing,
            };
        }
        if let Some(full) = self.statics.get(name) {
            return Res::Path {
                path: full.clone(),
                maybe: false,
            };
        }
        if FQN_ROOTS.contains(&name) {
            return Res::Path {
                path: name.to_owned(),
                maybe: false,
            };
        }
        if name.chars().next().is_some_and(char::is_uppercase) {
            return self.resolve_type_name(name);
        }
        Res::Nothing
    }

    /// The nearest declaration of `name` visible at `use_node`, if any.
    fn declared<'t>(&self, use_node: Node<'t>, name: &str) -> Option<Decl<'t>> {
        let start = use_node.start_byte();
        let mut child = use_node;
        let mut cur = use_node.parent();
        while let Some(a) = cur {
            if let Some(d) = self.declared_in(a, child, name, start) {
                return Some(d);
            }
            child = a;
            cur = a.parent();
        }
        None
    }

    fn declared_in<'t>(
        &self,
        scope: Node<'t>,
        child: Node<'t>,
        name: &str,
        start: usize,
    ) -> Option<Decl<'t>> {
        let named = |n: Option<Node<'_>>| n.is_some_and(|n| text(self.src, n) == name);
        match scope.kind() {
            "block" | "constructor_body" | "switch_block" | "switch_block_statement_group" => {
                let mut c = scope.walk();
                let kids: Vec<Node<'t>> = scope.named_children(&mut c).collect();
                kids.into_iter()
                    .rev()
                    .filter(|k| k.end_byte() <= start && k.kind() == "local_variable_declaration")
                    .find_map(|k| self.declarator(k, name, scope))
            }
            "class_body" => {
                let mut c = scope.walk();
                let kids: Vec<Node<'t>> = scope.named_children(&mut c).collect();
                kids.into_iter()
                    .filter(|k| k.kind() == "field_declaration")
                    .find_map(|k| self.declarator(k, name, scope))
            }
            "method_declaration" | "constructor_declaration" | "lambda_expression" => {
                self.parameter(scope.child_by_field_name("parameters")?, name, scope)
            }
            "enhanced_for_statement" => (scope.child_by_field_name("body") == Some(child)
                && named(scope.child_by_field_name("name")))
            .then(|| Decl {
                ty: scope.child_by_field_name("type"),
                init: None,
                reassigned: false,
            }),
            "for_statement" => {
                if scope.child_by_field_name("body") != Some(child) {
                    return None;
                }
                let init = scope.child_by_field_name("init")?;
                (init.kind() == "local_variable_declaration")
                    .then(|| self.declarator(init, name, scope))?
            }
            "try_with_resources_statement" => {
                if scope.child_by_field_name("body") != Some(child) {
                    return None;
                }
                let res = scope.child_by_field_name("resources")?;
                let mut c = res.walk();
                let kids: Vec<Node<'t>> = res.named_children(&mut c).collect();
                kids.into_iter()
                    .find(|r| r.kind() == "resource" && named(r.child_by_field_name("name")))
                    .map(|r| Decl {
                        ty: r.child_by_field_name("type"),
                        init: r.child_by_field_name("value"),
                        reassigned: false,
                    })
            }
            "catch_clause" => {
                let mut c = scope.walk();
                let kids: Vec<Node<'t>> = scope.named_children(&mut c).collect();
                kids.into_iter()
                    .find(|k| {
                        k.kind() == "catch_formal_parameter" && named(k.child_by_field_name("name"))
                    })
                    .map(|_| Decl {
                        ty: None,
                        init: None,
                        reassigned: false,
                    })
            }
            _ => None,
        }
    }

    /// The declarator of `name` in a local or field declaration `k`.
    fn declarator<'t>(&self, k: Node<'t>, name: &str, scope: Node<'t>) -> Option<Decl<'t>> {
        let mut c = k.walk();
        let found = k.children(&mut c).find(|d| {
            d.kind() == "variable_declarator"
                && d.child_by_field_name("name")
                    .is_some_and(|n| text(self.src, n) == name)
        })?;
        Some(Decl {
            ty: k.child_by_field_name("type"),
            init: found.child_by_field_name("value"),
            reassigned: self.reassigned(scope, name),
        })
    }

    /// The parameter `name` in a method or lambda parameter list.
    fn parameter<'t>(&self, list: Node<'t>, name: &str, scope: Node<'t>) -> Option<Decl<'t>> {
        if list.kind() == "identifier" {
            return (text(self.src, list) == name).then_some(Decl {
                ty: None,
                init: None,
                reassigned: false,
            });
        }
        let mut c = list.walk();
        let kids: Vec<Node<'t>> = list.named_children(&mut c).collect();
        kids.into_iter().find_map(|p| match p.kind() {
            "identifier" => (text(self.src, p) == name).then_some(Decl {
                ty: None,
                init: None,
                reassigned: false,
            }),
            "formal_parameter" | "spread_parameter" | "receiver_parameter" => {
                let mut pc = p.walk();
                let named = p.children(&mut pc).any(|k| {
                    matches!(k.kind(), "identifier" | "variable_declarator")
                        && (text(self.src, k) == name
                            || k.child_by_field_name("name")
                                .is_some_and(|n| text(self.src, n) == name))
                });
                let _ = scope;
                named.then(|| Decl {
                    ty: p.child_by_field_name("type").or_else(|| {
                        let mut tc = p.walk();
                        p.named_children(&mut tc)
                            .find(|k| k.kind().ends_with("_type"))
                    }),
                    init: None,
                    reassigned: false,
                })
            }
            "inferred_parameters" => {
                let mut ic = p.walk();
                let hit = p.named_children(&mut ic).any(|i| text(self.src, i) == name);
                hit.then_some(Decl {
                    ty: None,
                    init: None,
                    reassigned: false,
                })
            }
            _ => None,
        })
    }

    /// True when `name` is the target of a plain assignment anywhere under `scope`.
    fn reassigned(&self, scope: Node<'_>, name: &str) -> bool {
        let mut stack = vec![scope];
        while let Some(n) = stack.pop() {
            if n.kind() == "assignment_expression"
                && n.child_by_field_name("left")
                    .is_some_and(|l| l.kind() == "identifier" && text(self.src, l) == name)
            {
                return true;
            }
            let mut c = n.walk();
            stack.extend(n.children(&mut c));
        }
        false
    }
}

/// True when `n` is the receiver of a longer member chain (only the chain's top is emitted).
fn is_chain_object(n: Node<'_>) -> bool {
    n.parent().is_some_and(|p| {
        matches!(p.kind(), "method_invocation" | "field_access")
            && p.child_by_field_name("object") == Some(n)
    })
}

/// True when a qualified type is not already covered by an enclosing node.
fn emits_type(n: Node<'_>) -> bool {
    n.parent().is_none_or(|p| {
        !(p.kind() == "scoped_type_identifier"
            || (p.kind() == "object_creation_expression"
                && p.child_by_field_name("type") == Some(n)))
    })
}

#[cfg(test)]
mod tests {
    use crate::canon::{PathUse, path_uses};

    fn uses(src: &str) -> Vec<PathUse> {
        path_uses("java", src)
    }

    fn paths(src: &str) -> Vec<String> {
        uses(src).into_iter().map(|u| u.path).collect()
    }

    fn wrap(imports: &str, body: &str) -> String {
        format!(
            "{imports}\nclass A {{\n  void f(String c) throws Exception {{\n    {body}\n  }}\n}}\n"
        )
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn implicit_java_lang_and_chains_resolve() {
        let p = paths(&wrap("", "Runtime.getRuntime().exec(c);"));
        assert!(
            p.contains(&"java.lang.Runtime.getRuntime.exec".to_owned()),
            "{p:?}"
        );
        let p = paths(&wrap("", "new ProcessBuilder(c).start();"));
        assert!(p.contains(&"java.lang.ProcessBuilder".to_owned()), "{p:?}");
        assert!(
            p.contains(&"java.lang.ProcessBuilder.start".to_owned()),
            "{p:?}"
        );
        let p = paths(&wrap("", "String v = System.getenv(c);"));
        assert_eq!(p, ["java.lang.System.getenv"]);
    }

    // frob:ticket 01M688121YPN90V6GKDTFZAPQN
    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn a_call_chained_on_is_a_use_of_its_own() {
        let p = paths(&wrap(
            "",
            "Class.forName(\"java.lang.Runtime\").getMethod(\"exec\", String.class);",
        ));
        assert!(p.contains(&"java.lang.Class.forName".to_owned()), "{p:?}");
        let p = paths(&wrap("", "String v = System.getenv(c).trim();"));
        assert!(p.contains(&"java.lang.System.getenv".to_owned()), "{p:?}");
        let p = paths(&wrap(
            "class Class { static Object forName(String s) { return null; } }",
            "Class.forName(c).toString();",
        ));
        assert!(!p.iter().any(|x| x.starts_with("java.lang.Class")), "{p:?}");
    }

    // frob:ticket 01M68B54QSJ9VSZ6S1SZYJNFX1
    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn a_class_literal_is_a_use_of_its_type() {
        let p = paths(&wrap("", "Object m = Runtime.class.getMethod(\"exec\");"));
        assert!(p.contains(&"java.lang.Runtime.class".to_owned()), "{p:?}");
        let p = paths(&wrap("", "Class<?> c = java.lang.Runtime.class;"));
        assert!(p.contains(&"java.lang.Runtime.class".to_owned()), "{p:?}");
        let p = paths(&wrap("class Runtime {}", "Object c = Runtime.class;"));
        assert!(p.is_empty(), "{p:?}");
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn single_wildcard_static_and_qualified_imports_resolve() {
        let p = paths(&wrap("import java.nio.file.Files;", "Files.delete(null);"));
        assert_eq!(p, ["java.nio.file.Files.delete"]);
        let u = uses(&wrap("import java.nio.file.*;", "Files.delete(null);"));
        assert_eq!(u[0].path, "Files.delete");
        assert_eq!(u[0].wildcards, ["java.nio.file"]);
        let p = paths(&wrap(
            "import static java.lang.System.getenv;",
            "getenv(c);",
        ));
        assert_eq!(p, ["java.lang.System.getenv"]);
        let u = uses(&wrap("import static java.lang.System.*;", "getenv(c);"));
        assert_eq!(u[0].path, "getenv");
        assert_eq!(u[0].wildcards, ["java.lang.System"]);
        let p = paths(&wrap("", "java.lang.Runtime.getRuntime().exec(c);"));
        assert!(
            p.contains(&"java.lang.Runtime.getRuntime.exec".to_owned()),
            "{p:?}"
        );
        let p = paths(&wrap("", "java.io.File f = new java.io.File(c);"));
        assert!(p.iter().all(|x| x == "java.io.File"), "{p:?}");
        assert!(!p.is_empty());
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn typed_locals_and_var_aliases_resolve() {
        let p = paths(&wrap(
            "",
            "Runtime rt = Runtime.getRuntime();\n    rt.exec(c);",
        ));
        assert!(p.contains(&"java.lang.Runtime.exec".to_owned()), "{p:?}");
        let p = paths(&wrap("", "var rt = Runtime.getRuntime();\n    rt.exec(c);"));
        assert!(
            p.contains(&"java.lang.Runtime.getRuntime.exec".to_owned()),
            "{p:?}"
        );
        let moved = wrap(
            "",
            "var rt = Runtime.getRuntime();\n    rt = null;\n    rt.exec(c);",
        );
        let hit: Vec<_> = uses(&moved)
            .into_iter()
            .filter(|u| u.path.ends_with("exec"))
            .collect();
        assert_eq!(hit.len(), 1);
        assert!(hit[0].maybe);
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn declared_types_and_foreign_imports_hide_the_name() {
        let own = "class ProcessBuilder { void start() {} }\nclass A { void f() { new ProcessBuilder().start(); } }\n";
        assert!(paths(own).is_empty(), "{:?}", paths(own));
        let foreign = wrap(
            "import com.example.ProcessBuilder;",
            "new ProcessBuilder(c).start();",
        );
        assert!(
            paths(&foreign)
                .iter()
                .all(|p| p.starts_with("com.example."))
        );
        let param = "class A { void f(Runtime Runtime) { Runtime.exec(\"x\"); } }\n";
        assert!(paths(param).iter().all(|p| p == "java.lang.Runtime.exec"));
        let comment = wrap(
            "",
            "// Runtime.getRuntime().exec(c)\n    String s = \"System.getenv\";",
        );
        assert!(paths(&comment).is_empty());
    }
}
