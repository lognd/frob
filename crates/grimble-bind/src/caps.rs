//! CAP001 (through `grimble_capabilities::build`) and CAP002: the capability cell of a node, from observed uses and its `may` grants.
//!
//! Binding.md 7.2 item 3: a use of an ungranted atom in code a node owns is `undeclared` and
//! CAP001 (Error, P+, deny by default). Item 6: a grant whose whole scope is Must-owned,
//! detector-covered and complete, and in which no use is possible, is `declared-unused` and
//! CAP002 (Warn, P-). A use is a call that resolves to nothing in the repository and whose
//! callee text is in the callee vocabulary of an atom for the file's language
//! (`gob_ir::registry::callee_vocab`, class = the atom name). A May-owned use never fires CAP001
//! (it is Unresolved) and does prevent CAP002.
//!
//! Method vocabulary (ticket 2T7C4A9): `Path.m` names method `m` on a receiver whose type is
//! `pathlib.Path`, resolved textually (a `Path(..)` chain, or a name assigned or annotated as one
//! in the same file); it is a Must use. A `.m` entry on a receiver that does not resolve is a May
//! use, reported Unresolved (grimble-model.md 9.6: unknown never reads as clean).
//!
//! Import resolution (ticket D36SRKP): besides the call graph, `gob_symbols::path_uses` resolves
//! each call and each function-valued reference through `use ... as`, from-imports, `let` and
//! assignment aliases, literal `getattr` / `import_module` (the same use as the direct form) and explicit
//! `std::` / `tokio::` roots (which a repository type named `Command` cannot hide). Not resolved:
//! glob imports and macro bodies. A name-computed lookup (`getattr`, `__import__`,
//! `importlib.import_module`, `vars(m)[n]`, `m.__dict__[n]`, `sys.modules[n]`) resolves through
//! the shared gob-ir `name_lookup` rule (ticket 6CV37RW): a literal name denotes the origin symbol
//! exactly as the direct form, any other name is reported Unresolved against every atom its known
//! prefix could reach.
//!
//! Typed receivers (ticket YCR4M6H): a Rust vocabulary entry `<type path>.<method>`
//! (`ureq::Agent.run`) names a method call whose receiver type resolves, from the syntax tree, to
//! that path: through `use` imports and aliases, struct fields (`self.agent`), parameters, typed
//! or constructor `let` bindings, `Arc` / `Box` / `Rc` wrappers, `clone()` and typed `const` /
//! `static` items. It is a Must use. A name bound twice to different types, or by a pattern that
//! states no type, stays unresolved and is not reported.
//!
//! Known limits: receiver typing is per file and textual (no cross-module constants, no
//! shadowing by unannotated parameters; typed receivers resolve only types written in the same
//! file, not values returned by calls); `open(..)` in a write mode is `fs.write` (ticket 01M4HYH9CDNJSYEZQGKRZA7WX2) but a mode other than a literal is a May `fs.write` beside the read; the template excuses and CAP004 (packs.md 6.7) are computed by `grimble_capabilities::excuse` but not yet emitted here; the pack
//! severity table is not consulted (CAP001 is an Error, CAP002 a Warning).
//!
//! `may` arguments (ticket 5X9CAQE): a grant `may fs.read("config/**")` covers a use only when the
//! use's argument is statically known and `grimble_model::args::judge` matches it against a grant
//! argument. The argument is folded by `gob_symbols::call_args` (literals, concatenations,
//! single-assignment constants, tuples, path wrappers). A known argument outside every covering
//! grant argument is CAP001 (Error) naming both. An argument that cannot be folded, a use through
//! a receiver (`Path(..).read_text()`), or an atom a pack declares is Unresolved with reason
//! `unresolved-edge`, never clean. Paths are compared lexically (symlinks are not followed).
//!
//! Grant scope (ticket M64HENY): a grant's `at` selector is judged against the unit of the use
//! (the call edge's from-symbol) and its enclosing symbols, not its file. `at "f.rs::allowed"`
//! covers a use in `allowed` and in anything nested in it, and a use in a sibling function of
//! the same file is CAP001. CAP002 asks whether any use falls inside the selected units.

// frob:ticket 01M4FGXTB8T0F8AHNN604XCAZV
// frob:ticket 01M4FGXX1F6W7Z1K22NFSW5067
// frob:ticket 01M4HW9Y1TXZCN4Y5RF2T7C4A9
// frob:ticket 01M4HEMAM737MTY3385G7VKXQ4
// frob:ticket 01M59RWT16TFNSACMMTTXX200T
// frob:ticket 01M5XNNHBSPSM5XFG8FM64HENY
// frob:ticket 01M5XNNHJ0ES2PB6ZKAD36SRKP
// frob:ticket 01M5XNNH61Z437EDDB05X9CAQE
// frob:ticket 01M5XNNHRFE1K2DHBD7S9HQ7A6
// frob:ticket 01M5XWCAYVZQX363SSWYCR4M6H
// frob:ticket 01M4HYH9CDNJSYEZQGKRZA7WX2

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;

use gob_ir::Answer;
use gob_ir::registry::{DetectorKind, atoms, callee_vocab, detectors};
use gob_rules::Severity;
use gob_symbols::{EdgeKind, Target};
use gob_walk::{Owner, selects_unit_or_enclosing};
use grimble_capabilities::{Cell, NodeInput};
use grimble_model::args::{ArgKind, Judgement, arg_kind, judge};
use grimble_model::ast::EntityKind;
use grimble_model::{PackDetectorKind, PackPin};

use crate::code::CodeFile;
use crate::eval::{Cx, Output};
use crate::model::Grant;
use crate::types::Reason;

/// How many example call sites one finding names.
const EXAMPLES: usize = 3;

/// A method-name vocabulary entry (`.listen`) counts only in a file that also calls the gate
/// callee: `(atom, language, method, companion callee)`.
const METHOD_GATES: [(&str, &str, &str, &str); 2] = [
    ("net.listen", "python", "listen", "socket.socket"),
    ("net.connect", "python", "connect", "socket.socket"),
];

/// One observed use of an atom.
#[derive(Clone, Debug)]
struct Use {
    atom: String,
    file: String,
    /// The from-symbol of the call edge as text: the unit the use sits in.
    unit: String,
    /// The qualname segments of that unit (empty for module-level code).
    qual: Vec<String>,
    line: Option<u32>,
    callee: String,
    /// False when the receiver type did not resolve: a May use whoever owns the code.
    certain: bool,
    /// The statically known argument the call passes (see `attach_args`); `None` when it does not
    /// fold, which an argument-scoped grant can never clear.
    arg: Option<String>,
}

impl Use {
    fn site(&self) -> String {
        match self.line {
            Some(l) => format!("{}:{l} {}", self.file, self.callee),
            None => format!("{} {}", self.file, self.callee),
        }
    }
}

/// Uses by node anchor: `lo` from Must-owned code, `hi` only from May-owned code.
#[derive(Default)]
struct Uses {
    lo: BTreeMap<String, Vec<Use>>,
    hi: BTreeMap<String, Vec<Use>>,
    /// Uses in code no node owns (`Owner::Foreign`): checked against an implicit node with no
    /// grants (default-deny, ticket S9HQ7A6).
    unowned: Vec<Use>,
    /// Uses in code whose owner cannot be named and has no candidate (a hidden remainder).
    unseen: Vec<Use>,
}

/// Why CAP001 and CAP002 have no subject: no node owns code, so no cell exists.
pub fn caps_inapplicable(model: &crate::model::Model) -> Option<&'static str> {
    let owns = model
        .entities
        .values()
        .any(|e| e.kind == EntityKind::Node && !e.external && e.owns_code());
    (!owns).then_some("no node owns code, so no use can be observed")
}

fn callee_of(text: &str) -> &str {
    text.strip_suffix("(..)").unwrap_or(text)
}

/// Crates whose `Command` is a builder type, not a process: `clap::Command::new` names a CLI
/// command and must not match the `Command::new` spawn entry behind its extra leading segments.
const NON_PROCESS_CRATES: &[&str] = &["clap"];

/// True when the written `callee` names the vocabulary entry `name` (a Rust path entry also
/// matches behind extra leading segments: `std::fs::read` names `fs::read`, but a path rooted
/// in a `NON_PROCESS_CRATES` crate names nothing).
fn names_callee(lang: &str, names: &BTreeSet<&str>, callee: &str) -> bool {
    if names.contains(callee) {
        return true;
    }
    lang == "rust"
        && !callee
            .split_once("::")
            .is_some_and(|(root, _)| NON_PROCESS_CRATES.contains(&root))
        && names
            .iter()
            .any(|n| n.contains("::") && callee.ends_with(&format!("::{n}")))
}

/// One atom a call may use and whether the call certainly does.
struct Hit {
    atom: String,
    certain: bool,
}

