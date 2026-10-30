//! The C# scanner: `using` namespaces as glob prefixes, `using static`, `using X = ...` aliases,
//! `global using` (project-wide), `global::` qualified names, reflection, `DllImport` externs and
//! Unity's inherited `MonoBehaviour.print`.

// frob:ticket 01M5XMR67K19SFAWNTDJKKJPTT
// frob:ticket 01M64230Q2FSG2WXTFT4ENDA4R

use tree_sitter::Node;

use std::collections::BTreeMap;

use super::catalogue::{ArgInfo, Args, Seg};
use super::engine::{Binding, FileScan, Project, State, SymPath, Unres, all_kids, kids};

/// The canonical path of Unity's inherited `MonoBehaviour.print` helper.
const MONO_PRINT: [&str; 3] = ["UnityEngine", "MonoBehaviour", "print"];
/// The canonical prefix a native import resolves under (`DllImport.<lib>.<entry>`).
const PINVOKE: [&str; 4] = ["System", "Runtime", "InteropServices", "DllImport"];

/// Scan one parsed C# compilation unit.
pub fn scan(mut st: State<'_>, root: Node<'_>) -> FileScan {
    for g in &st.ctx.project.globals {
        st.globs.push(g.clone());
    }
    // `using` directives apply file-wide, wherever they appear before use.
    usings(&mut st, root);
    let decls = declarations(st.src, root, &st.ctx.project.globals);
    for e in &decls.externs {
        match &e.target {
            Ok(path) => st.bind(&e.method, Binding::Alias(path.clone())),
            Err(why) => {
                tracing::debug!(method = %e.method, why = %why, "native import target is dynamic");
                st.unresolved.push(Unres {
                    start: e.start,
                    end: e.end,
                    what: why.clone(),
                });
                st.bind(&e.method, Binding::Opaque);
            }
        }
    }
    visit(&mut st, root);
    st.finish()
}

/// One C# class: its simple name and the resolved paths of its base-list types.
#[derive(Debug, Clone)]
pub struct ClassDecl {
    /// The class's simple name.
    pub name: String,
    /// True when it declares its own `print` method (which shadows the inherited helper).
    pub own_print: bool,
    /// The base-list types, resolved through the file's `using` aliases and namespaces.
    pub bases: Vec<SymPath>,
}

/// One `extern` method bound to a native entry point by `[DllImport]` or `[LibraryImport]`.
#[derive(Debug, Clone)]
pub struct ExternDecl {
    /// The enclosing class's simple name.
    pub class: String,
    /// The managed method name callers use.
    pub method: String,
    /// The canonical native path, or why the entry point is dynamic.
    pub target: Result<SymPath, String>,
    /// Byte range of the declaration.
    pub start: usize,
    /// Byte range of the declaration.
    pub end: usize,
}

/// What one file declares that other files can inherit or call.
#[derive(Debug, Clone, Default)]
pub struct Decls {
    /// Classes with their resolved base types.
    pub classes: Vec<ClassDecl>,
    /// Native-import `extern` methods.
    pub externs: Vec<ExternDecl>,
}

/// One `using` directive: an alias or a namespace/static-type glob.
enum Using {
    Alias(String, SymPath),
    Glob(SymPath),
}

fn using_of(src: &str, n: Node<'_>) -> Option<Using> {
    let is_alias = all_kids(n).iter().any(|t| &src[t.byte_range()] == "=");
    let ks = kids(n);
    let target = dotted(&src[ks.last()?.byte_range()]);
    if is_alias {
        Some(Using::Alias(
            src[ks.first()?.byte_range()].to_owned(),
            target,
        ))
    } else {
        Some(Using::Glob(target))
    }
}

fn dotted(text: &str) -> SymPath {
    let text = text.trim().trim_start_matches("global::");
    text.split('.')
        .map(|s| s.trim().to_owned())
        .filter(|s| !s.is_empty())
        .collect()
}

fn usings(st: &mut State<'_>, n: Node<'_>) {
    for c in kids(n) {
        match c.kind() {
            "using_directive" => do_using(st, c),
            "namespace_declaration" | "file_scoped_namespace_declaration" => {
                for k in kids(c) {
                    if k.kind() == "declaration_list" {
                        usings(st, k);
                    }
                }
            }
            _ => {}
        }
    }
}

