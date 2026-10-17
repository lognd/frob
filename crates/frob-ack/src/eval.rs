//! The DRIFT and AFFECT evaluators and their entry points; the rule declarations are in `rules/`.

use std::collections::HashSet;
use std::path::Path;

use gob_cache::Cache;
use gob_lock::LockEntry;
use gob_rules::{Finding, RuleDecl, RuleDef, Severity};
use gob_symbols::{Status, SymbolKind, SymbolRecord, Symref, Target};
use gob_text::{FileInterner, Span};

use crate::inputs::{DocDirective, Inputs, section_digest};
use crate::repo_rule;
use crate::rules::affect001::Affect001;
use crate::rules::drift001::Drift001;
use crate::rules::drift002::Drift002;
use crate::rules::drift003::Drift003;
use crate::rules::drift004::Drift004;

/// How many dependent names an AFFECT001 message lists.
const LISTED_DEPENDENTS: usize = 5;

/// A finding before it becomes a [`Finding`]: plain data, cacheable.
#[derive(Debug, Clone)]
pub(crate) struct Raw {
    /// The rule that fired.
    pub meta: &'static RuleDef,
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
    fn new(
        meta: &'static RuleDef,
        span: Option<Span>,
        message: String,
        anchor: &impl ToString,
    ) -> Self {
        Self {
            meta,
            severity: meta.severity,
            span,
            message,
            anchor: anchor.to_string(),
        }
    }

    pub(crate) fn into_finding(self) -> Finding {
        let id = self.meta.id.parse().unwrap_or_else(|e| {
            unreachable!("the rule macro validated rule id {}: {e}", self.meta.id)
        });
        Finding::new(id, self.severity, self.span, self.message, &self.anchor)
    }
}

type RuleFn = fn(&Inputs) -> Vec<Raw>;

fn rules() -> [(&'static RuleDef, RuleFn); 5] {
    [
        (Drift001::DEF, drift001),
        (Drift002::DEF, drift002),
        (Drift003::DEF, drift003),
        (Drift004::DEF, drift004),
        (Affect001::DEF, affect001),
    ]
}

fn hex(d: gob_symbols::FacetDigest) -> String {
    d.to_string()
}

pub(crate) fn drift001(inputs: &Inputs) -> Vec<Raw> {
    let meta = Drift001::DEF;
    let mut out = Vec::new();
    if inputs.lock.is_stale() {
        return out;
    }
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
            if hex(cur.attr) != entry.attr {
                say("attr", "the attributes changed under the doc".to_owned());
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

pub(crate) fn drift002(inputs: &Inputs) -> Vec<Raw> {
    let meta = Drift002::DEF;
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

pub(crate) fn drift003(inputs: &Inputs) -> Vec<Raw> {
    let meta = Drift003::DEF;
    let covered: HashSet<String> = inputs.docs.iter().map(|d| d.symbol.to_string()).collect();
    let mut out = Vec::new();
    if inputs.lock.is_stale() {
        return out;
    }
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

pub(crate) fn drift004(inputs: &Inputs) -> Vec<Raw> {
    let meta = Drift004::DEF;
    inputs
        .lock
        .reattest()
        .into_iter()
        .map(|r| {
            Raw::new(
                meta,
                None,
                format!(
                    "lock entry `{}` was recorded under {}; its digests are not comparable, so it is not trusted; re-attest with `frob ack --all --reason ...`",
                    r.key,
                    r.why()
                ),
                &r.key,
            )
        })
        .collect()
}

/// True when some call edge of the graph names `name` without resolving to a target.
fn unknown_callers(inputs: &Inputs, name: &str) -> bool {
    inputs
        .graph
        .edges_with_status()
        .iter()
        .any(|e| e.status == Status::Unknown && e.name.as_deref() == Some(name))
}

/// The files that parsed with holes, with the hole count; symbols inside a hole are unseen.
pub fn partial_parse_files(graph: &gob_symbols::SymbolGraph) -> Vec<(String, u32)> {
    graph
        .files()
        .filter_map(|(p, i)| match i.parse_status {
            gob_symbols::ParseStatus::Partial { holes } => Some((p.to_owned(), holes)),
            _ => None,
        })
        .collect()
}

pub(crate) fn affect001(inputs: &Inputs) -> Vec<Raw> {
    let meta = Affect001::DEF;
    let mut out = Vec::new();
    if inputs.lock.is_stale() {
        return out;
    }
    let partial = partial_parse_files(&inputs.graph);
    if let Some((first, _)) = partial.first() {
        let mut raw = Raw::new(
            meta,
            None,
            format!(
                "{} file(s) parsed partially (first `{first}`); public symbols inside a parse hole are unseen, so AFFECT001 is undecided for them",
                partial.len()
            ),
            &"partial-parse",
        );
        raw.severity = Severity::Unresolved;
        out.push(raw);
    }
    for rec in inputs.graph.public_api() {
        let Some(entry) = inputs.lock.entries.get(&rec.symref.to_string()) else {
            continue;
        };
        if hex(rec.digests.sig) == entry.sig {
            continue;
        }
        let own = containers(inputs, rec);
        let (mut stale, mut maybe_stale): (Vec<String>, Vec<String>) = (Vec::new(), Vec::new());
        for (d, status) in inputs.graph.affects_with_status(&rec.symref) {
            let acked = inputs
                .lock
                .entries
                .get(&d.to_string())
                .is_some_and(|e| acked_after(entry, e));
            if own.contains(&d) || matches!(d.target(), Target::File) || acked {
                continue;
            }
            if status == Status::Must {
                stale.push(d.to_string());
            } else {
                maybe_stale.push(d.to_string());
            }
        }
        if stale.is_empty() {
            let unknown = rec
                .symref
                .name()
                .is_some_and(|n| unknown_callers(inputs, n));
            if !maybe_stale.is_empty() || unknown {
                tracing::info!(symref = %rec.symref, maybe = maybe_stale.len(), unknown, "AFFECT001 unresolved");
                let mut raw = Raw::new(
                    meta,
                    None,
                    format!(
                        "public `{}` changed its signature since its ack; its dependents cannot be decided ({} reached only through May edges, unresolved calls may name it)",
                        rec.symref,
                        maybe_stale.len()
                    ),
                    &rec.symref,
                );
                raw.severity = Severity::Unresolved;
                out.push(raw);
            }
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

/// Every raw finding of every rule, in rule order, uncached.
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
