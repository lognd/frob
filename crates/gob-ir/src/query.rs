//! The syntactic queries of Theorem 2 as a library (universal-model.md 4.3 and 5).
//!
//! Every query is total and polynomial in the term. Queries whose subject is an
//! `opaque` or `hole` node answer [`Answer::Unknown`] (nothing is computed
//! through them), except the lexical ones that read an opaque payload.

use std::collections::{BTreeSet, HashMap};

use crate::answer::Answer;
use crate::digest::{DIGEST_SCHEME, Digest, Facet, FacetDigest};
use crate::location::Location;
use crate::operator::{Operator, Sort, Universal};
use crate::scope::{Resolution, ScopeGraph};
use crate::symref::{Anchor, Identity, Symref, SymrefError};
use crate::term::{NodeId, Term};

/// A unit part and the symref of the identity it belongs to.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UnitInfo {
    /// The `unit` or `anon` node.
    pub node: NodeId,
    /// The identity's symref (shared by all parts of a multi-part unit).
    pub symref: Symref,
}

/// A binder (abstractor variable) in scope at a node.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BinderRef {
    /// The node whose abstractor binds the variable.
    pub owner: NodeId,
    /// Position in the owner's abstractor.
    pub index: usize,
    /// The variable's external name.
    pub name: String,
}

/// How a name occurs.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OccurrenceKind {
    /// A `ref` use.
    Use,
    /// An abstractor variable.
    Binder,
    /// A unit's declared name.
    Decl,
}

/// One occurrence of a name.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Occurrence {
    /// The node carrying the occurrence.
    pub node: NodeId,
    /// How the name occurs.
    pub kind: OccurrenceKind,
}

/// The answer to `resolve_symref` (query Q22) within one term.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SymrefLookup {
    /// One identity; the vector holds its parts in document order.
    One(Vec<NodeId>),
    /// No unit has this symref.
    NotFound,
}

impl Term {
    /// The operator of a node (Q06).
    pub fn operator(&self, id: NodeId) -> &Operator {
        &self.node(id).op
    }

    /// The sort of a node.
    pub fn sort(&self, id: NodeId) -> Sort {
        self.node(id).op.sort()
    }

    /// The parent (Q27).
    pub fn parent(&self, id: NodeId) -> Option<NodeId> {
        self.node(id).parent
    }

    /// The children in order (Q27).
    pub fn children(&self, id: NodeId) -> &[NodeId] {
        &self.node(id).children
    }

    /// The other children of the parent, in order.
    pub fn siblings(&self, id: NodeId) -> Vec<NodeId> {
        self.parent(id)
            .map(|p| {
                self.children(p)
                    .iter()
                    .copied()
                    .filter(|&c| c != id)
                    .collect()
            })
            .unwrap_or_default()
    }

    /// Ancestors, innermost first (Q27).
    pub fn ancestors(&self, id: NodeId) -> Vec<NodeId> {
        let mut out = Vec::new();
        let mut cur = self.parent(id);
        while let Some(p) = cur {
            out.push(p);
            cur = self.parent(p);
        }
        out
    }

    /// Descendants in preorder, excluding `id`.
    pub fn descendants(&self, id: NodeId) -> Vec<NodeId> {
        let mut out = Vec::new();
        let mut stack: Vec<NodeId> = self.children(id).iter().rev().copied().collect();
        while let Some(n) = stack.pop() {
            out.push(n);
            stack.extend(self.children(n).iter().rev());
        }
        out
    }

    /// Whether `a` is a proper ancestor of `b`.
    pub fn is_ancestor(&self, a: NodeId, b: NodeId) -> bool {
        self.ancestors(b).contains(&a)
    }

    /// Every `unit` and `anon` node with its symref, in document (preorder) order (Q04).
    pub fn units(&self) -> Vec<UnitInfo> {
        let mut out = Vec::new();
        let mut stack = vec![self.root()];
        while let Some(n) = stack.pop() {
            if let Some(s) = self.symref_of(n) {
                out.push(UnitInfo {
                    node: n,
                    symref: s.clone(),
                });
            }
            stack.extend(self.children(n).iter().rev());
        }
        out
    }

    /// Find the parts of the identity spelled `symref` (Q22, exact spelling only).
    pub fn find_unit(&self, symref: &Symref) -> SymrefLookup {
        let parts: Vec<NodeId> = self
            .units()
            .into_iter()
            .filter(|u| &u.symref == symref)
            .map(|u| u.node)
            .collect();
        if parts.is_empty() {
            SymrefLookup::NotFound
        } else {
            SymrefLookup::One(parts)
        }
    }