/// Global usings declared in `root`, as canonical paths (`global using static System.Console`).
#[must_use]
pub fn global_usings(src: &str, root: Node<'_>) -> Vec<SymPath> {
    kids(root)
        .into_iter()
        .filter(|c| c.kind() == "using_directive")
        .filter(|c| {
            all_kids(*c)
                .iter()
                .any(|t| &src[t.byte_range()] == "global")
        })
        .filter(|c| !all_kids(*c).iter().any(|t| &src[t.byte_range()] == "="))
        .filter_map(|c| kids(c).last().map(|k| dotted(&src[k.byte_range()])))
        .collect()
}

fn do_using(st: &mut State<'_>, n: Node<'_>) {
    match using_of(st.src, n) {
        Some(Using::Alias(name, target)) => st.bind(&name, Binding::Alias(target)),
        Some(Using::Glob(p)) => {
            st.note(&p);
            st.globs.push(p);
        }
        None => {}
    }
}

fn visit(st: &mut State<'_>, n: Node<'_>) {
    match n.kind() {
        "comment"
        | "using_directive"
        | "string_literal"
        | "verbatim_string_literal"
        | "raw_string_literal"
        | "character_literal"
        | "string_literal_content"
        | "attribute_list" => {}
        "class_declaration" | "record_declaration" | "struct_declaration" => {
            st.push();
            let saved = st.inherited_open;
            st.inherited_open = false;
            if let Some(name) = n.child_by_field_name("name").map(|c| st.txt(c).to_owned()) {
                let own = declares_print(st, n);
                if !own && st.ctx.project.mono.contains(&name) {
                    tracing::debug!(class = %name, "class inherits MonoBehaviour.print");
                    st.bind(
                        "print",
                        Binding::Alias(MONO_PRINT.map(str::to_owned).to_vec()),
                    );
                } else if !own && st.ctx.project.open_bases.contains(&name) {
                    tracing::debug!(class = %name, "class has a base the project cannot see");
                    st.inherited_open = true;
                }
            }
            for c in kids(n) {
                visit(st, c);
            }
            st.inherited_open = saved;
            st.pop();
        }
        "method_declaration"
        | "constructor_declaration"
        | "local_function_statement"
        | "lambda_expression"
        | "anonymous_method_expression" => {
            st.push();
            for c in kids(n) {
                if c.kind() == "parameter_list" || c.kind() == "parameter" {
                    bind_params(st, c);
                }
            }
            // The declared name is a definition, not a reference to the symbol it may alias.
            let declared = n.child_by_field_name("name").map(|d| d.id());
            for c in kids(n).into_iter().filter(|c| Some(c.id()) != declared) {
                visit(st, c);
            }
            st.pop();
        }
        "variable_declarator" => {
            if let Some(id) = kids(n).into_iter().find(|c| c.kind() == "identifier") {
                let name = st.txt(id).to_owned();
                let reflected = kids(n)
                    .into_iter()
                    .find_map(|c| reflect_target(st, c).map(|t| (c, t)));
                for c in kids(n) {
                    if c.kind() != "identifier" {
                        visit(st, c);
                    }
                }
                match reflected {
                    Some((_, Ok(p))) => st.bind(&name, Binding::Alias(p)),
                    Some((c, Err(why))) => {
                        st.unres(c, &why);
                        st.bind(&name, Binding::Opaque);
                    }
                    None => st.bind(&name, Binding::Opaque),
                }
            }
        }
        "invocation_expression" => do_call(st, n),
        "member_access_expression" | "identifier" | "qualified_name" | "alias_qualified_name" => {
            if let Some(p) = path_of(st, n)
                && st.hit_ref(n, &p)
            {
                return;
            }
            if n.kind() == "member_access_expression" {
                for c in kids(n) {
                    visit(st, c);
                }
            }
        }
        _ => {
            for c in kids(n) {
                visit(st, c);
            }
        }
    }
}

fn bind_params(st: &mut State<'_>, n: Node<'_>) {
    if n.kind() == "parameter" {
        if let Some(id) = n.child_by_field_name("name") {
            let name = st.txt(id).to_owned();
            st.bind(&name, Binding::Opaque);
        }
        return;
    }
    for c in kids(n) {
        bind_params(st, c);
    }
}

