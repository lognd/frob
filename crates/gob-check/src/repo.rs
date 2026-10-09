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

use gob_cache::Cache;
use gob_rules::{Finding, Rule, RuleId, RuleMeta, Severity};
use gob_text::{FileInterner, Span, TextRange, TextSize};

use crate::config::CheckTable;
use crate::product::{FULL_ONLY_REASON, Product, RepoGroup, Snapshot};
use crate::report::{Stats, Tally};
use crate::rules::Proc001;
use crate::store;

/// Digest of everything repo rules read (the repo-rule cache key component).
///
/// Every walked file's path and digest, then the product's own bytes.
pub(crate) fn inputs_digest<P: Product>(product: &P, snap: &Snapshot<P>) -> String {
    let mut h = blake3::Hasher::new();
    for e in &snap.core.entries {
        h.update(e.path.as_bytes());
        h.update(b"\0");
        h.update(e.digest.as_bytes());
    }
    h.update(&product.repo_digest(snap));
    h.finalize().to_hex().to_string()
}

/// A repo rule's cache identity: its id and version (a version bump misses).
#[derive(Debug, Clone, Copy)]
pub(crate) struct RuleKey {
    /// Rule id.
    pub id: &'static str,
    /// Rule version.
    pub version: u32,
}

impl From<&'static RuleMeta> for RuleKey {
    fn from(meta: &'static RuleMeta) -> Self {
        Self {
            id: meta.id,
            version: meta.version,
        }
    }
}

impl From<&'static gob_rules::RuleDef> for RuleKey {
    fn from(def: &'static gob_rules::RuleDef) -> Self {
        Self {
            id: def.id,
            version: def.version,
        }
    }
}

/// The row key: the inputs digest with the rule version folded in.
fn key(inputs: &str, rule: RuleKey) -> String {
    let mut h = blake3::Hasher::new();
    h.update(inputs.as_bytes());
    h.update(&rule.version.to_le_bytes());
    h.finalize().to_hex().to_string()
}

/// Cached or freshly computed findings of `group`; counters go to `stats`.
pub(crate) fn cached(
    cache: &Cache,
    digest: &str,
    name: &str,
    rules: &[RuleKey],
    files: &mut FileInterner,
    stats: &mut Stats,
    compute: impl FnOnce(&mut FileInterner) -> Vec<Finding>,
) -> Vec<Finding> {
    let mut hit = Vec::new();
    let mut complete = true;
    for rule in rules {
        let found = cache
            .get_repo_rule(&key(digest, *rule), rule.id)
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
        tracing::debug!(group = name, findings = hit.len(), "repo group cache hit");
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
    // frob:ticket 01M42MGNE7XHTT1MR5CA6C2R1C
    // A failed evaluation is never stored: fixing its cause must re-evaluate, not replay the failure.
    let failed = found.iter().any(|f| {
        matches!(
            f.required,
            Some(gob_rules::RequiredReason::EvaluationFailed { .. })
        )
    });
    if failed {
        tracing::warn!(group = name, "evaluation failed; group result not cached");
        by_rule.clear();
    }
    for rule in rules.iter().filter(|_| !failed) {
        let mine = by_rule.remove(rule.id).unwrap_or_default();
        cache.put_repo_rule(&key(digest, *rule), rule.id, &store::encode(&mine, files));
    }
    for (rule, strays) in by_rule {
        tracing::warn!(
            rule,
            count = strays.len(),
            group = name,
            "finding of an undeclared rule is not cached"
        );
    }
    tracing::debug!(group = name, findings = found.len(), "repo group computed");
    found
}

/// Byte offset of the start of 1-based `line` in `text`.
fn line_start(text: &str, line: usize) -> usize {
    text.split_inclusive('\n')
        .take(line.saturating_sub(1))
        .map(str::len)
        .sum()
}

/// `PROC001` over the repository: one finding per spawning reference outside `spawners`.
fn proc001(root: &Path, spawners: &[String], files: &mut FileInterner) -> Vec<Finding> {
    let id: RuleId = Proc001
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"));
    let mut out = Vec::new();
    for hit in gob_exec::proc001::scan(root, spawners) {
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
                "`{}` uses a process-spawning API outside {}; spawn through gob_exec::Runner",
                hit.text,
                spawners.join(", ")
            ),
            &rel,
        ));
    }
    out
}

/// The neutral repo groups every product gets: `PROC001`, which is inert without `process_spawners`.
pub(crate) fn builtin_groups<P: Product>(spawners: Vec<String>) -> Vec<RepoGroup<P>> {
    vec![RepoGroup::new(
        "repo:process",
        vec![Proc001.meta()],
        move |s: &Snapshot<P>, f| proc001(&s.core.root, &spawners, f),
    )]
}