/// Every atom with a callee vocabulary in `lang` and that vocabulary: the shared registry's atoms
/// and the atoms of the enabled repository packs whose detector row is a `callee` row.
fn vocabularies<'a>(
    lang: &str,
    packs: &'a BTreeMap<String, PackPin>,
) -> Vec<(&'a str, BTreeSet<&'a str>)> {
    let mut out: Vec<(&'a str, BTreeSet<&'a str>)> = Vec::new();
    for a in atoms() {
        if let Answer::Exact(names) = callee_vocab(lang, a.name) {
            out.push((a.name, names));
        }
    }
    for d in packs
        .values()
        .flat_map(|p| p.detectors.iter())
        .filter(|d| d.kind == PackDetectorKind::Callee && d.lang == lang)
    {
        let names = d.names.iter().map(String::as_str);
        match out.iter_mut().find(|(a, _)| *a == d.atom) {
            Some((_, have)) => have.extend(names),
            None => out.push((d.atom.as_str(), names.collect())),
        }
    }
    out
}

/// The atoms whose vocabulary in `lang` names the call `callee`, given the calls `file_calls` of
/// its file and the lazily computed type of its receiver.
fn atoms_of(
    vocabs: &[(&str, BTreeSet<&str>)],
    lang: &str,
    callee: &str,
    file_calls: &BTreeSet<String>,
    receiver_is_path: &mut dyn FnMut(&str) -> bool,
) -> Vec<Hit> {
    let mut out = Vec::new();
    for (atom, names) in vocabs {
        let atom = *atom;
        if names_callee(lang, names, callee) {
            out.push(Hit {
                atom: atom.to_owned(),
                certain: true,
            });
            continue;
        }
        let Some((recv, m)) = callee.rsplit_once('.') else {
            continue;
        };
        if !names.contains(format!(".{m}").as_str()) {
            continue;
        }
        let gated = METHOD_GATES
            .iter()
            .any(|(m_atom, l, method, _)| *m_atom == atom && *l == lang && *method == m);
        if gated {
            let open = METHOD_GATES.iter().any(|(m_atom, l, method, gate)| {
                *m_atom == atom && *l == lang && *method == m && file_calls.contains(*gate)
            });
            if open {
                out.push(Hit {
                    atom: atom.to_owned(),
                    certain: true,
                });
            }
        } else if names.contains(format!("Path.{m}").as_str()) && receiver_is_path(recv) {
            out.push(Hit {
                atom: atom.to_owned(),
                certain: true,
            });
        } else {
            tracing::debug!(
                callee,
                atom,
                "vocabulary method on an unresolved receiver: May"
            );
            out.push(Hit {
                atom: atom.to_owned(),
                certain: false,
            });
        }
    }
    out
}

/// Python receiver typing: is the expression `recv` a `pathlib.Path`? Textual and per file.
mod pytype {
    /// Methods and attributes that keep a `Path` a `Path`.
    const KEEPS: [&str; 14] = [
        "resolve",
        "absolute",
        "parent",
        "parents",
        "joinpath",
        "with_name",
        "with_suffix",
        "with_stem",
        "expanduser",
        "relative_to",
        "readlink",
        "home",
        "cwd",
        "samefile",
    ];

    fn is_ident(c: char) -> bool {
        c.is_alphanumeric() || c == '_'
    }

    /// The index just past the bracket group opening at byte `at` of `s`, honouring quotes.
    fn skip_group(s: &str, at: usize) -> Option<usize> {
        let mut depth = 0usize;
        let mut quote: Option<char> = None;
        for (i, c) in s[at..].char_indices() {
            match quote {
                Some(q) => {
                    if c == q {
                        quote = None;
                    }
                }
                None => match c {
                    '"' | '\'' => quote = Some(c),
                    '(' | '[' | '{' => depth += 1,
                    ')' | ']' | '}' => {
                        depth = depth.checked_sub(1)?;
                        if depth == 0 {
                            return Some(at + i + c.len_utf8());
                        }
                    }
                    _ => {}
                },
            }
        }
        None
    }

    /// Split `s` on top-level `/` (true division, not `//`).
    fn split_div(s: &str) -> Vec<&str> {
        let mut parts = Vec::new();
        let (mut last, mut i) = (0, 0);
        let b = s.as_bytes();
        while i < b.len() {
            match b[i] {
                b'(' | b'[' | b'{' => match skip_group(s, i) {
                    Some(end) => {
                        i = end;
                        continue;
                    }
                    None => return vec![s],
                },
                b'"' | b'\'' => {
                    let q = b[i];
                    i += 1;
                    while i < b.len() && b[i] != q {
                        i += 1;
                    }
                }
                b'/' if b.get(i + 1) != Some(&b'/') && i > 0 && b[i - 1] != b'/' => {
                    parts.push(&s[last..i]);
                    last = i + 1;
                }
                _ => {}
            }
            i += 1;
        }
        parts.push(&s[last..]);
        parts
    }

    /// True when `e` is a `Path(..)` / `Path.home()` head followed only by Path-keeping steps.
    fn path_chain(e: &str) -> bool {
        let rest = ["pathlib.Path", "Path"]
            .iter()
            .find_map(|h| e.strip_prefix(h))
            .filter(|r| !r.starts_with(is_ident));
        let Some(mut rest) = rest else { return false };
        loop {
            rest = rest.trim_start();
            if rest.is_empty() {
                return true;
            }
            if rest.starts_with('(') {
                let Some(end) = skip_group(rest, 0) else {
                    return false;
                };
                rest = &rest[end..];
                continue;
            }
            let Some(after) = rest.strip_prefix('.') else {
                return false;
            };
            let n = after.find(|c: char| !is_ident(c)).unwrap_or(after.len());
            if !KEEPS.contains(&&after[..n]) {
                return false;
            }
            rest = &after[n..];
        }
    }

    /// The right-hand sides and annotations evidencing `name` in `src`: `(is_path, is_evidence)`.
    fn evidence(src: &str, name: &str, depth: usize) -> Vec<bool> {
        let mut out = Vec::new();
        let mut lines = src.lines().peekable();
        while let Some(line) = lines.next() {
            let t = line.trim_start();
            let Some(after) = t.strip_prefix(name).filter(|r| !r.starts_with(is_ident)) else {
                continue;
            };
            let after = after.trim_start();
            let (ann, rest) = match after.strip_prefix(':') {
                Some(a) => match a.split_once('=') {
                    Some((ann, rhs)) if !rhs.starts_with('=') => (Some(ann.trim()), Some(rhs)),
                    _ => (Some(a.trim().trim_end_matches(',')), None),
                },
                None => (
                    None,
                    after.strip_prefix('=').filter(|r| !r.starts_with('=')),
                ),
            };
            if ann.is_none() && rest.is_none() {
                continue;
            }
            if let Some(ann) = ann {
                if ann == "Path" || ann == "pathlib.Path" {
                    out.push(true);
                    continue;
                }
                if rest.is_none() {
                    // `name: Other` in a signature or bare annotation
                    out.push(false);
                    continue;
                }
            }
            let mut rhs = rest.unwrap_or("").to_owned();
            while skip_group_balanced(&rhs).is_none() {
                match lines.next() {
                    Some(l) => {
                        rhs.push(' ');
                        rhs.push_str(l.trim());
                    }
                    None => break,
                }
            }
            out.push(is_path_expr(src, &rhs, depth + 1));
        }
        // `name: Path` inside a single-line signature
        for pat in [format!("{name}: Path"), format!("{name}: pathlib.Path")] {
            for (i, _) in src.match_indices(&pat) {
                let before_ok = !src[..i].ends_with(is_ident);
                let after_ok = !src[i + pat.len()..].starts_with(is_ident);
                let line_start = src[..i].rsplit('\n').next().unwrap_or("").trim().is_empty();
                if before_ok && after_ok && !line_start {
                    out.push(true);
                }
            }
        }
        out
    }

    fn skip_group_balanced(s: &str) -> Option<()> {
        let mut depth = 0i32;
        let mut quote: Option<char> = None;
        for c in s.chars() {
            match quote {
                Some(q) if c == q => quote = None,
                Some(_) => {}
                None => match c {
                    '"' | '\'' => quote = Some(c),
                    '(' | '[' | '{' => depth += 1,
                    ')' | ']' | '}' => depth -= 1,
                    _ => {}
                },
            }
        }
        (depth <= 0).then_some(())
    }

    /// True when the expression `expr` evaluates to a `pathlib.Path` as far as `src` shows.
    pub(super) fn is_path_expr(src: &str, expr: &str, depth: usize) -> bool {
        if depth > 4 || !src.contains("pathlib") {
            return false;
        }
        let e = expr.trim();
        let e = e.split('#').next().unwrap_or(e).trim();
        if let Some(inner) = e
            .strip_prefix('(')
            .filter(|_| skip_group(e, 0) == Some(e.len()))
        {
            return is_path_expr(src, inner.strip_suffix(')').unwrap_or(inner), depth + 1);
        }
        let parts = split_div(e);
        if parts.len() > 1 {
            return parts.iter().any(|p| is_path_expr(src, p, depth + 1));
        }
        if path_chain(e) {
            return true;
        }
        if !e.is_empty() && e.chars().all(is_ident) {
            let ev = evidence(src, e, depth);
            return !ev.is_empty() && ev.iter().all(|p| *p);
        }
        false
    }
}