fn unbound(st: &State<'_>, name: &str) -> SymPath {
    for g in &st.globs {
        let mut cand = g.clone();
        cand.push(name.to_owned());
        if st.group.any_atom(&cand) {
            return cand;
        }
    }
    vec![name.to_owned()]
}

fn path_of(st: &State<'_>, n: Node<'_>) -> Option<SymPath> {
    match n.kind() {
        "identifier" => {
            let name = st.txt(n);
            match st.lookup(name) {
                Some(Binding::Alias(p)) => Some(p.clone()),
                Some(Binding::Opaque | Binding::Lit(_)) => None,
                None => Some(unbound(st, name)),
            }
        }
        "alias_qualified_name" => {
            let alias = st.txt(n.child_by_field_name("alias")?);
            let name = st.txt(n.child_by_field_name("name")?);
            if alias == "global" {
                Some(st.ctx.project.link(vec![name.to_owned()]))
            } else {
                // An `extern alias` namespace: the assembly it names is not visible to the resolver.
                tracing::debug!(alias, name, "extern alias qualified name left unresolved");
                None
            }
        }
        "qualified_name" if st.txt(n).starts_with("global::") => {
            Some(st.ctx.project.link(dotted(st.txt(n))))
        }
        "qualified_name" => {
            let parts = dotted(st.txt(n));
            let (head, rest) = parts.split_first()?;
            let mut base = match st.lookup(head) {
                Some(Binding::Alias(p)) => p.clone(),
                Some(Binding::Opaque | Binding::Lit(_)) => return None,
                None => unbound(st, head),
            };
            base.extend_from_slice(rest);
            Some(st.ctx.project.link(base))
        }
        "member_access_expression" => {
            let name = n.child_by_field_name("name")?;
            let Some(e) = n.child_by_field_name("expression") else {
                // `this.print` / `base.print`: the member is looked up as if unqualified.
                let t = st.txt(n);
                if t.starts_with("this") || t.starts_with("base") {
                    return path_of(st, name);
                }
                return None;
            };
            let mut p = path_of(st, e)?;
            p.push(st.txt(name).to_owned());
            Some(st.ctx.project.link(p))
        }
        "parenthesized_expression" => path_of(st, kids(n).into_iter().next()?),
        "invocation_expression" => reflect_target(st, n)?.ok(),
        _ => None,
    }
}

fn do_call(st: &mut State<'_>, n: Node<'_>) {
    let Some(f) = n.child_by_field_name("function") else {
        return;
    };
    let arg_node = n.child_by_field_name("arguments");
    let cp = path_of(st, f);
    let dynamic =
        inherited_print(st, f).or_else(|| cp.is_none().then(|| reflect_dynamic(st, f)).flatten());
    if let Some(why) = dynamic {
        st.unres(n, &why);
    }
    let args = arg_node.map_or_else(Args::default, |a| args_of(st, a));
    let hit = cp.as_ref().is_some_and(|p| st.hit_call(n, p, &args));
    let (saved_suppress, saved_chain) = (st.suppress, st.in_chain);
    if hit {
        st.in_chain = true;
        visit(st, f);
        st.suppress = true;
    } else {
        visit(st, f);
    }
    st.in_chain = false;
    if let Some(a) = arg_node {
        for c in kids(a) {
            visit(st, c);
        }
    }
    st.suppress = saved_suppress;
    st.in_chain = saved_chain;
}

fn args_of(st: &State<'_>, a: Node<'_>) -> Args {
    let pos = kids(a)
        .into_iter()
        .map(|arg| {
            let inner = kids(arg).into_iter().next().unwrap_or(arg);
            let t = st.txt(inner);
            ArgInfo {
                int: t.parse::<i64>().ok(),
                text: (inner.kind().contains("string_literal")).then(|| {
                    t.trim_start_matches(['@', '$'])
                        .trim_matches('"')
                        .to_owned()
                }),
                path: path_of(st, inner),
            }
        })
        .collect();
    Args {
        pos,
        kw: Vec::new(),
    }
}

/// True when the class body declares a method named `print` (it shadows the inherited helper).
fn declares_print(st: &State<'_>, class: Node<'_>) -> bool {
    kids(class)
        .into_iter()
        .filter(|c| c.kind() == "declaration_list")
        .flat_map(kids)
        .any(|m| {
            m.kind() == "method_declaration"
                && m.child_by_field_name("name")
                    .is_some_and(|nm| st.txt(nm) == "print")
        })
}

