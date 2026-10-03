//! The compatibility view: [`SymbolRecord`]s computed from a U term.
//!
//! `SymbolRecord` is the `unit` view of a term (universal-model.md 8): one record
//! per named `unit`, with digests read from the canonical facet stream of
//! gob-ir, spans from node locations and containment from term ancestry.

// frob:ticket 01M3Z713F6VY15YSMS15033RN1

use std::collections::HashMap;
use std::fmt::Write as _;

use gob_ir::{Digest, Facet, FacetDigest as IrFacet, NodeId, Operator, Segment, Term, Universal};

use crate::adapter::ParseStatus;
use crate::model::{
    Digests, FacetDigest, MethodSig, RetType, SelfKind, SymbolKind, SymbolRecord, UnitExtras,
    Visibility,
};
use crate::symref::Symref;

/// Attribute key holding a unit's visibility (`public`, `crate`, `private`).
pub(crate) const ATTR_VISIBILITY: &str = "visibility";
/// Attribute key holding the trait text of an impl member.
pub(crate) const ATTR_IMPLEMENTS: &str = "implements";
/// Unit attribute: the `self` kind of a function (`none`, `ref`, `refmut`, `value`).
pub(crate) const ATTR_SELF_KIND: &str = "self_kind";
/// Unit attribute: the parameter count of a function, `self` excluded.
pub(crate) const ATTR_ARITY: &str = "arity";
/// Unit attribute: the plain head of a function's declared return type.
pub(crate) const ATTR_RET: &str = "ret";
/// Unit attribute: the plain first generic argument of a function's declared return type.
pub(crate) const ATTR_RET_ARG: &str = "ret_arg";
/// Unit attribute: the plain second generic argument of a function's declared return type.
pub(crate) const ATTR_RET_ARG2: &str = "ret_arg2";
/// Unit attribute: the element types of a tuple return type, comma-separated, `_` for an untyped element.
pub(crate) const ATTR_RET_TUPLE: &str = "ret_tuple";
/// Attribute key holding the slug of a markdown section's parent section.
pub(crate) const ATTR_SECTION_PARENT: &str = "section.parent";
/// Hole kind of a syntax error.
pub(crate) const HOLE_PARSE_ERROR: &str = "parse-error";
/// Hole kind of a token the parser inserted.
pub(crate) const HOLE_MISSING: &str = "missing";

/// How legacy symrefs are spelled for a term.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Naming {
    /// `path::Type.member`, impls as `Type[Trait]`.
    Rust,
    /// `path#slug`.
    Markdown,
    /// Model entities: `path::name`, kinds from the entity keyword.
    Model,
    /// Only the file node exists.
    Opaque,
}

/// The records computed from one term.
#[derive(Debug, Default)]
pub(crate) struct View {
    /// One record per named unit, in document order.
    pub symbols: Vec<SymbolRecord>,
    /// Extra facts, parallel to `symbols`.
    pub extras: Vec<UnitExtras>,
    /// The record symref of every unit node (the root maps to the file symref).
    pub by_node: HashMap<NodeId, Symref>,
}

/// The `parse_status` query (G11): holes of kind parse-error or missing in the term.
pub(crate) fn parse_status_of(term: &Term) -> ParseStatus {
    let holes = term
        .ids()
        .filter(|&n| {
            matches!(
                term.node(n).op(),
                Operator::Universal(Universal::Hole { kind })
                    if kind == HOLE_PARSE_ERROR || kind == HOLE_MISSING
            )
        })
        .count();
    if holes == 0 {
        ParseStatus::Complete
    } else {
        ParseStatus::Partial {
            holes: u32::try_from(holes).unwrap_or(u32::MAX),
        }
    }
}

fn convert(d: Digest) -> FacetDigest {
    FacetDigest::from_bytes(*d.as_bytes())
}

