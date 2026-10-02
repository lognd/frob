//! Arena-allocated sorted abstract binding trees (universal-model.md 2.1).
//!
//! Terms are built bottom-up with [`TermBuilder`]; a child must exist before its
//! parent, so a node id is also a topological index. Bound variables are the
//! `binders` of a node (named externally); the printer turns them into de Bruijn
//! levels, so alpha-equivalent terms print identically.

use std::fmt;
use std::sync::Arc;

use tracing::{debug, trace};

use crate::attrs::{Attributes, reserved};
use crate::location::Location;
use crate::operator::{Operator, Universal};
use crate::symref::{Segment, Symref};

/// Index of a node in its term's arena.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct NodeId(pub(crate) u32);

impl NodeId {
    /// The arena index.
    pub const fn index(self) -> usize {
        self.0 as usize
    }
}

impl fmt::Display for NodeId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "n{}", self.0)
    }
}

/// A construction error; all are programmer bugs in an adapter.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum TermError {
    /// The operator does not accept this number of children.
    #[error("operator `{op}` takes {expected} children, got {got}")]
    Arity {
        /// Operator tag.
        op: String,
        /// Human description of the accepted arity.
        expected: &'static str,
        /// Children supplied.
        got: usize,
    },
    /// Abstractors on an operator that cannot bind.
    #[error("operator `{0}` cannot carry binders")]
    BindersNotAllowed(String),
    /// A declared name on an operator that has none.
    #[error("operator `{0}` cannot carry a declared name")]
    NameNotAllowed(String),
    /// A child id does not exist.
    #[error("child {0} does not exist")]
    NoSuchChild(NodeId),
    /// A node was given two parents.
    #[error("node {0} already has a parent")]
    AlreadyParented(NodeId),
    /// A node other than the root has no parent.
    #[error("node {0} is not reachable from the root")]
    Orphan(NodeId),
    /// The root id does not exist.
    #[error("root {0} does not exist")]
    NoSuchRoot(NodeId),
}

/// One node of a term.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Node {
    pub(crate) op: Operator,
    pub(crate) name: Option<String>,
    pub(crate) binders: Vec<String>,
    pub(crate) children: Vec<NodeId>,
    pub(crate) parent: Option<NodeId>,
    pub(crate) location: Location,
    pub(crate) lang: Arc<str>,
    pub(crate) lang_param: Option<String>,
    pub(crate) attrs: Attributes,
}

impl Node {
    /// The operator.
    pub fn op(&self) -> &Operator {
        &self.op
    }
    /// The declared name of a unit, part of its identity (not an abstractor).
    pub fn name(&self) -> Option<&str> {
        self.name.as_deref()
    }
    /// Names of the bound variables of this node's abstractor.
    pub fn binders(&self) -> &[String] {
        &self.binders
    }
    /// Child ids in order.
    pub fn children(&self) -> &[NodeId] {
        &self.children
    }
    /// The parent, `None` at the root.
    pub fn parent(&self) -> Option<NodeId> {
        self.parent
    }
    /// The node's location.
    pub fn location(&self) -> &Location {
        &self.location
    }
    /// The language tag.
    pub fn lang(&self) -> &str {
        &self.lang
    }
    /// The language parameter (edition, `#lang`, pragma).
    pub fn lang_param(&self) -> Option<&str> {
        self.lang_param.as_deref()
    }
    /// The carried attributes.
    pub fn attrs(&self) -> &Attributes {
        &self.attrs
    }
}

/// A description of a node to add; see [`TermBuilder::node`].
#[derive(Debug, Clone)]
pub struct NodeSpec {
    op: Operator,
    location: Location,
    name: Option<String>,
    binders: Vec<String>,
    lang: Option<Arc<str>>,
    lang_param: Option<String>,
    attrs: Attributes,
}

impl NodeSpec {
    /// A spec with an operator and a location.
    pub fn new(op: Operator, location: Location) -> Self {
        Self {
            op,
            location,
            name: None,
            binders: Vec::new(),
            lang: None,
            lang_param: None,
            attrs: Attributes::default(),
        }
    }
    /// Declare the unit's name.
    #[must_use]
    pub fn named(mut self, name: &str) -> Self {
        self.name = Some(name.to_owned());
        self
    }
    /// Add abstractor variables.
    #[must_use]
    pub fn binders(mut self, names: &[&str]) -> Self {
        self.binders = names.iter().map(|s| (*s).to_owned()).collect();
        self
    }
    /// Override the language tag (an embedded island).
    #[must_use]
    pub fn lang(mut self, lang: &str) -> Self {
        self.lang = Some(lang.into());
        self
    }
    /// Set the language parameter.
    #[must_use]
    pub fn lang_param(mut self, p: &str) -> Self {
        self.lang_param = Some(p.to_owned());
        self
    }
    /// Set one attribute.
    #[must_use]
    pub fn attr(mut self, key: &str, value: impl Into<crate::attrs::AttrValue>) -> Self {
        self.attrs.set(key, value);
        self
    }
}

/// Builds a [`Term`] bottom-up.
#[derive(Debug)]
pub struct TermBuilder {
    locator: String,
    lang: Arc<str>,
    nodes: Vec<Node>,
}

fn arity_check(op: &Operator, got: usize) -> Result<(), TermError> {
    let (ok, expected) = match op {
        Operator::Universal(
            Universal::Ref { .. }
            | Universal::Lit { .. }
            | Universal::Comment { .. }
            | Universal::Hole { .. }
            | Universal::Opaque { .. },
        ) => (got == 0, "0"),
        Operator::Universal(Universal::Apply { .. }) => (got >= 1, "at least 1 (the head)"),
        Operator::Universal(Universal::Bind { .. } | Universal::Phase { .. }) => {
            ((1..=2).contains(&got), "1 or 2")
        }
        _ => (true, "any"),
    };
    if ok {
        Ok(())
    } else {
        Err(TermError::Arity {
            op: op.tag(),
            expected,
            got,
        })
    }
}