/// A bare or `this.`/`base.` `print(..)` call inside a class whose base the project cannot see.
fn inherited_print(st: &State<'_>, f: Node<'_>) -> Option<String> {
    let name = match f.kind() {
        "identifier" => f,
        "member_access_expression" if f.child_by_field_name("expression").is_none() => {
            f.child_by_field_name("name")?
        }
        _ => return None,
    };
    (st.inherited_open && st.txt(name) == "print" && st.lookup("print").is_none())
        .then(|| "print inherited from a base class the project cannot see".to_owned())
}

fn str_lit(st: &State<'_>, arg: Node<'_>) -> Option<String> {
    let inner = kids(arg).into_iter().next().unwrap_or(arg);
    inner.kind().contains("string_literal").then(|| {
        st.txt(inner)
            .trim_start_matches(['@', '$'])
            .trim_matches('"')
            .to_owned()
    })
}

/// True when some non-advisory atom could report a member called `name` (so a dynamic receiver matters).
fn could_be_output(st: &State<'_>, name: &str) -> bool {
    st.group.atoms.iter().any(|a| {
        !a.advisory
            && a.patterns.iter().any(|p| match p.last() {
                Some(Seg::Lit(l)) => l == name,
                Some(Seg::Any) | None => false,
            })
    })
}

/// The type a reflective receiver names: `typeof(T)` or `x.GetType("T")`; `Err` when it is dynamic.
fn reflect_type(st: &State<'_>, e: Node<'_>) -> Result<SymPath, String> {
    match e.kind() {
        "typeof_expression" => kids(e)
            .into_iter()
            .next()
            .and_then(|t| path_of(st, t))
            .ok_or_else(|| "typeof of a type the resolver cannot place".to_owned()),
        "parenthesized_expression" => kids(e)
            .into_iter()
            .next()
            .ok_or_else(|| "empty reflective receiver".to_owned())
            .and_then(|i| reflect_type(st, i)),
        "invocation_expression" => {
            let is_get_type = e
                .child_by_field_name("function")
                .filter(|f| f.kind() == "member_access_expression")
                .and_then(|f| f.child_by_field_name("name"))
                .is_some_and(|nm| st.txt(nm) == "GetType");
            let arg = e
                .child_by_field_name("arguments")
                .and_then(|a| kids(a).into_iter().next());
            match (is_get_type, arg.and_then(|a| str_lit(st, a))) {
                (true, Some(lit)) => Ok(st.ctx.project.link(dotted(&lit))),
                _ => Err("reflective type is computed at run time".to_owned()),
            }
        }
        _ => Err("reflective receiver is a runtime value".to_owned()),
    }
}

/// `T.GetMethod("M")` (and Property/Field/Member) resolved to `T.M`; `None` when `n` is not one.
/// `Err` carries why a reflective lookup that could reach an output atom stays unresolved.
fn reflect_target(st: &State<'_>, n: Node<'_>) -> Option<Result<SymPath, String>> {
    if n.kind() != "invocation_expression" {
        return None;
    }
    let f = n.child_by_field_name("function")?;
    if f.kind() != "member_access_expression" {
        return None;
    }
    let getter = st.txt(f.child_by_field_name("name")?);
    if !matches!(
        getter,
        "GetMethod" | "GetProperty" | "GetField" | "GetMember"
    ) {
        return None;
    }
    let recv = f.child_by_field_name("expression")?;
    let lit = n
        .child_by_field_name("arguments")
        .and_then(|a| kids(a).into_iter().next())
        .and_then(|a| str_lit(st, a));
    let ty = reflect_type(st, recv);
    Some(match (ty, lit) {
        (Ok(mut p), Some(m)) => {
            p.push(m);
            Ok(st.ctx.project.link(p))
        }
        (Ok(_), None) => Err(format!("{getter} with a computed member name")),
        (Err(why), Some(m)) if !could_be_output(st, &m) => {
            tracing::debug!(member = %m, why = %why, "dynamic reflection cannot reach an output atom");
            return None;
        }
        (Err(why), _) => Err(why),
    })
}

