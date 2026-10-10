//! Per-file checks and their cached evaluation.
//!
//! A [`FileCheck`] evaluates one file and may emit findings of several
//! rules. Results are cached per (file digest, rule id, rule version,
//! side-input digest) in the `findings` table: the lookups run in parallel,
//! the misses are computed one after another (a product's inputs need not be
//! `Sync`) and stored, empty results included. Every (rule, file) pair a check
//! examines counts as one subject of that rule, cache hit or not.

use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::path::Path;
use std::sync::Arc;

use gob_cache::{Cache, FindingsKey};
use gob_rules::{Finding, RuleMeta, UnresolvedReason};
use gob_text::FileId;
use rayon::prelude::*;

use crate::applicability::{FileFacts, RuleRef, resolve};
use crate::core::{Core, FileIndex};
use crate::product::{Product, Snapshot};
use crate::status::{
    FidelityReport, SubjectStatus, hole_caveat_of, is_binary, opaque_finding_for,
    unresolved_finding_for,
};
use crate::store;

/// Thread-safe facts a check may use to decide applicability and its cache key.
pub struct SharedCtx<'a, P: Product> {
    /// Repository root.
    pub root: &'a Path,
    /// Path lookups of the walk.
    pub index: &'a FileIndex,
    /// The product's thread-safe facts.
    pub product: &'a P::Shared,
}

impl<P: Product> SharedCtx<'_, P> {
    /// Content digest (hex) of a walked file.
    pub fn digest_of(&self, path: &str) -> Option<&str> {
        self.index.digests.get(path).map(String::as_str)
    }

    /// True when `path` is an ancestor directory of a walked file.
    pub fn has_dir(&self, path: &str) -> bool {
        self.index.dirs.contains(path)
    }
}

/// Everything a check may read while computing a miss.
pub struct CheckCtx<'a, P: Product> {
    /// The thread-safe part.
    pub shared: &'a SharedCtx<'a, P>,
    /// The walk.
    pub core: &'a Core,
    /// The product's inputs.
    pub inputs: &'a P::Inputs,
}

/// A unit that checks one file and emits findings of the rules it declares.
pub trait FileCheck<P: Product>: Send + Sync {
    /// Every rule this check can emit; each gets its own cache entry per file.
    fn rules(&self) -> Vec<&'static RuleMeta>;

    /// Whether the check looks at `path` at all.
    fn applies(&self, _ctx: &SharedCtx<'_, P>, _path: &str) -> bool {
        true
    }

    /// Whether `rule` actually examines `path` (counts as one subject); defaults to true.
    ///
    /// A rule that cannot run (frob: `REF001` without a ledger) examines nothing
    /// and so reports zero subjects instead of a clean pass.
    fn examines(&self, _ctx: &SharedCtx<'_, P>, _rule: &RuleMeta, _path: &str) -> bool {
        true
    }

    /// Digest of what `rule` reads besides the file itself (empty when nothing).
    ///
    /// `text` is the file's content. A changed side input must change the digest.
    fn side_input(
        &self,
        _ctx: &SharedCtx<'_, P>,
        _rule: &RuleMeta,
        _path: &str,
        _text: &str,
    ) -> String {
        String::new()
    }

    /// Whether [`FileCheck::side_input`] reads the file text (the pipeline reads it only then).
    fn side_input_needs_text(&self, _rule: &RuleMeta) -> bool {
        false
    }

