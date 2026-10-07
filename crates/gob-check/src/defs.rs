//! Running a product's declared rules (`RuleDef`s) through the pipeline (D107, ~GBBKJ6V).
//!
//! The legacy file checks and repo groups run beside this path until the migration tickets move
//! their rules over. A declared rule gets the same treatment a legacy one does: the one
//! applicability resolver decides per file (done in [`crate::filecheck`] together with the legacy
//! rules), results are cached per file digest or inputs digest, and a `must_measure` rule that
//! examined nothing is the required Unresolved. What is new is the rule's own `inapplicable()`:
//! a rule that cannot apply to this product at all is skipped, and its reason is reported once.

use std::collections::{BTreeMap, HashMap, HashSet};
use std::time::Instant;

use gob_cache::{Cache, FindingsKey};
use gob_rules::{Emitted, Finding, RuleDef};
use gob_text::FileInterner;

use crate::applicability::RuleRef;
use crate::filecheck::key_side_input;
use crate::product::{Product, Snapshot};
use crate::repo::{RuleKey, cached, inputs_digest};
use crate::report::Tally;
use crate::required::zero_subject_finding;
use crate::rule_set::{RuleEntry, RuleSet, Run};
use crate::store;

/// The declared rules that run this pass, and why the others do not.
pub(crate) struct Live<'a, P: Product> {
    /// Selected by `--only` and applicable to the product.
    pub entries: Vec<&'a RuleEntry<P>>,
    /// Rule id to the reason its own `inapplicable()` gave, once per rule.
    pub inapplicable: BTreeMap<&'static str, String>,
}

impl<'a, P: Product> Live<'a, P> {
    /// Ask every wanted rule whether it applies to this product at all.
    pub fn select(
        product: &P,
        snap: &Snapshot<P>,
        set: &'a RuleSet<P>,
        wanted: &dyn Fn(&RuleDef) -> bool,
    ) -> Self {
        let mut live = Self {
            entries: Vec::new(),
            inapplicable: BTreeMap::new(),
        };
        for entry in set.entries.iter().filter(|e| wanted(e.def)) {
            match (entry.inapplicable)(product, snap) {
                Some(why) => {
                    tracing::info!(rule = entry.def.id, %why, "declared rule inapplicable to this product");
                    live.inapplicable.insert(entry.def.id, why);
                }
                None => live.entries.push(entry),
            }
        }
        live
    }

    /// The live file rules, for the per-file applicability accounting.
    pub fn file_refs(&self) -> Vec<RuleRef> {
        self.entries
            .iter()
            .filter(|e| matches!(e.run, Run::File(_)))
            .map(|e| RuleRef::of_def(e.def))
            .collect()
    }

    /// The live repo rules, for the opaque-text roll-up.
    pub fn repo_refs(&self) -> Vec<RuleRef> {
        self.entries
            .iter()
            .filter(|e| matches!(e.run, Run::Repo(_)))
            .map(|e| RuleRef::of_def(e.def))
            .collect()
    }

    /// Record the reasons in the report's fidelity section.
    pub fn report_inapplicable(&self, tally: &mut Tally) {
        for (rule, why) in &self.inapplicable {
            tally.fidelity.add_inapplicable(rule, why);
        }
    }
}

/// Anchor `emitted` into findings of `def` (file id and path when the rule judged one file).
fn anchor(
    def: &RuleDef,
    emitted: Vec<Emitted>,
    file: Option<(gob_text::FileId, &str)>,
) -> Vec<Finding> {
    emitted
        .into_iter()
        .map(|e| e.into_finding(def, file.map(|f| f.0), file.map_or("repository", |f| f.1)))
        .collect()
}

