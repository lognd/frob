//! Import-resolved Go uses: `exec.Command`, `e.Command` (aliased import), `Command` (dot import),
//! `os.Getenv`, `http.Get`, `plugin.Open` and kin, resolved to the import path they denote.
//!
//! A path is the import path of the package plus the selected member chain, so `import e
//! "os/exec"; e.Command(x)` is `os/exec.Command`. Resolution is symbolic, never textual:
//!
//! - a package name is bound by an import (the alias, else the last path segment); a parameter, a
//!   `:=` / `var` / `const` / `type` declaration, a `range` variable or a top-level declaration
//!   of the same name hides it, so a local `exec` struct names no package;
//! - a blank import (`_ "os/exec"`) binds nothing;
//! - a local initialised from a package member (`run := exec.Command`) is an alias for it; one
//!   that is reassigned may denote anything, so its uses are `maybe` (reported Unresolved);
//! - a dot import (`. "os/exec"`) binds the bare names of the package: a bare call is emitted
//!   with the dot-imported modules as `wildcards`, and the consumer decides which package
//!   supplies the name (one known package is certain, several or an unknown one are not);
//! - a call to a reflection API that yields a value (`reflect.ValueOf(v)`) is typed
//!   `reflect.Value`, so `reflect.ValueOf(v).MethodByName(n).Call(nil)` resolves to
//!   `reflect.Value.MethodByName` and `reflect.Value.Call` (dynamic dispatch, `code.eval`).

// frob:ticket 01M64VBRCNYQ3WC895EYXR6GME
// frob:ticket 01M68811YBPN99TW7VD4RA3JAJ

use std::collections::BTreeMap;

use tree_sitter::Node;

use crate::canon::PathUse;

/// Deepest alias chain followed (`a := b; b := c; ..`).
const MAX_ALIAS_DEPTH: usize = 8;

/// What a name in scope denotes.
enum Res {
    /// A member path of an imported package; `maybe` when a reassigned alias may hide it.
    Path { path: String, maybe: bool },
    /// A bare dotted name some dot import may supply.
    Wild { path: String },
    /// Nothing from an import (a local, a parameter, an unbound name).
    Nothing,
}

/// What declares a name nearest to a use.
enum Decl<'t> {
    /// A local that holds anything.
    Shadow,
    /// A local initialised from this expression (and whether it is reassigned later).
    Alias(Node<'t>, bool),
}

struct Cx<'s> {
    src: &'s str,
    /// Package name -> import path, for named and default-named imports.
    imports: BTreeMap<String, String>,
    /// Import paths of the dot imports.
    dots: Vec<String>,
    out: Vec<PathUse>,
}

/// Every import-resolved reference to a package member in a Go syntax tree.
pub(crate) fn scan(src: &str, root: Node<'_>) -> Vec<PathUse> {
    let mut cx = Cx {
        src,
        imports: BTreeMap::new(),
        dots: Vec::new(),
        out: Vec::new(),
    };
    cx.collect_imports(root);
    if cx.imports.is_empty() && cx.dots.is_empty() {
        return Vec::new();
    }
    tracing::debug!(
        imports = cx.imports.len(),
        dots = cx.dots.len(),
        "go: imports bound"
    );
    cx.visit(root);
    cx.out
}

/// The `reflect` type a call to `path` returns, when `path` is a reflection API that yields one.
fn reflect_result(path: &str) -> Option<&'static str> {
    match path {
        "reflect.ValueOf"
        | "reflect.Indirect"
        | "reflect.New"
        | "reflect.Zero"
        | "reflect.MakeFunc"
        | "reflect.Append"
        | "reflect.Value.Method"
        | "reflect.Value.MethodByName"
        | "reflect.Value.Elem"
        | "reflect.Value.Field"
        | "reflect.Value.FieldByName"
        | "reflect.Value.Index"
        | "reflect.Value.Convert"
        | "reflect.Value.Addr"
        | "reflect.Value.MapIndex" => Some("reflect.Value"),
        "reflect.TypeOf" | "reflect.Value.Type" | "reflect.Type.Elem" => Some("reflect.Type"),
        _ => None,
    }
}

fn text<'a>(src: &'a str, n: Node<'_>) -> &'a str {
    &src[n.start_byte()..n.end_byte()]
}