/// Rust receiver typing (ticket YCR4M6H): resolves the type of the receiver of each method call
/// from the syntax tree, so `agent.run(..)` on an `ureq::Agent` is a `<type path>.<method>` call
/// the vocabulary can name. Per file: imports, struct fields, parameters, `let` bindings,
/// `self`, `const` and `static` items. A name bound more than once to different types, or by a
/// pattern that does not state a type, stays unresolved.
mod rstype {
    use std::collections::BTreeMap;

    use gob_languages::{Language, ParseLimits, ParseResult, parse};
    use tree_sitter::Node;

    /// A resolved type: an external path (`ureq::Agent`) or a type this file defines.
    #[derive(Clone, Debug, PartialEq, Eq)]
    enum Ty {
        Path(String),
        Local(String),
    }

    /// A method call whose receiver type resolved to an external path.
    pub(super) struct TypedCall {
        /// The resolved type path of the receiver.
        pub(super) ty: String,
        /// The called method.
        pub(super) method: String,
        pub(super) offset: usize,
        pub(super) line: u32,
    }

    /// A name's binding in a function: one type, or `None` when ambiguous or untyped.
    type Env = BTreeMap<String, Option<Ty>>;

    struct Cx<'s> {
        src: &'s str,
        imports: BTreeMap<String, String>,
        locals: BTreeMap<String, BTreeMap<String, Option<Node<'s>>>>,
        items: Env,
        out: Vec<TypedCall>,
    }

    fn text<'s>(src: &'s str, n: Node<'_>) -> &'s str {
        src.get(n.start_byte()..n.end_byte()).unwrap_or("")
    }

    fn kids(n: Node<'_>) -> Vec<Node<'_>> {
        let mut c = n.walk();
        n.named_children(&mut c).collect()
    }

    /// The method calls in `src` whose receiver type resolves to an external path.
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
            items: Env::new(),
            out: Vec::new(),
        };
        cx.collect_items(root);
        cx.visit(root, None);
        tracing::debug!(calls = cx.out.len(), "typed receiver calls resolved");
        cx.out
    }

    impl<'s> Cx<'s> {
        /// Imports, locally defined types with their fields, and typed `const` / `static` items.
        fn collect_items(&mut self, n: Node<'s>) {
            match n.kind() {
                "use_declaration" => {
                    if let Some(arg) = n.child_by_field_name("argument") {
                        let mut imports = std::mem::take(&mut self.imports);
                        flatten_use(self.src, arg, &[], &mut imports);
                        self.imports = imports;
                    }
                }
                "struct_item" | "enum_item" | "union_item" | "type_item" | "trait_item" => {
                    if let Some(name) = n.child_by_field_name("name") {
                        let fields = self
                            .locals
                            .entry(text(self.src, name).to_owned())
                            .or_default();
                        if let Some(body) = n.child_by_field_name("body") {
                            for f in kids(body) {
                                if f.kind() == "field_declaration"
                                    && let (Some(fname), Some(fty)) = (
                                        f.child_by_field_name("name"),
                                        f.child_by_field_name("type"),
                                    )
                                {
                                    fields.insert(text(self.src, fname).to_owned(), Some(fty));
                                }
                            }
                        }
                    }
                }
                _ => {}
            }
            for k in kids(n) {
                if k.kind() != "function_item" {
                    self.collect_items(k);
                }
            }
            if matches!(n.kind(), "const_item" | "static_item")
                && let (Some(name), Some(ty)) =
                    (n.child_by_field_name("name"), n.child_by_field_name("type"))
            {
                let ty = self.resolve_type(ty, None);
                bind(&mut self.items, text(self.src, name), ty);
            }
        }

        /// Walks for function items, resolving the calls in each with its own environment.
        fn visit(&mut self, n: Node<'s>, self_ty: Option<&Ty>) {
            if n.kind() == "function_item" {
                self.function(n, self_ty);
                return;
            }
            let impl_ty = (n.kind() == "impl_item")
                .then(|| n.child_by_field_name("type"))
                .flatten()
                .and_then(|t| self.resolve_type(t, None));
            let self_ty = impl_ty.as_ref().or(self_ty);
            for k in kids(n) {
                self.visit(k, self_ty);
            }
        }

        fn function(&mut self, f: Node<'s>, self_ty: Option<&Ty>) {
            let mut env = Env::new();
            if let Some(params) = f.child_by_field_name("parameters") {
                for p in kids(params) {
                    if p.kind() == "parameter"
                        && let (Some(pat), Some(ty)) = (
                            p.child_by_field_name("pattern"),
                            p.child_by_field_name("type"),
                        )
                    {
                        if pat.kind() == "identifier" {
                            let ty = self.resolve_type(ty, self_ty);
                            bind(&mut env, text(self.src, pat), ty);
                        } else {
                            self.shadow_all(pat, &mut env);
                        }
                    }
                }
            }
            let Some(body) = f.child_by_field_name("body") else {
                return;
            };
            self.bindings(body, self_ty, &mut env);
            self.calls(body, self_ty, &env);
            // nested functions have their own environment
            self.nested(body, self_ty);
        }

        fn nested(&mut self, n: Node<'s>, self_ty: Option<&Ty>) {
            for k in kids(n) {
                if k.kind() == "function_item" {
                    self.function(k, self_ty);
                } else {
                    self.nested(k, self_ty);
                }
            }
        }

        /// Marks every name a pattern binds as unresolved.
        fn shadow_all(&self, pat: Node<'s>, env: &mut Env) {
            if pat.kind() == "identifier" {
                env.insert(text(self.src, pat).to_owned(), None);
            }
            for k in kids(pat) {
                self.shadow_all(k, env);
            }
        }

        /// Records the types of `let` bindings; every other pattern shadows its names.
        fn bindings(&self, n: Node<'s>, self_ty: Option<&Ty>, env: &mut Env) {
            for k in kids(n) {
                match k.kind() {
                    "function_item" => continue,
                    "let_declaration" => match k.child_by_field_name("pattern") {
                        Some(p) if p.kind() == "identifier" => {
                            let ty = match (
                                k.child_by_field_name("type"),
                                k.child_by_field_name("value"),
                            ) {
                                (Some(t), _) => self.resolve_type(t, self_ty),
                                (None, Some(v)) => self.infer_value(v, self_ty),
                                (None, None) => None,
                            };
                            bind(env, text(self.src, p), ty);
                        }
                        Some(p) => self.shadow_all(p, env),
                        None => {}
                    },
                    "closure_parameters" | "for_expression" | "match_arm" | "let_condition"
                    | "match_pattern" => {
                        for pat in kids(k) {
                            if matches!(
                                k.kind(),
                                "closure_parameters"
                                    | "match_arm"
                                    | "match_pattern"
                                    | "let_condition"
                            ) || k.child_by_field_name("pattern") == Some(pat)
                            {
                                self.shadow_all(pat, env);
                            }
                        }
                    }
                    _ => {}
                }
                self.bindings(k, self_ty, env);
            }
        }

        /// The type a constructor expression (`Agent::new(..)`, `Arc::new(..)`) produces.
        fn infer_value(&self, v: Node<'s>, self_ty: Option<&Ty>) -> Option<Ty> {
            if v.kind() != "call_expression" {
                return None;
            }
            let f = v.child_by_field_name("function")?;
            if f.kind() != "scoped_identifier" {
                return None;
            }
            let full = text(self.src, f);
            let (prefix, last) = full.rsplit_once("::")?;
            if !matches!(
                last,
                "new" | "default" | "from" | "new_with_defaults" | "new_with_config"
            ) {
                return None;
            }
            if matches!(prefix, "Arc" | "Box" | "Rc") {
                let arg = kids(v.child_by_field_name("arguments")?)
                    .into_iter()
                    .next()?;
                return self.infer_value(arg, self_ty);
            }
            self.resolve_segments(prefix.split("::").map(str::to_owned).collect(), self_ty)
        }

        /// Resolves a type node, unwrapping references, smart pointers and generics.
        fn resolve_type(&self, t: Node<'s>, self_ty: Option<&Ty>) -> Option<Ty> {
            match t.kind() {
                "reference_type" => self.resolve_type(t.child_by_field_name("type")?, self_ty),
                "generic_type" => {
                    let base = t.child_by_field_name("type")?;
                    let name = text(self.src, base);
                    if matches!(
                        name,
                        "Arc" | "Box" | "Rc" | "std::sync::Arc" | "std::rc::Rc"
                    ) {
                        let args = t.child_by_field_name("type_arguments")?;
                        let inner = kids(args).into_iter().find(|a| a.kind() != "lifetime")?;
                        return self.resolve_type(inner, self_ty);
                    }
                    self.resolve_type(base, self_ty)
                }
                "type_identifier" | "scoped_type_identifier" => self.resolve_segments(
                    text(self.src, t)
                        .trim_start_matches("::")
                        .split("::")
                        .map(str::to_owned)
                        .collect(),
                    self_ty,
                ),
                _ => None,
            }
        }

        fn resolve_segments(&self, mut segs: Vec<String>, self_ty: Option<&Ty>) -> Option<Ty> {
            let first = segs.first()?.clone();
            if segs.len() == 1 && first == "Self" {
                return self_ty.cloned();
            }
            if segs.len() == 1 && self.locals.contains_key(&first) {
                return Some(Ty::Local(first));
            }
            if let Some(full) = self.imports.get(&first) {
                segs.remove(0);
                let mut path = full.clone();
                for s in segs {
                    path.push_str("::");
                    path.push_str(&s);
                }
                return Some(Ty::Path(path));
            }
            (segs.len() > 1).then(|| Ty::Path(segs.join("::")))
        }

        /// The type of a receiver expression, when it resolves.
        fn type_of(&self, e: Node<'s>, self_ty: Option<&Ty>, env: &Env) -> Option<Ty> {
            match e.kind() {
                "identifier" => {
                    let name = text(self.src, e);
                    env.get(name).or_else(|| self.items.get(name))?.clone()
                }
                "self" => self_ty.cloned(),
                "parenthesized_expression" | "reference_expression" => {
                    let inner = e
                        .child_by_field_name("value")
                        .or_else(|| kids(e).into_iter().next())?;
                    self.type_of(inner, self_ty, env)
                }
                "field_expression" => {
                    let Ty::Local(owner) =
                        self.type_of(e.child_by_field_name("value")?, self_ty, env)?
                    else {
                        return None;
                    };
                    let field = text(self.src, e.child_by_field_name("field")?);
                    let fty = (*self.locals.get(&owner)?.get(field)?)?;
                    self.resolve_type(fty, Some(&Ty::Local(owner)))
                }
                "call_expression" => {
                    // `x.clone()` keeps the type of `x`
                    let f = e.child_by_field_name("function")?;
                    (f.kind() == "field_expression"
                        && text(self.src, f.child_by_field_name("field")?) == "clone")
                        .then(|| self.type_of(f.child_by_field_name("value")?, self_ty, env))
                        .flatten()
                }
                _ => None,
            }
        }

        /// Records each method call whose receiver resolves to an external path.
        fn calls(&mut self, n: Node<'s>, self_ty: Option<&Ty>, env: &Env) {
            for k in kids(n) {
                if k.kind() == "function_item" {
                    continue;
                }
                if k.kind() == "call_expression"
                    && let Some(f) = k.child_by_field_name("function")
                    && f.kind() == "field_expression"
                    && let (Some(recv), Some(m)) = (
                        f.child_by_field_name("value"),
                        f.child_by_field_name("field"),
                    )
                    && let Some(Ty::Path(ty)) = self.type_of(recv, self_ty, env)
                {
                    self.out.push(TypedCall {
                        ty,
                        method: text(self.src, m).to_owned(),
                        offset: k.start_byte(),
                        line: u32::try_from(k.start_position().row + 1).unwrap_or(u32::MAX),
                    });
                }
                self.calls(k, self_ty, env);
            }
        }
    }

    /// Binds `name` to `ty`; a second, different binding makes the name unresolved.
    fn bind(env: &mut Env, name: &str, ty: Option<Ty>) {
        match env.get(name) {
            Some(have) if *have != ty => {
                env.insert(name.to_owned(), None);
            }
            Some(_) => {}
            None => {
                env.insert(name.to_owned(), ty);
            }
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
}

/// Files an owner `Must` claims go to `lo` when certain, else `hi`; `May` owners get `hi`.
fn route(uses: &mut Uses, owner: &Owner, u: Use) {
    match owner {
        Owner::Must(n) if !u.certain => {
            uses.hi.entry(n.as_str().to_owned()).or_default().push(u);
        }
        Owner::Must(n) => uses.lo.entry(n.as_str().to_owned()).or_default().push(u),
        Owner::May(ns) => {
            for n in ns {
                uses.hi
                    .entry(n.as_str().to_owned())
                    .or_default()
                    .push(u.clone());
            }
        }
        // A tie names its candidates: each may own the use.
        Owner::Unknown(ns) if !ns.is_empty() => {
            for n in ns {
                uses.hi
                    .entry(n.as_str().to_owned())
                    .or_default()
                    .push(u.clone());
            }
        }
        Owner::Unknown(_) => uses.unseen.push(u),
        Owner::Foreign => uses.unowned.push(u),
    }
}

/// The owner of the unit a use sits in. A file no selector reaches has no ownership units at all
/// (see `owner::build`), so its code is `Foreign` rather than skipped; frob-owned and unwalked
/// files and units the owner pass never saw have no owner to judge (`None`).
fn owner_of_use(cx: &Cx<'_>, unit: &str, path: &str) -> Option<Owner> {
    if let Some(uo) = cx.owners.units.get(unit) {
        return Some(uo.merged.owner.clone());
    }
    let unreached = cx.owners.files.get(path).is_some_and(|fo| !fo.expanded);
    if unreached && !crate::frob_owned::is_frob_owned(path, cx.ledger_dir) {
        tracing::debug!(path, unit, "use sits in code no node owns");
        return Some(Owner::Foreign);
    }
    None
}

/// The last path segment of a vocabulary name (`fs::read` -> `read`, `subprocess.run` -> `run`).
fn last_segment(name: &str) -> &str {
    let name = name.trim_start_matches('.');
    name.rsplit(['.', ':']).next().unwrap_or(name)
}

/// The ownership unit holding byte `offset` of a file: its innermost symbol that is a unit, else
/// the file unit. Returns the unit's symref text and qualname segments.
fn unit_at(
    cx: &Cx<'_>,
    symbols: &gob_symbols::FileSymbols,
    file_unit: &str,
    offset: usize,
) -> (String, Vec<String>) {
    let width = |s: &gob_symbols::SymbolRecord| u32::from(s.span.end()) - u32::from(s.span.start());
    let holder = symbols
        .symbols
        .iter()
        .filter(|s| {
            usize::try_from(u32::from(s.span.start())).is_ok_and(|a| a <= offset)
                && usize::try_from(u32::from(s.span.end())).is_ok_and(|b| offset < b)
        })
        .filter(|s| cx.owners.units.contains_key(&s.symref.to_string()))
        .min_by_key(|s| width(s));
    match holder {
        Some(s) => (
            s.symref.to_string(),
            match s.symref.target() {
                Target::Symbol(segs) => segs.clone(),
                _ => Vec::new(),
            },
        ),
        None => (file_unit.to_owned(), Vec::new()),
    }
}

/// frob:ticket 01M642301PNSE0VTM2F313NY13
/// True when the call edge proves no target: unresolved, or a guess by method name alone. A
/// project class that merely shares a method's name must never hide a use whose receiver may be
/// a capability type, so such an edge is judged like an unresolved call.
fn is_open_call(e: &gob_symbols::StatusEdge) -> bool {
    e.kind == EdgeKind::Calls && (e.to.is_none() || (e.basis == gob_symbols::EdgeBasis::NameOnly))
}

/// (file, line, name) of every call the graph resolved inside the repository.
fn graph_resolved_calls(cx: &Cx<'_>) -> BTreeSet<(String, u32, String)> {
    let mut local = BTreeSet::new();
    for e in cx.graph.edges_with_status() {
        if e.kind == EdgeKind::Calls
            && e.to.is_some()
            && !is_open_call(e)
            && let (Some(l), Some(n)) = (e.line, e.name.as_ref())
        {
            local.insert((e.from.path().to_owned(), l, n.clone()));
        }
    }
    local
}

/// Dedup keys (unit, line, atom, certain) of every use already recorded.
fn seen_uses(uses: &Uses) -> BTreeSet<(String, Option<u32>, String, bool)> {
    let mut set = BTreeSet::new();
    for us in uses
        .lo
        .values()
        .chain(uses.hi.values())
        .chain([&uses.unowned, &uses.unseen])
    {
        for u in us {
            set.insert((u.unit.clone(), u.line, u.atom.clone(), u.certain));
        }
    }
    set
}

/// Files the import-resolution pass reads: every unit file plus unexpanded (unowned) files.
fn scan_files<'a>(cx: &'a Cx<'_>) -> BTreeSet<&'a str> {
    cx.owners
        .units
        .values()
        .map(|u| u.file.as_str())
        .chain(
            cx.owners
                .files
                .iter()
                .filter(|(_, fo)| !fo.expanded)
                .map(|(p, _)| p.as_str()),
        )
        .collect()
}

/// Uses found by import resolution (ticket D36SRKP): calls and function values whose written
/// path names a vocabulary entry only through an alias, a from-import, a `let` binding, a literal
/// `getattr` / `import_module`, or an explicit `std::` / `tokio::` root that a same-named
/// repository item hides from the call graph. Added to `uses` unless the call-graph pass already
/// recorded the same atom on the same line of the same unit.
fn scan_resolved(cx: &Cx<'_>, uses: &mut Uses) {
    let local = graph_resolved_calls(cx);
    let mut seen = seen_uses(uses);
    let files = scan_files(cx);
    let mut vocabs: BTreeMap<String, Vec<(&str, BTreeSet<&str>)>> = BTreeMap::new();
    let mut added = 0usize;
    for path in files {
        let Some(code) = cx.code.file(path) else {
            continue;
        };
        if !matches!(code.language.as_str(), "rust" | "python") {
            continue;
        }
        let vocab = vocabs
            .entry(code.language.clone())
            .or_insert_with(|| vocabularies(&code.language, cx.packs));
        let Some(src) = code.source() else { continue };
        // cheap prefilter: some vocabulary name's last segment must occur in the file at all
        // (a name-computed lookup names no vocabulary entry, so a lookup primitive also passes)
        if !gob_ir::name_lookup::mentions_lookup(&code.language, &src)
            && !vocab
                .iter()
                .any(|(_, names)| names.iter().any(|n| src.contains(last_segment(n))))
        {
            continue;
        }
        let Some(symbols) = code.symbols() else {
            continue;
        };
        let file_unit = gob_symbols::Symref::file(path).to_string();
        for pu in gob_symbols::path_uses(&code.language, &src) {
            if !pu.external_root
                && !pu.dynamic
                && local.contains(&(
                    path.to_owned(),
                    pu.line,
                    last_segment(&pu.spelled).to_owned(),
                ))
            {
                tracing::debug!(file = path, line = pu.line, spelled = %pu.spelled, "resolved path is a repository item");
                continue;
            }
            let prefix = format!("{}.", pu.path);
            let hits: Vec<&str> = vocab
                .iter()
                .filter(|(_, names)| {
                    if pu.computed {
                        // unknown tail: any atom whose vocabulary lives under the known prefix
                        pu.path.is_empty() || names.iter().any(|n| n.starts_with(&prefix))
                    } else {
                        names_callee(&code.language, names, &pu.path)
                    }
                })
                .map(|(a, _)| *a)
                .collect();
            if hits.is_empty() {
                continue;
            }
            let (unit, qual) = unit_at(cx, symbols, &file_unit, pu.offset);
            let Some(owner) = owner_of_use(cx, &unit, path) else {
                tracing::debug!(file = path, unit = %unit, "resolved use has no ownership unit");
                continue;
            };
            // a literal lookup name denotes the origin symbol exactly as the direct form; only a
            // computed name is unproven
            let certain = !pu.computed;
            for atom in hits {
                if !seen.insert((unit.clone(), Some(pu.line), atom.to_owned(), certain)) {
                    continue;
                }
                tracing::debug!(file = path, line = pu.line, atom, callee = %pu.path, certain, "resolved capability use");
                added += 1;
                route(
                    uses,
                    &owner,
                    Use {
                        atom: atom.to_owned(),
                        file: path.to_owned(),
                        unit: unit.clone(),
                        qual: qual.clone(),
                        line: Some(pu.line),
                        callee: pu.path.clone(),
                        certain,
                        arg: None,
                    },
                );
            }
        }
    }
    tracing::info!(added, "import-resolved capability uses added");
}

/// True for a `<type path>.<method>` vocabulary name (`ureq::Agent.run`).
fn is_typed_name(name: &str) -> bool {
    name.contains('.') && !name.starts_with('.') && name.contains("::")
}

/// Uses found by typed-receiver resolution (ticket YCR4M6H): method calls whose receiver type
/// resolves (`rstype`) to a path a vocabulary names as `<type path>.<method>`, such as
/// `ureq::Agent.run`. A Must use, added unless an earlier pass recorded the same atom on the same
/// line of the same unit.
fn scan_typed_receivers(cx: &Cx<'_>, uses: &mut Uses) {
    let mut seen = seen_uses(uses);
    let vocab = vocabularies("rust", cx.packs);
    if !vocab
        .iter()
        .any(|(_, names)| names.iter().any(|n| is_typed_name(n)))
    {
        return;
    }
    let mut added = 0usize;
    for path in scan_files(cx) {
        let Some(code) = cx.code.file(path) else {
            continue;
        };
        if code.language != "rust" {
            continue;
        }
        let Some(src) = code.source() else { continue };
        // cheap prefilter: some typed entry's type name must occur in the file at all
        if !vocab.iter().any(|(_, names)| {
            names.iter().filter(|n| is_typed_name(n)).any(|n| {
                n.rsplit_once('.')
                    .is_some_and(|(ty, _)| src.contains(last_segment(ty)))
            })
        }) {
            continue;
        }
        let Some(symbols) = code.symbols() else {
            continue;
        };
        let file_unit = gob_symbols::Symref::file(path).to_string();
        for call in rstype::typed_calls(&src) {
            let callee = format!("{}.{}", call.ty, call.method);
            let hits: Vec<&str> = vocab
                .iter()
                .filter(|(_, names)| names.contains(callee.as_str()))
                .map(|(a, _)| *a)
                .collect();
            if hits.is_empty() {
                continue;
            }
            let (unit, qual) = unit_at(cx, symbols, &file_unit, call.offset);
            let Some(owner) = owner_of_use(cx, &unit, path) else {
                tracing::debug!(file = path, unit = %unit, "typed use has no ownership unit");
                continue;
            };
            for atom in hits {
                if !seen.insert((unit.clone(), Some(call.line), atom.to_owned(), true)) {
                    continue;
                }
                tracing::debug!(file = path, line = call.line, atom, %callee, "typed-receiver capability use");
                added += 1;
                route(
                    uses,
                    &owner,
                    Use {
                        atom: atom.to_owned(),
                        file: path.to_owned(),
                        unit: unit.clone(),
                        qual: qual.clone(),
                        line: Some(call.line),
                        callee: callee.clone(),
                        certain: true,
                        arg: None,
                    },
                );
            }
        }
    }
    tracing::info!(added, "typed-receiver capability uses added");
}

fn observe(cx: &Cx<'_>) -> Uses {
    let edges: Vec<_> = cx
        .graph
        .edges_with_status()
        .iter()
        .filter(|e| is_open_call(e))
        .collect();
    let mut calls_in: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for e in &edges {
        if let Some(t) = &e.text {
            calls_in
                .entry(e.from.path().to_owned())
                .or_default()
                .insert(callee_of(t).to_owned());
        }
    }
    let empty = BTreeSet::new();
    let mut sources: BTreeMap<String, Option<String>> = BTreeMap::new();
    let mut uses = Uses::default();
    let mut vocabs: BTreeMap<String, Vec<(&str, BTreeSet<&str>)>> = BTreeMap::new();
    // A name-only call carries one edge per same-named method: judge the site once.
    let mut judged: BTreeSet<(String, Option<u32>, String)> = BTreeSet::new();
    for e in &edges {
        let Some(text) = &e.text else { continue };
        let path = e.from.path();
        if e.to.is_some() && !judged.insert((e.from.to_string(), e.line, text.clone())) {
            continue;
        }
        // Code no selector reaches has no units: its calls sit in the file unit.
        let from = if cx.owners.units.contains_key(&e.from.to_string()) {
            e.from.to_string()
        } else {
            gob_symbols::Symref::file(path).to_string()
        };
        let Some(owner) = owner_of_use(cx, &from, path) else {
            continue;
        };
        let callee = callee_of(text);
        let Some(code) = cx.code.file(path) else {
            continue;
        };
        let file_calls = calls_in.get(path).unwrap_or(&empty);
        // A cut-off callee text cannot be split; fall back to the spelled method name.
        let spelled;
        let callee = if callee.ends_with("...") {
            spelled = format!("?.{}", e.name.as_deref().unwrap_or(""));
            spelled.as_str()
        } else {
            callee
        };
        let mut is_path = |recv: &str| {
            code.language == "python"
                && sources
                    .entry(path.to_owned())
                    .or_insert_with(|| code.source())
                    .as_deref()
                    .is_some_and(|src| pytype::is_path_expr(src, recv, 0))
        };
        let vocab = vocabs
            .entry(code.language.clone())
            .or_insert_with(|| vocabularies(&code.language, cx.packs));
        for Hit { atom, certain } in
            atoms_of(vocab, &code.language, callee, file_calls, &mut is_path)
        {
            let u = Use {
                atom,
                file: path.to_owned(),
                unit: from.clone(),
                qual: match e.from.target() {
                    Target::Symbol(segs) => segs.clone(),
                    _ => Vec::new(),
                },
                line: e.line,
                callee: callee.to_owned(),
                certain,
                arg: None,
            };
            route(&mut uses, &owner, u);
        }
    }
    scan_resolved(cx, &mut uses);
    scan_typed_receivers(cx, &mut uses);
    refine_open_modes(cx, &mut uses);
    attach_args(cx, &mut uses);
    tracing::info!(
        must_nodes = uses.lo.len(),
        may_nodes = uses.hi.len(),
        unowned = uses.unowned.len(),
        unseen = uses.unseen.len(),
        "capability uses observed"
    );
    uses
}

/// True when `sel` covers the unit a use sits in, or an enclosing symbol of it.
fn selects_use(sel: &gob_walk::Selector, u: &Use) -> bool {
    selects_unit_or_enclosing(sel, &u.file, &u.qual)
}

/// The first token of a shell string, or `None` when it holds a shell metacharacter and so may run
/// something else.
fn shell_program(cmd: &str) -> Option<String> {
    if cmd.contains([';', '|', '&', '$', '`', '<', '>', '(', ')', '\n']) {
        return None;
    }
    cmd.split_whitespace().next().map(str::to_owned)
}

/// The host pattern text of an observed `(host, port)` pair, bracketing an IPv6 host.
fn host_port(host: &str, port: Option<&str>) -> String {
    let host = if host.contains(':') && !host.starts_with('[') {
        format!("[{host}]")
    } else {
        host.to_owned()
    };
    match port {
        Some(p) => format!("{host}:{p}"),
        None => host,
    }
}

/// The argument a call passes, as the string `judge` compares, for an atom of `kind`.
fn observed_arg(kind: ArgKind, call: &gob_symbols::CallArgs) -> Option<String> {
    use gob_symbols::ArgValue;
    let first = call.args.first()?.as_ref()?;
    match (kind, first) {
        (ArgKind::Path | ArgKind::EnvName | ArgKind::Host, ArgValue::Str(s)) => Some(s.clone()),
        (ArgKind::Binary, ArgValue::Str(s)) => shell_program(s),
        (ArgKind::Binary, ArgValue::Seq(v)) => v.first().cloned().flatten(),
        (ArgKind::Host, ArgValue::Seq(v)) if v.len() == 2 => {
            let host = v[0].as_deref()?;
            Some(host_port(host, v[1].as_deref()))
        }
        _ => None,
    }
}

/// True when the vocabulary entry reaches the call through a receiver, so the first call argument
/// is not the path, name or program the atom is about (`Path.read_text`, `.read_text`).
fn receiver_entry(callee: &str) -> bool {
    callee.starts_with("Path.")
        || callee.starts_with('.')
        || callee.starts_with("?.")
        || is_typed_name(callee)
}

/// Fill `Use::arg` for the uses an argument-scoped grant could judge: parse each file once and
/// match a use to the one call on its line with the same last callee segment. An ambiguous line
/// (two such calls with different arguments), a missing call or an unfoldable argument leaves
/// `None`. Does nothing when no grant carries arguments.
fn attach_args(cx: &Cx<'_>, uses: &mut Uses) {
    let scoped = cx
        .model
        .entities
        .values()
        .any(|e| e.grants.iter().any(|g| !g.args.is_empty()));
    if !scoped {
        return;
    }
    let mut parsed: BTreeMap<String, BTreeMap<(u32, String), Vec<gob_symbols::CallArgs>>> =
        BTreeMap::new();
    let (mut known, mut unknown) = (0usize, 0usize);
    for u in uses.lo.values_mut().chain(uses.hi.values_mut()).flatten() {
        let Some(kind) = arg_kind(&u.atom) else {
            continue;
        };
        let Some(line) = u.line else { continue };
        if kind != ArgKind::Host && receiver_entry(&u.callee) {
            unknown += 1;
            continue;
        }
        let Some(code) = cx.code.file(&u.file) else {
            continue;
        };
        let calls = parsed.entry(u.file.clone()).or_insert_with(|| {
            let mut m: BTreeMap<(u32, String), Vec<gob_symbols::CallArgs>> = BTreeMap::new();
            if let Some(src) = code.source() {
                for c in gob_symbols::call_args(&code.language, &src) {
                    m.entry((c.line, last_segment(&c.callee).to_owned()))
                        .or_default()
                        .push(c);
                }
            }
            m
        });
        let Some(cands) = calls.get(&(line, last_segment(&u.callee).to_owned())) else {
            unknown += 1;
            continue;
        };
        let vals: BTreeSet<Option<String>> = cands.iter().map(|c| observed_arg(kind, c)).collect();
        if vals.len() == 1 {
            u.arg = vals.into_iter().next().flatten();
        }
        if u.arg.is_some() {
            known += 1;
        } else {
            unknown += 1;
        }
    }
    tracing::info!(known, unknown, "call arguments attached to uses");
}

/// What the mode argument of a Python `open` says.
#[derive(Debug, PartialEq, Eq)]
enum OpenMode {
    /// Read only (no mode, or a literal without `w`, `a`, `x` or `+`).
    Read,
    /// A literal mode that writes; `reads` when it also reads (`r+`, `w+`).
    Write { reads: bool },
    /// A mode that does not fold: it may write.
    Unknown,
}

/// Classify the mode of the `open` call `c`; a receiver form (`Path.open`) takes the mode first.
fn open_mode(c: &gob_symbols::CallArgs, receiver: bool) -> OpenMode {
    use gob_symbols::ArgValue;
    let slot = usize::from(!receiver);
    let given = match c.kwargs.get("mode") {
        Some(v) => Some(v),
        None => c.args.get(slot),
    };
    match given {
        None => OpenMode::Read,
        Some(Some(ArgValue::Str(m))) => {
            let plus = m.contains('+');
            if plus || m.contains(['w', 'a', 'x']) {
                OpenMode::Write {
                    reads: plus || m.contains('r'),
                }
            } else {
                OpenMode::Read
            }
        }
        Some(_) => OpenMode::Unknown,
    }
}

/// Make a Python `open` mode-aware (ticket 01M4HYH9CDNJSYEZQGKRZA7WX2): `open(p, 'w')` is `fs.write` and no longer
/// `fs.read` (unless the mode also reads), and a mode that is not a literal adds a May `fs.write`
/// beside the read. A use whose call cannot be found on its line stays a plain read.
fn refine_open_modes(cx: &Cx<'_>, uses: &mut Uses) {
    let mut parsed: BTreeMap<String, BTreeMap<(u32, String), Vec<gob_symbols::CallArgs>>> =
        BTreeMap::new();
    let (mut writes, mut mays) = (0usize, 0usize);
    let mut refine = |bucket: &mut Vec<Use>| -> Vec<Use> {
        let mut added = Vec::new();
        bucket.retain(|u| {
            if u.atom != "fs.read" || last_segment(&u.callee) != "open" {
                return true;
            }
            let (Some(line), Some(code)) = (u.line, cx.code.file(&u.file)) else {
                return true;
            };
            if code.language != "python" {
                return true;
            }
            let calls = parsed.entry(u.file.clone()).or_insert_with(|| {
                let mut m: BTreeMap<(u32, String), Vec<gob_symbols::CallArgs>> = BTreeMap::new();
                if let Some(src) = code.source() {
                    for c in gob_symbols::call_args(&code.language, &src) {
                        m.entry((c.line, last_segment(&c.callee).to_owned()))
                            .or_default()
                            .push(c);
                    }
                }
                m
            });
            let Some(cands) = calls.get(&(line, "open".to_owned())) else {
                return true;
            };
            let receiver = !matches!(u.callee.as_str(), "open" | "io.open" | "codecs.open");
            let modes: Vec<OpenMode> = cands.iter().map(|c| open_mode(c, receiver)).collect();
            let mode = match modes.as_slice() {
                [only] => only,
                _ => &OpenMode::Unknown,
            };
            match mode {
                OpenMode::Read => true,
                OpenMode::Write { reads } => {
                    writes += 1;
                    tracing::debug!(file = %u.file, line, callee = %u.callee, reads, "open mode writes: fs.write");
                    added.push(Use { atom: "fs.write".to_owned(), ..u.clone() });
                    *reads
                }
                OpenMode::Unknown => {
                    mays += 1;
                    tracing::debug!(file = %u.file, line, callee = %u.callee, "open mode not a literal: May fs.write");
                    added.push(Use { atom: "fs.write".to_owned(), certain: false, ..u.clone() });
                    true
                }
            }
        });
        added
    };
    let mut to_hi: Vec<(String, Use)> = Vec::new();
    for (node, bucket) in &mut uses.lo {
        for u in refine(bucket) {
            if u.certain {
                bucket.push(u);
            } else {
                to_hi.push((node.clone(), u));
            }
        }
    }
    for bucket in uses.hi.values_mut() {
        let add = refine(bucket);
        bucket.extend(add);
    }
    let extra = refine(&mut uses.unowned);
    uses.unowned.extend(extra);
    for (node, u) in to_hi {
        uses.hi.entry(node).or_default().push(u);
    }
    tracing::info!(writes, mays, "open modes refined");
}

/// How the grants of a node judge one use.
#[derive(Clone, Debug, PartialEq, Eq)]
enum Coverage {
    /// No grant names the atom in the use's unit.
    Uncovered,
    /// A grant with no arguments, or an argument the use satisfies.
    Covered,
    /// Argument-scoped grants cover the atom and unit, but the observed argument matches none.
    Mismatch {
        observed: String,
        granted: Vec<String>,
    },
    /// Argument-scoped grants cover the atom and unit and the argument is not statically known.
    Unknown { granted: Vec<String> },
}

/// The `Judgement` of the use against one argument-scoped grant: any grant argument that matches
/// is `Match`; otherwise `Unknown` if any could not be decided or the use has no folded argument.
fn judge_use(grant: &Grant, atom: &str, u: &Use) -> Judgement {
    let (Some(kind), Some(obs)) = (arg_kind(atom), u.arg.as_deref()) else {
        return Judgement::Unknown;
    };
    let mut out = Judgement::NoMatch;
    for a in &grant.args {
        match judge(kind, a, obs) {
            Judgement::Match => return Judgement::Match,
            Judgement::Unknown => out = Judgement::Unknown,
            Judgement::NoMatch => {}
        }
    }
    out
}

/// Fold the grants of a node into one `Coverage` of the use `u` of `atom`.
fn coverage(grants: &[Grant], atom: &str, u: &Use) -> Coverage {
    let mut granted: Vec<String> = Vec::new();
    let mut unknown = false;
    for g in grants.iter().filter(|g| covers(g, atom, u)) {
        if g.args.is_empty() {
            return Coverage::Covered;
        }
        match judge_use(g, atom, u) {
            Judgement::Match => return Coverage::Covered,
            Judgement::Unknown => unknown = true,
            Judgement::NoMatch => {}
        }
        granted.extend(g.args.iter().cloned());
    }
    if granted.is_empty() {
        return Coverage::Uncovered;
    }
    match (&u.arg, unknown) {
        (Some(observed), false) => Coverage::Mismatch {
            observed: observed.clone(),
            granted,
        },
        _ => Coverage::Unknown { granted },
    }
}

/// True when `grant` covers the use `u` of `atom` (the atom itself or its parent) in its unit,
/// whatever its arguments say.
fn covers(grant: &Grant, atom: &str, u: &Use) -> bool {
    let granted = gob_ir::registry::canonical(&grant.atom).unwrap_or(&grant.atom);
    let named = granted == atom
        || atom
            .strip_prefix(granted)
            .is_some_and(|rest| rest.starts_with('.'));
    named && grant.at.as_ref().is_none_or(|sel| selects_use(sel, u))
}

fn list(uses: &[&Use]) -> String {
    let mut s = uses
        .iter()
        .take(EXAMPLES)
        .map(|u| u.site())
        .collect::<Vec<_>>()
        .join("; ");
    if uses.len() > EXAMPLES {
        let _ = write!(s, " (+{} more)", uses.len() - EXAMPLES);
    }
    s
}

/// The `(node anchor, atom, file)` triples the capability matrix marks `undeclared` (or `unknown`:
/// the callee vocabulary matched but no registry detector row exists, e.g. a pack atom) from the
/// certain uses in Must-owned code. Coverage is decided per use site (binding.md 7.2 item 3): a
/// grant that covers the atom in one unit never masks the same atom used in another unit. The
/// third element is the use's unit (its from-symbol), not its file.
fn matrix_undeclared(cx: &Cx<'_>, uses: &Uses) -> BTreeSet<(String, String, String)> {
    let mut out = BTreeSet::new();
    for e in cx
        .model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node && !e.external && e.owns_code())
    {
        let Some(found) = uses.lo.get(&e.anchor) else {
            continue;
        };
        // One matrix input per (file, language) of the node's used code, so each use is judged
        // against the grants that cover it at its own file.
        let mut inputs: BTreeMap<(&str, &str), NodeInput> = BTreeMap::new();
        for u in found.iter().filter(|u| u.certain) {
            let Some(lang) = cx.code.file(&u.file).map(|c| c.language.as_str()) else {
                continue;
            };
            let input = inputs
                .entry((u.unit.as_str(), lang))
                .or_insert_with(|| NodeInput {
                    node: e.anchor.clone(),
                    lang: lang.to_owned(),
                    ..NodeInput::default()
                });
            input.uses.insert(u.atom.clone());
            // An argument-scoped grant that names the atom keeps the cell declared; CAP001
            // judges its argument separately.
            if coverage(&e.grants, &u.atom, u) != Coverage::Uncovered {
                input.grants.insert(u.atom.clone());
            }
        }
        for ((unit, _), input) in inputs {
            let atoms: Vec<String> = input.uses.iter().cloned().collect();
            let atoms: Vec<&str> = atoms.iter().map(String::as_str).collect();
            let matrix = grimble_capabilities::build(&[input], &atoms);
            for (atom, cell) in matrix.cells.values().flatten() {
                if matches!(cell, Cell::Undeclared | Cell::Unknown) {
                    out.insert((e.anchor.clone(), atom.clone(), unit.to_owned()));
                }
            }
        }
    }
    tracing::debug!(cells = out.len(), "matrix undeclared cells");
    out
}

