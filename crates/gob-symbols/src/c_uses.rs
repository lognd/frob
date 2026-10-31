//! Include-resolved C and C++ uses: `system`, `popen`, `exec*`, `fopen`, `open`, `socket`,
//! `connect`, `bind`, `getenv`, `dlopen`, resolved to the header that supplies them.
//!
//! A path is the supplying header plus the function, so `#include <stdlib.h>` then `system(c)` is
//! `stdlib.h.system`. C++ spells the same header `<cstdlib>` and the call `std::system(c)`; both
//! give the same path. Resolution is over tree-sitter nodes, never text:
//!
//! - a call or function reference binds to its nearest enclosing declaration first: a function
//!   defined in the file (a local `system`) hides the library one and names nothing; a local,
//!   parameter or global variable of that name is a function pointer, so a call through it is
//!   Unresolved unless it was initialised from a resolvable name (then that name, as `maybe`);
//! - otherwise the name is the library function when a header known to declare it is included, or
//!   a prototype for it is present; with no such header (an implicit declaration, a declaration in
//!   a project header) it is emitted as `maybe`, never dropped;
//! - a call through a function pointer expression (`s->run(x)`, `tbl[i](x)`, `(*fp)(x)`) and a
//!   call or use of a macro (`#define RUN system`) are emitted computed: the callee is not known
//!   without running the preprocessor, so the consumer reports them Unresolved;
//! - names inside strings, comments and `#if 0` text are never nodes, so they name nothing;
//! - a C++ namespace alias (`namespace s = std;`, chained, or declared in a nested scope) is
//!   followed to its target, the innermost visible alias winning, so `s::system` is `std::system`.
//!
//! Not modelled: transitive includes (a project header may include `<stdlib.h>`; the use is then
//! `maybe`), `using namespace std` unqualified C++ names beyond the same bare-name rule, member
//! functions named like a library function, and C++ method calls through a stored callable.

// frob:ticket 01M64VBRHX20P2EJGQ2S1VG0FG

use std::collections::{BTreeMap, BTreeSet};

use tree_sitter::Node;

use crate::canon::PathUse;

/// Deepest alias chain followed (`fp = g; g = system`).
const MAX_ALIAS_DEPTH: usize = 6;

/// One library function: its name, the headers that declare it (the first is canonical in the
/// path) and whether `std::` names it in C++.
struct Libc {
    name: &'static str,
    headers: &'static [&'static str],
    std: bool,
}

const fn libc(name: &'static str, headers: &'static [&'static str], std: bool) -> Libc {
    Libc { name, headers, std }
}

/// The library functions capabilities live in.
const LIBC: &[Libc] = &[
    libc("system", &["stdlib.h"], true),
    libc("popen", &["stdio.h"], false),
    libc("execl", &["unistd.h"], false),
    libc("execlp", &["unistd.h"], false),
    libc("execle", &["unistd.h"], false),
    libc("execv", &["unistd.h"], false),
    libc("execvp", &["unistd.h"], false),
    libc("execve", &["unistd.h"], false),
    libc("execvpe", &["unistd.h"], false),
    libc("fexecve", &["unistd.h"], false),
    libc("posix_spawn", &["spawn.h"], false),
    libc("posix_spawnp", &["spawn.h"], false),
    libc("fopen", &["stdio.h"], true),
    libc("freopen", &["stdio.h"], true),
    libc("open", &["fcntl.h"], false),
    libc("openat", &["fcntl.h"], false),
    libc("creat", &["fcntl.h"], false),
    libc("opendir", &["dirent.h"], false),
    libc("remove", &["stdio.h"], true),
    libc("rename", &["stdio.h"], true),
    libc("unlink", &["unistd.h"], false),
    libc("mkdir", &["sys/stat.h"], false),
    libc("socket", &["sys/socket.h", "winsock2.h"], false),
    libc("connect", &["sys/socket.h", "winsock2.h"], false),
    libc("bind", &["sys/socket.h", "winsock2.h"], false),
    libc("listen", &["sys/socket.h", "winsock2.h"], false),
    libc("accept", &["sys/socket.h", "winsock2.h"], false),
    libc("getaddrinfo", &["netdb.h", "ws2tcpip.h"], false),
    libc("gethostbyname", &["netdb.h", "winsock2.h"], false),
    libc("getenv", &["stdlib.h"], true),
    libc("secure_getenv", &["stdlib.h"], false),
    libc("dlopen", &["dlfcn.h"], false),
    libc("dlsym", &["dlfcn.h"], false),
];

fn libc_entry(name: &str) -> Option<&'static Libc> {
    LIBC.iter().find(|l| l.name == name)
}

