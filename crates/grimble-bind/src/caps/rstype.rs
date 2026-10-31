//! Rust receiver typing (tickets YCR4M6H and 01M64230GWHHTH9R7CZ55XRPGG): resolves the type of the
//! receiver of each method call from the syntax tree, so `agent.run(..)` on an `ureq::Agent` is a
//! `<type path>.<method>` call the vocabulary can name.
//!
//! Types flow through imports and local aliases, struct fields, parameters, `let` bindings with
//! lexical scoping (an inner `let` hides the outer name only inside its block), `self`, typed
//! `const` / `static` items, constructors (`Agent::new()`), the declared return types of functions
//! and methods defined in the file (builder chains included), `Option` / `Result` unwrapping
//! (`?`, `unwrap`, `if let Some(x)`, `match`), `Arc` / `Box` / `Rc` wrappers and lock guards. A
//! receiver typed by a generic parameter, `impl Trait`, `dyn Trait` or an associated type is
//! `Unproven`; any other receiver this pass cannot type is simply not reported.

use std::collections::{BTreeMap, BTreeSet};

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use tree_sitter::Node;

/// A resolved type: an external path, a type this file defines, a wrapper, or an unprovable one.
#[derive(Clone, Debug, PartialEq, Eq)]
enum Ty {
    /// An external path (`ureq::Agent`), or a `crate::` / `self::` / `super::` path to resolve.
    Path(String),
    /// A struct, enum or union this file defines.
    Local(String),
    /// `Option<T>` or `Result<T, _>`: unwrapped to `T` by `?`, `unwrap` and `Some(x)` / `Ok(x)`.
    Fallible(Box<Ty>),
    /// `Mutex<T>`, `RwLock<T>` or `RefCell<T>`.
    Cell(Box<Ty>),
    /// A lock guard result: `T` after `unwrap`, `await` or `?`, and `T` for method calls.
    Guard(Box<Ty>),
    /// A generic parameter, `impl Trait`, `dyn Trait` or associated type: the type is not known.
    Unproven,
}

/// A resolved value type; `None` when the pass cannot type the expression.
type Val = Option<Ty>;

/// A method call whose receiver type resolved to an external path or is unprovable.
pub(super) struct TypedCall {
    /// The resolved type path of the receiver; `None` when the receiver type is unprovable.
    pub(super) ty: Option<String>,
    /// The called method.
    pub(super) method: String,
    pub(super) offset: usize,
    pub(super) line: u32,
}

/// Names visible in one lexical scope; a `None` type is a binding whose type is unknown.
type Scope = BTreeMap<String, Val>;

/// A struct, enum, union or trait defined in the file.
#[derive(Default)]
struct LocalTy<'s> {
    generics: BTreeSet<String>,
    /// Field types by name; `None` when two definitions disagree.
    fields: BTreeMap<String, Option<Node<'s>>>,
}

/// A `type` alias; `target` is `None` when two aliases of the name disagree.
struct Alias<'s> {
    params: Vec<String>,
    target: Option<Node<'s>>,
}

/// A function or method signature: `(impl type, name)`, the impl type `None` for free functions.
struct Sig<'s> {
    ret: Option<Node<'s>>,
    impl_ty: Option<Node<'s>>,
    generics: BTreeSet<String>,
    ambiguous: bool,
}

type SigKey = (Option<String>, String);

/// Type-resolution context: the `Self` type, generic names, and alias parameter substitutions.
#[derive(Clone, Default)]
struct Tcx {
    self_ty: Val,
    generics: BTreeSet<String>,
    subst: BTreeMap<String, Val>,
    depth: u8,
}

/// The state of one function body walk: its context and its stack of lexical scopes.
struct Fx {
    tcx: Tcx,
    scopes: Vec<Scope>,
}

impl Fx {
    fn bind(&mut self, name: &str, ty: Val) {
        if let Some(top) = self.scopes.last_mut() {
            top.insert(name.to_owned(), ty);
        }
    }
}

struct Cx<'s> {
    src: &'s str,
    imports: BTreeMap<String, String>,
    locals: BTreeMap<String, LocalTy<'s>>,
    aliases: BTreeMap<String, Alias<'s>>,
    sigs: BTreeMap<SigKey, Sig<'s>>,
    mods: BTreeSet<String>,
    items: Scope,
    out: Vec<TypedCall>,
}

