//! The alpha-normal printer and the canonical facet stream (universal-model.md 7.1).
//!
//! A term prints as an s-expression in which bound variables are de Bruijn
//! levels (`#k`) and free variables are quoted names, so alpha-equivalent
//! terms print byte-identically. Facet digests are BLAKE3 over a facet's
//! printed stream with trivia excluded and literals exact. The printer
//! walks the term with an explicit work stack, so term depth is bounded by memory, not by
//! the thread stack (Theorem 1, totality).

use std::collections::HashMap;
use std::fmt::Write as _;

use tracing::trace;

use crate::attrs::{AttrValue, reserved};
use crate::digest::{DIGEST_SCHEME, Digest, Facet, FacetDigest};
use crate::operator::{Operator, Universal};
use crate::scope::ScopeGraph;
use crate::term::{Node, NodeId, Term};

/// What the printer includes.
#[allow(clippy::struct_excessive_bools, reason = "independent print switches")]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PrintOpts {
    /// Print `comment` nodes.
    pub trivia: bool,
    /// Print carried attribute maps.
    pub attrs: bool,
    /// Print locations.
    pub locations: bool,
    /// Erase declared names and free-variable names (contract rendering).
    pub erase_names: bool,
    /// Skip `attr("doc")` nodes (they have their own facet).
    pub skip_docs: bool,
}

impl PrintOpts {
    /// The full print: everything, used for the graph digest.
    pub const FULL: Self = Self {
        trivia: true,
        attrs: true,
        locations: true,
        erase_names: false,
        skip_docs: false,
    };
    /// The alpha-normal print: structure and trivia, no attributes or locations.
    pub const ALPHA: Self = Self {
        trivia: true,
        attrs: false,
        locations: false,
        erase_names: false,
        skip_docs: false,
    };
    const FACET: Self = Self {
        trivia: false,
        attrs: false,
        locations: false,
        erase_names: false,
        skip_docs: true,
    };
}

/// A facet's canonical stream.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FacetStream {
    /// The unit has no such facet.
    Absent,
    /// The stream contains a hole.
    Unknown,
    /// The canonical stream text.
    Stream(String),
}

fn esc_into(out: &mut String, s: &str) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            ' '..='~' => out.push(c),
            _ => {
                let _ = write!(out, "\\u{{{:x}}}", c as u32);
            }
        }
    }
    out.push('"');
}

fn bytes_into(out: &mut String, b: &[u8]) {
    out.push_str("b\"");
    for &x in b {
        match x {
            b'"' => out.push_str("\\\""),
            b'\\' => out.push_str("\\\\"),
            b' '..=b'~' => out.push(x as char),
            _ => {
                let _ = write!(out, "\\x{x:02x}");
            }
        }
    }
    out.push('"');
}

fn value_into(out: &mut String, v: &AttrValue) {
    match v {
        AttrValue::Bool(b) => {
            let _ = write!(out, "{b}");
        }
        AttrValue::Int(i) => {
            let _ = write!(out, "{i}");
        }
        AttrValue::Str(s) => esc_into(out, s),
        AttrValue::List(items) => {
            out.push('[');
            for (i, it) in items.iter().enumerate() {
                if i > 0 {
                    out.push(' ');
                }
                value_into(out, it);
            }
            out.push(']');
        }
        AttrValue::Map(m) => {
            out.push('{');
            for (i, (k, it)) in m.iter().enumerate() {
                if i > 0 {
                    out.push(' ');
                }
                let _ = write!(out, "{k}=");
                value_into(out, it);
            }
            out.push('}');
        }
    }
}

fn attrs_into(out: &mut String, node: &Node) {
    let mut first = true;
    for (k, v) in node.attrs.user() {
        out.push_str(if first { " {" } else { " " });
        first = false;
        let _ = write!(out, "{k}=");
        value_into(out, v);
    }
    if !first {
        out.push('}');
    }
}