/// Argument findings keyed by (atom, observed argument or None when unfolded, granted arguments).
type ByArg<'a> = BTreeMap<(&'a str, Option<String>, Vec<String>), Vec<&'a Use>>;

#[allow(clippy::too_many_lines)] // one pass per node: exact, argument and may findings together
fn cap001(cx: &Cx<'_>, uses: &Uses, today: gob_time::Day, out: &mut Output) {
    let undeclared = matrix_undeclared(cx, uses);
    for e in cx
        .model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node && !e.external && e.owns_code())
    {
        let site = Some((e.file.as_str(), (e.span.start, e.span.end)));
        out.count("CAP001", 1);
        for (set, must) in [(&uses.lo, true), (&uses.hi, false)] {
            let Some(found) = set.get(&e.anchor) else {
                continue;
            };
            // (atom, receiver unresolved) -> uses; an unresolved receiver is a May use.
            let mut by_atom: BTreeMap<(&str, bool), Vec<&Use>> = BTreeMap::new();
            // argument findings: (atom, observed, granted) -> uses; observed None is unfolded
            let mut by_arg: ByArg<'_> = BTreeMap::new();
            for u in found {
                if crate::model::silenced(e, "CAP001", &u.atom, today) {
                    continue;
                }
                match coverage(&e.grants, &u.atom, u) {
                    Coverage::Covered => {}
                    Coverage::Mismatch { observed, granted } => by_arg
                        .entry((u.atom.as_str(), Some(observed), granted))
                        .or_default()
                        .push(u),
                    Coverage::Unknown { granted } => by_arg
                        .entry((u.atom.as_str(), None, granted))
                        .or_default()
                        .push(u),
                    Coverage::Uncovered => {
                        let flagged = !(must && u.certain)
                            || undeclared.contains(&(
                                e.anchor.clone(),
                                u.atom.clone(),
                                u.unit.clone(),
                            ));
                        if flagged {
                            by_atom
                                .entry((u.atom.as_str(), !u.certain))
                                .or_default()
                                .push(u);
                        }
                    }
                }
            }
            for ((atom, observed, granted), us) in by_arg {
                let allowed = granted
                    .iter()
                    .map(|a| format!("{a:?}"))
                    .collect::<Vec<_>>()
                    .join(", ");
                match observed {
                    Some(obs) if must && us.iter().all(|u| u.certain) => {
                        let anchor = format!("cap/{}/{atom}", e.anchor);
                        out.fire(
                            "CAP001",
                            Severity::Error,
                            format!(
                                "`{}` uses `{atom}` with argument {obs:?}, outside every granted argument ({allowed}) ({} use(s)): {}",
                                e.anchor,
                                us.len(),
                                list(&us)
                            ),
                            &anchor,
                            site,
                        );
                    }
                    Some(obs) => {
                        let anchor = format!("cap/{}/{atom}/arg", e.anchor);
                        out.unresolved(
                            "CAP001",
                            Reason::MayOnlyOwner,
                            &format!(
                                "`{atom}` may be used by `{}` with argument {obs:?}, outside every granted argument ({allowed}); the use is not certain Must-owned code: {}",
                                e.anchor,
                                list(&us)
                            ),
                            &anchor,
                            site,
                        );
                    }
                    None => {
                        let anchor = format!("cap/{}/{atom}/arg", e.anchor);
                        out.unresolved(
                            "CAP001",
                            Reason::UnresolvedEdge,
                            &format!(
                                "`{atom}` is used by `{}` with an argument that cannot be resolved statically, so the granted arguments ({allowed}) cannot be checked: {}",
                                e.anchor,
                                list(&us)
                            ),
                            &anchor,
                            site,
                        );
                    }
                }
            }
            for ((atom, unresolved_receiver), us) in by_atom {
                if must && !unresolved_receiver {
                    let anchor = format!("cap/{}/{atom}", e.anchor);
                    out.fire(
                        "CAP001",
                        Severity::Error,
                        format!(
                            "`{}` uses `{atom}` with no grant ({} use(s)): {}",
                            e.anchor,
                            us.len(),
                            list(&us)
                        ),
                        &anchor,
                        site,
                    );
                } else if unresolved_receiver {
                    let anchor = format!("cap/{}/{atom}/receiver", e.anchor);
                    out.unresolved(
                        "CAP001",
                        Reason::UnresolvedEdge,
                        &format!(
                            "`{atom}` may be used by `{}` with no grant; the receiver type of the call could not be resolved: {}",
                            e.anchor,
                            list(&us)
                        ),
                        &anchor,
                        site,
                    );
                } else {
                    let anchor = format!("cap/{}/{atom}", e.anchor);
                    out.unresolved(
                        "CAP001",
                        Reason::MayOnlyOwner,
                        &format!(
                            "`{atom}` may be used by `{}` with no grant; the code is owned only at May: {}",
                            e.anchor,
                            list(&us)
                        ),
                        &anchor,
                        site,
                    );
                }
            }
        }
    }
}