    /// Parse and find a symref given as text.
    ///
    /// # Errors
    ///
    /// Returns the parse error when `text` is not a symref.
    pub fn resolve_symref(&self, text: &str) -> Result<SymrefLookup, SymrefError> {
        Ok(self.find_unit(&text.parse()?))
    }

    /// Binders in scope at `id`, innermost first (Q20 lexical part); `Unknown` on opaque or hole.
    ///
    /// # Panics
    ///
    /// Never for terms built by [`crate::TermBuilder`]; a panic means a corrupted parent link.
    pub fn binders_in_scope(&self, id: NodeId) -> Answer<Vec<BinderRef>> {
        let n = self.node(id);
        if n.op.is_opaque() || n.op.is_hole() {
            return Answer::Unknown;
        }
        let mut out = Vec::new();
        let mut child = id;
        while let Some(p) = self.parent(child) {
            let pn = self.node(p);
            let idx = pn
                .children
                .iter()
                .position(|&c| c == child)
                .expect("child of its parent");
            if pn.op.binds_over(idx) {
                for (i, b) in pn.binders.iter().enumerate().rev() {
                    out.push(BinderRef {
                        owner: p,
                        index: i,
                        name: b.clone(),
                    });
                }
            }
            child = p;
        }
        Answer::Exact(out)
    }

    /// Free variables of the subterm at `id` (names of `ref`s not bound inside it).
    // frob:ticket 01M3Z8NVCBM9KXN5ZY97QWX8P1
    pub fn free_vars(&self, id: NodeId) -> BTreeSet<String> {
        /// Pending work of the explicit-stack walk.
        enum Task<'a> {
            Visit(NodeId),
            Bind(&'a [String]),
            Unbind(&'a [String]),
        }
        let mut out = BTreeSet::new();
        let mut bound: HashMap<&str, usize> = HashMap::new();
        let mut work = vec![Task::Visit(id)];
        while let Some(task) = work.pop() {
            match task {
                Task::Bind(names) => {
                    for n in names {
                        *bound.entry(n.as_str()).or_default() += 1;
                    }
                }
                Task::Unbind(names) => {
                    for n in names {
                        if let Some(c) = bound.get_mut(n.as_str()) {
                            *c -= 1;
                        }
                    }
                }
                Task::Visit(id) => {
                    let n = self.node(id);
                    if let Operator::Universal(Universal::Ref { name }) = &n.op
                        && bound.get(name.as_str()).is_none_or(|c| *c == 0)
                    {
                        out.insert(name.clone());
                    }
                    for (i, &c) in n.children.iter().enumerate().rev() {
                        let scoped = n.op.binds_over(i) && !n.binders.is_empty();
                        if scoped {
                            work.push(Task::Unbind(&n.binders));
                        }
                        work.push(Task::Visit(c));
                        if scoped {
                            work.push(Task::Bind(&n.binders));
                        }
                    }
                }
            }
        }
        out
    }

    /// Occurrences of `name` as use, binder or unit declaration (Q13), in arena order.
    pub fn occurrences(&self, name: &str) -> Vec<Occurrence> {
        let mut out = Vec::new();
        for id in self.ids() {
            let n = self.node(id);
            if let Operator::Universal(Universal::Ref { name: r }) = &n.op
                && r == name
            {
                out.push(Occurrence {
                    node: id,
                    kind: OccurrenceKind::Use,
                });
            }
            if n.binders.iter().any(|b| b == name) {
                out.push(Occurrence {
                    node: id,
                    kind: OccurrenceKind::Binder,
                });
            }
            if n.name.as_deref() == Some(name) {
                out.push(Occurrence {
                    node: id,
                    kind: OccurrenceKind::Decl,
                });
            }
        }
        out
    }

    /// Attributes and comments attached to `id` (Q08, Q10), in order.
    pub fn attachments(&self, id: NodeId) -> Vec<NodeId> {
        self.children(id)
            .iter()
            .copied()
            .filter(|&c| self.node(c).op.is_attachment())
            .collect()
    }

    /// Comments attached to `id`.
    pub fn comments(&self, id: NodeId) -> Vec<NodeId> {
        self.attachments(id)
            .into_iter()
            .filter(|&c| {
                matches!(
                    self.node(c).op,
                    Operator::Universal(Universal::Comment { .. })
                )
            })
            .collect()
    }

    /// `opaque` nodes under (or at) `id`, in preorder (Q17).
    pub fn opaque_regions(&self, id: NodeId) -> Vec<NodeId> {
        std::iter::once(id)
            .chain(self.descendants(id))
            .filter(|&n| self.node(n).op.is_opaque())
            .collect()
    }

    /// The raw payload of an opaque node: lexical queries read it (Q03).
    pub fn payload(&self, id: NodeId) -> Option<&[u8]> {
        match &self.node(id).op {
            Operator::Universal(Universal::Opaque { payload, .. }) => Some(payload),
            _ => None,
        }
    }

    /// `(kind, lexeme)` of every literal under `id` (Q14).
    pub fn literals(&self, id: NodeId) -> Vec<(String, String)> {
        std::iter::once(id)
            .chain(self.descendants(id))
            .filter_map(|n| match &self.node(n).op {
                Operator::Universal(Universal::Lit { kind, lexeme }) => {
                    Some((kind.clone(), lexeme.clone()))
                }
                _ => None,
            })
            .collect()
    }

    /// The deepest node whose location contains `loc`, if any (Q05).
    pub fn node_at(&self, loc: &Location) -> Option<NodeId> {
        let mut cur = self.root();
        if !self.node(cur).location.contains(loc) {
            return None;
        }
        'down: loop {
            for &c in self.children(cur) {
                if self.node(c).location.contains(loc) {
                    cur = c;
                    continue 'down;
                }
            }
            return Some(cur);
        }
    }