/// The package name an import path binds by default: its last segment, skipping a `vN` major
/// version suffix and a `gopkg.in` `.vN` tail.
fn default_name(path: &str) -> String {
    let mut segs: Vec<&str> = path.split('/').collect();
    if segs.len() > 1
        && segs.last().is_some_and(|s| {
            s.len() > 1 && s.starts_with('v') && s[1..].bytes().all(|b| b.is_ascii_digit())
        })
    {
        segs.pop();
    }
    let last = segs.last().copied().unwrap_or(path);
    let last = last.rsplit_once(".v").map_or(last, |(a, _)| a);
    last.replace('-', "_")
}

impl Cx<'_> {
    fn collect_imports(&mut self, root: Node<'_>) {
        let mut stack = vec![root];
        while let Some(n) = stack.pop() {
            if n.kind() == "import_spec" {
                self.bind_import(n);
                continue;
            }
            // imports only appear at the top of the file
            if matches!(
                n.kind(),
                "source_file" | "import_declaration" | "import_spec_list"
            ) {
                let mut c = n.walk();
                stack.extend(n.children(&mut c));
            }
        }
    }

    fn bind_import(&mut self, spec: Node<'_>) {
        let Some(p) = spec.child_by_field_name("path") else {
            return;
        };
        let path = text(self.src, p).trim_matches(['"', '`']).to_owned();
        match spec.child_by_field_name("name") {
            Some(n) if n.kind() == "dot" => self.dots.push(path),
            Some(n) if n.kind() == "blank_identifier" => {
                tracing::debug!(%path, "go: blank import binds nothing");
            }
            Some(n) => {
                self.imports.insert(text(self.src, n).to_owned(), path);
            }
            None => {
                self.imports.insert(default_name(&path), path);
            }
        }
    }

    fn visit(&mut self, root: Node<'_>) {
        let mut stack = vec![root];
        while let Some(n) = stack.pop() {
            let mut c = n.walk();
            stack.extend(n.children(&mut c));
            match n.kind() {
                "selector_expression"
                    if n.parent().is_none_or(|p| {
                        !(p.kind() == "selector_expression"
                            && p.child_by_field_name("operand") == Some(n))
                    }) =>
                {
                    self.emit(n);
                }
                "identifier" if is_call_function(n) => self.emit(n),
                "qualified_type" => self.emit_type(n),
                _ => {}
            }
        }
    }

    fn emit_type(&mut self, n: Node<'_>) {
        let (Some(pkg), Some(name)) = (
            n.child_by_field_name("package"),
            n.child_by_field_name("name"),
        ) else {
            return;
        };
        let pkg_name = text(self.src, pkg);
        if self.declared(pkg, pkg_name).is_some() {
            return;
        }
        let Some(import) = self.imports.get(pkg_name) else {
            return;
        };
        let path = format!("{import}.{}", text(self.src, name));
        self.push(n, path, false, false, Vec::new());
    }

    fn emit(&mut self, at: Node<'_>) {
        let call = is_call_function(at);
        match self.resolve(at, 0) {
            Res::Path { path, maybe } => self.push(at, path, call, maybe, Vec::new()),
            Res::Wild { path } => {
                if call || at.kind() == "selector_expression" {
                    let wild = self.dots.clone();
                    self.push(at, path, call, false, wild);
                }
            }
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
        tracing::debug!(%path, call, maybe, wild = wildcards.len(), "go: package member use");
        self.out.push(PathUse {
            offset: at.start_byte(),
            line: u32::try_from(at.start_position().row + 1).unwrap_or(u32::MAX),
            spelled: text(self.src, at).split_whitespace().collect(),
            path,
            call,
            dynamic: maybe,
            external_root: false,
            computed: false,
            wildcards,
            maybe,
        });
    }

    /// What expression `e` denotes: a package member, a dot-import name or nothing.
    fn resolve(&self, e: Node<'_>, depth: usize) -> Res {
        if depth > MAX_ALIAS_DEPTH {
            return Res::Nothing;
        }
        match e.kind() {
            "parenthesized_expression" => e
                .named_child(0)
                .map_or(Res::Nothing, |i| self.resolve(i, depth + 1)),
            "identifier" => self.resolve_name(e, depth),
            "call_expression" => self.resolve_call_result(e, depth),
            "selector_expression" => {
                let (Some(op), Some(f)) = (
                    e.child_by_field_name("operand"),
                    e.child_by_field_name("field"),
                ) else {
                    return Res::Nothing;
                };
                let member = text(self.src, f);
                match self.resolve(op, depth + 1) {
                    Res::Path { path, maybe } => Res::Path {
                        path: format!("{path}.{member}"),
                        maybe,
                    },
                    Res::Wild { path } => Res::Wild {
                        path: format!("{path}.{member}"),
                    },
                    Res::Nothing => Res::Nothing,
                }
            }
            _ => Res::Nothing,
        }
    }

    /// The value a call to a known reflection API yields (`reflect.ValueOf(v)` is a
    /// `reflect.Value`), so a member chain on it keeps resolving; any other call yields nothing.
    fn resolve_call_result(&self, call: Node<'_>, depth: usize) -> Res {
        let Some(f) = call.child_by_field_name("function") else {
            return Res::Nothing;
        };
        match self.resolve(f, depth + 1) {
            Res::Path { path, maybe } => match reflect_result(&path) {
                Some(ty) => {
                    tracing::debug!(%path, ty, "go: reflection call yields a reflect value");
                    Res::Path {
                        path: ty.to_owned(),
                        maybe,
                    }
                }
                None => Res::Nothing,
            },
            _ => Res::Nothing,
        }
    }

    fn resolve_name(&self, id: Node<'_>, depth: usize) -> Res {
        let name = text(self.src, id);
        match self.declared(id, name) {
            Some(Decl::Shadow) => Res::Nothing,
            Some(Decl::Alias(rhs, reassigned)) => match self.resolve(rhs, depth + 1) {
                Res::Path { path, maybe } => Res::Path {
                    path,
                    maybe: maybe || reassigned,
                },
                other => {
                    if reassigned {
                        Res::Nothing
                    } else {
                        other
                    }
                }
            },
            None => match self.imports.get(name) {
                Some(path) => Res::Path {
                    path: path.clone(),
                    maybe: false,
                },
                None if !self.dots.is_empty() => Res::Wild {
                    path: name.to_owned(),
                },
                None => Res::Nothing,
            },
        }
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
        match scope.kind() {
            "block" | "statement_list" | "expression_case" | "default_case" | "type_case"
            | "communication_case" => {
                let mut c = scope.walk();
                let kids: Vec<Node<'t>> = scope.named_children(&mut c).collect();
                for k in kids.into_iter().rev() {
                    if k.end_byte() <= start
                        && let Some(d) = self.declares(k, name, scope)
                    {
                        return Some(d);
                    }
                }
                if scope.kind() == "type_case"
                    && let Some(sw) = scope.parent()
                    && let Some(alias) = sw.child_by_field_name("alias")
                    && self
                        .names_in(alias)
                        .iter()
                        .any(|n| text(self.src, *n) == name)
                {
                    return Some(Decl::Shadow);
                }
                None
            }
            "function_declaration" | "method_declaration" | "func_literal" => {
                for field in ["receiver", "parameters", "result"] {
                    if let Some(list) = scope.child_by_field_name(field)
                        && self
                            .param_names(list)
                            .iter()
                            .any(|n| text(self.src, *n) == name)
                    {
                        return Some(Decl::Shadow);
                    }
                }
                None
            }
            "if_statement" | "expression_switch_statement" | "type_switch_statement" => scope
                .child_by_field_name("initializer")
                .filter(|i| i.end_byte() <= start && i != &child)
                .and_then(|i| self.declares(i, name, scope)),
            "for_statement" => {
                if scope.child_by_field_name("body") != Some(child) {
                    return None;
                }
                let mut c = scope.walk();
                let clause = scope
                    .named_children(&mut c)
                    .find(|k| matches!(k.kind(), "for_clause" | "range_clause"))?;
                if clause.kind() == "for_clause" {
                    return clause
                        .child_by_field_name("initializer")
                        .and_then(|i| self.declares(i, name, scope));
                }
                let mut cc = clause.walk();
                let defines = clause.children(&mut cc).any(|k| k.kind() == ":=");
                let left = clause.child_by_field_name("left")?;
                (defines
                    && self
                        .names_in(left)
                        .iter()
                        .any(|n| text(self.src, *n) == name))
                .then_some(Decl::Shadow)
            }
            "source_file" => {
                let mut c = scope.walk();
                let kids: Vec<Node<'t>> = scope.named_children(&mut c).collect();
                kids.into_iter().find_map(|k| match k.kind() {
                    "function_declaration" => (k
                        .child_by_field_name("name")
                        .is_some_and(|n| text(self.src, n) == name))
                    .then_some(Decl::Shadow),
                    "var_declaration" | "const_declaration" | "type_declaration" => {
                        self.declares(k, name, scope).map(|_| Decl::Shadow)
                    }
                    _ => None,
                })
            }
            _ => None,
        }
    }

    /// Whether statement or declaration `k` declares `name`, and how.
    fn declares<'t>(&self, k: Node<'t>, name: &str, scope: Node<'t>) -> Option<Decl<'t>> {
        match k.kind() {
            "short_var_declaration" => {
                let left = k.child_by_field_name("left")?;
                let right = k.child_by_field_name("right")?;
                let names = self.names_in(left);
                let idx = names.iter().position(|n| text(self.src, *n) == name)?;
                Some(self.alias_or_shadow(&names, idx, right, name, scope))
            }
            "var_declaration" | "const_declaration" => {
                let mut c = k.walk();
                let specs: Vec<Node<'t>> = k.named_children(&mut c).collect();
                specs
                    .into_iter()
                    .flat_map(|s| {
                        let mut c = s.walk();
                        let inner: Vec<Node<'t>> = if s.kind() == "var_spec_list" {
                            s.named_children(&mut c).collect()
                        } else {
                            vec![s]
                        };
                        inner
                    })
                    .find_map(|s| {
                        let mut c = s.walk();
                        let names: Vec<Node<'t>> = s
                            .children_by_field_name("name", &mut c)
                            .filter(|n| n.kind() == "identifier")
                            .collect();
                        let idx = names.iter().position(|n| text(self.src, *n) == name)?;
                        match s.child_by_field_name("value") {
                            Some(v) if s.kind() == "var_spec" => {
                                Some(self.alias_or_shadow(&names, idx, v, name, scope))
                            }
                            _ => Some(Decl::Shadow),
                        }
                    })
            }
            "type_declaration" => {
                let mut c = k.walk();
                let hit = k.named_children(&mut c).any(|s| {
                    matches!(s.kind(), "type_spec" | "type_alias")
                        && s.child_by_field_name("name")
                            .is_some_and(|n| text(self.src, n) == name)
                });
                hit.then_some(Decl::Shadow)
            }
            _ => None,
        }
    }

    /// `name := expr` binds an alias when exactly one value initialises exactly one name;
    /// anything else (a tuple return, a multi-assign) is an opaque local.
    fn alias_or_shadow<'t>(
        &self,
        names: &[Node<'t>],
        idx: usize,
        right: Node<'t>,
        name: &str,
        scope: Node<'t>,
    ) -> Decl<'t> {
        let values: Vec<Node<'t>> = if right.kind() == "expression_list" {
            let mut c = right.walk();
            right.named_children(&mut c).collect()
        } else {
            vec![right]
        };
        if values.len() != names.len() {
            return Decl::Shadow;
        }
        let value = values[idx];
        if !matches!(value.kind(), "selector_expression" | "identifier") {
            return Decl::Shadow;
        }
        Decl::Alias(value, self.reassigned(scope, name))
    }

    /// True when `name` is the target of a plain assignment anywhere under `scope`.
    fn reassigned(&self, scope: Node<'_>, name: &str) -> bool {
        let mut stack = vec![scope];
        while let Some(n) = stack.pop() {
            if n.kind() == "assignment_statement"
                && let Some(left) = n.child_by_field_name("left")
                && self
                    .names_in(left)
                    .iter()
                    .any(|i| text(self.src, *i) == name)
            {
                return true;
            }
            let mut c = n.walk();
            stack.extend(n.children(&mut c));
        }
        false
    }

    /// The identifiers directly in an `expression_list` (or the lone identifier).
    #[allow(clippy::unused_self)]
    fn names_in<'t>(&self, n: Node<'t>) -> Vec<Node<'t>> {
        if n.kind() == "identifier" {
            return vec![n];
        }
        let mut c = n.walk();
        n.named_children(&mut c)
            .filter(|k| k.kind() == "identifier")
            .collect()
    }

    /// The names a parameter list declares.
    #[allow(clippy::unused_self)]
    fn param_names<'t>(&self, list: Node<'t>) -> Vec<Node<'t>> {
        let mut out = Vec::new();
        let mut c = list.walk();
        for p in list.named_children(&mut c) {
            if matches!(
                p.kind(),
                "parameter_declaration" | "variadic_parameter_declaration"
            ) {
                let mut pc = p.walk();
                out.extend(p.children_by_field_name("name", &mut pc));
            }
        }
        out
    }
}