/// CAP001 for code no node owns: an implicit node with no grants, so every observed use is denied.
///
/// A certain use in `Foreign` code is an Error; an unresolved receiver, or code whose owner is
/// hidden (an unseen remainder), is Unresolved, never silent. Frob-owned and `[check] exclude`d
/// files are not in the walk of uses (see `owner_of_use`).
fn cap001_unowned(uses: &Uses, out: &mut Output) {
    out.count("CAP001", 1);
    // (atom, receiver unresolved, owner hidden) -> uses
    let mut by_atom: BTreeMap<(&str, bool, bool), Vec<&Use>> = BTreeMap::new();
    for (set, hidden) in [(&uses.unowned, false), (&uses.unseen, true)] {
        for u in set {
            by_atom
                .entry((u.atom.as_str(), !u.certain, hidden))
                .or_default()
                .push(u);
        }
    }
    for ((atom, unresolved_receiver, hidden), us) in by_atom {
        if !unresolved_receiver && !hidden {
            let anchor = format!("cap/unowned/{atom}");
            out.fire(
                "CAP001",
                Severity::Error,
                format!(
                    "unowned code uses `{atom}`; no node owns it, so nothing grants it ({} use(s)): {}",
                    us.len(),
                    list(&us)
                ),
                &anchor,
                None,
            );
        } else if hidden {
            let anchor = format!("cap/unowned/{atom}/hidden");
            out.unresolved(
                "CAP001",
                Reason::UnseenRemainder,
                &format!(
                    "`{atom}` is used in code whose owner cannot be named (unseen remainder): {}",
                    list(&us)
                ),
                &anchor,
                None,
            );
        } else {
            let anchor = format!("cap/unowned/{atom}/receiver");
            out.unresolved(
                "CAP001",
                Reason::UnresolvedEdge,
                &format!(
                    "`{atom}` may be used by unowned code, which has no grant; the receiver type of the call could not be resolved: {}",
                    list(&us)
                ),
                &anchor,
                None,
            );
        }
    }
}

