//! grimble as a [`gob_check::Product`]: the `.grmb` model files, the MDL rule group and the
//! exceptions written in the model.

use std::collections::BTreeMap;
use std::sync::{Arc, Mutex, PoisonError};

use gob_check::{
    CheckError, CollectCx, Collected, FileCheck, NoScope, Product, RepoGroup, Snapshot,
};
use gob_rules::{
    BoundException, ExceptionCtx, ExceptionKind, Finding, Registry, Resolved, RuleMeta, Severity,
    apply_exceptions,
};
use gob_text::{FileInterner, Span};
use grimble_model::{ModelFiles, check_model, rules::file_table};

use crate::bind_cache::{self, BindSummary};
use crate::config::{GrimbleTable, PRODUCT};
use crate::fidelity::language_tag;
use crate::model_view::ModelView;
use crate::{bind_models, read_models};

/// Extension of a model file.
pub const MODEL_EXTENSION: &str = ".grmb";

/// Thread-safe facts the pipeline reads for applicability and cache keys.
#[derive(Debug, Clone, Copy)]
pub struct GrimbleShared {
    /// `.grmb` files in the walk.
    pub model_files: usize,
}

/// Everything grimble's rules read besides the walk.
pub struct GrimbleInputs {
    /// The raw model files handed to `grimble-model`.
    pub model: ModelFiles,
    /// Entities, exceptions and file status derived from them.
    pub view: Arc<ModelView>,
    /// The rows of B, the SYS findings and subject counts (grimble-bind), possibly from the cache.
    pub binding: BindSummary,
}

/// What a run leaves behind for the document builder: the model view and which exception parked which finding.
#[derive(Default)]
pub(crate) struct Trace {
    /// The view built by the last collection.
    pub view: Option<Arc<ModelView>>,
    /// Files per language tag (`opaque` for unadapted files, `grmb` for models).
    pub languages: BTreeMap<String, usize>,
    /// Finding key (see [`park_key`]) to the id of the exception that suppressed it.
    pub parks: BTreeMap<String, String>,
    /// The rows of B as sibling `bindings` items.
    pub bindings: Vec<serde_json::Value>,
    /// True when the binding result was read from the cache.
    pub bind_cached: bool,
}

/// The grimble product driving the shared check pipeline.
#[derive(Default)]
pub struct Grimble {
    pub(crate) trace: Mutex<Trace>,
}

impl Grimble {
    /// A fresh product with an empty trace.
    pub fn new() -> Self {
        Self::default()
    }
}

/// Directive-scanner rules `check_model` also emits for `frob:` and `grimble:` comments in `.grmb` files.
const DIRECTIVE_RULES: [&str; 3] = ["PARSE001", "DSL001", "DSL002"];

/// The rules the model group emits: the MDL family and the directive-scanner rules it relays.
///
/// The families SYS, CAP, CYCLE/LARGE/DEAD, PACK, GPOL, NEAT, CI and DK register their own
/// groups as their tickets land.
pub fn model_rules() -> Vec<&'static RuleMeta> {
    let registry = Registry::global();
    let mut metas: Vec<&'static RuleMeta> = registry
        .iter()
        .filter(|m| m.product == PRODUCT && m.family == "MDL")
        .collect();
    metas.extend(DIRECTIVE_RULES.iter().filter_map(|id| registry.by_id(id)));
    metas
}

/// The binding rules (the SYS family `grimble-bind` evaluates).
pub fn binding_rules() -> Vec<&'static RuleMeta> {
    Registry::global()
        .iter()
        .filter(|m| m.product == PRODUCT && grimble_bind::RULES.contains(&m.id))
        .collect()
}

/// Key under which a suppressed finding is remembered: rule, file, offset and message.
pub(crate) fn park_key(f: &Finding, files: &FileInterner) -> String {
    let (path, start) = f.span.map_or((String::new(), 0), |s| {
        (
            files.path(s.file).unwrap_or_default().to_owned(),
            u32::from(s.range.start()),
        )
    });
    format!("{}|{path}|{start}|{}", f.rule, f.message)
}

/// Re-intern the spans of `findings` (ids of the model file table) in the pipeline interner.
fn remap(findings: Vec<Finding>, from: &FileInterner, to: &mut FileInterner) -> Vec<Finding> {
    findings
        .into_iter()
        .map(|mut f| {
            if let Some(span) = f.span
                && let Some(path) = from.path(span.file)
            {
                f.span = Some(Span::new(to.intern(path), span.range));
            }
            f
        })
        .collect()
}

impl Product for Grimble {
    type Shared = GrimbleShared;
    type Inputs = GrimbleInputs;
    type Scope = NoScope;