    /// The innermost unit-like node containing `loc` (Q05 `enclosing`).
    pub fn enclosing_unit_at(&self, loc: &Location) -> Option<NodeId> {
        let n = self.node_at(loc)?;
        std::iter::once(n)
            .chain(self.ancestors(n))
            .find(|&a| self.node(a).op.is_unit_like())
    }

    /// All nodes ordered by location, then by id (location ordering query).
    pub fn nodes_by_location(&self) -> Vec<NodeId> {
        let mut v: Vec<NodeId> = self.ids().collect();
        v.sort_by(|&a, &b| {
            self.node(a)
                .location
                .cmp(&self.node(b).location)
                .then(a.cmp(&b))
        });
        v
    }

    /// Units whose facet digest equals `d` (Q42).
    pub fn by_digest(&self, facet: Facet, d: &Digest) -> Vec<NodeId> {
        self.units()
            .into_iter()
            .filter(|u| self.facet_digest(u.node, facet) == FacetDigest::Exact(*d))
            .map(|u| u.node)
            .collect()
    }

    /// The facet digest of a whole identity: the part digest, or a combination of the parts'
    /// digests in document order for a multi-part unit. `Unknown` if any part is `Unknown`.
    pub fn identity_facet_digest(&self, symref: &Symref, facet: Facet) -> FacetDigest {
        let SymrefLookup::One(parts) = self.find_unit(symref) else {
            return FacetDigest::Absent;
        };
        let mut digests = Vec::new();
        for p in parts {
            match self.facet_digest(p, facet) {
                FacetDigest::Unknown => return FacetDigest::Unknown,
                FacetDigest::Absent => {}
                FacetDigest::Exact(d) => digests.push(d),
            }
        }
        match digests.as_slice() {
            [] => FacetDigest::Absent,
            [one] => FacetDigest::Exact(*one),
            many => FacetDigest::Exact(Digest::combine(
                &format!("gob-ir/{DIGEST_SCHEME}/parts/{}", facet.name()),
                many,
            )),
        }
    }
}

/// A term together with its scope graph: the unit of analysis.
#[derive(Debug, Clone)]
pub struct Model {
    term: Term,
    scopes: ScopeGraph,
}

impl Model {
    /// Pair a term with an adapter-built scope graph.
    pub fn new(term: Term, scopes: ScopeGraph) -> Self {
        Self { term, scopes }
    }

    /// Derive the lexical scope graph from the term's binders.
    pub fn lexical(term: Term) -> Self {
        let scopes = ScopeGraph::from_term(&term);
        Self { term, scopes }
    }

    /// The term.
    pub fn term(&self) -> &Term {
        &self.term
    }

    /// The scope graph.
    pub fn scopes(&self) -> &ScopeGraph {
        &self.scopes
    }

    /// Resolve the `ref` node `node`; `Unknown` for any other node.
    pub fn resolve_node(&self, node: NodeId) -> Resolution {
        self.scopes
            .ref_at(node)
            .map_or(Resolution::Unknown, |r| self.scopes.resolve(r))
    }

    /// The identity of a unit part: its symref anchor with the Body digest as content.
    pub fn identity(&self, unit: NodeId) -> Option<Identity> {
        let sym = self.term.symref_of(unit)?.clone();
        let content = match self.term.facet_digest(unit, Facet::Body) {
            FacetDigest::Exact(d) => Some(d),
            _ => None,
        };
        Some(Identity::new(Anchor::Symref(sym), content))
    }

    /// The graph digest over the whole term and scope graph.
    pub fn graph_digest(&self) -> Digest {
        self.term.graph_digest(&self.scopes)
    }
}