/// Run the live declared file rules over `paths`, skipping the pairs `blocked` forbids.
///
/// `scoped` is true for a `--scope` run: a rule that examined no file there may simply have none
/// in scope, so only a positive count is recorded.
#[allow(
    clippy::too_many_arguments,
    reason = "the pipeline's per-pass state is passed explicitly, as for the legacy file stage"
)]
pub(crate) fn run_file_rules<P: Product>(
    product: &P,
    snap: &Snapshot<P>,
    cache: &Cache,
    live: &Live<'_, P>,
    paths: &[String],
    blocked: &HashMap<String, HashSet<&'static str>>,
    scoped: bool,
    tally: &mut Tally,
) -> Vec<Finding> {
    let mut out = Vec::new();
    for entry in &live.entries {
        let Run::File(run) = &entry.run else { continue };
        let def = entry.def;
        let mut examined = 0usize;
        for path in paths {
            if blocked.get(path).is_some_and(|b| b.contains(def.id)) {
                continue;
            }
            let (Some(digest), Some(&file)) = (
                snap.core.index.digests.get(path),
                snap.core.index.ids.get(path),
            ) else {
                continue;
            };
            examined += 1;
            let key = FindingsKey {
                file_digest: digest.clone(),
                rule_id: def.id.to_owned(),
                rule_version: def.version,
                side_input_digest: key_side_input(path, ""),
            };
            let hit = cache
                .get_findings(&key)
                .and_then(|b| store::decode(&b, |p| snap.core.index.ids.get(p).copied()));
            if let Some(found) = hit {
                tally.stats.file_hits += 1;
                out.extend(found);
                continue;
            }
            tally.stats.file_misses += 1;
            let Ok(text) = std::fs::read_to_string(snap.core.root.join(path)) else {
                tracing::warn!(
                    path,
                    rule = def.id,
                    "unreadable file skipped by declared rule"
                );
                continue;
            };
            let found = anchor(def, run(product, snap, &text), Some((file, path)));
            tracing::debug!(
                path,
                rule = def.id,
                findings = found.len(),
                "declared file rule computed"
            );
            cache.put_findings(&key, &store::encode(&found, &snap.core.files));
            out.extend(found);
        }
        if !scoped || examined > 0 {
            tally.subjects.insert(def.id.to_owned(), examined);
        }
    }
    out
}

/// Run the live declared repo rules (cached per inputs digest) and count `must_measure` subjects.
pub(crate) fn run_repo_rules<P: Product>(
    product: &P,
    snap: &Snapshot<P>,
    cache: &Cache,
    live: &Live<'_, P>,
    files: &mut FileInterner,
    tally: &mut Tally,
) -> Vec<Finding> {
    let digest = inputs_digest(product, snap);
    let mut out = Vec::new();
    for entry in &live.entries {
        let Run::Repo(run) = &entry.run else { continue };
        let def = entry.def;
        let started = Instant::now();
        let name = format!("repo:{}", def.id.to_ascii_lowercase());
        out.extend(cached(
            cache,
            &digest,
            &name,
            &[RuleKey::from(def)],
            files,
            &mut tally.stats,
            |_| anchor(def, run(product, snap), None),
        ));
        if let Some(count) = &entry.subjects {
            let n = count(product, snap);
            tracing::debug!(
                rule = def.id,
                subjects = n,
                "declared rule subjects measured"
            );
            tally.subjects.insert(def.id.to_owned(), n);
        }
        tally.timing.push(name, started.elapsed(), true);
    }
    out
}

/// One required Unresolved per wanted, applicable `must_measure` declared rule that examined zero subjects.
pub(crate) fn zero_subjects<P: Product>(
    set: &RuleSet<P>,
    wanted: &dyn Fn(&RuleDef) -> bool,
    inapplicable: &BTreeMap<&'static str, String>,
    subjects: &BTreeMap<String, usize>,
) -> Vec<Finding> {
    set.entries
        .iter()
        .map(|e| e.def)
        .filter(|d| d.must_measure && wanted(d) && !inapplicable.contains_key(d.id))
        .filter(|d| subjects.get(d.id) == Some(&0))
        .filter_map(|d| zero_subject_finding(d.id))
        .collect()
}