    fn name(&self) -> &'static str {
        PRODUCT
    }

    fn collect(&self, cx: &mut CollectCx<'_>) -> Result<Collected<Self>, CheckError> {
        let mut languages: BTreeMap<String, usize> = BTreeMap::new();
        for e in &cx.core.entries {
            *languages
                .entry(language_tag(&e.path, &e.language).to_owned())
                .or_default() += 1;
        }
        let table = GrimbleTable::load(&cx.core.root)?;
        let model = read_models(&cx.core.root, &cx.core.entries, &table);
        let started = std::time::Instant::now();
        let view = Arc::new(ModelView::build(&model));
        cx.timing.push("model", started.elapsed(), true);
        let started = std::time::Instant::now();
        let digest = bind_cache::digest(&cx.core.root, &cx.core.entries, &table);
        let key = bind_cache::key(&digest, cx.cache.engine());
        let cached = cx
            .cache
            .get_artifact(&key)
            .and_then(|b| BindSummary::decode(&b));
        let bind_cached = cached.is_some();
        let binding = if let Some(summary) = cached {
            tracing::info!(digest = %digest, rows = summary.bindings.len(), "binding reused from cache");
            summary
        } else {
            let summary = BindSummary::of(&bind_models(
                &cx.core.root,
                &cx.core.entries,
                &model,
                &table,
            ));
            cx.cache.put_artifact(&key, &summary.encode());
            tracing::info!(digest = %digest, rows = summary.bindings.len(), "binding computed and cached");
            summary
        };
        cx.timing.push("binding", started.elapsed(), true);
        {
            let mut trace = self.trace.lock().unwrap_or_else(PoisonError::into_inner);
            trace.view = Some(Arc::clone(&view));
            trace.languages = languages;
            trace.bindings.clone_from(&binding.bindings);
            trace.bind_cached = bind_cached;
        }
        Ok(Collected {
            shared: GrimbleShared {
                model_files: model.files.len(),
            },
            inputs: GrimbleInputs {
                model,
                view,
                binding,
            },
            findings: Vec::new(),
        })
    }

    fn file_checks(&self) -> Vec<Arc<dyn FileCheck<Self>>> {
        Vec::new()
    }

    fn repo_groups(&self) -> Vec<RepoGroup<Self>> {
        let metas = model_rules();
        let ids: Vec<&'static str> = metas.iter().map(|m| m.id).collect();
        vec![
            RepoGroup::new(
                "repo:model",
                metas,
                |s: &Snapshot<Self>, files: &mut FileInterner| {
                    let table = file_table(&s.inputs.model);
                    remap(check_model(&s.inputs.model), &table, files)
                },
            )
            .counting(move |s| {
                if s.shared.model_files == 0 {
                    return Vec::new();
                }
                ids.iter().map(|id| (*id, s.shared.model_files)).collect()
            }),
            RepoGroup::new(
                "repo:binding",
                binding_rules(),
                |s: &Snapshot<Self>, files: &mut FileInterner| {
                    s.inputs
                        .binding
                        .findings
                        .iter()
                        .cloned()
                        .filter_map(|f| f.into_finding(files))
                        .collect()
                },
            )
            .counting(|s| {
                s.inputs
                    .binding
                    .subjects
                    .iter()
                    .map(|(rule, n)| (*rule, *n))
                    .collect()
            }),
        ]
    }

    fn repo_digest(&self, _snap: &Snapshot<Self>) -> Vec<u8> {
        b"grimble/model/1".to_vec()
    }

    fn resolve_exceptions(
        &self,
        snap: &Snapshot<Self>,
        files: &FileInterner,
        raw: Vec<Finding>,
    ) -> Resolved {
        let rows = snap.inputs.view.bound();
        let bounds: Vec<BoundException> = rows.iter().map(|(_, b)| (*b).clone()).collect();
        let ctx = ExceptionCtx { files };
        let mut resolved = apply_exceptions(raw, &bounds, &ctx);
        // EXC016: an accept never parks an Unresolved finding.
        let (kept_back, parked): (Vec<_>, Vec<_>) =
            resolved.suppressed.into_iter().partition(|(f, e)| {
                f.severity == Severity::Unresolved && e.kind == ExceptionKind::Accept
            });
        resolved
            .findings
            .extend(kept_back.into_iter().map(|(f, _)| f));
        let mut parks = BTreeMap::new();
        for (f, _) in &parked {
            let best = rows
                .iter()
                .filter(|(_, b)| b.covers(f, &ctx))
                .min_by_key(|(_, b)| b.width());
            if let Some((i, _)) = best {
                parks.insert(
                    park_key(f, files),
                    snap.inputs.view.exceptions[*i].id.clone(),
                );
            }
        }
        tracing::info!(
            suppressed = parked.len(),
            exceptions = bounds.len(),
            "grimble exceptions applied"
        );
        self.trace
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .parks = parks;
        Resolved {
            findings: resolved.findings,
            suppressed: parked,
        }
    }
}