/// Why `f` (the callee of a call) is a reflective invocation whose target stays unresolved.
fn reflect_dynamic(st: &State<'_>, f: Node<'_>) -> Option<String> {
    if f.kind() != "member_access_expression" {
        return None;
    }
    let recv = f.child_by_field_name("expression")?;
    let invoked = matches!(
        st.txt(f.child_by_field_name("name")?),
        "Invoke" | "DynamicInvoke" | "CreateDelegate"
    );
    if !invoked {
        return None;
    }
    reflect_target(st, recv)?.err()
}

/// The classes and native imports `root` declares, resolved through its own `using` directives.
#[must_use]
pub fn declarations(src: &str, root: Node<'_>, globals: &[SymPath]) -> Decls {
    let mut aliases: BTreeMap<String, SymPath> = BTreeMap::new();
    let mut globs: Vec<SymPath> = globals.to_vec();
    collect_usings(src, root, &mut aliases, &mut globs);
    let mut out = Decls::default();
    collect_decls(src, root, &aliases, &globs, &mut out);
    out
}

fn collect_usings(
    src: &str,
    n: Node<'_>,
    aliases: &mut BTreeMap<String, SymPath>,
    globs: &mut Vec<SymPath>,
) {
    for c in kids(n) {
        match c.kind() {
            "using_directive" => match using_of(src, c) {
                Some(Using::Alias(a, p)) => {
                    aliases.insert(a, p);
                }
                Some(Using::Glob(p)) => globs.push(p),
                None => {}
            },
            "namespace_declaration" | "file_scoped_namespace_declaration" => {
                collect_usings(src, c, aliases, globs);
                kids(c)
                    .into_iter()
                    .filter(|k| k.kind() == "declaration_list")
                    .for_each(|k| collect_usings(src, k, aliases, globs));
            }
            _ => {}
        }
    }
}

fn resolve_type(
    src: &str,
    n: Node<'_>,
    aliases: &BTreeMap<String, SymPath>,
    globs: &[SymPath],
) -> SymPath {
    let raw = src[n.byte_range()].split('<').next().unwrap_or_default();
    let absolute = raw.trim().starts_with("global::");
    let mut p = dotted(raw);
    if absolute {
        return p;
    }
    if let Some(a) = p.first().and_then(|h| aliases.get(h)) {
        let mut full = a.clone();
        full.extend_from_slice(&p[1..]);
        return full;
    }
    // A bare name under `using UnityEngine;` is the namespace's type.
    if p.len() == 1
        && let Some(g) = globs
            .iter()
            .find(|g| g.first().is_some_and(|f| f == "UnityEngine"))
        && p[0] == "MonoBehaviour"
    {
        let mut full = g.clone();
        full.append(&mut p);
        return full;
    }
    p
}

fn collect_decls(
    src: &str,
    n: Node<'_>,
    aliases: &BTreeMap<String, SymPath>,
    globs: &[SymPath],
    out: &mut Decls,
) {
    for c in kids(n) {
        match c.kind() {
            "class_declaration" | "record_declaration" | "struct_declaration" => {
                let Some(name) = c
                    .child_by_field_name("name")
                    .map(|x| src[x.byte_range()].to_owned())
                else {
                    continue;
                };
                let bases = kids(c)
                    .into_iter()
                    .filter(|k| k.kind() == "base_list")
                    .flat_map(kids)
                    .map(|b| resolve_type(src, b, aliases, globs))
                    .collect();
                let body: Vec<Node<'_>> = kids(c)
                    .into_iter()
                    .filter(|k| k.kind() == "declaration_list")
                    .flat_map(kids)
                    .collect();
                let own_print = body.iter().any(|m| {
                    m.kind() == "method_declaration"
                        && m.child_by_field_name("name")
                            .is_some_and(|nm| &src[nm.byte_range()] == "print")
                });
                for m in &body {
                    if let Some(e) = extern_of(src, *m, &name) {
                        out.externs.push(e);
                    }
                }
                out.classes.push(ClassDecl {
                    name,
                    own_print,
                    bases,
                });
                kids(c)
                    .into_iter()
                    .filter(|k| k.kind() == "declaration_list")
                    .for_each(|k| collect_decls(src, k, aliases, globs, out));
            }
            "namespace_declaration" | "file_scoped_namespace_declaration" => {
                collect_decls(src, c, aliases, globs, out);
                kids(c)
                    .into_iter()
                    .filter(|k| k.kind() == "declaration_list")
                    .for_each(|k| collect_decls(src, k, aliases, globs, out));
            }
            _ => {}
        }
    }
}