struct Printer<'a> {
    term: &'a Term,
    opts: PrintOpts,
    env: Vec<&'a str>,
    /// For each bound name, the indices (de Bruijn levels) at which it sits in `env`.
    levels: HashMap<&'a str, Vec<usize>>,
    out: String,
}

/// One unit of pending printer work.
enum Task<'a> {
    /// Print a node (preceded by a space when it is a child).
    Enter {
        id: NodeId,
        parent: Option<&'a Node>,
        space: bool,
    },
    /// Print the closing paren of a node.
    Close,
    /// Bring the binders of a node into scope.
    Bind(&'a Node),
    /// Drop the most recent `n` binders from scope.
    Unbind(usize),
}

impl<'a> Printer<'a> {
    fn new(term: &'a Term, opts: PrintOpts) -> Self {
        Self {
            term,
            opts,
            env: Vec::new(),
            levels: HashMap::new(),
            out: String::new(),
        }
    }

    fn bind(&mut self, name: &'a str) {
        self.levels.entry(name).or_default().push(self.env.len());
        self.env.push(name);
    }

    fn unbind(&mut self, n: usize) {
        for _ in 0..n {
            let name = self.env.pop().expect("balanced binders");
            if let Some(v) = self.levels.get_mut(name) {
                v.pop();
            }
        }
    }

    fn skipped(&self, node: &Node) -> bool {
        match &node.op {
            Operator::Universal(Universal::Comment { .. }) => !self.opts.trivia,
            Operator::Universal(Universal::Attr { name }) => self.opts.skip_docs && name == "doc",
            _ => false,
        }
    }

    /// Print `(tag params name binders`, without children or the closing paren.
    fn header(&mut self, node: &'a Node, parent: Option<&Node>) {
        let out = &mut self.out;
        out.push('(');
        out.push_str(&node.op.tag());
        match &node.op {
            Operator::Universal(u) => match u {
                Universal::Unit { kind, role } => {
                    out.push(' ');
                    esc_into(out, kind);
                    out.push(' ');
                    esc_into(out, role);
                }
                Universal::Anon { kind }
                | Universal::Apply { kind }
                | Universal::Region { kind }
                | Universal::Phase { kind }
                | Universal::Hole { kind } => {
                    out.push(' ');
                    esc_into(out, kind);
                }
                Universal::Ref { .. } => {}
                Universal::Bind { kind, mode } => {
                    out.push(' ');
                    esc_into(out, kind);
                    out.push(' ');
                    esc_into(out, mode);
                }
                Universal::Group { order } => {
                    out.push(' ');
                    esc_into(out, order.as_str());
                }
                Universal::Lit { kind, lexeme } => {
                    out.push(' ');
                    esc_into(out, kind);
                    out.push(' ');
                    esc_into(out, lexeme);
                }
                Universal::Attr { name } => {
                    out.push(' ');
                    esc_into(out, name);
                }
                Universal::Comment { text } => {
                    out.push(' ');
                    esc_into(out, text);
                }
                Universal::Opaque { reason, payload } => {
                    out.push(' ');
                    esc_into(out, reason);
                    out.push(' ');
                    bytes_into(out, payload);
                }
            },
            Operator::Adapter(_) => {}
        }
        let same_lang =
            parent.is_some_and(|p| p.lang == node.lang && p.lang_param == node.lang_param);
        if !same_lang {
            let _ = write!(out, " @{}", node.lang);
            if let Some(p) = &node.lang_param {
                out.push('~');
                esc_into(out, p);
            }
        }
        if !self.opts.erase_names {
            if let Some(n) = &node.name {
                out.push_str(" name=");
                esc_into(out, n);
            }
            if let Some(q) = node.attrs.get_str(reserved::QUALIFIER) {
                out.push_str(" q=");
                esc_into(out, q);
            }
        }
        if !node.binders.is_empty() {
            let _ = write!(out, " \\{}", node.binders.len());
        }
        if self.opts.attrs {
            attrs_into(out, node);
        }
        if self.opts.locations {
            let _ = write!(out, " @@{}", node.location);
        }
    }