/// The atoms a grant of `granted` covers: itself and its children, registered or declared by a pack.
fn expansion(granted: &str, packs: &BTreeMap<String, PackPin>) -> Vec<String> {
    atoms()
        .into_iter()
        .map(|a| a.name)
        .chain(
            packs
                .values()
                .flat_map(|p| p.atoms.iter().map(String::as_str)),
        )
        .filter(|n| *n == granted || n.strip_prefix(granted).is_some_and(|r| r.starts_with('.')))
        .map(str::to_owned)
        .collect()
}

/// How the enabled packs answer `(atom, lang)`: `Some(kind)` for a real row, `None` for no row.
///
/// A `callee` row wins over `impossible` (PACK004 reports the clash); `none` rows are no row.
fn pack_answer(
    packs: &BTreeMap<String, PackPin>,
    atom: &str,
    lang: &str,
) -> Option<PackDetectorKind> {
    let kinds: BTreeSet<PackDetectorKind> = packs
        .values()
        .flat_map(|p| p.detectors.iter())
        .filter(|d| d.atom == atom && d.lang == lang && d.kind != PackDetectorKind::None)
        .map(|d| d.kind)
        .collect();
    if kinds.contains(&PackDetectorKind::Callee) {
        Some(PackDetectorKind::Callee)
    } else {
        kinds.into_iter().next()
    }
}

