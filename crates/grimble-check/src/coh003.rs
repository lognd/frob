//! COH003 "mixed abstraction levels" (cohesion.md 1): a unit whose callees span layers further
//! apart than `max_level_spread` mixes domain-level calls with lower-layer primitives (string
//! slicing, index access, raw IO) in one body. The single level of abstraction principle.
//!
//! Every call in the unit (nested functions and lambdas are other units) is placed on a layer:
//! a callee named in [`Coh003Options::layers`] (filled from the grimble model or module depth)
//! sits on that layer, a primitive callee or an index/slice expression sits on
//! [`Coh003Options::primitive_layer`], trivial calls (logging) do not count. P+: the rule fires
//! only when two placed callees are provably further apart than the spread. A callee on no layer
//! leaves the verdict Unresolved with those callees named, never a silent pass.

// frob:ticket 01M4CXSSGYVE2QQ7ACW7T5Y51S

use std::collections::{BTreeMap, BTreeSet};

use gob_ir::{NodeId, Operator, Term};
use gob_symbols::syntax_for;
use tracing::{debug, trace};

use crate::coh001::{CohOptions, statements};
use crate::coh002::{callee_of, is_call, is_nested_unit};

/// The name an index or slice expression (`s[1:3]`, `xs[i + 1]`) carries in a verdict.
pub const INDEX_CALLEE: &str = "[]";

/// Knobs of COH003 (the `[coh]` table of cohesion.md, defaults here until the table lands).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Coh003Options {
    /// The largest layer distance that is still one level of abstraction.
    pub max_level_spread: u32,
    /// Callee name (last path segment) to layer, from the grimble model or module depth.
    pub layers: BTreeMap<String, u32>,
    /// The layer of primitives: raw slicing, index access, raw IO.
    pub primitive_layer: u32,
    /// Callee names that are primitives when no model layer names them.
    pub primitive_calls: Vec<String>,
    /// Callee names that are trivial (logging, metrics, asserts); never placed on a layer.
    pub trivial: Vec<String>,
}

impl Default for Coh003Options {
    fn default() -> Self {
        Self {
            max_level_spread: 1,
            layers: BTreeMap::new(),
            primitive_layer: 0,
            primitive_calls: [
                "substring",
                "substr",
                "slice",
                "split_at",
                "split",
                "splitn",
                "rsplit",
                "strip",
                "lstrip",
                "rstrip",
                "trim",
                "find",
                "rfind",
                "charAt",
                "charCodeAt",
                "indexOf",
                "lastIndexOf",
                "from_utf8",
                "read",
                "read_to_string",
                "readline",
                "readlines",
                "recv",
            ]
            .map(str::to_owned)
            .to_vec(),
            trivial: CohOptions::default().trivial,
        }
    }
}

/// One call (or index expression) placed on a layer.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LayeredCall {
    /// The call or index node.
    pub node: NodeId,
    /// The callee's last path segment, or [`INDEX_CALLEE`].
    pub callee: String,
    /// The layer the callee sits on.
    pub layer: u32,
}

/// Why a verdict is Unresolved.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Coh003Unresolved {
    /// The placed callees do not exceed the spread, but callees on no layer might.
    UnknownCallees {
        /// The sorted callee names with no layer.
        callees: Vec<String>,
    },
}

/// COH003's judgement of one unit.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Coh003 {
    /// Placed callees span more than `max_level_spread` layers.
    Fire {
        /// Highest layer minus lowest layer among the placed callees.
        spread: u32,
        /// The calls on the highest layer, in source order.
        high: Vec<LayeredCall>,
        /// The calls on the lowest layer, in source order.
        low: Vec<LayeredCall>,
    },
    /// Every call is placed and within the spread, or no call is left to judge.
    Clean,
    /// Neither proven nor excluded.
    Unresolved(Coh003Unresolved),
}

/// Collect the unit's calls and index expressions, skipping nested units.
fn calls_and_indexes(term: &Term, n: NodeId, indexes: &[&str], out: &mut Vec<(NodeId, String)>) {
    for &c in term.node(n).children() {
        if is_nested_unit(term, c) {
            continue;
        }
        if is_call(term, c) {
            if let Some(name) = callee_of(term, c) {
                out.push((c, name));
            }
        } else if matches!(term.node(c).op(), Operator::Adapter(a) if indexes.contains(&a.name.as_str()))
        {
            out.push((c, INDEX_CALLEE.to_owned()));
        }
        calls_and_indexes(term, c, indexes, out);
    }
}

/// Judge `unit` of `term` (language tag `lang`); a language without syntax tables is Clean.
pub fn coh003(term: &Term, lang: &str, unit: NodeId, opts: &Coh003Options) -> Coh003 {
    let Some(syntax) = syntax_for(lang) else {
        return Coh003::Clean;
    };
    let mut found = Vec::new();
    for stmt in statements(term, unit) {
        if is_nested_unit(term, stmt) {
            continue;
        }
        if matches!(term.node(stmt).op(), Operator::Adapter(a) if syntax.indexes.contains(&a.name.as_str()))
        {
            found.push((stmt, INDEX_CALLEE.to_owned()));
        } else if is_call(term, stmt)
            && let Some(name) = callee_of(term, stmt)
        {
            found.push((stmt, name));
        }
        calls_and_indexes(term, stmt, syntax.indexes, &mut found);
    }
    found.sort();
    found.dedup();
    let mut placed = Vec::new();
    let mut unknown = BTreeSet::new();
    for (node, callee) in found {
        if opts.trivial.contains(&callee) {
            continue;
        }
        let layer = if let Some(&l) = opts.layers.get(&callee) {
            Some(l)
        } else if callee == INDEX_CALLEE || opts.primitive_calls.contains(&callee) {
            Some(opts.primitive_layer)
        } else {
            None
        };
        trace!(?node, %callee, ?layer, "coh003 callee");
        match layer {
            Some(layer) => placed.push(LayeredCall {
                node,
                callee,
                layer,
            }),
            None => {
                unknown.insert(callee);
            }
        }
    }
    let top = placed.iter().map(|c| c.layer).max();
    let bottom = placed.iter().map(|c| c.layer).min();
    debug!(unit = ?unit, placed = placed.len(), unknown = unknown.len(), ?top, ?bottom, "coh003 judged");
    if let (Some(top), Some(bottom)) = (top, bottom)
        && top - bottom > opts.max_level_spread
    {
        return Coh003::Fire {
            spread: top - bottom,
            high: placed.iter().filter(|c| c.layer == top).cloned().collect(),
            low: placed
                .iter()
                .filter(|c| c.layer == bottom)
                .cloned()
                .collect(),
        };
    }
    if unknown.is_empty() {
        Coh003::Clean
    } else {
        Coh003::Unresolved(Coh003Unresolved::UnknownCallees {
            callees: unknown.into_iter().collect(),
        })
    }
}