/// Digest of one facet; `Absent` digests the empty string, `Unknown` the partial print.
fn facet(term: &Term, node: NodeId, f: Facet, unknown: &mut Vec<String>) -> FacetDigest {
    match term.facet_digest(node, f) {
        IrFacet::Exact(d) => convert(d),
        IrFacet::Absent => FacetDigest::of(b""),
        IrFacet::Unknown => {
            unknown.push(f.name().to_owned());
            let partial = term.print_alpha(node);
            FacetDigest::of(format!("unknown:{}:{partial}", f.name()).as_bytes())
        }
    }
}

fn kind_of(naming: Naming, kind: &str) -> SymbolKind {
    match (naming, kind) {
        (Naming::Markdown, _) => SymbolKind::Heading,
        (Naming::Model, "node") => SymbolKind::Node,
        (Naming::Model, "flow") => SymbolKind::Flow,
        (Naming::Model, "contract") => SymbolKind::Contract,
        (Naming::Model, "claim") => SymbolKind::Claim,
        (Naming::Model, "vmodel") => SymbolKind::VModel,
        (Naming::Model, "pack") => SymbolKind::Pack,
        (Naming::Model, "boundary") => SymbolKind::Boundary,
        (_, "function") => SymbolKind::Function,
        (_, "method") => SymbolKind::Method,
        (_, "struct") => SymbolKind::Struct,
        (_, "enum") => SymbolKind::Enum,
        (_, "variant") => SymbolKind::Variant,
        (_, "trait") => SymbolKind::Trait,
        (_, "impl") => SymbolKind::Impl,
        (_, "const") => SymbolKind::Const,
        (_, "static") => SymbolKind::Static,
        (_, "type") => SymbolKind::TypeAlias,
        (_, "macro") => SymbolKind::Macro,
        _ => SymbolKind::Module,
    }
}

fn visibility_of(term: &Term, n: NodeId, naming: Naming) -> Visibility {
    match term.node(n).attrs().get_str(ATTR_VISIBILITY) {
        Some("public") => Visibility::Public,
        Some("crate") => Visibility::Crate,
        None if naming == Naming::Markdown => Visibility::Public,
        Some(_) | None => Visibility::Private,
    }
}

fn seg_text(seg: &Segment) -> String {
    seg.to_string()
}

fn seg_name(seg: &Segment) -> String {
    match seg {
        Segment::Name { name, .. } => name.clone(),
        Segment::Anon(i) => format!("{{{i}}}"),
    }
}

fn span_of(term: &Term, n: NodeId) -> gob_text::TextRange {
    match term.node(n).location() {
        gob_ir::Location::Text { range, .. } => *range,
        _ => gob_text::TextRange::empty(gob_text::TextSize::new(0)),
    }
}

/// Nearest ancestor of `n` that is a named unit (not the root).
fn unit_parent(term: &Term, n: NodeId) -> Option<NodeId> {
    let mut cur = term.parent(n);
    while let Some(p) = cur {
        if p != term.root()
            && matches!(
                term.operator(p),
                Operator::Universal(Universal::Unit { .. })
            )
        {
            return Some(p);
        }
        cur = term.parent(p);
    }
    None
}

struct Pending {
    node: NodeId,
    kind: String,
    segs: Vec<String>,
    parent: Option<NodeId>,
    implements: Option<String>,
}

/// The named units of `term` with their legacy segments (before disambiguation).
fn collect_pending(term: &Term, naming: Naming) -> Vec<Pending> {
    let mut base: HashMap<NodeId, Vec<String>> = HashMap::new();
    let mut pending: Vec<Pending> = Vec::new();
    for info in term.units() {
        let n = info.node;
        if n == term.root() {
            continue;
        }
        let Operator::Universal(Universal::Unit { kind, .. }) = term.operator(n) else {
            continue;
        };
        let node = term.node(n);
        let Some(seg) = info.symref.qual().last() else {
            continue;
        };
        let parent = unit_parent(term, n);
        let parent_base: Vec<String> = parent
            .and_then(|p| base.get(&p).cloned())
            .unwrap_or_default();
        let mut full = parent_base.clone();
        full.push(seg_text(seg));
        let mut b = parent_base;
        if kind == "impl" {
            b.push(seg_name(seg));
        } else {
            b.clone_from(&full);
        }
        base.insert(n, b);
        pending.push(Pending {
            node: n,
            kind: kind.clone(),
            segs: full,
            parent,
            implements: node.attrs().get_str(ATTR_IMPLEMENTS).map(str::to_owned),
        });
    }
    // Member of an impl: `Type.m`, from the base of the impl. Rewrite segs for members.
    let impl_nodes: std::collections::HashSet<NodeId> = pending
        .iter()
        .filter(|p| p.kind == "impl")
        .map(|p| p.node)
        .collect();
    for p in &mut pending {
        if naming == Naming::Rust
            && let Some(par) = p.parent
            && impl_nodes.contains(&par)
        {
            let mut segs = base[&par].clone();
            if let Some(seg) = term.symref_of(p.node).and_then(|s| s.qual().last()) {
                segs.push(seg_text(seg));
            }
            p.segs = segs;
        }
    }
    pending
}

