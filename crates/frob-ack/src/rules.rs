//! The DRIFT and AFFECT rules and their evaluation entry points.

use std::collections::HashSet;
use std::path::Path;

use gob_cache::Cache;
use gob_lock::LockEntry;
use gob_rules::{Finding, Rule, RuleMeta, Severity};
use gob_symbols::{SymbolKind, SymbolRecord, Symref, Target};
use gob_text::{FileInterner, Span};

use crate::inputs::{DocDirective, Inputs, section_digest};
use crate::repo_rule;

/// How many dependent names an AFFECT001 message lists.
const LISTED_DEPENDENTS: usize = 5;

/// A `frob:doc` binding went stale: the code changed under the doc, or the doc under the code.
///
/// The symbol bound by a `frob:doc path#slug` directive has a lock entry
/// (an ack). The finding fires when that entry no longer matches: the sig,
/// body or doc facet of the symbol changed (the code changed under the doc),
/// or the digest of the named markdown section changed (the doc changed
/// under the code). The message names the facet. Re-read the pair and run
/// `frob ack <symref> --reason ...` to record the new state.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "DRIFT001",
    slug = "doc-binding-drift",
    family = "DRIFT",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Drift001;

/// A `frob:doc` directive names a markdown section that does not exist.
///
/// The message carries the nearest heading slug of the target file by edit
/// distance, so a renamed or mistyped heading is a one-line fix.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "DRIFT002",
    slug = "dangling-doc-target",
    family = "DRIFT",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Drift002;

/// A symbol was acked, its signature changed, and no `frob:doc` directive covers it.
///
/// The ack recorded an older contract and nothing ties it to documentation,
/// so nobody is told to re-read anything. Re-ack the symbol or bind it to
/// the doc that describes it.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "DRIFT003",
    slug = "stale-ack",
    family = "DRIFT",
    severity = Warn,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Drift003;

/// A public symbol changed its signature and its dependents were not re-acked.
///
/// Predicate: the symbol is in the public API graph, has a lock entry whose
/// sig digest differs from the current one, and at least one dependent (a
/// transitive caller from `SymbolGraph::affects`, excluding the symbol's own
/// containers and file nodes) has no lock entry acked strictly later than
/// the symbol's own entry. Re-ack the symbol after reviewing its dependents,
/// and ack the dependents you reviewed.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "AFFECT001",
    slug = "dependents-not-updated",
    family = "AFFECT",
    severity = Warn,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Affect001;

/// A finding before it becomes a [`Finding`]: plain data, cacheable.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Raw {
    /// The rule that fired.
    pub meta: &'static RuleMeta,
    /// Severity of this finding.
    pub severity: Severity,
    /// Location, when the finding has one.
    pub span: Option<Span>,
    /// The message.
    pub message: String,
    /// The symref the finding is about (its fingerprint anchor).
    pub anchor: String,
}

impl Raw {
    fn new(meta: &'static RuleMeta, span: Option<Span>, message: String, anchor: &Symref) -> Self {
        Self {
            meta,
            severity: meta.severity,
            span,
            message,
            anchor: anchor.to_string(),
        }
    }

    fn into_finding(self) -> Finding {
        let id = self
            .meta
            .rule_id()
            .unwrap_or_else(|e| unreachable!("derive validated rule id {}: {e}", self.meta.id));
        Finding::new(id, self.severity, self.span, self.message, &self.anchor)
    }
}

type RuleFn = fn(&Inputs) -> Vec<Raw>;

fn rules() -> [(&'static RuleMeta, RuleFn); 4] {
    [
        (Drift001.meta(), drift001),
        (Drift002.meta(), drift002),
        (Drift003.meta(), drift003),
        (Affect001.meta(), affect001),
    ]
}

fn hex(d: gob_symbols::FacetDigest) -> String {
    d.to_string()
}

fn drift001(inputs: &Inputs) -> Vec<Raw> {
    let meta = Drift001.meta();
    let mut out = Vec::new();
    for d in &inputs.docs {
        let key = d.symbol.to_string();
        let Some(entry) = inputs.lock.entries.get(&key) else {
            continue;
        };
        let target = d.target.to_string();
        let mut say = |facet: &str, what: String| {
            out.push(Raw::new(
                meta,
                Some(d.span),
                format!(
                    "`{key}` is bound to `{target}` and its {facet} facet drifted since the ack: {what}; re-read both, then `frob ack {key}`"
                ),
                &d.symbol,
            ));
        };
        if let Some(rec) = inputs.graph.get(&d.symbol) {
            let cur = &rec.digests;
            if hex(cur.sig) != entry.sig {
                say("sig", "the signature changed under the doc".to_owned());
            }
            if hex(cur.body) != entry.body {
                say("body", "the body changed under the doc".to_owned());
            }
            if hex(cur.doc) != entry.doc {
                say("doc", "the doc comment changed".to_owned());
            }
        }
        if let (Some(rec), Some(was)) = (inputs.graph.get(&d.target), entry.target_digest(&target))
            && hex(section_digest(&rec.digests)) != was
        {
            say(
                "target",
                "the doc section changed under the code".to_owned(),
            );
        }
    }
    out
}

fn nearest_heading<'g>(inputs: &'g Inputs, target: &Symref) -> Option<(&'g str, usize)> {
    let want = target.name()?;
    inputs
        .graph
        .records()
        .filter(|r| r.kind == SymbolKind::Heading && r.symref.path() == target.path())
        .filter_map(|r| r.symref.name())
        .map(|slug| (slug, strsim::levenshtein(slug, want)))
        .min_by_key(|(slug, dist)| (*dist, *slug))
}