/// The max depth type aliases are expanded to, so a recursive alias cannot loop.
const ALIAS_DEPTH: u8 = 8;

/// Constructor names whose result is the type they are called on.
const CTORS: [&str; 5] = [
    "new",
    "default",
    "from",
    "new_with_defaults",
    "new_with_config",
];

/// `Option` / `Result` methods that keep the wrapper.
const KEEP_FALLIBLE: [&str; 15] = [
    "as_ref",
    "as_mut",
    "as_deref",
    "cloned",
    "copied",
    "clone",
    "ok",
    "ok_or",
    "ok_or_else",
    "map_err",
    "context",
    "with_context",
    "or",
    "or_else",
    "take",
];

/// `Option` / `Result` / guard methods that yield the wrapped value.
const UNWRAP: [&str; 6] = [
    "unwrap",
    "expect",
    "unwrap_or",
    "unwrap_or_else",
    "unwrap_or_default",
    "unwrap_unchecked",
];

fn text<'s>(src: &'s str, n: Node<'_>) -> &'s str {
    src.get(n.start_byte()..n.end_byte()).unwrap_or("")
}

fn kids(n: Node<'_>) -> Vec<Node<'_>> {
    let mut c = n.walk();
    n.named_children(&mut c).collect()
}

/// The method calls in `src` whose receiver type resolves to an external path or is unprovable.
pub(super) fn typed_calls(src: &str) -> Vec<TypedCall> {
    let ParseResult::Parsed(tree) = parse(Language::Rust, src, &ParseLimits::default()) else {
        tracing::debug!("rust source did not parse: no typed receivers");
        return Vec::new();
    };
    let root = tree.root();
    let mut cx = Cx {
        src,
        imports: BTreeMap::new(),
        locals: BTreeMap::new(),
        aliases: BTreeMap::new(),
        sigs: BTreeMap::new(),
        mods: BTreeSet::new(),
        items: Scope::new(),
        out: Vec::new(),
    };
    cx.collect(root, false);
    cx.collect_sigs(root, &SigCx::default());
    cx.items(root, &Tcx::default());
    tracing::debug!(calls = cx.out.len(), "typed receiver calls resolved");
    cx.out
}

/// The impl a function being registered sits in.
#[derive(Default)]
struct SigCx<'s> {
    in_impl: bool,
    owner: Option<String>,
    impl_ty: Option<Node<'s>>,
    generics: BTreeSet<String>,
}

/// The type parameter names a `type_parameters` node declares.
fn type_params(src: &str, params: Option<Node<'_>>) -> Vec<String> {
    let Some(params) = params else {
        return Vec::new();
    };
    kids(params)
        .into_iter()
        .filter_map(|p| match p.kind() {
            "type_parameter" | "const_parameter" => p
                .child_by_field_name("name")
                .map(|n| text(src, n).to_owned()),
            _ => None,
        })
        .collect()
}