/// The native entry point an `extern`/`partial` method imports through `[DllImport]`/`[LibraryImport]`.
fn extern_of(src: &str, m: Node<'_>, class: &str) -> Option<ExternDecl> {
    if m.kind() != "method_declaration" {
        return None;
    }
    let method = src[m.child_by_field_name("name")?.byte_range()].to_owned();
    let attr = kids(m)
        .into_iter()
        .filter(|k| k.kind() == "attribute_list")
        .flat_map(kids)
        .find(|a| {
            a.child_by_field_name("name").is_some_and(|nm| {
                let t = src[nm.byte_range()].rsplit('.').next().unwrap_or_default();
                matches!(
                    t.trim_end_matches("Attribute"),
                    "DllImport" | "LibraryImport"
                )
            })
        })?;
    let args: Vec<Node<'_>> = kids(attr)
        .into_iter()
        .filter(|k| k.kind() == "attribute_argument_list")
        .flat_map(kids)
        .collect();
    let lit = |a: &Node<'_>| {
        kids(*a)
            .into_iter()
            .find(|k| k.kind().contains("string_literal"))
            .map(|k| {
                src[k.byte_range()]
                    .trim_start_matches(['@', '$'])
                    .trim_matches('"')
                    .to_owned()
            })
    };
    let named = |key: &str| {
        args.iter().find(|a| {
            a.child_by_field_name("name")
                .is_some_and(|n| &src[n.byte_range()] == key)
        })
    };
    let lib = args
        .iter()
        .find(|a| a.child_by_field_name("name").is_none())
        .and_then(lit)
        .unwrap_or_default();
    let entry = match named("EntryPoint") {
        None => Ok(method.clone()),
        Some(a) => {
            lit(a).ok_or_else(|| "native import EntryPoint is computed at run time".to_owned())
        }
    };
    let target = entry.map(|e| {
        let mut p: SymPath = PINVOKE.map(str::to_owned).to_vec();
        p.push(lib);
        p.push(e);
        p
    });
    Some(ExternDecl {
        class: class.to_owned(),
        method,
        target,
        start: m.start_byte(),
        end: m.end_byte(),
    })
}

fn simple(p: &SymPath) -> &str {
    p.last().map_or("", String::as_str)
}

/// Fill the project-wide C# facts from every file's declarations: the MonoBehaviour-derived class
/// set (closed over project inheritance), classes with unseen bases, and class-qualified externs.
pub fn seed(project: &mut Project, files: &[Decls]) {
    let classes: Vec<&ClassDecl> = files.iter().flat_map(|d| &d.classes).collect();
    let is_mono_path = |p: &SymPath| {
        p.iter()
            .map(String::as_str)
            .eq(["UnityEngine", "MonoBehaviour"])
    };
    let known: std::collections::BTreeSet<&str> = classes.iter().map(|c| c.name.as_str()).collect();
    loop {
        let mut grew = false;
        for c in &classes {
            let derives = c
                .bases
                .iter()
                .any(|b| is_mono_path(b) || project.mono.contains(simple(b)));
            if derives && project.mono.insert(c.name.clone()) {
                grew = true;
            }
            let unseen = c.bases.iter().enumerate().any(|(i, b)| {
                let n = simple(b);
                let iface = n.len() > 1
                    && n.starts_with('I')
                    && n.chars().nth(1).is_some_and(char::is_uppercase);
                i == 0 && !iface && !is_mono_path(b) && !known.contains(n) && n != "object"
                    || project.open_bases.contains(n)
            });
            if unseen && project.open_bases.insert(c.name.clone()) {
                grew = true;
            }
        }
        if !grew {
            break;
        }
    }
    for e in files.iter().flat_map(|d| &d.externs) {
        if let Ok(p) = &e.target {
            project
                .modules
                .entry(e.class.clone())
                .or_default()
                .insert(e.method.clone(), p.clone());
        }
    }
    tracing::debug!(
        mono = project.mono.len(),
        open = project.open_bases.len(),
        "csharp class hierarchy seeded"
    );
}