    fn reference(&mut self, name: &str) {
        match self.levels.get(name).and_then(|v| v.last().copied()) {
            Some(level) => {
                let _ = write!(self.out, " #{level}");
            }
            None if self.opts.erase_names => self.out.push_str(" _"),
            None => {
                self.out.push(' ');
                esc_into(&mut self.out, name);
            }
        }
    }

    /// Print the subtree at `id` with an explicit work stack (no recursion over depth).
    // frob:ticket 01M3Z8NVCBM9KXN5ZY97QWX8P1
    fn node_with_parent(&mut self, id: NodeId, parent: Option<&'a Node>) {
        let term = self.term;
        let mut work = vec![Task::Enter {
            id,
            parent,
            space: false,
        }];
        while let Some(task) = work.pop() {
            match task {
                Task::Close => self.out.push(')'),
                Task::Bind(node) => {
                    for b in &node.binders {
                        self.bind(b);
                    }
                }
                Task::Unbind(n) => self.unbind(n),
                Task::Enter { id, parent, space } => {
                    let node = term.node(id);
                    if space {
                        self.out.push(' ');
                    }
                    self.header(node, parent);
                    if let Operator::Universal(Universal::Ref { name }) = &node.op {
                        self.reference(name);
                    }
                    work.push(Task::Close);
                    for (i, &c) in node.children.iter().enumerate().rev() {
                        let child = term.node(c);
                        if self.skipped(child) {
                            continue;
                        }
                        let bound = node.op.binds_over(i) && !node.binders.is_empty();
                        if bound {
                            work.push(Task::Unbind(node.binders.len()));
                        }
                        work.push(Task::Enter {
                            id: c,
                            parent: Some(node),
                            space: true,
                        });
                        if bound {
                            work.push(Task::Bind(node));
                        }
                    }
                }
            }
        }
    }
}

impl Term {
    /// Print `id` with explicit options; bound variables are levels relative to `id`.
    pub fn print_with(&self, id: NodeId, opts: PrintOpts) -> String {
        let mut p = Printer::new(self, opts);
        p.node_with_parent(id, None);
        trace!(node = %id, bytes = p.out.len(), "term printed");
        p.out
    }

    /// The alpha-normal print of `id` (structure and trivia; no attributes or locations).
    ///
    /// Alpha-equivalent terms print identically.
    pub fn print_alpha(&self, id: NodeId) -> String {
        self.print_with(id, PrintOpts::ALPHA)
    }

    /// Binder names in scope at `id`'s own position (outermost first), so facet streams use
    /// absolute de Bruijn levels and outer renames do not disturb inner digests.
    fn env_at(&self, id: NodeId) -> Vec<&str> {
        let mut chain = Vec::new();
        let mut child = id;
        while let Some(p) = self.parent(child) {
            let idx = self
                .children(p)
                .iter()
                .position(|&c| c == child)
                .expect("child of its parent");
            if self.node(p).op.binds_over(idx) {
                chain.push(p);
            }
            child = p;
        }
        chain
            .iter()
            .rev()
            .flat_map(|&p| self.node(p).binders.iter().map(String::as_str))
            .collect()
    }

    /// Whether any node at or under `id` satisfies `pred`; an explicit-stack preorder walk.
    fn any_under(&self, id: NodeId, pred: impl Fn(&Operator) -> bool) -> bool {
        let mut stack = vec![id];
        while let Some(n) = stack.pop() {
            let node = self.node(n);
            if pred(&node.op) {
                return true;
            }
            stack.extend(node.children.iter().rev());
        }
        false
    }

    fn has_hole(&self, id: NodeId) -> bool {
        self.any_under(id, Operator::is_hole)
    }

    fn has_hole_or_opaque(&self, id: NodeId) -> bool {
        self.any_under(id, |op| op.is_hole() || op.is_opaque())
    }

