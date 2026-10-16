//! COH004 "mixed vocabularies" (cohesion.md 1): split the identifiers a unit mentions into words,
//! link the words that occur in one top-level statement, and report the unit when two or more
//! disjoint word clusters remain. A heuristic, so the verdict is Advisory only, never Warn.

// frob:ticket 01M4CXSTHZXVBMWSTRCBH9BHQ5

use std::collections::{BTreeMap, BTreeSet};

use gob_ir::{NodeId, Operator, Term, Universal};
use tracing::debug;

use crate::coh001::statements;

/// Knobs of COH004.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Coh004Options {
    /// A cluster with fewer distinct words than this does not count as a vocabulary.
    pub min_cluster_words: usize,
    /// Words shorter than this are noise (`i`, `x`) and are dropped.
    pub min_word_len: usize,
    /// Generic words that carry no domain meaning and are dropped.
    pub stop_words: Vec<String>,
}

impl Default for Coh004Options {
    fn default() -> Self {
        Self {
            min_cluster_words: 2,
            min_word_len: 3,
            stop_words: [
                "self", "this", "cls", "new", "get", "set", "len", "str", "int", "let", "true",
                "false", "none", "null", "some", "ok", "err", "return", "result", "value", "val",
                "tmp", "temp", "res", "ret", "out",
            ]
            .map(str::to_owned)
            .to_vec(),
        }
    }
}

/// COH004's judgement of one unit.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Coh004 {
    /// Two or more disjoint vocabularies; each cluster is its sorted word list (Advisory).
    Advisory {
        /// The disjoint clusters, largest first.
        clusters: Vec<Vec<String>>,
    },
    /// At most one vocabulary.
    Clean,
}

/// Split an identifier into lowercase words on `_`, `-`, and camelCase boundaries.
pub fn split_words(ident: &str) -> Vec<String> {
    let mut words = Vec::new();
    let mut cur = String::new();
    let chars: Vec<char> = ident.trim_end_matches('!').chars().collect();
    for (i, &c) in chars.iter().enumerate() {
        if !c.is_alphanumeric() {
            flush(&mut cur, &mut words);
            continue;
        }
        let boundary = c.is_uppercase()
            && i > 0
            && (chars[i - 1].is_lowercase()
                || chars[i - 1].is_ascii_digit()
                || chars.get(i + 1).is_some_and(|n| n.is_lowercase())
                    && chars[i - 1].is_uppercase());
        if boundary {
            flush(&mut cur, &mut words);
        }
        cur.extend(c.to_lowercase());
    }
    flush(&mut cur, &mut words);
    words
}

fn flush(cur: &mut String, words: &mut Vec<String>) {
    if !cur.is_empty() {
        words.push(std::mem::take(cur));
    }
}

fn idents(term: &Term, n: NodeId, out: &mut Vec<String>) {
    match term.node(n).op() {
        Operator::Universal(Universal::Ref { name }) => out.push(name.clone()),
        Operator::Universal(Universal::Lit { kind, lexeme }) if kind == "identifier" => {
            out.push(lexeme.clone());
        }
        _ => {}
    }
    for &c in term.node(n).children() {
        idents(term, c, out);
    }
}

struct Union(Vec<usize>);

impl Union {
    fn find(&mut self, x: usize) -> usize {
        let p = self.0[x];
        if p == x {
            return x;
        }
        let r = self.find(p);
        self.0[x] = r;
        r
    }
}

/// Judge `unit` of `term`: cluster the words of its statements and report disjoint vocabularies.
pub fn coh004(term: &Term, unit: NodeId, opts: &Coh004Options) -> Coh004 {
    let per_stmt: Vec<BTreeSet<String>> = statements(term, unit)
        .into_iter()
        .map(|s| {
            let mut raw = Vec::new();
            idents(term, s, &mut raw);
            raw.iter()
                .flat_map(|r| split_words(r))
                .filter(|w| w.chars().count() >= opts.min_word_len)
                .filter(|w| !opts.stop_words.contains(w))
                .collect()
        })
        .collect();
    let vocab: Vec<&String> = per_stmt
        .iter()
        .flatten()
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    let index: BTreeMap<&String, usize> = vocab.iter().enumerate().map(|(i, &w)| (w, i)).collect();
    let mut uf = Union((0..vocab.len()).collect());
    for words in &per_stmt {
        let mut it = words.iter().map(|w| index[w]);
        if let Some(first) = it.next() {
            for other in it {
                let (a, b) = (uf.find(first), uf.find(other));
                uf.0[a.max(b)] = a.min(b);
            }
        }
    }
    let mut groups: BTreeMap<usize, Vec<String>> = BTreeMap::new();
    for (i, w) in vocab.iter().enumerate() {
        groups.entry(uf.find(i)).or_default().push((*w).clone());
    }
    let mut clusters: Vec<Vec<String>> = groups
        .into_values()
        .filter(|g| g.len() >= opts.min_cluster_words)
        .collect();
    clusters.sort_by(|a, b| b.len().cmp(&a.len()).then_with(|| a.cmp(b)));
    debug!(unit = ?unit, words = vocab.len(), clusters = clusters.len(), "coh004 clusters");
    if clusters.len() >= 2 {
        Coh004::Advisory { clusters }
    } else {
        Coh004::Clean
    }
}