/// What a name binds to at a use site.
enum Bind<'t> {
    /// A variable (local, parameter, global), with its initialiser when it has one.
    Var(Option<Node<'t>>),
    /// A function defined in this file.
    Defined,
    /// A function declared (a prototype) but not defined here.
    Proto,
    /// A macro defined in this file, with whether its replacement may hide a call.
    Macro { hides_call: bool },
    /// Nothing declared in this file.
    Unbound,
}

/// What a use resolves to.
enum Out {
    /// A library function; `maybe` when its supplier is not proven.
    Path { path: String, maybe: bool },
    /// A callee only the preprocessor or the program run can know.
    Computed,
    /// Nothing capability-bearing.
    Nothing,
}

struct Cx<'s> {
    src: &'s str,
    cpp: bool,
    /// Included headers, normalised (`<cstdlib>` is `stdlib.h`).
    includes: BTreeSet<String>,
    /// Whether an `#include` the scanner cannot read (a macro operand) is present.
    opaque_include: bool,
    macros: BTreeMap<String, bool>,
    /// File-scope declarations by name, looked through namespaces and linkage blocks.
    file_scope: BTreeMap<String, FileDecl>,
    /// Every `namespace a = b;` alias, wherever it is declared.
    aliases: Vec<NsAlias>,
    out: Vec<PathUse>,
}

/// A C++ namespace alias and the scope that makes it visible.
struct NsAlias {
    name: String,
    /// The aliased namespace as spelled (`std`, `::std`, `a::b`, or another alias).
    target: String,
    /// Where the alias begins; it is visible only after this.
    start: usize,
    /// Byte range of the enclosing scope (file, namespace body or block).
    scope: (usize, usize),
}

/// Deepest alias chain followed before giving up (a cycle is a compile error).
const ALIAS_DEPTH: usize = 16;

/// A file-scope declaration kind.
#[derive(Clone, Copy)]
enum FileDecl {
    Defined,
    Proto,
    Var,
}

/// Every include-resolved library use in a C (`cpp` false) or C++ syntax tree.
pub(crate) fn scan(src: &str, root: Node<'_>, cpp: bool) -> Vec<PathUse> {
    let mut cx = Cx {
        src,
        cpp,
        includes: BTreeSet::new(),
        opaque_include: false,
        macros: BTreeMap::new(),
        file_scope: BTreeMap::new(),
        aliases: Vec::new(),
        out: Vec::new(),
    };
    cx.collect(root);
    tracing::debug!(
        cpp,
        includes = cx.includes.len(),
        macros = cx.macros.len(),
        file_decls = cx.file_scope.len(),
        "c: file bound"
    );
    cx.visit(root);
    cx.out
}

fn text<'a>(src: &'a str, n: Node<'_>) -> &'a str {
    &src[n.start_byte()..n.end_byte()]
}

/// The name node a declarator declares, and whether it declares a function (not a pointer to one).
fn peel(d: Node<'_>) -> Option<(Node<'_>, bool)> {
    let mut cur = d;
    loop {
        match cur.kind() {
            "identifier"
            | "field_identifier"
            | "qualified_identifier"
            | "destructor_name"
            | "operator_name" => return Some((cur, false)),
            "function_declarator" => {
                let inner = cur.child_by_field_name("declarator")?;
                if matches!(
                    inner.kind(),
                    "identifier" | "field_identifier" | "qualified_identifier"
                ) {
                    return Some((inner, true));
                }
                cur = inner;
            }
            _ => {
                cur = cur
                    .child_by_field_name("declarator")
                    .or_else(|| cur.named_child(0))?;
            }
        }
    }
}

