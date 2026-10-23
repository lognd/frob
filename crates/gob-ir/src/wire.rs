//! Serialization of [`Term`], [`ScopeGraph`] and [`Location`] for the folded-term cache.
//!
//! The wire form carries only primary data. Everything derivable (symrefs, the node-to-scope and
//! node-to-reference maps, the declaration index, the resolution memo) is rebuilt on decode, and
//! every id is range-checked, so a corrupt or skewed payload is an error and never a panic or a
//! silently wrong graph. Encoding is deterministic: no hash-map iteration order reaches the bytes.
//!
//! Bump [`TERM_SCHEMA_VERSION`] whenever a serialized shape or its meaning changes.

use std::collections::{HashMap, HashSet};
use std::sync::{Arc, Mutex, OnceLock};

use gob_text::{FileId, FileInterner, TextRange, TextSize};
use serde::de::Error as _;
use serde::{Deserialize, Deserializer, Serialize, Serializer};
use tracing::{debug, warn};

use crate::attrs::Attributes;
use crate::location::Location;
use crate::operator::Operator;
use crate::scope::{DeclId, Memo, RefId, Scope, ScopeGraph, ScopeId};
use crate::term::{Node, NodeId, Term, compute_symrefs};

// frob:ticket 01M4HB1ZAX0Q6QHK1DK3Y3EZ9E
/// Version of the serialized [`Term`] and [`ScopeGraph`] shape; part of any cache key holding them.
pub const TERM_SCHEMA_VERSION: u32 = 1;

/// The process-wide interner used to mint [`FileId`]s from stored indices.
///
/// `FileId` has no public constructor, so ids are minted by interning placeholder paths; the
/// result equals the id the adapter's own interner handed out because ids are dense indices.
fn file_id<E: serde::de::Error>(index: u32) -> Result<FileId, E> {
    /// A fold interns one file; a larger index is corruption, and minting it would allocate.
    const MAX_MINTED: u32 = 4096;
    static MINTED: OnceLock<Mutex<FileInterner>> = OnceLock::new();
    if index > MAX_MINTED {
        return Err(E::custom(format!("file index {index} out of range")));
    }
    let mut files = MINTED
        .get_or_init(|| Mutex::new(FileInterner::new()))
        .lock()
        .expect("file id minter lock");
    for i in files.len()..=index as usize {
        files.intern(&format!("#{i}"));
    }
    Ok(files.intern(&format!("#{index}")))
}

#[derive(Serialize, Deserialize)]
enum LocationWire {
    Text {
        file: u32,
        start: u32,
        end: u32,
    },
    Grid {
        sheet: u32,
        row: u32,
        col: u32,
    },
    Graph {
        doc: u32,
        node: String,
        port: Option<String>,
    },
    Stream {
        artifact: u32,
        seq: u64,
    },
    Notebook {
        nb: u32,
        cell: u32,
        start: u32,
        end: u32,
    },
    Pointer {
        artifact: u32,
        json_pointer: String,
    },
}

impl Serialize for Location {
    fn serialize<S: Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        let wire = match self {
            Self::Text { file, range } => LocationWire::Text {
                file: file.index(),
                start: range.start().into(),
                end: range.end().into(),
            },
            Self::Grid { sheet, row, col } => LocationWire::Grid {
                sheet: sheet.index(),
                row: *row,
                col: *col,
            },
            Self::Graph { doc, node, port } => LocationWire::Graph {
                doc: doc.index(),
                node: node.clone(),
                port: port.clone(),
            },
            Self::Stream { artifact, seq } => LocationWire::Stream {
                artifact: artifact.index(),
                seq: *seq,
            },
            Self::Notebook { nb, cell, range } => LocationWire::Notebook {
                nb: nb.index(),
                cell: *cell,
                start: range.start().into(),
                end: range.end().into(),
            },
            Self::Pointer {
                artifact,
                json_pointer,
            } => LocationWire::Pointer {
                artifact: artifact.index(),
                json_pointer: json_pointer.clone(),
            },
        };
        wire.serialize(s)
    }
}

fn range_of<E: serde::de::Error>(start: u32, end: u32) -> Result<TextRange, E> {
    if start > end {
        return Err(E::custom(format!("inverted text range {start}..{end}")));
    }
    Ok(TextRange::new(TextSize::new(start), TextSize::new(end)))
}