/// Run every repo-scope rule (cached) and return the raw findings.
///
/// Subject counts of every group that ran or hit the cache go to `tally.subjects`.
#[allow(clippy::too_many_arguments)] // one pass-wide context per argument; a bundle struct would only move them
pub(crate) fn run_repo_rules<P: Product>(
    product: &P,
    snap: &Snapshot<P>,
    cache: &Cache,
    files: &mut FileInterner,
    wanted: &dyn Fn(&RuleMeta) -> bool,
    tally: &mut Tally,
    table: &CheckTable,
    scoped: bool,
) -> Vec<Finding> {
    let digest = inputs_digest(product, snap);
    let mut out = Vec::new();
    let mut groups = product.repo_groups();
    groups.extend(builtin_groups(table.process_spawners.clone()));
    for group in groups {
        if !group.metas.iter().any(|m| wanted(m)) {
            tracing::debug!(group = group.name, "repo group skipped by --only");
            continue;
        }
        // frob:ticket 01M4HAJZA6JTNSSGJYV040TA9M
        if scoped && group.full_only {
            for meta in group.metas.iter().filter(|m| wanted(m)) {
                tally.fidelity.add_inapplicable(meta.id, FULL_ONLY_REASON);
            }
            tracing::info!(
                group = group.name,
                why = FULL_ONLY_REASON,
                "repo group not evaluated in a scoped run"
            );
            continue;
        }
        let started = Instant::now();
        out.extend(cached(
            cache,
            &digest,
            group.name,
            &group
                .metas
                .iter()
                .map(|m| RuleKey::from(*m))
                .collect::<Vec<_>>(),
            files,
            &mut tally.stats,
            |f| (group.run)(snap, f),
        ));
        for (rule, n) in (group.subjects)(snap) {
            tracing::debug!(rule, subjects = n, group = group.name, "subjects examined");
            tally.subjects.insert(rule.to_owned(), n);
        }
        tally.timing.push(group.name, started.elapsed(), true);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Runs `cached` for `PROC001` on a fresh interner; returns whether `compute` ran.
    fn ran(cache: &Cache) -> bool {
        let metas = [RuleKey::from(Proc001.meta())];
        let mut computed = false;
        let mut stats = Stats::default();
        let mut files = FileInterner::default();
        cached(
            cache,
            "inputs",
            "repo:process",
            &metas,
            &mut files,
            &mut stats,
            |_| {
                computed = true;
                Vec::new()
            },
        );
        computed
    }

    // frob:ticket 01M42MGNE7XHTT1MR5CA6C2R1C
    // frob:tests crates/gob-check/src/repo.rs::cached
    #[test]
    fn a_rule_level_evaluation_failure_is_never_cached_and_the_fixed_run_is_fresh() {
        let dir = tempfile::tempdir().unwrap();
        let cache = Cache::open(dir.path());
        let metas = [RuleKey::from(Proc001.meta())];
        let id: RuleId = "PROC001".parse().unwrap();
        let run = |fail: bool| {
            let mut computed = false;
            let found = cached(
                &cache,
                "inputs",
                "repo:process",
                &metas,
                &mut FileInterner::default(),
                &mut Stats::default(),
                |_| {
                    computed = true;
                    if !fail {
                        return Vec::new();
                    }
                    vec![
                        Finding::new(id.clone(), Severity::Unresolved, None, "boom", "repository")
                            .with_required(gob_rules::RequiredReason::EvaluationFailed {
                                rule: "PROC001".into(),
                                error: "boom".into(),
                            }),
                    ]
                },
            );
            (computed, found.len())
        };
        assert_eq!(run(true), (true, 1), "the failure is reported");
        assert_eq!(run(true), (true, 1), "and recomputed, not replayed");
        assert_eq!(
            run(false),
            (true, 0),
            "after the fix the run is fresh and clean"
        );
        assert_eq!(run(false), (false, 0), "a clean result is cached as before");
    }

    // frob:tests crates/gob-check/src/repo.rs::cached
    #[test]
    fn engines_never_share_a_cached_repo_group() {
        let dir = tempfile::tempdir().unwrap();
        let open = |e: &str| Cache::open(dir.path()).with_engine(e);
        assert!(ran(&open("a")), "cold run computes");
        assert!(!ran(&open("a")), "same engine hits");
        assert!(
            ran(&open("b")),
            "another engine over the same inputs recomputes"
        );
        assert!(!ran(&open("b")));
    }
}