/// The calling shape recorded on a function unit, if any.
fn signature_of(term: &Term, n: NodeId) -> Option<MethodSig> {
    let attrs = term.node(n).attrs();
    let self_kind = SelfKind::from_attr(attrs.get_str(ATTR_SELF_KIND)?)?;
    let arity = attrs.get_str(ATTR_ARITY)?.parse().ok()?;
    let ret = attrs.get_str(ATTR_RET).map(|head| RetType {
        head: head.to_owned(),
        arg: attrs.get_str(ATTR_RET_ARG).map(str::to_owned),
        arg2: attrs.get_str(ATTR_RET_ARG2).map(str::to_owned),
        tuple: attrs.get_str(ATTR_RET_TUPLE).map(|t| {
            t.split(',')
                .map(|e| (e != "_").then(|| e.to_owned()))
                .collect()
        }),
    });
    Some(MethodSig {
        self_kind,
        arity,
        ret,
    })
}

/// Computes the view of `term` for `path`.
pub(crate) fn build(term: &Term, path: &str, naming: Naming) -> View {
    let mut view = View::default();
    view.by_node.insert(term.root(), Symref::file(path));
    if naming == Naming::Opaque {
        return view;
    }
    let mut pending = collect_pending(term, naming);
    let symrefs = disambiguate(path, naming, &mut pending, term);
    let final_of: HashMap<NodeId, Symref> = pending
        .iter()
        .zip(&symrefs)
        .map(|(p, s)| (p.node, s.clone()))
        .collect();
    for (p, symref) in pending.iter().zip(symrefs) {
        let n = p.node;
        let mut unknown = Vec::new();
        let digests = Digests {
            sig: facet(term, n, Facet::Sig, &mut unknown),
            body: facet(term, n, Facet::Body, &mut unknown),
            doc: facet(term, n, Facet::Doc, &mut unknown),
            attr: facet(term, n, Facet::Attr, &mut unknown),
            contract: facet(term, n, Facet::Contract, &mut unknown),
        };
        let parent = match naming {
            Naming::Markdown => term
                .node(n)
                .attrs()
                .get_str(ATTR_SECTION_PARENT)
                .map(|s| Symref::anchor(path, s)),
            _ => p.parent.and_then(|q| final_of.get(&q).cloned()),
        };
        view.by_node.insert(n, symref.clone());
        view.extras.push(UnitExtras {
            symref: symref.clone(),
            unknown,
            subtree: None,
        });
        view.symbols.push(SymbolRecord {
            symref,
            kind: kind_of(naming, &p.kind),
            span: span_of(term, n),
            visibility: visibility_of(term, n, naming),
            digests,
            parent,
            implements: p.implements.clone(),
            signature: signature_of(term, n),
        });
    }
    match naming {
        Naming::Rust => patch_impl_visibility(&mut view.symbols),
        Naming::Markdown => subtree_digests(&mut view),
        Naming::Model | Naming::Opaque => {}
    }
    view
}