impl<'de> Deserialize<'de> for Location {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        Ok(match LocationWire::deserialize(d)? {
            LocationWire::Text { file, start, end } => Self::Text {
                file: file_id(file)?,
                range: range_of(start, end)?,
            },
            LocationWire::Grid { sheet, row, col } => Self::Grid {
                sheet: file_id(sheet)?,
                row,
                col,
            },
            LocationWire::Graph { doc, node, port } => Self::Graph {
                doc: file_id(doc)?,
                node,
                port,
            },
            LocationWire::Stream { artifact, seq } => Self::Stream {
                artifact: file_id(artifact)?,
                seq,
            },
            LocationWire::Notebook {
                nb,
                cell,
                start,
                end,
            } => Self::Notebook {
                nb: file_id(nb)?,
                cell,
                range: range_of(start, end)?,
            },
            LocationWire::Pointer {
                artifact,
                json_pointer,
            } => Self::Pointer {
                artifact: file_id(artifact)?,
                json_pointer,
            },
        })
    }
}

/// Borrowed view of a [`Node`] for encoding; field order must match [`NodeIn`].
#[derive(Serialize)]
struct NodeOut<'a> {
    op: &'a Operator,
    name: &'a Option<String>,
    binders: &'a Vec<String>,
    children: &'a Vec<NodeId>,
    parent: &'a Option<NodeId>,
    location: &'a Location,
    lang: &'a str,
    lang_param: &'a Option<String>,
    attrs: &'a Attributes,
}

/// Owned decode form of a [`Node`]; field order must match [`NodeOut`].
#[derive(Deserialize)]
struct NodeIn {
    op: Operator,
    name: Option<String>,
    binders: Vec<String>,
    children: Vec<NodeId>,
    parent: Option<NodeId>,
    location: Location,
    lang: String,
    lang_param: Option<String>,
    attrs: Attributes,
}

#[derive(Serialize)]
struct TermOut<'a> {
    locator: &'a str,
    nodes: Vec<NodeOut<'a>>,
    root: NodeId,
}

#[derive(Deserialize)]
struct TermIn {
    locator: String,
    nodes: Vec<NodeIn>,
    root: NodeId,
}

impl Serialize for Term {
    fn serialize<S: Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        TermOut {
            locator: &self.locator,
            nodes: self
                .nodes
                .iter()
                .map(|n| NodeOut {
                    op: &n.op,
                    name: &n.name,
                    binders: &n.binders,
                    children: &n.children,
                    parent: &n.parent,
                    location: &n.location,
                    lang: &n.lang,
                    lang_param: &n.lang_param,
                    attrs: &n.attrs,
                })
                .collect(),
            root: self.root,
        }
        .serialize(s)
    }
}

impl<'de> Deserialize<'de> for Term {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        let wire = TermIn::deserialize(d)?;
        let len = wire.nodes.len();
        let in_range = |id: NodeId| id.index() < len;
        if !in_range(wire.root) {
            return Err(D::Error::custom(format!("root {} out of range", wire.root)));
        }
        let mut seen_child = vec![false; len];
        for (i, n) in wire.nodes.iter().enumerate() {
            for &c in &n.children {
                if !in_range(c) {
                    return Err(D::Error::custom(format!("child {c} of n{i} out of range")));
                }
                if std::mem::replace(&mut seen_child[c.index()], true)
                    || wire.nodes[c.index()].parent != Some(NodeId(crate::idx32(i)))
                {
                    return Err(D::Error::custom(format!("inconsistent parent link at {c}")));
                }
            }
            match n.parent {
                Some(p) if !in_range(p) => {
                    return Err(D::Error::custom(format!("parent {p} of n{i} out of range")));
                }
                None if i != wire.root.index() => {
                    return Err(D::Error::custom(format!("n{i} is an orphan")));
                }
                _ => {}
            }
        }
        if wire.nodes[wire.root.index()].parent.is_some() {
            return Err(D::Error::custom("root has a parent"));
        }
        let mut langs: HashMap<String, Arc<str>> = HashMap::new();
        let nodes = wire
            .nodes
            .into_iter()
            .map(|n| {
                let lang = langs
                    .entry(n.lang)
                    .or_insert_with_key(|k| Arc::from(k.as_str()))
                    .clone();
                Node {
                    op: n.op,
                    name: n.name,
                    binders: n.binders,
                    children: n.children,
                    parent: n.parent,
                    location: n.location,
                    lang,
                    lang_param: n.lang_param,
                    attrs: n.attrs,
                }
            })
            .collect();
        let mut term = Self {
            locator: wire.locator,
            nodes,
            root: wire.root,
            symrefs: Vec::new(),
        };
        term.symrefs = compute_symrefs(&term);
        debug!(nodes = term.len(), locator = %term.locator, "term decoded");
        Ok(term)
    }
}

