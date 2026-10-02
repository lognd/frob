//! Unit-level selector evaluation and the owner of one unit (grmb-spec 6.4 steps 2-5, 6.5).
//!
//! The selector grammar and combinators live in gob-walk; this module supplies the leaves from
//! U terms and the scope graph: unit kind, language tag, attributes (Unknown when the adapter
//! does not provide them) and the status of the containment chain from the file to the unit.

// frob:ticket 01M3Z713RETBN30XBC6CK11FBF

use std::collections::{BTreeMap, BTreeSet};

use gob_walk::selector::{AttrPred, Cmp, Glob, Leaves, Tri, Value, truth_of, wildcard_match};
use gob_walk::{EntityName, MatchStatus, Ownership, Selector, WalkResult, owner::resolve_owner};

use crate::attrs::{AttrValue, reserved};
use crate::digest::{Facet, FacetDigest};
use crate::operator::{Operator, Universal};
use crate::scope::{Label, ScopeGraph, Status};
use crate::symref::{Anchor, Identity, Symref};
use crate::term::{NodeId, Term};

/// A unit selected by a selector.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UnitMatch {
    /// The identity (symref anchor, Body digest as content when known).
    pub identity: Identity,
    /// The symref of the identity.
    pub symref: Symref,
    /// Must when only Must facts decide it; May along a May or Unknown fact. Never Unknown.
    pub status: Status,
}

/// Why a file hides units the selector might match (the unseen remainder, grmb-spec 6.4 step 4).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum HiddenReason {
    /// The file contains an `opaque` region.
    Opaque,
    /// The file contains a `hole` (parse error).
    Hole,
    /// The file contains a `phase` with no expansion.
    Phase,
}

/// A hidden placeholder: the selector may match units the term cannot show. Only in `hi`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Hidden {
    /// The artifact that hides units.
    pub locator: String,
    /// Why they are hidden.
    pub reason: HiddenReason,
}

/// The unit-level answer: matches (Must in `lo`, all in `hi`) and hidden placeholders (`hi` only).
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct UnitSelection {
    /// Matching identities in symref order with their status.
    pub matches: Vec<UnitMatch>,
    /// Placeholders for the unseen remainder.
    pub hidden: Vec<Hidden>,
}

fn unit_kind(op: &Operator) -> Option<&str> {
    match op {
        Operator::Universal(Universal::Unit { kind, .. } | Universal::Anon { kind }) => Some(kind),
        _ => None,
    }
}

/// The status of the containment chain from the file root to `node`: the declaration statuses,
/// the lexical edge of every enclosing scope and unexpanded phases on the way.
fn containment(term: &Term, scopes: &ScopeGraph, node: NodeId) -> Status {
    let mut st = Status::Must;
    let mut cur = Some(node);
    while let Some(n) = cur {
        if let Some(d) = scopes.decl_at(n) {
            st = st.meet(scopes.decl(d).status);
        }
        if let Some(s) = scopes.scope_at(n)
            && let Some(lex) = scopes
                .edges(s)
                .iter()
                .filter(|e| e.label == Label::Lexical)
                .map(|e| e.status)
                .max()
        {
            st = st.meet(lex);
        }
        if n != node
            && matches!(
                term.operator(n),
                Operator::Universal(Universal::Phase { .. })
            )
            && term.children(n).len() < 2
        {
            st = st.meet(Status::May);
        }
        cur = term.parent(n);
    }
    st
}

fn status_of(t: Tri) -> Option<Status> {
    match t {
        Tri::Yes => Some(Status::Must),
        Tri::Unknown => Some(Status::May),
        Tri::No => None,
    }
}

fn match_status(s: Status) -> MatchStatus {
    if s == Status::Must {
        MatchStatus::Must
    } else {
        MatchStatus::May
    }
}

fn quals(term: &Term, node: NodeId) -> Vec<String> {
    term.symref_of(node)
        .map(|s| s.qual().iter().map(ToString::to_string).collect())
        .unwrap_or_default()
}

fn attr_lookup(term: &Term, node: NodeId, name: &str) -> Option<AttrValue> {
    let names: &[&str] = if name == "vis" || name == "visibility" {
        &["vis", "visibility"]
    } else {
        &[name]
    };
    for n in names {
        if let Some(v) = term.node(node).attrs().get(n) {
            return Some(v.clone());
        }
    }
    for &c in term.children(node) {
        if let Operator::Universal(Universal::Attr { name: an }) = term.operator(c)
            && an == name
        {
            let payload = term
                .children(c)
                .iter()
                .find_map(|&p| match term.operator(p) {
                    Operator::Universal(Universal::Lit { lexeme, .. }) => Some(lexeme.clone()),
                    _ => None,
                });
            return Some(payload.map_or(AttrValue::Bool(true), AttrValue::Str));
        }
    }
    None
}

fn scalar_text(v: &AttrValue) -> Option<String> {
    match v {
        AttrValue::Str(s) => Some(s.clone()),
        AttrValue::Int(i) => Some(i.to_string()),
        AttrValue::Bool(b) => Some(b.to_string()),
        AttrValue::List(_) | AttrValue::Map(_) => None,
    }
}