/// The positional (non-lifetime) type arguments of a `type_arguments` node.
fn type_args(args: Option<Node<'_>>) -> Vec<Node<'_>> {
    args.map(|a| {
        kids(a)
            .into_iter()
            .filter(|k| !matches!(k.kind(), "lifetime" | "type_binding"))
            .collect()
    })
    .unwrap_or_default()
}

impl<'s> Cx<'s> {
    /// Imports, defined types with their fields, aliases, inline modules and typed items.
    fn collect(&mut self, n: Node<'s>, in_fn: bool) {
        match n.kind() {
            "use_declaration" => {
                if let Some(arg) = n.child_by_field_name("argument") {
                    let mut imports = std::mem::take(&mut self.imports);
                    flatten_use(self.src, arg, &[], &mut imports);
                    self.imports = imports;
                }
            }
            "struct_item" | "enum_item" | "union_item" | "trait_item" => self.collect_type(n),
            "type_item" => self.collect_alias(n),
            "mod_item" => {
                if let Some(name) = n.child_by_field_name("name") {
                    self.mods.insert(text(self.src, name).to_owned());
                }
            }
            "const_item" | "static_item" if !in_fn => {
                if let (Some(name), Some(ty)) =
                    (n.child_by_field_name("name"), n.child_by_field_name("type"))
                {
                    let ty = self.resolve_type(ty, &Tcx::default());
                    let name = text(self.src, name).to_owned();
                    let merged = match self.items.get(&name) {
                        Some(have) if *have != ty => None,
                        _ => ty,
                    };
                    self.items.insert(name, merged);
                }
            }
            _ => {}
        }
        let in_fn = in_fn || n.kind() == "function_item";
        for k in kids(n) {
            self.collect(k, in_fn);
        }
    }

    fn collect_type(&mut self, n: Node<'s>) {
        let Some(name) = n.child_by_field_name("name") else {
            return;
        };
        let generics = type_params(self.src, n.child_by_field_name("type_parameters"));
        let entry = self
            .locals
            .entry(text(self.src, name).to_owned())
            .or_default();
        entry.generics.extend(generics);
        let Some(body) = n.child_by_field_name("body") else {
            return;
        };
        for f in kids(body) {
            if f.kind() != "field_declaration" {
                continue;
            }
            let (Some(fname), Some(fty)) =
                (f.child_by_field_name("name"), f.child_by_field_name("type"))
            else {
                continue;
            };
            let fname = text(self.src, fname).to_owned();
            let merged = match entry.fields.get(&fname) {
                Some(Some(have)) if text(self.src, *have) != text(self.src, fty) => None,
                Some(None) => None,
                _ => Some(fty),
            };
            entry.fields.insert(fname, merged);
        }
    }

    fn collect_alias(&mut self, n: Node<'s>) {
        let (Some(name), Some(target)) =
            (n.child_by_field_name("name"), n.child_by_field_name("type"))
        else {
            return;
        };
        let name = text(self.src, name).to_owned();
        let params = type_params(self.src, n.child_by_field_name("type_parameters"));
        let agrees = self.aliases.get(&name).is_none_or(|a| {
            a.target
                .is_some_and(|t| text(self.src, t) == text(self.src, target))
        });
        let target = agrees.then_some(target);
        self.aliases.insert(name, Alias { params, target });
    }

    /// Records the signature of every function and method, by owning type and name.
    fn collect_sigs(&mut self, n: Node<'s>, sx: &SigCx<'s>) {
        match n.kind() {
            "function_item" => self.register(n, sx),
            "trait_item" | "block" => {}
            "impl_item" => {
                let generics: BTreeSet<String> =
                    type_params(self.src, n.child_by_field_name("type_parameters"))
                        .into_iter()
                        .collect();
                let impl_ty = n.child_by_field_name("type");
                let owner = impl_ty
                    .and_then(|t| {
                        self.resolve_type(
                            t,
                            &Tcx {
                                generics: generics.clone(),
                                ..Tcx::default()
                            },
                        )
                    })
                    .and_then(|t| match t {
                        Ty::Local(name) => Some(name),
                        _ => None,
                    });
                if owner.is_none() {
                    return;
                }
                let inner = SigCx {
                    in_impl: true,
                    owner,
                    impl_ty,
                    generics,
                };
                for k in kids(n) {
                    self.collect_sigs(k, &inner);
                }
            }
            _ => {
                for k in kids(n) {
                    self.collect_sigs(k, sx);
                }
            }
        }
    }

    fn register(&mut self, f: Node<'s>, sx: &SigCx<'s>) {
        let Some(name) = f.child_by_field_name("name") else {
            return;
        };
        let key = (sx.owner.clone(), text(self.src, name).to_owned());
        debug_assert!(sx.owner.is_some() || !sx.in_impl);
        let ret = f.child_by_field_name("return_type");
        let mut generics = sx.generics.clone();
        generics.extend(type_params(
            self.src,
            f.child_by_field_name("type_parameters"),
        ));
        let sig = Sig {
            ret,
            impl_ty: sx.impl_ty,
            generics,
            ambiguous: false,
        };
        match self.sigs.get_mut(&key) {
            Some(have) => {
                let same = match (have.ret, ret) {
                    (Some(a), Some(b)) => text(self.src, a) == text(self.src, b),
                    (None, None) => true,
                    _ => false,
                };
                if !same {
                    tracing::debug!(name = %key.1, "function name defined twice with different returns");
                    have.ambiguous = true;
                }
            }
            None => {
                self.sigs.insert(key, sig);
            }
        }
    }

    /// The declared return type of a function or method, resolved in its own context.
    fn sig_ret(&self, key: &SigKey) -> Val {
        let sig = self.sigs.get(key)?;
        if sig.ambiguous {
            return None;
        }
        let base = Tcx {
            generics: sig.generics.clone(),
            ..Tcx::default()
        };
        let self_ty = sig.impl_ty.and_then(|t| self.resolve_type(t, &base));
        self.resolve_type(sig.ret?, &Tcx { self_ty, ..base })
    }

    /// Walks item containers, analysing each function with the impl or trait it sits in.
    fn items(&mut self, n: Node<'s>, ctx: &Tcx) {
        match n.kind() {
            "function_item" => self.function(n, ctx),
            "impl_item" => {
                let mut tcx = Tcx {
                    generics: type_params(self.src, n.child_by_field_name("type_parameters"))
                        .into_iter()
                        .collect(),
                    ..Tcx::default()
                };
                tcx.self_ty = n
                    .child_by_field_name("type")
                    .and_then(|t| self.resolve_type(t, &tcx));
                for k in kids(n) {
                    self.items(k, &tcx);
                }
            }
            "trait_item" => {
                let tcx = Tcx {
                    self_ty: Some(Ty::Unproven),
                    generics: type_params(self.src, n.child_by_field_name("type_parameters"))
                        .into_iter()
                        .collect(),
                    ..Tcx::default()
                };
                for k in kids(n) {
                    self.items(k, &tcx);
                }
            }
            _ => {
                for k in kids(n) {
                    self.items(k, ctx);
                }
            }
        }
    }

    fn function(&mut self, f: Node<'s>, ctx: &Tcx) {
        let mut tcx = ctx.clone();
        tcx.generics.extend(type_params(
            self.src,
            f.child_by_field_name("type_parameters"),
        ));
        let mut fx = Fx {
            tcx,
            scopes: vec![Scope::new()],
        };
        if let Some(params) = f.child_by_field_name("parameters") {
            for p in kids(params) {
                if p.kind() == "parameter"
                    && let Some(pat) = p.child_by_field_name("pattern")
                {
                    let ty = p
                        .child_by_field_name("type")
                        .and_then(|t| self.resolve_type(t, &fx.tcx));
                    self.bind_pattern(pat, ty, &mut fx);
                }
            }
        }
        if let Some(body) = f.child_by_field_name("body") {
            self.walk(body, &mut fx);
        }
    }

    /// Walks a body in evaluation order, scoping `let` bindings and recording method calls.
    fn walk(&mut self, n: Node<'s>, fx: &mut Fx) {
        match n.kind() {
            "function_item" | "impl_item" | "trait_item" | "mod_item" => {
                self.items(n, &Tcx::default());
            }
            "block" => {
                fx.scopes.push(Scope::new());
                self.walk_kids(n, fx);
                fx.scopes.pop();
            }
            "let_declaration" => self.let_declaration(n, fx),
            "let_condition" => {
                if let Some(v) = n.child_by_field_name("value") {
                    self.walk(v, fx);
                    let ty = self.value(v, fx);
                    if let Some(p) = n.child_by_field_name("pattern") {
                        self.bind_pattern(p, ty, fx);
                    }
                }
            }
            "closure_expression" => {
                fx.scopes.push(Scope::new());
                if let Some(params) = n.child_by_field_name("parameters") {
                    for p in kids(params) {
                        if p.kind() == "parameter"
                            && let Some(pat) = p.child_by_field_name("pattern")
                        {
                            let ty = p
                                .child_by_field_name("type")
                                .and_then(|t| self.resolve_type(t, &fx.tcx));
                            self.bind_pattern(pat, ty, fx);
                        } else {
                            self.bind_pattern(p, None, fx);
                        }
                    }
                }
                if let Some(body) = n.child_by_field_name("body") {
                    self.walk(body, fx);
                }
                fx.scopes.pop();
            }
            "for_expression" => {
                if let Some(v) = n.child_by_field_name("value") {
                    self.walk(v, fx);
                }
                fx.scopes.push(Scope::new());
                if let Some(p) = n.child_by_field_name("pattern") {
                    self.bind_pattern(p, None, fx);
                }
                if let Some(b) = n.child_by_field_name("body") {
                    self.walk(b, fx);
                }
                fx.scopes.pop();
            }
            "if_expression" | "while_expression" => {
                fx.scopes.push(Scope::new());
                if let Some(c) = n.child_by_field_name("condition") {
                    self.walk(c, fx);
                }
                for field in ["consequence", "body"] {
                    if let Some(b) = n.child_by_field_name(field) {
                        self.walk(b, fx);
                    }
                }
                fx.scopes.pop();
                if let Some(alt) = n.child_by_field_name("alternative") {
                    self.walk(alt, fx);
                }
            }
            "match_expression" => self.match_expression(n, fx),
            "call_expression" => {
                self.walk_kids(n, fx);
                self.record(n, fx);
            }
            _ => self.walk_kids(n, fx),
        }
    }

    fn walk_kids(&mut self, n: Node<'s>, fx: &mut Fx) {
        for k in kids(n) {
            self.walk(k, fx);
        }
    }

    fn let_declaration(&mut self, n: Node<'s>, fx: &mut Fx) {
        let value = n.child_by_field_name("value");
        if let Some(v) = value {
            self.walk(v, fx);
        }
        if let Some(alt) = n.child_by_field_name("alternative") {
            self.walk(alt, fx);
        }
        let ty = match (n.child_by_field_name("type"), value) {
            (Some(t), _) => self.resolve_type(t, &fx.tcx),
            (None, Some(v)) => self.value(v, fx),
            (None, None) => None,
        };
        if let Some(p) = n.child_by_field_name("pattern") {
            self.bind_pattern(p, ty, fx);
        }
    }

    fn match_expression(&mut self, n: Node<'s>, fx: &mut Fx) {
        let scrutinee = n.child_by_field_name("value");
        let sty = scrutinee.and_then(|v| {
            self.walk(v, fx);
            self.value(v, fx)
        });
        let Some(body) = n.child_by_field_name("body") else {
            return;
        };
        for arm in kids(body) {
            if arm.kind() != "match_arm" {
                continue;
            }
            fx.scopes.push(Scope::new());
            if let Some(pat) = arm.child_by_field_name("pattern") {
                let guard = pat.child_by_field_name("condition");
                for p in kids(pat) {
                    if Some(p) != guard {
                        self.bind_pattern(p, sty.clone(), fx);
                    }
                }
                if let Some(g) = guard {
                    self.walk(g, fx);
                }
            }
            if let Some(v) = arm.child_by_field_name("value") {
                self.walk(v, fx);
            }
            fx.scopes.pop();
        }
    }

    /// Binds the names a pattern introduces; `Some(x)` / `Ok(x)` bind the unwrapped type.
    fn bind_pattern(&self, p: Node<'s>, ty: Val, fx: &mut Fx) {
        match p.kind() {
            "identifier" | "shorthand_field_identifier" => fx.bind(text(self.src, p), ty),
            "scoped_identifier" | "scoped_type_identifier" | "type_identifier" => {}
            "mut_pattern" | "ref_pattern" | "reference_pattern" | "captured_pattern" => {
                for k in kids(p) {
                    self.bind_pattern(k, ty.clone(), fx);
                }
            }
            "tuple_struct_pattern" => {
                let ctor = p.child_by_field_name("type");
                let inner = match (ctor.map(|c| text(self.src, c)), &ty) {
                    (Some("Some" | "Ok"), Some(Ty::Fallible(t) | Ty::Guard(t))) => {
                        Some((**t).clone())
                    }
                    _ => None,
                };
                for k in kids(p) {
                    if Some(k) != ctor {
                        self.bind_pattern(k, inner.clone(), fx);
                    }
                }
            }
            _ => {
                for k in kids(p) {
                    self.bind_pattern(k, None, fx);
                }
            }
        }
    }

    /// Records a method call whose receiver is typed to an external path or is unprovable.
    fn record(&mut self, call: Node<'s>, fx: &Fx) {
        let Some(mut f) = call.child_by_field_name("function") else {
            return;
        };
        if f.kind() == "generic_function" {
            let Some(inner) = f.child_by_field_name("function") else {
                return;
            };
            f = inner;
        }
        if f.kind() != "field_expression" {
            return;
        }
        let (Some(recv), Some(m)) = (
            f.child_by_field_name("value"),
            f.child_by_field_name("field"),
        ) else {
            return;
        };
        let ty = match self.value(recv, fx) {
            Some(Ty::Guard(t)) => Some(*t),
            other => other,
        };
        let ty = match ty {
            Some(Ty::Path(p)) => Some(p),
            Some(Ty::Unproven) => None,
            _ => return,
        };
        self.out.push(TypedCall {
            ty,
            method: text(self.src, m).to_owned(),
            offset: call.start_byte(),
            line: u32::try_from(call.start_position().row + 1).unwrap_or(u32::MAX),
        });
    }

    fn lookup(&self, fx: &Fx, name: &str) -> Val {
        fx.scopes
            .iter()
            .rev()
            .find_map(|s| s.get(name))
            .or_else(|| self.items.get(name))
            .cloned()
            .flatten()
    }

    /// The type of an expression, when it resolves.
    fn value(&self, e: Node<'s>, fx: &Fx) -> Val {
        match e.kind() {
            "identifier" => self.lookup(fx, text(self.src, e)),
            "self" => fx.tcx.self_ty.clone(),
            "parenthesized_expression" | "reference_expression" => {
                let inner = e
                    .child_by_field_name("value")
                    .or_else(|| kids(e).into_iter().next())?;
                self.value(inner, fx)
            }
            "unary_expression" => {
                if !text(self.src, e).starts_with('*') {
                    return None;
                }
                self.value(kids(e).into_iter().next()?, fx)
            }
            "await_expression" => match self.value(kids(e).into_iter().next()?, fx)? {
                Ty::Guard(t) => Some(*t),
                other => Some(other),
            },
            "try_expression" => match self.value(kids(e).into_iter().next()?, fx)? {
                Ty::Fallible(t) | Ty::Guard(t) => Some(*t),
                Ty::Unproven => Some(Ty::Unproven),
                _ => None,
            },
            "field_expression" => {
                let Ty::Local(owner) = self.value(e.child_by_field_name("value")?, fx)? else {
                    return None;
                };
                let field = text(self.src, e.child_by_field_name("field")?);
                let local = self.locals.get(&owner)?;
                let fty = (*local.fields.get(field)?)?;
                self.resolve_type(
                    fty,
                    &Tcx {
                        self_ty: Some(Ty::Local(owner)),
                        generics: local.generics.clone(),
                        ..Tcx::default()
                    },
                )
            }
            "struct_expression" => {
                let name = e.child_by_field_name("name")?;
                self.resolve_type(name, &fx.tcx)
            }
            "call_expression" => self.call_value(e, fx),
            _ => None,
        }
    }

    fn first_arg(&self, call: Node<'s>, fx: &Fx) -> Val {
        let arg = kids(call.child_by_field_name("arguments")?)
            .into_iter()
            .next()?;
        self.value(arg, fx)
    }

    /// The type a call expression produces: a method, associated function or free function.
    fn call_value(&self, call: Node<'s>, fx: &Fx) -> Val {
        let mut f = call.child_by_field_name("function")?;
        if f.kind() == "generic_function" {
            f = f.child_by_field_name("function")?;
        }
        match f.kind() {
            "field_expression" => {
                let recv = self.value(f.child_by_field_name("value")?, fx)?;
                let method = text(self.src, f.child_by_field_name("field")?);
                self.method_value(recv, method)
            }
            "identifier" => {
                let name = text(self.src, f);
                match name {
                    "Some" | "Ok" => Some(Ty::Fallible(Box::new(self.first_arg(call, fx)?))),
                    _ if fx.scopes.iter().any(|s| s.contains_key(name)) => None,
                    _ => self.sig_ret(&(None, name.to_owned())),
                }
            }
            "scoped_identifier" => self.scoped_call(call, f, fx),
            _ => None,
        }
    }

    fn scoped_call(&self, call: Node<'s>, f: Node<'s>, fx: &Fx) -> Val {
        let full = text(self.src, f);
        if full.contains('<') {
            return None;
        }
        let (prefix, last) = full.rsplit_once("::")?;
        let segs: Vec<&str> = prefix.trim_start_matches("::").split("::").collect();
        let tail = *segs.last()?;
        if segs
            .iter()
            .all(|s| matches!(*s, "self" | "super" | "crate") || self.mods.contains(*s))
        {
            return self.sig_ret(&(None, last.to_owned()));
        }
        let canonical_tail = self
            .imports
            .get(tail)
            .map_or(tail, |p| p.rsplit("::").next().unwrap_or(tail));
        match (canonical_tail, last) {
            ("Arc" | "Box" | "Rc", "new" | "from" | "clone" | "pin") => {
                return self.first_arg(call, fx);
            }
            ("Mutex" | "RwLock" | "RefCell" | "Cell" | "OnceCell", "new") => {
                return Some(Ty::Cell(Box::new(self.first_arg(call, fx)?)));
            }
            _ => {}
        }
        let owner = self.named(&segs, None, &fx.tcx)?;
        match owner {
            Ty::Local(t) => {
                let key = (Some(t.clone()), last.to_owned());
                if self.sigs.contains_key(&key) {
                    self.sig_ret(&key)
                } else {
                    CTORS.contains(&last).then_some(Ty::Local(t))
                }
            }
            Ty::Path(p) => CTORS.contains(&last).then_some(Ty::Path(p)),
            _ => None,
        }
    }

    /// The type of `recv.method(..)`: unwrapping, wrapper-keeping, or a local method's return.
    fn method_value(&self, recv: Ty, method: &str) -> Val {
        match recv {
            Ty::Fallible(t) => {
                if UNWRAP.contains(&method) {
                    Some(*t)
                } else {
                    KEEP_FALLIBLE
                        .contains(&method)
                        .then(|| Ty::Fallible(t.clone()))
                }
            }
            Ty::Guard(t) => UNWRAP.contains(&method).then_some(*t),
            Ty::Cell(t) => match method {
                "lock" | "try_lock" | "read" | "write" | "try_read" | "try_write" | "get_mut"
                | "into_inner" => Some(Ty::Guard(t)),
                "borrow" | "borrow_mut" => Some(*t),
                "clone" => Some(Ty::Cell(t)),
                _ => None,
            },
            Ty::Local(name) => {
                let key = (Some(name.clone()), method.to_owned());
                if self.sigs.contains_key(&key) {
                    self.sig_ret(&key)
                } else {
                    (method == "clone").then_some(Ty::Local(name))
                }
            }
            other @ (Ty::Path(_) | Ty::Unproven) => (method == "clone").then_some(other),
        }
    }

    /// Resolves a type node, unwrapping references, smart pointers, options and generics.
    fn resolve_type(&self, t: Node<'s>, tcx: &Tcx) -> Val {
        match t.kind() {
            "reference_type" => self.resolve_type(t.child_by_field_name("type")?, tcx),
            "abstract_type" | "dynamic_type" | "bounded_type" | "qualified_type" => {
                Some(Ty::Unproven)
            }
            "type_identifier" | "identifier" => self.named(&[text(self.src, t)], None, tcx),
            "scoped_type_identifier" | "scoped_identifier" => {
                let full = text(self.src, t);
                if full.contains('<') {
                    return None;
                }
                let segs: Vec<&str> = full.trim_start_matches("::").split("::").collect();
                self.named(&segs, None, tcx)
            }
            "generic_type" => {
                let base = t.child_by_field_name("type")?;
                let full = text(self.src, base);
                let segs: Vec<&str> = full.trim_start_matches("::").split("::").collect();
                self.named(&segs, t.child_by_field_name("type_arguments"), tcx)
            }
            _ => None,
        }
    }

    /// Resolves a (possibly generic) named type from its path segments.
    fn named(&self, segs: &[&str], args: Option<Node<'s>>, tcx: &Tcx) -> Val {
        let first = *segs.first()?;
        if segs.len() > 1 {
            if first == "Self" || tcx.generics.contains(first) || tcx.subst.contains_key(first) {
                return Some(Ty::Unproven);
            }
        } else {
            if let Some(v) = tcx.subst.get(first) {
                return v.clone();
            }
            if tcx.generics.contains(first) {
                return Some(Ty::Unproven);
            }
            if first == "Self" {
                return tcx.self_ty.clone();
            }
            if let Some(alias) = self.aliases.get(first) {
                return self.expand(alias, args, tcx);
            }
            if self.locals.contains_key(first) {
                return Some(Ty::Local(first.to_owned()));
            }
        }
        let mut path = self
            .imports
            .get(first)
            .cloned()
            .unwrap_or_else(|| first.to_owned());
        for s in &segs[1..] {
            path.push_str("::");
            path.push_str(s);
        }
        let last = path.rsplit("::").next().unwrap_or("");
        let arg = || type_args(args).into_iter().next();
        match last {
            "Arc" | "Box" | "Rc" | "Pin" if args.is_some() => self.resolve_type(arg()?, tcx),
            "Mutex" | "RwLock" | "RefCell" | "Cell" | "OnceCell" | "OnceLock" if args.is_some() => {
                Some(Ty::Cell(Box::new(self.resolve_type(arg()?, tcx)?)))
            }
            "Option" | "Result" if args.is_some() => {
                Some(Ty::Fallible(Box::new(self.resolve_type(arg()?, tcx)?)))
            }
            _ => (segs.len() > 1 || self.imports.contains_key(first)).then_some(Ty::Path(path)),
        }
    }

    /// Expands a type alias, substituting the arguments it was applied to.
    fn expand(&self, alias: &Alias<'s>, args: Option<Node<'s>>, tcx: &Tcx) -> Val {
        if tcx.depth >= ALIAS_DEPTH {
            tracing::debug!("type alias expansion too deep");
            return None;
        }
        let target = alias.target?;
        let supplied = type_args(args);
        let mut inner = Tcx {
            self_ty: tcx.self_ty.clone(),
            generics: BTreeSet::new(),
            subst: BTreeMap::new(),
            depth: tcx.depth + 1,
        };
        for (i, param) in alias.params.iter().enumerate() {
            match supplied.get(i) {
                Some(a) => {
                    inner
                        .subst
                        .insert(param.clone(), self.resolve_type(*a, tcx));
                }
                None => {
                    inner.generics.insert(param.clone());
                }
            }
        }
        self.resolve_type(target, &inner)
    }
}

/// Flattens one use tree into `local name -> full path`.
fn flatten_use(src: &str, n: Node<'_>, prefix: &[String], out: &mut BTreeMap<String, String>) {
    let join = |segs: &[String]| segs.join("::");
    let spelled = |n: Node<'_>| -> Vec<String> {
        let mut v = prefix.to_vec();
        v.extend(
            text(src, n)
                .trim_start_matches("::")
                .split("::")
                .map(str::to_owned),
        );
        v
    };
    match n.kind() {
        "identifier" | "scoped_identifier" => {
            let full = spelled(n);
            if let Some(last) = full.last() {
                out.insert(last.clone(), join(&full));
            }
        }
        "self" => {
            if let Some(last) = prefix.last() {
                out.insert(last.clone(), join(prefix));
            }
        }
        "use_as_clause" => {
            if let (Some(path), Some(alias)) = (
                n.child_by_field_name("path"),
                n.child_by_field_name("alias"),
            ) {
                out.insert(text(src, alias).to_owned(), join(&spelled(path)));
            }
        }
        "scoped_use_list" => {
            let base = n
                .child_by_field_name("path")
                .map_or_else(|| prefix.to_vec(), spelled);
            if let Some(list) = n.child_by_field_name("list") {
                for k in kids(list) {
                    flatten_use(src, k, &base, out);
                }
            }
        }
        "use_list" => {
            for k in kids(n) {
                flatten_use(src, k, prefix, out);
            }
        }
        _ => {}
    }
}