#[derive(Serialize)]
struct GraphOut<'a> {
    scopes: &'a Vec<Scope>,
    decls: &'a Vec<crate::scope::Decl>,
    refs: &'a Vec<crate::scope::Reference>,
    decl_of_node: Vec<(NodeId, DeclId)>,
}

#[derive(Deserialize)]
struct GraphIn {
    scopes: Vec<Scope>,
    decls: Vec<crate::scope::Decl>,
    refs: Vec<crate::scope::Reference>,
    decl_of_node: Vec<(NodeId, DeclId)>,
}

impl Serialize for ScopeGraph {
    fn serialize<S: Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        let mut decl_of_node: Vec<(NodeId, DeclId)> =
            self.decl_of_node.iter().map(|(n, d)| (*n, *d)).collect();
        decl_of_node.sort_unstable();
        GraphOut {
            scopes: &self.scopes,
            decls: &self.decls,
            refs: &self.refs,
            decl_of_node,
        }
        .serialize(s)
    }
}

impl<'de> Deserialize<'de> for ScopeGraph {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        let wire = GraphIn::deserialize(d)?;
        let (ns, nd) = (wire.scopes.len(), wire.decls.len());
        let scope_ok = |s: ScopeId| s.index() < ns;
        let decl_ok = |x: DeclId| x.index() < nd;
        let bad = |what: &str| D::Error::custom(format!("scope graph: {what} out of range"));
        for sc in &wire.scopes {
            if !sc.decls.iter().all(|&x| decl_ok(x)) {
                return Err(bad("scope declaration"));
            }
            if !sc.edges.iter().all(|e| scope_ok(e.target)) {
                return Err(bad("edge target"));
            }
        }
        if !wire.decls.iter().all(|x| scope_ok(x.scope)) {
            return Err(bad("declaration scope"));
        }
        if !wire.refs.iter().all(|r| scope_ok(r.scope)) {
            return Err(bad("reference scope"));
        }
        if !wire.decl_of_node.iter().all(|(_, x)| decl_ok(*x)) {
            return Err(bad("node declaration"));
        }
        let mut g = Self {
            memo: Memo::with_cells(wire.refs.len()),
            scopes: wire.scopes,
            decls: wire.decls,
            refs: wire.refs,
            ..Self::default()
        };
        for (i, sc) in g.scopes.iter().enumerate() {
            if let Some(n) = sc.node {
                g.scope_of_node.insert(n, ScopeId(crate::idx32(i)));
            }
        }
        for (i, r) in g.refs.iter().enumerate() {
            if let Some(n) = r.node {
                g.ref_of_node.insert(n, RefId(crate::idx32(i)));
            }
        }
        for (i, x) in g.decls.iter().enumerate() {
            if x.kind != crate::scope::DeclKind::Binder {
                g.decl_index
                    .entry((x.scope, x.name.clone(), x.qualifier.clone(), false))
                    .or_insert(DeclId(crate::idx32(i)));
            }
        }
        g.decl_of_node = wire.decl_of_node.into_iter().collect();
        debug!(
            scopes = g.scopes.len(),
            decls = g.decls.len(),
            refs = g.refs.len(),
            "scope graph decoded"
        );
        Ok(g)
    }
}

impl ScopeGraph {
    // frob:ticket 01M4HB1ZAX0Q6QHK1DK3Y3EZ9E
    /// Whether every term node this graph mentions exists in a term of `nodes` nodes.
    ///
    /// A decoded graph is only meaningful beside the term it was folded with; the cache calls
    /// this on the decoded pair so a mismatched pair is rejected rather than indexed out of range.
    pub fn nodes_within(&self, nodes: usize) -> bool {
        let ok = |n: &NodeId| n.index() < nodes;
        let all: HashSet<&NodeId> = self
            .scope_of_node
            .keys()
            .chain(self.ref_of_node.keys())
            .chain(self.decl_of_node.keys())
            .chain(self.decls.iter().flat_map(|d| d.nodes.iter()))
            .chain(
                self.scopes
                    .iter()
                    .flat_map(|s| s.hints.iter().filter_map(|h| h.node.as_ref())),
            )
            .collect();
        let within = all.into_iter().all(ok);
        if !within {
            warn!(nodes, "scope graph mentions nodes outside its term");
        }
        within
    }
}