impl TermBuilder {
    /// Start a term for the artifact named by `locator` whose default language is `lang`.
    pub fn new(locator: &str, lang: &str) -> Self {
        Self {
            locator: locator.to_owned(),
            lang: lang.into(),
            nodes: Vec::new(),
        }
    }

    /// Add a node over already-built `children`.
    ///
    /// # Errors
    ///
    /// Returns [`TermError`] on an arity violation, binders or a name on an
    /// operator that cannot carry them, a missing child, or a child that already
    /// has a parent.
    pub fn node(&mut self, spec: NodeSpec, children: &[NodeId]) -> Result<NodeId, TermError> {
        arity_check(&spec.op, children.len())?;
        if !spec.binders.is_empty() && !spec.op.may_bind() {
            return Err(TermError::BindersNotAllowed(spec.op.tag()));
        }
        if spec.name.is_some()
            && !matches!(
                spec.op,
                Operator::Universal(Universal::Unit { .. }) | Operator::Adapter(_)
            )
        {
            return Err(TermError::NameNotAllowed(spec.op.tag()));
        }
        for &c in children {
            match self.nodes.get(c.index()) {
                None => return Err(TermError::NoSuchChild(c)),
                Some(n) if n.parent.is_some() => return Err(TermError::AlreadyParented(c)),
                Some(_) => {}
            }
        }
        let id = NodeId(crate::idx32(self.nodes.len()));
        for &c in children {
            self.nodes[c.index()].parent = Some(id);
        }
        trace!(node = %id, op = %spec.op, children = children.len(), "term node added");
        self.nodes.push(Node {
            op: spec.op,
            name: spec.name,
            binders: spec.binders,
            children: children.to_vec(),
            parent: None,
            location: spec.location,
            lang: spec.lang.unwrap_or_else(|| Arc::clone(&self.lang)),
            lang_param: spec.lang_param,
            attrs: spec.attrs,
        });
        Ok(id)
    }

    /// Seal the term at `root`.
    ///
    /// # Errors
    ///
    /// Returns [`TermError::NoSuchRoot`] or [`TermError::Orphan`] when the
    /// nodes do not form a single tree under `root`.
    pub fn finish(self, root: NodeId) -> Result<Term, TermError> {
        if root.index() >= self.nodes.len() {
            return Err(TermError::NoSuchRoot(root));
        }
        for (i, n) in self.nodes.iter().enumerate() {
            if n.parent.is_none() && i != root.index() {
                return Err(TermError::Orphan(NodeId(crate::idx32(i))));
            }
        }
        let mut term = Term {
            locator: self.locator,
            nodes: self.nodes,
            root,
            symrefs: Vec::new(),
        };
        term.symrefs = compute_symrefs(&term);
        debug!(nodes = term.len(), locator = %term.locator, "term sealed");
        Ok(term)
    }
}

/// A sealed term: an arena of nodes under one root.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Term {
    locator: String,
    nodes: Vec<Node>,
    root: NodeId,
    symrefs: Vec<Option<Symref>>,
}

fn compute_symrefs(term: &Term) -> Vec<Option<Symref>> {
    fn walk(term: &Term, id: NodeId, base: &Symref, counter: &mut u32, out: &mut [Option<Symref>]) {
        let node = term.node(id);
        let own = match &node.op {
            Operator::Universal(Universal::Unit { .. }) => Some(match &node.name {
                Some(n) => base.child(Segment::Name {
                    name: n.clone(),
                    qualifier: node.attrs.get_str(reserved::QUALIFIER).map(str::to_owned),
                }),
                None => base.clone(),
            }),
            Operator::Universal(Universal::Anon { .. }) => {
                let i = *counter;
                *counter += 1;
                Some(base.child(Segment::Anon(i)))
            }
            _ => None,
        };
        match own {
            Some(sym) => {
                out[id.index()] = Some(sym.clone());
                let mut inner = 0;
                for &c in &node.children {
                    walk(term, c, &sym, &mut inner, out);
                }
            }
            None => {
                for &c in &node.children {
                    walk(term, c, base, counter, out);
                }
            }
        }
    }
    let mut out = vec![None; term.nodes.len()];
    let base = Symref::locator_only(term.locator.clone());
    let mut counter = 0;
    walk(term, term.root, &base, &mut counter, &mut out);
    out
}

impl Term {
    /// The artifact locator the term's symrefs are rooted at.
    pub fn locator(&self) -> &str {
        &self.locator
    }
    /// The root node.
    pub fn root(&self) -> NodeId {
        self.root
    }
    /// Number of nodes.
    pub fn len(&self) -> usize {
        self.nodes.len()
    }
    /// A sealed term always has a root, so this is always false.
    pub fn is_empty(&self) -> bool {
        self.nodes.is_empty()
    }
    /// The node with id `id`.
    ///
    /// # Panics
    ///
    /// Panics if `id` came from a different term (a programmer bug).
    pub fn node(&self, id: NodeId) -> &Node {
        &self.nodes[id.index()]
    }
    /// Every node id in arena (children-before-parent) order.
    pub fn ids(&self) -> impl Iterator<Item = NodeId> + use<> {
        let n = crate::idx32(self.nodes.len());
        (0..n).map(NodeId)
    }
    /// The symref of a `unit` or `anon` node; `None` for every other node.
    pub fn symref_of(&self, id: NodeId) -> Option<&Symref> {
        self.symrefs[id.index()].as_ref()
    }
}