/// True when another pack atom is a child of `atom` (`db` over `db.query`): it has no row of its own.
fn is_pack_parent(packs: &BTreeMap<String, PackPin>, atom: &str) -> bool {
    packs
        .values()
        .flat_map(|p| p.atoms.iter())
        .any(|n| n.strip_prefix(atom).is_some_and(|r| r.starts_with('.')))
}

/// True when `atom` is declared by an enabled pack rather than the shared registry.
fn is_pack_atom(packs: &BTreeMap<String, PackPin>, atom: &str) -> bool {
    !atom_registered(atom) && packs.values().any(|p| p.atoms.contains(atom))
}

fn atom_registered(atom: &str) -> bool {
    gob_ir::registry::atom(atom).is_some()
}

/// One Unresolved per node, pack atom and language for a granted pack atom that no enabled pack
/// has a detector for, in the languages of the node's files within the grant's scope.
fn report_no_detector(
    cx: &Cx<'_>,
    e: &crate::model::Entity,
    atoms: &[String],
    files: &[&str],
    reported: &mut BTreeSet<(String, String)>,
    site: Option<(&str, (usize, usize))>,
    out: &mut Output,
) {
    for a in atoms
        .iter()
        .filter(|a| is_pack_atom(cx.packs, a) && !is_pack_parent(cx.packs, a))
    {
        let mut no_detector: BTreeSet<&str> = BTreeSet::new();
        for f in files {
            let Some(lang) = cx.code.file(f).map(|c| c.language.as_str()) else {
                continue;
            };
            if lang != crate::code::OPAQUE && pack_answer(cx.packs, a, lang).is_none() {
                no_detector.insert(lang);
            }
        }
        for lang in no_detector {
            if !reported.insert((a.clone(), lang.to_owned())) {
                continue;
            }
            tracing::warn!(node = %e.anchor, atom = %a, lang, "pack atom has no detector for the language; not enforced");
            out.unresolved(
                "CAP002",
                Reason::Fidelity,
                &format!(
                    "`{a}` is granted to `{}` but no pack detector covers it in {lang} (no-detector); its use in {lang} code is not enforced",
                    e.anchor
                ),
                &format!("cap/{}/{a}/{lang}/no-detector", e.anchor),
                site,
            );
        }
    }
}

