//! Repo-scope rules and their cache.
//!
//! Repo rules read the whole repository, so their cache key is an inputs
//! digest: every walked file's path and content digest, the ledger tip and
//! the `[invariants]` table. Any edit anywhere therefore misses, which is
//! the correct (and simple) answer for rules that read the graph; the
//! per-file rules carry the fine-grained cache. The key also folds in the
//! rule version, so a bump misses.

use std::collections::HashMap;
use std::path::Path;
use std::time::Instant;

use frob_ack::{Affect001, Drift001, Drift002, Drift003};
use frob_ledger::rules::{Tick001, Tick003};
use frob_obligations::{Cov001, Inv001, Inv002, Todo002, evaluate_repo};
use gob_cache::Cache;
use gob_rules::{Finding, Rule, RuleId, RuleMeta, Severity};
use gob_text::{FileInterner, Span, TextRange, TextSize};

use crate::report::{Stats, Timing};
use crate::rules::Proc001;
use crate::snapshot::Snapshot;
use crate::store;

/// Digest of everything repo rules read (the repo-rule cache key component).
pub(crate) fn inputs_digest(snap: &Snapshot) -> String {
    let mut h = blake3::Hasher::new();
    for e in &snap.entries {
        h.update(e.path.as_bytes());
        h.update(b"\0");
        h.update(e.digest.as_bytes());
    }
    h.update(b"ledger\0");
    h.update(snap.ledger_tip().as_bytes());
    h.update(format!("{:?}", snap.invariants.forbid_imports).as_bytes());
    h.finalize().to_hex().to_string()
}

/// The row key: the inputs digest with the rule version folded in.
fn key(inputs: &str, meta: &RuleMeta) -> String {
    let mut h = blake3::Hasher::new();
    h.update(inputs.as_bytes());
    h.update(&meta.version.to_le_bytes());
    h.finalize().to_hex().to_string()
}

/// A group of rules computed together and cached per rule.
pub(crate) struct Group {
    /// Name used in timing (`repo:obligations`).
    pub name: &'static str,
    /// Rules the group emits.
    pub metas: Vec<&'static RuleMeta>,
}

/// Cached or freshly computed findings of `group`; counters go to `stats`.
pub(crate) fn cached(
    cache: &Cache,
    digest: &str,
    group: &Group,
    files: &mut FileInterner,
    stats: &mut Stats,
    compute: impl FnOnce(&mut FileInterner) -> Vec<Finding>,
) -> Vec<Finding> {
    let mut hit = Vec::new();
    let mut complete = true;
    for meta in &group.metas {
        let found = cache
            .get_repo_rule(&key(digest, meta), meta.id)
            .and_then(|b| store::decode(&b, |p| Some(files.intern(p))));
        if let Some(f) = found {
            hit.extend(f);
        } else {
            complete = false;
            break;
        }
    }
    if complete {
        stats.repo_hits += 1;
        tracing::debug!(
            group = group.name,
            findings = hit.len(),
            "repo group cache hit"
        );
        return hit;
    }
    stats.repo_misses += 1;
    let found = compute(files);
    let mut by_rule: HashMap<String, Vec<Finding>> = HashMap::new();
    for f in &found {
        by_rule
            .entry(f.rule.to_string())
            .or_default()
            .push(f.clone());
    }
    for meta in &group.metas {
        let mine = by_rule.remove(meta.id).unwrap_or_default();
        cache.put_repo_rule(&key(digest, meta), meta.id, &store::encode(&mine, files));
    }
    for (rule, strays) in by_rule {
        tracing::warn!(
            rule,
            count = strays.len(),
            group = group.name,
            "finding of an undeclared rule is not cached"
        );
    }
    tracing::debug!(
        group = group.name,
        findings = found.len(),
        "repo group computed"
    );
    found
}

/// Byte offset of the start of 1-based `line` in `text`.
fn line_start(text: &str, line: usize) -> usize {
    text.split_inclusive('\n')
        .take(line.saturating_sub(1))
        .map(str::len)
        .sum()
}