fn split_quantity(text: &str) -> Option<(f64, String)> {
    let t = text.trim();
    let end = t
        .find(|c: char| !(c.is_ascii_digit() || c == '.'))
        .unwrap_or(t.len());
    let n: f64 = t[..end].parse().ok()?;
    Some((n, t[end..].trim().to_owned()))
}

fn norm_vis(s: &str) -> &str {
    if s == "public" { "pub" } else { s }
}

fn number_eq(a: f64, b: f64) -> bool {
    (a - b).abs() < f64::EPSILON
}

fn compare(cmp: Cmp, rhs: &Value, text: &str, is_vis: bool) -> Tri {
    let eq = |text: &str| -> bool {
        match rhs {
            Value::Str(s) | Value::Ident(s) if is_vis => norm_vis(text) == norm_vis(s),
            Value::Str(s) | Value::Ident(s) => text == s,
            Value::Number(n) => match (split_quantity(text), n.parse::<f64>()) {
                (Some((a, u)), Ok(b)) => u.is_empty() && number_eq(a, b),
                _ => false,
            },
            Value::Quantity { number, unit } => match (split_quantity(text), number.parse::<f64>())
            {
                (Some((a, u)), Ok(b)) => u == *unit && number_eq(a, b),
                _ => false,
            },
        }
    };
    match cmp {
        Cmp::Eq => Tri::from_bool(eq(text)),
        Cmp::Ne => Tri::from_bool(!eq(text)),
        Cmp::Match => match rhs {
            Value::Str(p) => Tri::from_bool(wildcard_match(p, text)),
            _ => Tri::Unknown,
        },
        Cmp::Le => {
            let (n, u) = match rhs {
                Value::Number(n) => (n.as_str(), String::new()),
                Value::Quantity { number, unit } => (number.as_str(), unit.clone()),
                _ => return Tri::Unknown,
            };
            match (split_quantity(text), n.parse::<f64>()) {
                (Some((a, au)), Ok(b)) if au == u => Tri::from_bool(a <= b),
                _ => Tri::Unknown,
            }
        }
    }
}

/// The leaves of one unit part: its own kind, language and attributes and its glob position.
struct UnitLeaves<'a> {
    term: &'a Term,
    node: NodeId,
    qual: Vec<String>,
    attrs_provided: bool,
}

impl<'a> UnitLeaves<'a> {
    fn new(term: &'a Term, node: NodeId) -> Self {
        let attrs_provided = !matches!(
            term.node(term.root()).attrs().get(reserved::ATTRS_PROVIDED),
            Some(AttrValue::Bool(false))
        );
        Self {
            term,
            node,
            qual: quals(term, node),
            attrs_provided,
        }
    }
}

impl Leaves for UnitLeaves<'_> {
    fn glob(&self, glob: &Glob) -> Tri {
        Tri::from_bool(glob.matches_path(self.term.locator()) && glob.matches_qual(&self.qual))
    }

    fn lang(&self, lang: &str) -> Tri {
        Tri::from_bool(self.term.node(self.node).lang() == lang)
    }

    fn kind(&self, kinds: &[String]) -> Tri {
        let k = unit_kind(self.term.operator(self.node));
        Tri::from_bool(k.is_some_and(|k| kinds.iter().any(|w| w == k)))
    }

    fn attr(&self, pred: &AttrPred) -> Tri {
        let Some(v) = attr_lookup(self.term, self.node, &pred.name) else {
            return if self.attrs_provided {
                Tri::No
            } else {
                Tri::Unknown
            };
        };
        let Some((cmp, rhs)) = &pred.test else {
            return Tri::Yes;
        };
        let is_vis = pred.name == "vis" || pred.name == "visibility";
        scalar_text(&v).map_or(Tri::Unknown, |t| compare(*cmp, rhs, &t, is_vis))
    }
}

/// Leaves for the unseen-remainder question: could any unit of this file match?
struct HiddenLeaves<'a> {
    term: &'a Term,
}

impl Leaves for HiddenLeaves<'_> {
    fn glob(&self, glob: &Glob) -> Tri {
        if !glob.matches_path(self.term.locator()) {
            Tri::No
        } else if glob.qual().is_some() {
            Tri::Unknown
        } else {
            Tri::Yes
        }
    }

    fn lang(&self, lang: &str) -> Tri {
        Tri::from_bool(self.term.node(self.term.root()).lang() == lang)
    }

    fn kind(&self, _: &[String]) -> Tri {
        Tri::Unknown
    }

    fn attr(&self, _: &AttrPred) -> Tri {
        Tri::Unknown
    }
}

fn unseen(term: &Term) -> BTreeSet<HiddenReason> {
    let mut out = BTreeSet::new();
    for id in term.ids() {
        match term.operator(id) {
            op if op.is_opaque() => out.insert(HiddenReason::Opaque),
            op if op.is_hole() => out.insert(HiddenReason::Hole),
            Operator::Universal(Universal::Phase { .. }) if term.children(id).len() < 2 => {
                out.insert(HiddenReason::Phase)
            }
            _ => false,
        };
    }
    out
}