    /// Evaluate `path` (id `file`, content `text`).
    fn check(&self, ctx: &CheckCtx<'_, P>, file: FileId, path: &str, text: &str) -> Vec<Finding>;
}

/// The stored side-input digest: the check's own, with the file path folded in.
///
/// Findings name their file (spans, messages quoting symrefs), so two files
/// with identical content must not share an entry.
pub(crate) fn key_side_input(path: &str, side: &str) -> String {
    let mut h = blake3::Hasher::new();
    h.update(path.as_bytes());
    h.update(b"\0");
    h.update(side.as_bytes());
    h.finalize().to_hex().to_string()
}

/// Outcome of the per-file stage.
pub(crate) struct FileStage {
    /// Raw findings (exceptions not applied).
    pub findings: Vec<Finding>,
    /// Subjects (files) each rule examined, by rule id.
    pub subjects: BTreeMap<&'static str, usize>,
    /// Cache hits (one per check and file).
    pub hits: usize,
    /// Computed results.
    pub misses: usize,
    /// Per-language fidelity accounting of every checked file.
    pub fidelity: FidelityReport,
    /// `(path, rule)` pairs no rule may examine (`NotApplicable` or Unresolved), for declared rules too.
    pub blocked: HashMap<String, HashSet<&'static str>>,
}

/// What the status pass decided for the checked files.
struct Accounting {
    /// `(path, rule)` pairs the rule must not examine (`NotApplicable` or Unresolved).
    blocked: HashMap<String, HashSet<&'static str>>,
    /// Unresolved findings for blocked and caveated pairs.
    findings: Vec<Finding>,
    /// Per-language counts.
    fidelity: FidelityReport,
}

/// True when `info` is opaque and the file at `root/path` looks binary.
pub(crate) fn opaque_binary(root: &Path, path: &str, info: &gob_symbols::FileInfo) -> bool {
    if !info.is_opaque() {
        return false;
    }
    let mut head = vec![0u8; 4096];
    let n = std::fs::File::open(root.join(path))
        .and_then(|mut f| std::io::Read::read(&mut f, &mut head))
        .unwrap_or(0);
    is_binary(path, &head[..n])
}

/// Decide, for every checked file and file rule, examine / not applicable / unresolved.
///
/// `rules` holds the legacy file checks' rules and the declared (`RuleDef`) file rules alike.
fn account<P: Product>(
    product: &P,
    snap: &Snapshot<P>,
    rules: &[RuleRef],
    paths: &[String],
) -> Accounting {
    let mut acc = Accounting {
        blocked: HashMap::new(),
        findings: Vec::new(),
        fidelity: FidelityReport::default(),
    };
    let mut opaque: BTreeMap<&str, (&'static str, Vec<&str>)> = BTreeMap::new();
    for path in paths {
        let Some(info) = product.file_info(&snap.shared, path) else {
            continue;
        };
        let binary = opaque_binary(&snap.core.root, path, &info);
        let scanned = product.scans_text(path);
        let file = snap.core.index.ids.get(path).copied();
        let mut examined = false;
        let mut hole_site: Option<Option<crate::status::HoleSite>> = None;
        let mut unresolved: Vec<&str> = Vec::new();
        let mut family_total: BTreeMap<&str, (usize, usize)> = BTreeMap::new();
        for rule in rules {
            let entry = family_total.entry(rule.family).or_default();
            entry.0 += 1;
            let status = resolve(&rule.applies, &FileFacts::of(&info, binary, scanned));
            tracing::trace!(rule = rule.id, ?status, "subject status");
            match status {
                SubjectStatus::Examine => {
                    examined = true;
                    if let Some(why) = hole_caveat_of(&info, &rule.applies) {
                        unresolved.push(rule.id);
                        // frob:ticket 01M4GKD8WNG2NW2VAR1MBP382J
                        let site = file.zip(
                            hole_site
                                .get_or_insert_with(|| {
                                    std::fs::read_to_string(snap.core.root.join(path))
                                        .ok()
                                        .and_then(|t| crate::status::locate_hole(path, &t))
                                })
                                .as_ref(),
                        );
                        acc.findings.push(match site {
                            Some((file, site)) => crate::status::unresolved_finding_at(
                                rule.id, file, path, &why, site,
                            ),
                            None => unresolved_finding_for(
                                rule.id,
                                file,
                                path,
                                &why,
                                UnresolvedReason::Partial,
                            ),
                        });
                    }
                }
                SubjectStatus::NotApplicable(why) => {
                    entry.1 += 1;
                    tracing::debug!(path, rule = rule.id, %why, "not applicable");
                    acc.fidelity.add_not_applicable_reason(
                        &FidelityReport::label(&info),
                        rule.id,
                        &why,
                    );
                    acc.blocked.entry(path.clone()).or_default().insert(rule.id);
                }
                SubjectStatus::Unresolved(why) => {
                    tracing::info!(path, rule = rule.id, %why, "unresolved subject");
                    unresolved.push(rule.id);
                    acc.blocked.entry(path.clone()).or_default().insert(rule.id);
                    if info.is_opaque() {
                        opaque
                            .entry(rule.id)
                            .or_insert((rule.id, Vec::new()))
                            .1
                            .push(path);
                    } else {
                        acc.findings.push(unresolved_finding_for(
                            rule.id,
                            file,
                            path,
                            &why,
                            UnresolvedReason::Fidelity,
                        ));
                    }
                }
            }
        }
        let na: Vec<&str> = family_total
            .iter()
            .filter(|(_, (all, na))| all == na)
            .map(|(f, _)| *f)
            .collect();
        acc.fidelity.record(&info, examined, &na, &unresolved);
    }
    for (id, files) in opaque.into_values() {
        acc.findings.push(opaque_finding_for(id, &files));
    }
    acc
}

/// What the parallel lookup found for one (file, check) pair.
struct Lookup {
    check: usize,
    path: String,
    digest: String,
    keys: Vec<FindingsKey>,
    examined: Vec<&'static str>,
    hit: Option<Vec<Finding>>,
}

/// Rule id of `finding` as an owned string.
fn rule_of(f: &Finding) -> String {
    f.rule.to_string()
}

/// Run `checks` over `paths` with the findings cache; `declared` are the `RuleDef` file rules, accounted only.
#[allow(
    clippy::too_many_lines,
    reason = "lookup, compute and accounting read best as one staged function"
)]
pub(crate) fn run_file_checks<P: Product>(
    product: &P,
    snap: &Snapshot<P>,
    cache: &Cache,
    checks: &[Arc<dyn FileCheck<P>>],
    declared: &[RuleRef],
    paths: &[String],
) -> FileStage {
    let shared = SharedCtx::<P> {
        root: &snap.core.root,
        index: &snap.core.index,
        product: &snap.shared,
    };
    let metas: Vec<Vec<&'static RuleMeta>> = checks.iter().map(|c| c.rules()).collect();
    let (root, index) = (&snap.core.root, &snap.core.index);
    let mut rules: Vec<RuleRef> = unique_metas(&metas)
        .into_iter()
        .map(RuleRef::of_meta)
        .collect();
    rules.extend_from_slice(declared);
    let acc = account(product, snap, &rules, paths);
    let blocked = &acc.blocked;
    let lookups: Vec<Lookup> = paths
        .par_iter()
        .flat_map_iter(|path| {
            let mut out = Vec::new();
            let Some(digest) = index.digests.get(path) else {
                return out;
            };
            for (ci, check) in checks.iter().enumerate() {
                if !check.applies(&shared, path) {
                    continue;
                }
                let needs_text = metas[ci].iter().any(|m| check.side_input_needs_text(m));
                let text = if needs_text {
                    std::fs::read_to_string(root.join(path)).unwrap_or_default()
                } else {
                    String::new()
                };
                let keys: Vec<FindingsKey> = metas[ci]
                    .iter()
                    .map(|m| FindingsKey {
                        file_digest: digest.clone(),
                        rule_id: m.id.to_owned(),
                        rule_version: m.version,
                        side_input_digest: key_side_input(
                            path,
                            &check.side_input(&shared, m, path, &text),
                        ),
                    })
                    .collect();
                let examined: Vec<&'static str> = metas[ci]
                    .iter()
                    .filter(|m| check.examines(&shared, m, path))
                    .filter(|m| !blocked.get(path).is_some_and(|b| b.contains(m.id)))
                    .map(|m| m.id)
                    .collect();
                let hit = decode_all(cache, &keys, &index.ids);
                out.push(Lookup {
                    check: ci,
                    path: path.clone(),
                    digest: digest.clone(),
                    keys,
                    examined,
                    hit,
                });
            }
            out
        })
        .collect();

    let ctx = CheckCtx::<P> {
        shared: &shared,
        core: &snap.core,
        inputs: &snap.inputs,
    };
    let mut stage = FileStage {
        findings: Vec::new(),
        subjects: BTreeMap::new(),
        hits: 0,
        misses: 0,
        fidelity: FidelityReport::default(),
        blocked: acc.blocked.clone(),
    };
    for lookup in lookups {
        for rule in &lookup.examined {
            *stage.subjects.entry(*rule).or_default() += 1;
        }
        if let Some(found) = lookup.hit {
            stage.hits += 1;
            stage.findings.extend(found);
            continue;
        }
        stage.misses += 1;
        let Ok(text) = std::fs::read_to_string(snap.core.root.join(&lookup.path)) else {
            tracing::warn!(path = %lookup.path, "unreadable file skipped by per-file rules");
            continue;
        };
        let file = snap.core.index.ids[&lookup.path];
        let found = checks[lookup.check].check(&ctx, file, &lookup.path, &text);
        tracing::debug!(path = %lookup.path, findings = found.len(), digest = %lookup.digest, "per-file check computed");
        let mut by_rule: HashMap<String, Vec<Finding>> = HashMap::new();
        for f in &found {
            by_rule.entry(rule_of(f)).or_default().push(f.clone());
        }
        for key in &lookup.keys {
            let mine = by_rule.remove(&key.rule_id).unwrap_or_default();
            cache.put_findings(key, &store::encode(&mine, &snap.core.files));
        }
        for (rule, strays) in by_rule {
            tracing::warn!(
                rule,
                count = strays.len(),
                "finding of an undeclared rule is not cached"
            );
        }
        stage.findings.extend(found);
    }
    apply_accounting(&mut stage, snap, acc);
    stage
}