/// True when `n` is the function of a call expression.
fn is_call_function(n: Node<'_>) -> bool {
    n.parent().is_some_and(|p| {
        p.kind() == "call_expression" && p.child_by_field_name("function") == Some(n)
    })
}

#[cfg(test)]
mod tests {
    use crate::canon::{PathUse, path_uses};

    fn uses(src: &str) -> Vec<PathUse> {
        path_uses("go", src)
    }

    fn paths(src: &str) -> Vec<String> {
        uses(src).into_iter().map(|u| u.path).collect()
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn plain_aliased_and_grouped_imports_resolve() {
        let plain = "package m\nimport \"os/exec\"\nfunc f() { exec.Command(\"ls\") }\n";
        assert_eq!(paths(plain), ["os/exec.Command"]);
        let alias = "package m\nimport e \"os/exec\"\nfunc f() { e.Command(\"ls\") }\n";
        assert_eq!(paths(alias), ["os/exec.Command"]);
        let grouped = "package m\nimport (\n\t\"fmt\"\n\th \"net/http\"\n\t\"os\"\n)\nfunc f() {\n\th.Get(\"u\")\n\tos.Getenv(\"K\")\n\tfmt.Println()\n}\n";
        let p = paths(grouped);
        assert!(p.contains(&"net/http.Get".to_owned()), "{p:?}");
        assert!(p.contains(&"os.Getenv".to_owned()), "{p:?}");
        let call = uses(plain);
        assert!(call[0].call && !call[0].maybe && call[0].wildcards.is_empty());
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn locals_and_blank_imports_hide_the_package() {
        let local = "package m\nimport \"os/exec\"\nfunc f() {\n\texec := struct{ Command func(string) }{}\n\texec.Command(\"ls\")\n}\n";
        assert!(paths(local).is_empty(), "{:?}", paths(local));
        let param = "package m\nimport \"os\"\nfunc f(os T) { os.Getenv(\"K\") }\n";
        assert!(paths(param).is_empty());
        let blank = "package m\nimport _ \"os/exec\"\nfunc f() { exec.Command(\"ls\") }\n";
        assert!(paths(blank).is_empty());
        let rhs =
            "package m\nimport \"os/exec\"\nfunc f() { exec := exec.Command(\"ls\"); _ = exec }\n";
        assert_eq!(paths(rhs), ["os/exec.Command"]);
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn dot_imports_emit_bare_names_with_wildcards() {
        let src = "package m\nimport . \"os/exec\"\nfunc f() { Command(\"ls\") }\n";
        let u = uses(src);
        assert_eq!(u.len(), 1);
        assert_eq!(u[0].path, "Command");
        assert_eq!(u[0].wildcards, ["os/exec"]);
        let local =
            "package m\nimport . \"os/exec\"\nfunc f() {\n\tCommand := g\n\tCommand(\"ls\")\n}\n";
        assert!(paths(local).iter().all(|p| p != "Command"));
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn value_aliases_resolve_and_reassigned_ones_are_maybe() {
        let alias =
            "package m\nimport \"os/exec\"\nfunc f() {\n\trun := exec.Command\n\trun(\"ls\")\n}\n";
        assert!(
            uses(alias)
                .iter()
                .all(|u| u.path == "os/exec.Command" && !u.maybe)
        );
        assert_eq!(uses(alias).len(), 2);
        let moved = "package m\nimport \"os/exec\"\nfunc f(x func(string)) {\n\trun := exec.Command\n\trun = x\n\trun(\"ls\")\n}\n";
        let call: Vec<_> = uses(moved).into_iter().filter(|u| u.call).collect();
        assert_eq!(call.len(), 1);
        assert!(call[0].maybe);
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn types_and_selector_chains_resolve() {
        let src = "package m\nimport \"net/http\"\nvar c = http.Client{}\nfunc f() { http.DefaultClient.Get(\"u\") }\n";
        let p = paths(src);
        assert!(p.contains(&"net/http.Client".to_owned()), "{p:?}");
        assert!(
            p.contains(&"net/http.DefaultClient.Get".to_owned()),
            "{p:?}"
        );
    }

    #[test]
    fn default_name_skips_version_suffixes() {
        assert_eq!(super::default_name("net/http"), "http");
        assert_eq!(super::default_name("github.com/x/y/v3"), "y");
        assert_eq!(super::default_name("gopkg.in/yaml.v2"), "yaml");
    }
}