fn identity_of(term: &Term, node: NodeId, symref: &Symref) -> Identity {
    let content = match term.facet_digest(node, Facet::Body) {
        FacetDigest::Exact(d) => Some(d),
        _ => None,
    };
    Identity::new(Anchor::Symref(symref.clone()), content)
}

fn walked(files: &WalkResult, locator: &str) -> bool {
    files
        .files
        .binary_search_by(|f| f.path.as_str().cmp(locator))
        .is_ok()
}

/// Resolves a LITERAL selector through exact qualname then unique suffix (grmb-spec 6.4 item 5).
fn literal_matches(
    glob: &Glob,
    term: &Term,
    scopes: &ScopeGraph,
) -> BTreeMap<Symref, (NodeId, Status)> {
    let mut out = BTreeMap::new();
    if !glob.matches_path(term.locator()) {
        return out;
    }
    let units = term.units();
    let want = glob.qual_segments();
    let mut cands: BTreeMap<Symref, NodeId> = BTreeMap::new();
    for u in &units {
        let q = quals(term, u.node);
        if q.iter().map(String::as_str).eq(want.iter().copied()) {
            cands.entry(u.symref.clone()).or_insert(u.node);
        }
    }
    if cands.is_empty() {
        for u in &units {
            let q = quals(term, u.node);
            if q.len() >= want.len()
                && q[q.len() - want.len()..]
                    .iter()
                    .map(String::as_str)
                    .eq(want.iter().copied())
            {
                cands.entry(u.symref.clone()).or_insert(u.node);
            }
        }
    }
    let unique = cands.len() == 1;
    for (sym, node) in cands {
        let base = if unique { Status::Must } else { Status::May };
        out.insert(sym, (node, base.meet(containment(term, scopes, node))));
    }
    out
}

/// Evaluates `sel` over the units of one term, with hidden placeholders.
///
/// Must where a literal path would be; May along a May or Unknown fact; never dropping a
/// candidate (an Unknown predicate yields May). A term whose file is not in `files` yields
/// nothing: the selector says nothing about files outside the walk.
pub fn select(
    sel: &Selector,
    term: &Term,
    scopes: &ScopeGraph,
    files: &WalkResult,
) -> UnitSelection {
    let locator = term.locator();
    if !walked(files, locator) {
        tracing::debug!(locator, "term file is not in the walk; selector is silent");
        return UnitSelection::default();
    }
    let best: BTreeMap<Symref, (NodeId, Status)> = match sel.literal() {
        Some(g) if g.qual().is_some() => literal_matches(g, term, scopes),
        _ => {
            let mut best: BTreeMap<Symref, (NodeId, Status)> = BTreeMap::new();
            for u in term.units() {
                let leaves = UnitLeaves::new(term, u.node);
                let Some(member) = status_of(truth_of(&sel.rows(&leaves))) else {
                    continue;
                };
                let mut st = member.meet(containment(term, scopes, u.node));
                if st == Status::Unknown {
                    st = Status::May;
                }
                let e = best.entry(u.symref).or_insert((u.node, st));
                e.1 = e.1.max(st);
            }
            best
        }
    };
    let matches: Vec<UnitMatch> = best
        .into_iter()
        .map(|(symref, (node, status))| UnitMatch {
            identity: identity_of(term, node, &symref),
            symref,
            status,
        })
        .collect();
    let hidden = if sel.truth(&HiddenLeaves { term }) == Tri::No {
        Vec::new()
    } else {
        unseen(term)
            .into_iter()
            .map(|reason| Hidden {
                locator: locator.to_owned(),
                reason,
            })
            .collect()
    };
    tracing::debug!(
        selector = %sel,
        locator,
        matches = matches.len(),
        hidden = hidden.len(),
        "unit selection"
    );
    UnitSelection { matches, hidden }
}

/// The units of `term` selected by `sel` (see [`select`] for the placeholders).
pub fn select_units(
    sel: &Selector,
    term: &Term,
    scopes: &ScopeGraph,
    files: &WalkResult,
) -> Vec<UnitMatch> {
    select(sel, term, scopes, files).matches
}

/// The rank-2 owner of the unit `symref` under `entities`' selectors (grmb-spec 6.5 step 2).
///
/// `None` when the term has no such unit. The item's file counts as having an unseen remainder
/// when it holds an opaque region, a hole or an unexpanded phase.
pub fn owner_of_unit(
    entities: &[(EntityName, Selector)],
    symref: &Symref,
    term: &Term,
    scopes: &ScopeGraph,
) -> Option<Ownership> {
    let parts: Vec<NodeId> = term
        .units()
        .into_iter()
        .filter(|u| &u.symref == symref)
        .map(|u| u.node)
        .collect();
    if parts.is_empty() {
        return None;
    }
    let mut cands = Vec::new();
    for node in parts {
        let ceiling = match_status(containment(term, scopes, node));
        let leaves = UnitLeaves::new(term, node);
        cands.extend(gob_walk::owner::candidates(entities, &leaves, ceiling));
    }
    Some(resolve_owner(cands, !unseen(term).is_empty()))
}