/// Every distinct rule of `metas`, first occurrence order.
fn unique_metas(metas: &[Vec<&'static RuleMeta>]) -> Vec<&'static RuleMeta> {
    let mut seen = BTreeSet::new();
    metas
        .iter()
        .flatten()
        .copied()
        .filter(|m| seen.insert(m.id))
        .collect()
}

/// Drop findings of blocked (file, rule) pairs and add the status findings and counts.
fn apply_accounting<P: Product>(stage: &mut FileStage, snap: &Snapshot<P>, acc: Accounting) {
    stage.findings.retain(|f| {
        let Some(span) = f.span else { return true };
        let Some(path) = snap.core.files.path(span.file) else {
            return true;
        };
        !acc.blocked
            .get(path)
            .is_some_and(|b| b.contains(f.rule.as_str()))
    });
    stage.findings.extend(acc.findings);
    stage.fidelity = acc.fidelity;
}

/// All keys hit and decode: the concatenated findings; otherwise `None`.
fn decode_all(
    cache: &Cache,
    keys: &[FindingsKey],
    ids: &HashMap<String, FileId>,
) -> Option<Vec<Finding>> {
    let mut out = Vec::new();
    for key in keys {
        let bytes = cache.get_findings(key)?;
        out.extend(store::decode(&bytes, |p| ids.get(p).copied())?);
    }
    Some(out)
}