/// Turns segments into unique symrefs: colliding trait-impl members become
/// `Type[Trait].m`, remaining collisions get a `[dupN]` suffix.
fn disambiguate(path: &str, naming: Naming, pending: &mut [Pending], term: &Term) -> Vec<Symref> {
    if naming == Naming::Markdown {
        return pending
            .iter()
            .map(|p| {
                let name = term
                    .symref_of(p.node)
                    .and_then(|s| s.qual().last())
                    .map(seg_name)
                    .unwrap_or_default();
                Symref::anchor(path, &name)
            })
            .collect();
    }
    let mut counts: HashMap<Vec<String>, usize> = HashMap::new();
    for p in pending.iter() {
        *counts.entry(p.segs.clone()).or_default() += 1;
    }
    for p in pending.iter_mut() {
        let n = p.segs.len();
        if counts[&p.segs] > 1
            && p.kind != "impl"
            && let Some(tr) = &p.implements
            && n >= 2
        {
            p.segs[n - 2] = format!("{}[{tr}]", p.segs[n - 2]);
        }
    }
    let mut seen: HashMap<Vec<String>, usize> = HashMap::new();
    pending
        .iter()
        .map(|p| {
            let mut segs = p.segs.clone();
            let c = seen.entry(segs.clone()).or_default();
            *c += 1;
            if *c > 1
                && let Some(last) = segs.last_mut()
            {
                let _ = write!(last, "[dup{c}]");
            }
            Symref::symbol(path, segs)
        })
        .collect()
}

/// Impl blocks take the visibility of the target type when it is defined in this
/// file; otherwise the block is public.
fn patch_impl_visibility(symbols: &mut [SymbolRecord]) {
    let types: HashMap<Vec<String>, Visibility> = symbols
        .iter()
        .filter(|s| {
            matches!(
                s.kind,
                SymbolKind::Struct | SymbolKind::Enum | SymbolKind::TypeAlias | SymbolKind::Trait
            )
        })
        .map(|s| (s.symref.segments().to_vec(), s.visibility))
        .collect();
    for s in symbols.iter_mut().filter(|s| s.kind == SymbolKind::Impl) {
        let mut segs = s.symref.segments().to_vec();
        if let Some(last) = segs.last_mut()
            && let Some((ty, _)) = last.split_once('[')
        {
            *last = ty.to_owned();
        }
        s.visibility = types.get(&segs).copied().unwrap_or(Visibility::Public);
    }
}

/// Fills `UnitExtras::subtree` for markdown sections (G9): sig, own body and the
/// subtrees of the sections whose parent attribute names this one, in order.
fn subtree_digests(view: &mut View) {
    let index: HashMap<Symref, usize> = view
        .symbols
        .iter()
        .enumerate()
        .map(|(i, s)| (s.symref.clone(), i))
        .collect();
    let mut kids: Vec<Vec<usize>> = vec![Vec::new(); view.symbols.len()];
    for (i, s) in view.symbols.iter().enumerate() {
        if let Some(p) = s.parent.as_ref().and_then(|p| index.get(p)) {
            kids[*p].push(i);
        }
    }
    let mut memo: Vec<Option<FacetDigest>> = vec![None; view.symbols.len()];
    // Children always follow their parent in document order, so a reverse sweep
    // sees every child before its parent.
    for i in (0..view.symbols.len()).rev() {
        let s = &view.symbols[i];
        let mut h = blake3::Hasher::new();
        h.update(b"gob-symbols/subtree/1");
        h.update(s.digests.sig.as_bytes());
        h.update(s.digests.body.as_bytes());
        for &k in &kids[i] {
            if let Some(d) = memo[k] {
                h.update(d.as_bytes());
            }
        }
        memo[i] = Some(FacetDigest::from_bytes(*h.finalize().as_bytes()));
    }
    for (e, m) in view.extras.iter_mut().zip(memo) {
        e.subtree = m;
    }
}

/// The entity symbols of a model term for `path`, with their extras, in document order.
///
/// For adapters (grimble-model) whose units are model entities rather than code items.
pub fn model_symbols(term: &Term, path: &str) -> (Vec<SymbolRecord>, Vec<UnitExtras>) {
    let v = build(term, path, Naming::Model);
    tracing::debug!(path, symbols = v.symbols.len(), "model symbol view");
    (v.symbols, v.extras)
}