/// `PROC001` over the repository: one finding per forbidden `std::process` reference.
fn proc001(root: &Path, files: &mut FileInterner) -> Vec<Finding> {
    let id: RuleId = Proc001
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"));
    let mut out = Vec::new();
    for hit in gob_exec::proc001::scan(root) {
        let rel = hit
            .path
            .strip_prefix(root)
            .unwrap_or(&hit.path)
            .to_string_lossy()
            .replace('\\', "/");
        let text = std::fs::read_to_string(&hit.path).unwrap_or_default();
        let start = line_start(&text, hit.line) + hit.col.saturating_sub(1);
        let line_end = line_start(&text, hit.line + 1).min(text.len());
        let end = line_end.max(start);
        let to_size = |n: usize| TextSize::new(u32::try_from(n).unwrap_or(u32::MAX));
        let span = Span::new(
            files.intern(&rel),
            TextRange::new(to_size(start), to_size(end)),
        );
        out.push(Finding::new(
            id.clone(),
            Severity::Error,
            Some(span),
            format!(
                "`{}` uses the process API outside gob-exec and gob-git; spawn through gob_exec::Runner",
                hit.text
            ),
            &rel,
        ));
    }
    out
}

/// Run every repo-scope rule (cached) and return the raw findings.
pub(crate) fn run_repo_rules(
    snap: &Snapshot,
    cache: &Cache,
    files: &mut FileInterner,
    wanted: &dyn Fn(&RuleMeta) -> bool,
    stats: &mut Stats,
    timing: &mut Timing,
) -> Vec<Finding> {
    let digest = inputs_digest(snap);
    let mut out = Vec::new();
    let groups: [(Group, GroupFn); 5] = [
        (
            Group {
                name: "repo:obligations",
                metas: vec![Cov001.meta(), Todo002.meta(), Inv001.meta(), Inv002.meta()],
            },
            Box::new(|s, f| evaluate_repo(&s.obligations(), f)),
        ),
        (
            Group {
                name: "repo:ack",
                metas: vec![
                    Drift001.meta(),
                    Drift002.meta(),
                    Drift003.meta(),
                    Affect001.meta(),
                ],
            },
            Box::new(|s, _| frob_ack::check(&s.ack)),
        ),
        (
            Group {
                name: "repo:tests",
                metas: vec![frob_tests::Test001.meta()],
            },
            Box::new(|s, _| {
                let read = |p: &str| std::fs::read_to_string(s.root.join(p)).ok();
                frob_tests::test001_with_sources(&s.directives, &s.ack.graph, &read)
            }),
        ),
        (
            Group {
                name: "repo:ledger",
                metas: vec![Tick001.meta(), Tick003.meta()],
            },
            Box::new(|s, _| ledger_findings(s)),
        ),
        (
            Group {
                name: "repo:process",
                metas: vec![Proc001.meta()],
            },
            Box::new(|s, f| proc001(&s.root, f)),
        ),
    ];
    for (group, run) in groups {
        if !group.metas.iter().any(|m| wanted(m)) {
            tracing::debug!(group = group.name, "repo group skipped by --only");
            continue;
        }
        let started = Instant::now();
        out.extend(cached(cache, &digest, &group, files, stats, |f| {
            run(snap, f)
        }));
        timing.push(group.name, started.elapsed(), true);
    }
    out
}

/// A group's computation: the snapshot and the extendable interner in, raw findings out.
type GroupFn = Box<dyn FnOnce(&Snapshot, &mut FileInterner) -> Vec<Finding>>;

/// `TICK001` and `TICK003` from the ledger doctor (read-only); empty without a ledger.
fn ledger_findings(snap: &Snapshot) -> Vec<Finding> {
    let Some(state) = &snap.ledger else {
        return Vec::new();
    };
    match state.ledger.doctor(false) {
        Ok(report) => report.findings,
        Err(err) => {
            tracing::warn!(%err, "ledger doctor failed; TICK001 and TICK003 not evaluated");
            Vec::new()
        }
    }
}