fn drift002(inputs: &Inputs) -> Vec<Raw> {
    let meta = Drift002.meta();
    let mut out = Vec::new();
    for d in &inputs.docs {
        if inputs.graph.get(&d.target).is_some() {
            continue;
        }
        let hint = if inputs.graph.get(&Symref::file(d.target.path())).is_none() {
            format!("the file `{}` is not in the repository", d.target.path())
        } else if let Some((slug, dist)) = nearest_heading(inputs, &d.target) {
            format!(
                "nearest heading is `{}#{slug}` (edit distance {dist})",
                d.target.path()
            )
        } else {
            format!("`{}` has no headings", d.target.path())
        };
        out.push(Raw::new(
            meta,
            Some(d.span),
            format!("frob:doc target `{}` does not exist; {hint}", d.target),
            &d.symbol,
        ));
    }
    out
}

fn drift003(inputs: &Inputs) -> Vec<Raw> {
    let meta = Drift003.meta();
    let covered: HashSet<String> = inputs.docs.iter().map(|d| d.symbol.to_string()).collect();
    let mut out = Vec::new();
    for (key, entry) in &inputs.lock.entries {
        if covered.contains(key) {
            continue;
        }
        let Ok(symref) = Symref::parse(key) else {
            continue;
        };
        let Some(rec) = inputs.graph.get(&symref) else {
            continue;
        };
        if hex(rec.digests.sig) != entry.sig {
            out.push(Raw::new(
                meta,
                None,
                format!(
                    "ack of `{key}` is stale: its signature changed since {} and no frob:doc covers it; `frob ack {key}` after review",
                    entry.acked_at
                ),
                &symref,
            ));
        }
    }
    out
}

/// Symrefs that contain `rec`: its parent chain and its file node.
fn containers(inputs: &Inputs, rec: &SymbolRecord) -> HashSet<Symref> {
    let mut out = HashSet::new();
    out.insert(Symref::file(rec.symref.path()));
    let mut cur = rec.parent.clone();
    while let Some(p) = cur {
        cur = inputs.graph.get(&p).and_then(|r| r.parent.clone());
        out.insert(p);
    }
    out
}

fn acked_after(entry: &LockEntry, dependent: &LockEntry) -> bool {
    let parse = |s: &str| s.parse::<jiff::Timestamp>().ok();
    matches!((parse(&dependent.acked_at), parse(&entry.acked_at)), (Some(d), Some(e)) if d > e)
}

fn affect001(inputs: &Inputs) -> Vec<Raw> {
    let meta = Affect001.meta();
    let mut out = Vec::new();
    for rec in inputs.graph.public_api() {
        let Some(entry) = inputs.lock.entries.get(&rec.symref.to_string()) else {
            continue;
        };
        if hex(rec.digests.sig) == entry.sig {
            continue;
        }
        let own = containers(inputs, rec);
        let stale: Vec<String> = inputs
            .graph
            .affects(&rec.symref)
            .into_iter()
            .filter(|d| !own.contains(d) && !matches!(d.target(), Target::File))
            .filter(|d| {
                !inputs
                    .lock
                    .entries
                    .get(&d.to_string())
                    .is_some_and(|e| acked_after(entry, e))
            })
            .map(|d| d.to_string())
            .collect();
        if stale.is_empty() {
            continue;
        }
        let shown: Vec<&str> = stale
            .iter()
            .take(LISTED_DEPENDENTS)
            .map(String::as_str)
            .collect();
        let more = stale.len().saturating_sub(shown.len());
        let tail = if more > 0 {
            format!(" and {more} more")
        } else {
            String::new()
        };
        out.push(Raw::new(
            meta,
            None,
            format!(
                "public `{}` changed its signature since its ack and {} dependent(s) were not re-acked: {}{tail}",
                rec.symref,
                stale.len(),
                shown.join(", ")
            ),
            &rec.symref,
        ));
    }
    out
}

/// Every finding of every rule, in rule order, uncached.
pub fn check(inputs: &Inputs) -> Vec<Finding> {
    raw_all(inputs).into_iter().map(Raw::into_finding).collect()
}

pub(crate) fn raw_all(inputs: &Inputs) -> Vec<Raw> {
    rules().into_iter().flat_map(|(_, f)| f(inputs)).collect()
}

/// Every finding of every rule for the repo at `root`, served from the gob-cache `repo_rule`
/// table when the inputs digest and rule version match.
pub fn evaluate(root: &Path, inputs: &Inputs) -> Vec<Finding> {
    let cache = Cache::open(&root.join(".frob"));
    let digest = inputs.digest();
    let mut files: FileInterner = inputs.files.clone();
    let mut out = Vec::new();
    for (meta, run) in rules() {
        let raws = repo_rule::load(&cache, &digest, meta, &mut files).unwrap_or_else(|| {
            let raws = run(inputs);
            repo_rule::store(&cache, &digest, meta, &inputs.files, &raws);
            raws
        });
        tracing::debug!(rule = meta.id, findings = raws.len(), "rule evaluated");
        out.extend(raws.into_iter().map(Raw::into_finding));
    }
    out
}

impl DocDirective {
    /// True when this directive binds `symref` or names it as its target.
    pub(crate) fn involves(&self, symref: &Symref) -> bool {
        &self.symbol == symref || &self.target == symref
    }
}
