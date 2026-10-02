//! Comparing two lock files.

use crate::file::{LockEntry, LockFile};

/// One recorded facet of a [`LockEntry`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Facet {
    /// The signature digest.
    Sig,
    /// The body digest.
    Body,
    /// The doc-comment digest.
    Doc,
    /// The attribute-set digest.
    Attr,
    /// The language-neutral contract digest.
    Contract,
    /// A bound doc section digest (any of the targets).
    Target,
}

impl Facet {
    /// The lowercase facet name used in messages and JSON.
    pub const fn name(self) -> &'static str {
        match self {
            Self::Sig => "sig",
            Self::Body => "body",
            Self::Doc => "doc",
            Self::Attr => "attr",
            Self::Contract => "contract",
            Self::Target => "target",
        }
    }
}

/// What differs between an old and a new lock.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct LockDiff {
    /// Symrefs only in the new lock.
    pub added: Vec<String>,
    /// Symrefs only in the old lock.
    pub removed: Vec<String>,
    /// Symrefs in both whose recorded facets differ, with the facets.
    pub changed: Vec<(String, Vec<Facet>)>,
    /// Flow keys only in the new lock.
    pub flows_added: Vec<String>,
    /// Flow keys only in the old lock.
    pub flows_removed: Vec<String>,
    /// Flow keys in both whose ends (identity or contract digest) differ.
    pub flows_changed: Vec<String>,
}

impl LockDiff {
    /// True when the two locks record the same facets for the same symrefs.
    pub fn is_empty(&self) -> bool {
        self.added.is_empty()
            && self.removed.is_empty()
            && self.changed.is_empty()
            && self.flows_added.is_empty()
            && self.flows_removed.is_empty()
            && self.flows_changed.is_empty()
    }
}

fn facets_changed(old: &LockEntry, new: &LockEntry) -> Vec<Facet> {
    let mut out = Vec::new();
    if old.sig != new.sig {
        out.push(Facet::Sig);
    }
    if old.body != new.body {
        out.push(Facet::Body);
    }
    if old.doc != new.doc {
        out.push(Facet::Doc);
    }
    if old.attr != new.attr {
        out.push(Facet::Attr);
    }
    if old.contract != new.contract {
        out.push(Facet::Contract);
    }
    if old.targets != new.targets {
        out.push(Facet::Target);
    }
    out
}

/// Compares `old` to `new`; actor, time and reason differences alone do not count.
pub fn diff(old: &LockFile, new: &LockFile) -> LockDiff {
    let mut d = LockDiff::default();
    for (k, n) in &new.entries {
        match old.entries.get(k) {
            None => d.added.push(k.clone()),
            Some(o) => {
                let f = facets_changed(o, n);
                if !f.is_empty() {
                    d.changed.push((k.clone(), f));
                }
            }
        }
    }
    d.removed = old
        .entries
        .keys()
        .filter(|k| !new.entries.contains_key(*k))
        .cloned()
        .collect();
    for (k, n) in &new.flows {
        match old.flows.get(k) {
            None => d.flows_added.push(k.clone()),
            Some(o) if o.producer != n.producer || o.consumer != n.consumer => {
                d.flows_changed.push(k.clone());
            }
            Some(_) => {}
        }
    }
    d.flows_removed = old
        .flows
        .keys()
        .filter(|k| !new.flows.contains_key(*k))
        .cloned()
        .collect();
    tracing::debug!(
        added = d.added.len(),
        removed = d.removed.len(),
        changed = d.changed.len(),
        "lock diffed"
    );
    d
}