fn cap002(cx: &Cx<'_>, uses: &Uses, today: gob_time::Day, out: &mut Output) {
    for e in cx
        .model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node && !e.external && e.owns_code())
    {
        // A node without grants is still a subject: its cells are all `denied`, nothing to judge.
        out.count("CAP002", usize::from(e.grants.is_empty()));
        // The files of every unit the node owns, and whether any unit is only possibly its.
        let mut files: BTreeSet<&str> = BTreeSet::new();
        let mut may_owned = false;
        for uo in cx.owners.units.values() {
            match &uo.merged.owner {
                Owner::Must(n) if n.as_str() == e.anchor => {
                    files.insert(uo.file.as_str());
                }
                Owner::May(ns) if ns.iter().any(|n| n.as_str() == e.anchor) => may_owned = true,
                _ => {}
            }
        }
        let langs: BTreeSet<&str> = files
            .iter()
            .filter_map(|f| cx.code.file(f))
            .map(|f| f.language.as_str())
            .collect();
        let unseen = files
            .iter()
            .filter_map(|f| cx.code.file(f))
            .any(CodeFile::has_unseen);
        let mut reported: BTreeSet<(String, String)> = BTreeSet::new();
        for g in &e.grants {
            out.count("CAP002", 1);
            let site = Some((g.file.as_str(), (g.span.start, g.span.end)));
            let atoms = expansion(
                gob_ir::registry::canonical(&g.atom).unwrap_or(&g.atom),
                cx.packs,
            );
            if atoms.is_empty() || files.is_empty() {
                tracing::debug!(node = %e.anchor, atom = %g.atom, "grant has no detectable atom or no owned code; not judged");
                continue;
            }
            // Scope in units: a file is in scope when the selector may reach it; a use is in
            // scope when its own unit (or an enclosing one) is selected.
            let in_scope = |f: &str| {
                g.at.as_ref().is_none_or(|sel| {
                    gob_walk::select_files(sel, &cx.code.walk)
                        .iter()
                        .any(|m| m.path == f)
                })
            };
            let use_in_scope = |u: &Use| g.at.as_ref().is_none_or(|sel| selects_use(sel, u));
            let scoped: Vec<&str> = files.iter().copied().filter(|f| in_scope(f)).collect();
            report_no_detector(cx, e, &atoms, &scoped, &mut reported, site, out);
            let observed = [&uses.lo, &uses.hi].iter().any(|by_node| {
                by_node.get(&e.anchor).is_some_and(|us| {
                    us.iter()
                        .any(|u| atoms.contains(&u.atom) && use_in_scope(u))
                })
            });
            if observed {
                continue;
            }
            let covered = atoms.iter().all(|a| {
                langs.iter().all(|l| {
                    if is_pack_atom(cx.packs, a) {
                        return is_pack_parent(cx.packs, a)
                            || pack_answer(cx.packs, a, l).is_some();
                    }
                    match detectors(a, l) {
                        Answer::Exact(kinds) => !kinds.contains(&DetectorKind::Lexical),
                        Answer::NotApplicable => true,
                        _ => false,
                    }
                })
            });
            if may_owned || unseen || !covered {
                tracing::debug!(node = %e.anchor, atom = %g.atom, may_owned, unseen, covered, "grant not judged: absence is not Exact");
                continue;
            }
            if crate::model::silenced(e, "CAP002", &g.atom, today) {
                continue;
            }
            out.fire(
                "CAP002",
                Severity::Error,
                format!(
                    "`{}` grants `{}` but no use of it is observed in the code it owns",
                    e.anchor, g.written
                ),
                &format!("cap/{}/{}", e.anchor, g.atom),
                site,
            );
        }
    }
}

/// Evaluate CAP001 and CAP002 over the observed uses and the node grants.
pub fn evaluate(cx: &Cx<'_>, out: &mut Output) {
    let uses = observe(cx);
    let today = gob_time::Clock::today(&gob_time::SystemClock::pin());
    cap001(cx, &uses, today, out);
    cap001_unowned(&uses, out);
    cap002(cx, &uses, today, out);
    tracing::info!(
        cap001 = out.subjects.get("CAP001").copied().unwrap_or(0),
        cap002 = out.subjects.get("CAP002").copied().unwrap_or(0),
        "CAP rules evaluated"
    );
}