/// What `decl` (a `declaration`) declares under `name`: whether it is a function, and its initialiser.
fn declares<'t>(src: &str, decl: Node<'t>, name: &str) -> Option<(bool, Option<Node<'t>>)> {
    let mut c = decl.walk();
    for d in decl.children_by_field_name("declarator", &mut c) {
        let init = (d.kind() == "init_declarator")
            .then(|| d.child_by_field_name("value"))
            .flatten();
        let target = if d.kind() == "init_declarator" {
            d.child_by_field_name("declarator")?
        } else {
            d
        };
        if let Some((n, func)) = peel(target)
            && text(src, n) == name
        {
            return Some((func, init));
        }
    }
    None
}

/// The declarator chain's parameter list (a function definition's or lambda's), if any.
fn params_of(def: Node<'_>) -> Option<Node<'_>> {
    let mut cur = def.child_by_field_name("declarator");
    while let Some(n) = cur {
        if let Some(p) = n.child_by_field_name("parameters") {
            return Some(p);
        }
        cur = n.child_by_field_name("declarator");
    }
    None
}

/// Whether a replacement text may hide a call (it holds a parenthesis or names a library function).
fn body_hides_call(body: &str) -> bool {
    body.contains('(')
        || body
            .split(|c: char| !(c.is_ascii_alphanumeric() || c == '_'))
            .any(|t| libc_entry(t).is_some())
}

impl<'t> Cx<'_> {
    /// Bind includes, macros and file-scope declarations.
    fn collect(&mut self, root: Node<'_>) {
        let mut stack = vec![root];
        while let Some(n) = stack.pop() {
            match n.kind() {
                "preproc_include" => self.bind_include(n),
                "preproc_def" | "preproc_function_def" => {
                    if let Some(name) = n.child_by_field_name("name") {
                        let body = n
                            .child_by_field_name("value")
                            .map_or("", |v| text(self.src, v));
                        let hides = n.kind() == "preproc_function_def" || body_hides_call(body);
                        self.macros.insert(text(self.src, name).to_owned(), hides);
                    }
                }
                "function_definition" => {
                    if let Some((name, _)) = n.child_by_field_name("declarator").and_then(peel) {
                        self.file_scope
                            .insert(text(self.src, name).to_owned(), FileDecl::Defined);
                    }
                    // a body holds only local scopes
                    continue;
                }
                "declaration" => {
                    let mut c = n.walk();
                    for d in n.children_by_field_name("declarator", &mut c) {
                        let target = if d.kind() == "init_declarator" {
                            d.child_by_field_name("declarator").unwrap_or(d)
                        } else {
                            d
                        };
                        if let Some((name, func)) = peel(target) {
                            let kind = if func { FileDecl::Proto } else { FileDecl::Var };
                            self.file_scope
                                .entry(text(self.src, name).to_owned())
                                .or_insert(kind);
                        }
                    }
                    continue;
                }
                "compound_statement" | "field_declaration_list" => continue,
                _ => {}
            }
            let mut c = n.walk();
            stack.extend(n.children(&mut c));
        }
        self.collect_aliases(root);
    }

    /// Bind every namespace alias in the tree, including those in function bodies.
    fn collect_aliases(&mut self, root: Node<'_>) {
        let mut stack = vec![root];
        while let Some(n) = stack.pop() {
            if n.kind() == "namespace_alias_definition"
                && let Some(name) = n.child_by_field_name("name")
                && let Some(scope) = n.parent()
                && let Some(target) = n
                    .named_children(&mut n.walk())
                    .find(|c| c.id() != name.id() && c.kind() != "comment")
            {
                let alias = NsAlias {
                    name: text(self.src, name).to_owned(),
                    target: text(self.src, target).split_whitespace().collect(),
                    start: n.start_byte(),
                    scope: (scope.start_byte(), scope.end_byte()),
                };
                tracing::debug!(alias = %alias.name, target = %alias.target, "c: namespace alias bound");
                self.aliases.push(alias);
            }
            let mut c = n.walk();
            stack.extend(n.children(&mut c));
        }
    }

    /// The namespace `scope` really names at byte `at`, following visible aliases (innermost wins).
    fn resolve_ns(&self, scope: &str, at: usize) -> String {
        let mut cur = scope.split_whitespace().collect::<String>();
        for _ in 0..ALIAS_DEPTH {
            let (head, rest) = match cur.split_once("::") {
                Some((h, r)) if !h.is_empty() => (h.to_owned(), Some(r.to_owned())),
                _ => (cur.clone(), None),
            };
            let hit = self
                .aliases
                .iter()
                .filter(|a| a.name == head && a.start < at && a.scope.0 <= at && at < a.scope.1)
                .min_by_key(|a| a.scope.1 - a.scope.0);
            let Some(alias) = hit else { return cur };
            tracing::debug!(%head, target = %alias.target, "c: namespace alias followed");
            cur = match rest {
                Some(r) => format!("{}::{r}", alias.target),
                None => alias.target.clone(),
            };
        }
        cur
    }

    fn bind_include(&mut self, n: Node<'_>) {
        let Some(path) = n.child_by_field_name("path") else {
            return;
        };
        let raw = text(self.src, path);
        match path.kind() {
            "system_lib_string" | "string_literal" => {
                let inner = raw.trim_matches(['<', '>', '"']).trim();
                let header = normalise_header(inner);
                tracing::debug!(%header, "c: include bound");
                self.includes.insert(header);
            }
            _ => self.opaque_include = true,
        }
    }

    fn visit(&mut self, root: Node<'_>) {
        let mut stack = vec![root];
        while let Some(n) = stack.pop() {
            let mut c = n.walk();
            stack.extend(n.children(&mut c));
            match n.kind() {
                "call_expression" => self.call(n),
                "identifier" if Self::is_reference(n) => self.reference(n),
                "qualified_identifier" if !is_call_function(n) => self.qualified(n, n, false),
                _ => {}
            }
        }
    }

    /// True when the identifier is an expression reference, not a declared name, a call's callee
    /// (the call is handled whole) or the member of a qualified name.
    fn is_reference(n: Node<'_>) -> bool {
        let Some(p) = n.parent() else { return false };
        if is_call_function(n) {
            return false;
        }
        if matches!(
            p.kind(),
            "qualified_identifier"
                | "parenthesized_declarator"
                | "parameter_declaration"
                | "optional_parameter_declaration"
                | "preproc_params"
                | "preproc_include"
                | "preproc_def"
                | "preproc_function_def"
                | "enumerator"
                | "using_declaration"
                | "namespace_definition"
                | "namespace_alias_definition"
        ) {
            return false;
        }
        let named = |f: &str| p.child_by_field_name(f).is_some_and(|d| d.id() == n.id());
        !(named("declarator") || named("name"))
    }

    /// A non-call reference to a name (a function value, or an object-like macro).
    fn reference(&mut self, id: Node<'_>) {
        let name = text(self.src, id);
        let is_lib = libc_entry(name).is_some();
        let bind = self.lookup(name, id);
        let out = match bind {
            Bind::Macro { hides_call: true } => Out::Computed,
            Bind::Proto | Bind::Unbound if is_lib => self.library(name, false),
            _ => Out::Nothing,
        };
        self.emit(id, id, false, out);
    }

    fn call(&mut self, call: Node<'_>) {
        let Some(f) = call.child_by_field_name("function") else {
            return;
        };
        let out = self.callee(f, 0);
        let out = match (out, f.kind()) {
            (Some(o), _) => o,
            (None, "qualified_identifier") => {
                self.qualified(f, call, true);
                return;
            }
            (None, _) => Out::Nothing,
        };
        self.emit(f, call, true, out);
    }

    /// Resolves a call's callee expression; `None` for a qualified name (handled by the caller).
    fn callee(&self, f: Node<'_>, depth: usize) -> Option<Out> {
        Some(match f.kind() {
            "identifier" => self.call_of(f, depth),
            "qualified_identifier" => return None,
            "parenthesized_expression" | "pointer_expression" => match f.named_child(0) {
                Some(inner) if depth < MAX_ALIAS_DEPTH => {
                    return self.callee(inner, depth + 1).or(Some(Out::Computed));
                }
                _ => Out::Computed,
            },
            "subscript_expression"
            | "call_expression"
            | "conditional_expression"
            | "cast_expression"
            | "comma_expression" => Out::Computed,
            _ if !self.cpp => Out::Computed,
            _ => Out::Nothing,
        })
    }

    /// A call of a bare name, resolved through its binding.
    fn call_of(&self, id: Node<'_>, depth: usize) -> Out {
        let name = text(self.src, id);
        match self.lookup(name, id) {
            Bind::Macro { .. } => Out::Computed,
            Bind::Var(init) => self.through_pointer(init, depth),
            Bind::Proto | Bind::Unbound if libc_entry(name).is_some() => self.library(name, true),
            Bind::Defined | Bind::Proto | Bind::Unbound => Out::Nothing,
        }
    }

    /// A call through a variable: its initialiser's callee if that resolves (unproven, since the
    /// variable may be reassigned), else unknown.
    fn through_pointer(&self, init: Option<Node<'_>>, depth: usize) -> Out {
        let Some(init) = init else {
            return Out::Computed;
        };
        if depth >= MAX_ALIAS_DEPTH {
            return Out::Computed;
        }
        let target = match init.kind() {
            "identifier" => self.call_of(init, depth + 1),
            "pointer_expression" | "parenthesized_expression" => init
                .named_child(0)
                .filter(|n| n.kind() == "identifier")
                .map_or(Out::Computed, |n| self.call_of(n, depth + 1)),
            _ => Out::Computed,
        };
        match target {
            Out::Path { path, .. } => Out::Path { path, maybe: true },
            _ => Out::Computed,
        }
    }

    /// A `scope::name` use in C++ (`std::system`, `::system`).
    fn qualified(&mut self, q: Node<'_>, at: Node<'_>, call: bool) {
        let (Some(name), scope) = (
            q.child_by_field_name("name"),
            q.child_by_field_name("scope"),
        ) else {
            return;
        };
        if name.kind() != "identifier" {
            return;
        }
        let spelled = text(self.src, name);
        let Some(entry) = libc_entry(spelled) else {
            return;
        };
        let resolved = scope.map(|s| self.resolve_ns(text(self.src, s), s.start_byte()));
        let out = match resolved.as_deref() {
            Some("std" | "::std") if entry.std => self.library(spelled, call),
            // `::system` is the global name: a file-scope function hides it, a local does not
            None => match self.file_scope.get(spelled) {
                Some(FileDecl::Defined | FileDecl::Var) => Out::Nothing,
                _ => self.library(spelled, call),
            },
            _ => Out::Nothing,
        };
        self.emit(name, at, call, out);
    }

    /// The library function `name`, certain when a declaring header is included.
    fn library(&self, name: &str, _call: bool) -> Out {
        let Some(entry) = libc_entry(name) else {
            return Out::Nothing;
        };
        let path = format!("{}.{}", entry.headers[0], entry.name);
        let proto = matches!(self.file_scope.get(name), Some(FileDecl::Proto));
        let supplied = entry.headers.iter().any(|h| self.includes.contains(*h));
        let maybe = !supplied && (!proto || self.opaque_include);
        Out::Path { path, maybe }
    }

    fn emit(&mut self, f: Node<'_>, at: Node<'_>, call: bool, out: Out) {
        let (path, maybe, computed) = match out {
            Out::Path { path, maybe } => (path, maybe, false),
            Out::Computed => (String::new(), true, true),
            Out::Nothing => return,
        };
        tracing::debug!(%path, call, maybe, computed, "c: library use");
        self.out.push(PathUse {
            offset: at.start_byte(),
            line: u32::try_from(at.start_position().row + 1).unwrap_or(u32::MAX),
            spelled: text(self.src, f).split_whitespace().collect(),
            path,
            call,
            dynamic: maybe,
            external_root: false,
            computed,
            wildcards: Vec::new(),
            maybe,
        });
    }

    /// What `name` binds to at `at`: the nearest enclosing declaration, else the file scope.
    fn lookup(&self, name: &str, at: Node<'t>) -> Bind<'t> {
        if let Some(&hides_call) = self.macros.get(name) {
            return Bind::Macro { hides_call };
        }
        let mut cur = at;
        while let Some(p) = cur.parent() {
            match p.kind() {
                "compound_statement" => {
                    let mut found = None;
                    let mut c = p.walk();
                    for s in p.children(&mut c) {
                        if s.start_byte() < at.start_byte()
                            && s.kind() == "declaration"
                            && let Some((func, init)) = declares(self.src, s, name)
                        {
                            found = Some(if func { Bind::Proto } else { Bind::Var(init) });
                        }
                    }
                    if let Some(b) = found {
                        return b;
                    }
                }
                "for_statement" | "for_range_loop" | "if_statement" | "while_statement"
                | "switch_statement" => {
                    let mut c = p.walk();
                    for s in p.children(&mut c) {
                        if s.kind() == "declaration"
                            && let Some((_, init)) = declares(self.src, s, name)
                        {
                            return Bind::Var(init);
                        }
                    }
                    if let Some(d) = p.child_by_field_name("declarator")
                        && peel(d).is_some_and(|(n, _)| text(self.src, n) == name)
                    {
                        return Bind::Var(None);
                    }
                }
                "function_definition" | "lambda_expression" => {
                    if let Some(params) = params_of(p) {
                        let mut c = params.walk();
                        for prm in params.named_children(&mut c) {
                            if let Some(d) = prm.child_by_field_name("declarator")
                                && peel(d).is_some_and(|(n, _)| text(self.src, n) == name)
                            {
                                return Bind::Var(None);
                            }
                        }
                    }
                }
                _ => {}
            }
            cur = p;
        }
        match self.file_scope.get(name) {
            Some(FileDecl::Defined) => Bind::Defined,
            Some(FileDecl::Proto) => Bind::Proto,
            Some(FileDecl::Var) => Bind::Var(None),
            None => Bind::Unbound,
        }
    }
}

/// True when `n` is the callee of a call expression.
fn is_call_function(n: Node<'_>) -> bool {
    n.parent().is_some_and(|p| {
        p.kind() == "call_expression"
            && p.child_by_field_name("function")
                .is_some_and(|f| f.id() == n.id())
    })
}

/// A header spelled `<cstdlib>` is C's `stdlib.h`; every other spelling is kept as written.
fn normalise_header(h: &str) -> String {
    match h.strip_prefix('c') {
        Some(rest) if !h.contains('.') && !rest.is_empty() => format!("{rest}.h"),
        _ => h.to_owned(),
    }
}

#[cfg(test)]
mod tests {
    use gob_languages::{Language, ParseLimits, ParseResult, parse};

    use super::*;

    fn uses(cpp: bool, src: &str) -> Vec<PathUse> {
        let lang = if cpp { Language::Cpp } else { Language::C };
        let ParseResult::Parsed(t) = parse(lang, src, &ParseLimits::default()) else {
            panic!("parse");
        };
        scan(&t.text, t.root(), cpp)
    }

    fn paths(cpp: bool, src: &str) -> Vec<(String, bool, bool)> {
        uses(cpp, src)
            .into_iter()
            .map(|u| (u.path, u.maybe, u.computed))
            .collect()
    }

    // frob:tests crates/gob-symbols/src/c_uses.rs::scan
    #[test]
    fn resolves_a_call_through_its_include() {
        let got = paths(
            false,
            "#include <stdlib.h>\nvoid f(const char*c){ system(c); }\n",
        );
        assert_eq!(got, vec![("stdlib.h.system".to_owned(), false, false)]);
    }

    // frob:tests crates/gob-symbols/src/c_uses.rs::scan
    #[test]
    fn cpp_headers_and_std_names_resolve_alike() {
        let got = paths(
            true,
            "#include <cstdlib>\nvoid f(const char*c){ std::system(c); ::getenv(c); }\n",
        );
        assert_eq!(got.len(), 2, "{got:?}");
        assert!(got.iter().all(|(_, maybe, _)| !maybe));
    }

    // frob:tests crates/gob-symbols/src/c_uses.rs::scan
    #[test]
    fn a_local_definition_shadows_the_library() {
        let src = "int system(const char*c){return 0;}\nvoid f(){ system(\"x\"); }\n";
        assert!(uses(false, src).is_empty());
        let local = "#include <stdlib.h>\nvoid f(){ int getenv = 1; (void)getenv; }\n";
        assert!(uses(false, local).is_empty());
    }

    // frob:tests crates/gob-symbols/src/c_uses.rs::scan
    #[test]
    fn strings_and_comments_name_nothing() {
        let src = "#include <stdlib.h>\n// system(x)\nchar *s = \"system(x)\";\n/* getenv */\n";
        assert!(uses(false, src).is_empty());
    }

    // frob:tests crates/gob-symbols/src/c_uses.rs::scan
    #[test]
    fn pointers_and_macros_are_computed() {
        let src = "struct S { int (*run)(const char*); };\nvoid f(struct S *s, int (*fp)(const char*)){ s->run(\"x\"); fp(\"x\"); }\n";
        assert!(paths(false, src).iter().all(|(_, _, c)| *c));
        assert_eq!(paths(false, src).len(), 2);
        let mac = "#define RUN system\nvoid f(){ RUN(\"x\"); }\n";
        assert_eq!(paths(false, mac), vec![(String::new(), true, true)]);
    }

    // frob:tests crates/gob-symbols/src/c_uses.rs::scan
    #[test]
    fn an_alias_and_an_unincluded_name_are_unproven() {
        let src = "#include <stdlib.h>\nvoid f(){ int (*r)(const char*) = system; r(\"x\"); }\n";
        let got = paths(false, src);
        assert!(
            got.contains(&("stdlib.h.system".to_owned(), false, false)),
            "{got:?}"
        );
        assert!(
            got.contains(&("stdlib.h.system".to_owned(), true, false)),
            "{got:?}"
        );
        let bare = paths(false, "void f(){ system(\"x\"); }\n");
        assert_eq!(bare, vec![("stdlib.h.system".to_owned(), true, false)]);
    }

    // frob:ticket 01M688124N09MGJXMHXHVSKPQW
    // frob:tests crates/gob-symbols/src/c_uses.rs::scan
    #[test]
    fn namespace_aliases_resolve_to_std_and_respect_scope() {
        let hdr = "#include <cstdlib>\n";
        let got = |body: &str| paths(true, &format!("{hdr}{body}"));
        let hit = vec![("stdlib.h.system".to_owned(), false, false)];
        assert_eq!(
            got("namespace s = std;\nvoid f(){ s::system(\"x\"); }\n"),
            hit
        );
        assert_eq!(
            got("namespace a = std; namespace b = a;\nvoid f(){ b::system(\"x\"); }\n"),
            hit
        );
        assert_eq!(
            got("void f(){ namespace s = std; s::system(\"x\"); }\n"),
            hit
        );
        assert!(
            got("namespace n { int system(const char*); } namespace s = n;\nvoid f(){ s::system(\"x\"); }\n")
                .is_empty()
        );
        assert!(got("namespace s = std;\nvoid f(){ s::cout; }\n").is_empty());
    }
}