    /// The canonical stream of `facet` for the `unit` or `anon` node `unit` (query Q38).
    pub fn facet_stream(&self, unit: NodeId, facet: Facet) -> FacetStream {
        let node = self.node(unit);
        if !node.op.is_unit_like() {
            return FacetStream::Absent;
        }
        let part = |c: NodeId| classify(self.node(c));
        let selected: Vec<NodeId> = node
            .children
            .iter()
            .copied()
            .filter(|&c| match facet {
                Facet::Sig | Facet::Contract => part(c) == Part::Sig,
                Facet::Body => part(c) == Part::Body,
                Facet::Doc => part(c) == Part::Doc,
                Facet::Attr => part(c) == Part::Attr,
            })
            .collect();
        let has_attr_map = facet == Facet::Attr && node.attrs.user().next().is_some();
        if matches!(facet, Facet::Body | Facet::Doc | Facet::Attr)
            && selected.is_empty()
            && !has_attr_map
        {
            return FacetStream::Absent;
        }
        let unknown = match facet {
            Facet::Contract => selected.iter().any(|&c| self.has_hole_or_opaque(c)),
            _ => selected.iter().any(|&c| self.has_hole(c)),
        };
        if unknown {
            return FacetStream::Unknown;
        }
        let mut opts = PrintOpts::FACET;
        opts.erase_names = facet == Facet::Contract;
        if matches!(facet, Facet::Doc | Facet::Attr) {
            opts.skip_docs = false;
        }
        let mut p = Printer::new(self, opts);
        match facet {
            Facet::Sig | Facet::Contract => p.header(node, None),
            Facet::Body | Facet::Doc | Facet::Attr => {
                let _ = write!(p.out, "({}", facet.name());
                if has_attr_map {
                    attrs_into(&mut p.out, node);
                }
            }
        }
        for name in self.env_at(unit) {
            p.bind(name);
        }
        for b in &node.binders {
            p.bind(b);
        }
        for c in selected {
            p.out.push(' ');
            p.node_with_parent(c, Some(node));
        }
        p.out.push(')');
        FacetStream::Stream(p.out)
    }

    /// The digest of one facet of one unit part.
    pub fn facet_digest(&self, unit: NodeId, facet: Facet) -> FacetDigest {
        match self.facet_stream(unit, facet) {
            FacetStream::Absent => FacetDigest::Absent,
            FacetStream::Unknown => FacetDigest::Unknown,
            FacetStream::Stream(s) => FacetDigest::Exact(facet_domain_digest(facet, &s)),
        }
    }

    /// All five facet digests of a unit part, in scheme order.
    pub fn facet_digests(&self, unit: NodeId) -> [(Facet, FacetDigest); 5] {
        Facet::ALL.map(|f| (f, self.facet_digest(unit, f)))
    }

    /// The graph digest: the full print of the term plus the canonical scope graph stream.
    pub fn graph_digest(&self, scopes: &ScopeGraph) -> Digest {
        let mut s = self.print_with(self.root(), PrintOpts::FULL);
        s.push('\n');
        s.push_str(&scopes.canonical_stream());
        Digest::of(&format!("gob-ir/{DIGEST_SCHEME}/graph"), s.as_bytes())
    }
}

fn facet_domain_digest(facet: Facet, stream: &str) -> Digest {
    Digest::of(
        &format!("gob-ir/{DIGEST_SCHEME}/{}", facet.name()),
        stream.as_bytes(),
    )
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Part {
    Sig,
    Doc,
    Attr,
    Trivia,
    Body,
}

fn classify(node: &Node) -> Part {
    match &node.op {
        Operator::Universal(Universal::Comment { .. }) => return Part::Trivia,
        _ if node.attrs.get_str(reserved::FACET) == Some("sig") => return Part::Sig,
        Operator::Universal(Universal::Attr { name }) if name == "doc" => return Part::Doc,
        Operator::Universal(Universal::Attr { .. }) => return Part::Attr,
        _ => {}
    }
    Part::Body
}
