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

use crate::product::{Product, RepoGroup, Snapshot};
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

/// The row key: the inputs digest with the rule version folded in.
fn key(inputs: &str, meta: &RuleMeta) -> String {
    let mut h = blake3::Hasher::new();
    h.update(inputs.as_bytes());
    h.update(&meta.version.to_le_bytes());
    h.finalize().to_hex().to_string()
}

/// Cached or freshly computed findings of `group`; counters go to `stats`.
pub(crate) fn cached(
    cache: &Cache,
    digest: &str,
    name: &str,
    metas: &[&'static RuleMeta],
    files: &mut FileInterner,
    stats: &mut Stats,
    compute: impl FnOnce(&mut FileInterner) -> Vec<Finding>,
) -> Vec<Finding> {
    let mut hit = Vec::new();
    let mut complete = true;
    for meta in metas {
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
    for meta in metas {
        let mine = by_rule.remove(meta.id).unwrap_or_default();
        cache.put_repo_rule(&key(digest, meta), meta.id, &store::encode(&mine, files));
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

/// The neutral repo groups every product gets: `PROC001`.
pub(crate) fn builtin_groups<P: Product>() -> Vec<RepoGroup<P>> {
    vec![RepoGroup::new(
        "repo:process",
        vec![Proc001.meta()],
        |s: &Snapshot<P>, f| proc001(&s.core.root, f),
    )]
}

/// Run every repo-scope rule (cached) and return the raw findings.
///
/// Subject counts of every group that ran or hit the cache go to `tally.subjects`.
pub(crate) fn run_repo_rules<P: Product>(
    product: &P,
    snap: &Snapshot<P>,
    cache: &Cache,
    files: &mut FileInterner,
    wanted: &dyn Fn(&RuleMeta) -> bool,
    tally: &mut Tally,
) -> Vec<Finding> {
    let digest = inputs_digest(product, snap);
    let mut out = Vec::new();
    let mut groups = product.repo_groups();
    groups.extend(builtin_groups());
    for group in groups {
        if !group.metas.iter().any(|m| wanted(m)) {
            tracing::debug!(group = group.name, "repo group skipped by --only");
            continue;
        }
        let started = Instant::now();
        out.extend(cached(
            cache,
            &digest,
            group.name,
            &group.metas,
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
        let metas = [Proc001.meta()];
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
