//! grimble as a [`gob_check::Product`]: the `.grmb` model files, the MDL rule group and the
//! exceptions written in the model.

use std::collections::BTreeMap;
use std::sync::{Arc, Mutex, OnceLock, PoisonError};

use gob_check::{
    CheckError, CollectCx, Collected, FileCheck, NoScope, Product, RepoGroup, RuleSet, Snapshot,
};
use gob_rules::{
    BoundException, ExceptionCtx, ExceptionKind, Finding, Registry, Resolved, RuleDef, RuleMeta,
    Severity, Tier, apply_exceptions,
};
use gob_text::{FileInterner, Span};
use grimble_arch::{ArchInput, ArchReport};
use grimble_ci::{CiConfig, CiInput, CiReport};
use grimble_lints::pass::{PathFile, PathReport};
use grimble_model::{ModelFiles, check_model, file_table};

use crate::bind_cache::{self, BindSummary};
use crate::coh_pass::CohPassOptions;
use crate::coh002::Coh002Options;
use crate::config::{CohTable, GrimbleTable, PRODUCT, RuleOverrides};
use crate::fidelity::language_tag;
use crate::layers::ModelLayers;
use crate::model_view::ModelView;
use crate::report_cache;
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
    /// The CYCLE, LARGE and DEAD verdicts (grimble-arch), recomputed each run.
    pub arch: ArchReport,
    /// The CI and Dockerfile verdicts (grimble-ci), recomputed each run.
    pub ci: CiReport,
    /// The PATH001 to PATH003 verdicts (grimble-lints), recomputed each run.
    pub path: PathReport,
    /// The TIME001 and TIME002 verdicts (grimble-lints), cached like the PATH report.
    pub time: PathReport,
    /// The PAIR001 verdicts (grimble-lints), cached like the TIME report.
    pub pair: PathReport,
    /// The ERR001 to ERR003 verdicts (grimble-lints), cached like the PAIR report.
    pub err: PathReport,
    /// The UNITY201 and UNITY202 verdicts (grimble-lints), cached like the PAIR report.
    pub unity: PathReport,
    /// The COH report (COH002 and COH003 verdicts under the `[coh]` table and the model's layers).
    pub coh: PathReport,
    /// The `[rules.<id>]` severity overrides of `grimble.toml`.
    pub overrides: RuleOverrides,
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
    /// Rules whose whole scope is `NotApplicable` on this model, with the reason.
    pub not_applicable: BTreeMap<String, String>,
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
const DIRECTIVE_RULES: [&str; 5] = ["PARSE001", "PARSE002", "DSL001", "DSL002", "DSL003"];

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P
// frob:ticket 01M5HJ075VJZAP88EVTCX1MH8C
// frob:ticket 01M5HDAS62G7H4YY9FVG59GJ01
// frob:ticket 01M5HPSP14N3NCX5TNA9XDR1GY
/// The legacy metadata of a declared rule, leaked once per process (the legacy groups hold `&'static`).
fn legacy_meta(def: &'static RuleDef) -> &'static RuleMeta {
    let summary = def.summary();
    Box::leak(Box::new(RuleMeta {
        id: def.id,
        slug: def.slug,
        family: def.family,
        product: PRODUCT,
        severity: def.severity,
        summary,
        explanation: def.doc,
        tier: Tier::Universal,
        scope: def.scope,
        fix: def.fix,
        polarity: def.polarity,
        must_measure: def.must_measure,
        needs: def.needs,
        version: def.version,
        since: def.since,
        module: "grimble",
    }))
}

/// The legacy metadata of the declared rules in `defs`, built on first use.
fn legacy_metas(
    cell: &'static OnceLock<Vec<&'static RuleMeta>>,
    defs: &[&'static RuleDef],
) -> Vec<&'static RuleMeta> {
    cell.get_or_init(|| defs.iter().map(|d| legacy_meta(d)).collect())
        .clone()
}

/// The rules the model group emits: the MDL family declared in `grimble-model`.
fn model_metas() -> Vec<&'static RuleMeta> {
    static CELL: OnceLock<Vec<&'static RuleMeta>> = OnceLock::new();
    legacy_metas(&CELL, grimble_model::rules::METAS)
}

/// The binding rules (the SYS family `grimble-bind` declares).
fn binding_metas() -> Vec<&'static RuleMeta> {
    static CELL: OnceLock<Vec<&'static RuleMeta>> = OnceLock::new();
    legacy_metas(&CELL, grimble_bind::rules::METAS)
}

/// The architecture rules (the CYCLE, LARGE and DEAD families `grimble-arch` declares).
fn arch_metas() -> Vec<&'static RuleMeta> {
    static CELL: OnceLock<Vec<&'static RuleMeta>> = OnceLock::new();
    legacy_metas(&CELL, grimble_arch::rules::METAS)
}

// frob:ticket 01M5KDWHPF5YTVP64PYCXX0FRT
/// The CI workflow and Dockerfile rules `grimble-ci` declares, minus ids `gob-check` already owns.
fn ci_metas() -> Vec<&'static RuleMeta> {
    static CELL: OnceLock<Vec<&'static RuleMeta>> = OnceLock::new();
    legacy_metas(&CELL, grimble_ci::rules::METAS)
}

/// The host-path portability rules (the PATH family `grimble-lints` declares).
fn path_metas() -> Vec<&'static RuleMeta> {
    lint_metas()
        .into_iter()
        .filter(|m| {
            !["TIME", "PAIR", "ERR", "UNITY"]
                .iter()
                .any(|f| m.id.starts_with(f))
        })
        .collect()
}

/// Every rule `grimble-lints` declares (the PATH, TIME, PAIR, ERR and UNITY families).
fn lint_metas() -> Vec<&'static RuleMeta> {
    static CELL: OnceLock<Vec<&'static RuleMeta>> = OnceLock::new();
    legacy_metas(&CELL, grimble_lints::rules::METAS)
}

/// The clock-handling rules (the TIME family `grimble-lints` declares).
fn time_metas() -> Vec<&'static RuleMeta> {
    lint_metas()
        .into_iter()
        .filter(|m| m.id.starts_with("TIME"))
        .collect()
}

/// The acquire-and-release pairing rules (the PAIR family `grimble-lints` declares).
fn pair_metas() -> Vec<&'static RuleMeta> {
    lint_metas()
        .into_iter()
        .filter(|m| m.id.starts_with("PAIR"))
        .collect()
}

/// The swallowed-error rules (the ERR family `grimble-lints` declares).
fn err_metas() -> Vec<&'static RuleMeta> {
    lint_metas()
        .into_iter()
        .filter(|m| m.id.starts_with("ERR"))
        .collect()
}

/// The Unity hot-code rules (the UNITY family `grimble-lints` declares).
fn unity_metas() -> Vec<&'static RuleMeta> {
    lint_metas()
        .into_iter()
        .filter(|m| m.id.starts_with("UNITY"))
        .collect()
}

/// The cohesion rules (the COH family this crate declares).
fn coh_metas() -> Vec<&'static RuleMeta> {
    static CELL: OnceLock<Vec<&'static RuleMeta>> = OnceLock::new();
    legacy_metas(&CELL, crate::rules::METAS)
}

/// Every rule grimble reports: the global registry plus the declared MDL, SYS, architecture, path and time rules (for slugs and polarity).
pub(crate) fn registry() -> &'static Registry {
    static CELL: OnceLock<Registry> = OnceLock::new();
    CELL.get_or_init(|| {
        let global = Registry::global();
        let metas = global
            .iter()
            .chain(model_metas())
            .chain(binding_metas())
            .chain(arch_metas())
            .chain(
                ci_metas()
                    .into_iter()
                    .filter(|m| global.by_id(m.id).is_none()),
            )
            .chain(lint_metas())
            .chain(coh_metas());
        Registry::from_metas(metas)
    })
}

/// The directive-scanner rules `check_model` relays; they are still legacy `RuleMeta` rules.
fn directive_metas() -> Vec<&'static RuleMeta> {
    let registry = Registry::global();
    DIRECTIVE_RULES
        .iter()
        .filter_map(|id| registry.by_id(id))
        .collect()
}

/// The reason the declared rule `def` does not apply on this model, from the binding.
fn inapplicable(_: &Grimble, snap: &Snapshot<Grimble>, def: &'static RuleDef) -> Option<String> {
    snap.inputs
        .binding
        .not_applicable
        .get(def.id)
        .cloned()
        .or_else(|| snap.inputs.arch.not_applicable.get(def.id).cloned())
        .or_else(|| snap.inputs.ci.not_applicable.get(def.id).cloned())
        .or_else(|| snap.inputs.path.not_applicable.get(def.id).cloned())
        .or_else(|| snap.inputs.time.not_applicable.get(def.id).cloned())
        .or_else(|| snap.inputs.pair.not_applicable.get(def.id).cloned())
        .or_else(|| snap.inputs.err.not_applicable.get(def.id).cloned())
        .or_else(|| snap.inputs.unity.not_applicable.get(def.id).cloned())
        .or_else(|| snap.inputs.coh.not_applicable.get(def.id).cloned())
}

// frob:ticket 01M5KDWHPF5YTVP64PYCXX0FRT
/// Run the CI and Dockerfile rules over the walk with the default `CiConfig` (uncached, so the files CI012 reads beyond the walk are never stale).
fn ci_report(entries: &[gob_walk::FileEntry], read: &dyn Fn(&str) -> Option<String>) -> CiReport {
    let files: Vec<String> = entries.iter().map(|e| e.path.clone()).collect();
    let report = grimble_ci::analyze(&CiInput {
        files: &files,
        read,
        config: &CiConfig::default(),
    });
    tracing::info!(
        findings = report.findings.len(),
        not_applicable = report.not_applicable.len(),
        "ci report computed"
    );
    report
}

/// Run the PATH rules over every Rust, Python, TypeScript and C# file of the walk (uncached).
fn path_report(
    entries: &[gob_walk::FileEntry],
    read: &dyn Fn(&str) -> Option<String>,
) -> PathReport {
    let texts: Vec<(&str, gob_languages::Language, String)> = entries
        .iter()
        .filter_map(|e| {
            let language = gob_languages::Language::detect(&e.path)?;
            read(&e.path).map(|text| (e.path.as_str(), language, text))
        })
        .collect();
    let files: Vec<PathFile<'_>> = texts
        .iter()
        .map(|(path, language, text)| PathFile {
            path,
            language: *language,
            text,
        })
        .collect();
    grimble_lints::pass::analyze(&files, &grimble_lints::path::Options::default())
}

/// Run the TIME rules over every Rust and Python file of the walk (uncached).
fn time_report(
    entries: &[gob_walk::FileEntry],
    read: &dyn Fn(&str) -> Option<String>,
) -> PathReport {
    let texts: Vec<(&str, gob_languages::Language, String)> = entries
        .iter()
        .filter_map(|e| {
            let language = gob_languages::Language::detect(&e.path)?;
            read(&e.path).map(|text| (e.path.as_str(), language, text))
        })
        .collect();
    let files: Vec<PathFile<'_>> = texts
        .iter()
        .map(|(path, language, text)| PathFile {
            path,
            language: *language,
            text,
        })
        .collect();
    grimble_lints::time_pass::analyze(&files)
}

/// Run PAIR001 over every TypeScript and JavaScript file of the walk (uncached).
fn pair_report(
    entries: &[gob_walk::FileEntry],
    read: &dyn Fn(&str) -> Option<String>,
) -> PathReport {
    let texts: Vec<(&str, gob_languages::Language, String)> = entries
        .iter()
        .filter_map(|e| {
            let language = gob_languages::Language::detect(&e.path)?;
            read(&e.path).map(|text| (e.path.as_str(), language, text))
        })
        .collect();
    let files: Vec<PathFile<'_>> = texts
        .iter()
        .map(|(path, language, text)| PathFile {
            path,
            language: *language,
            text,
        })
        .collect();
    grimble_lints::pair_pass::analyze(&files)
}

/// Run ERR001 to ERR003 over the Rust, Python, TypeScript and C# files of the walk (uncached).
fn err_report(
    entries: &[gob_walk::FileEntry],
    read: &dyn Fn(&str) -> Option<String>,
) -> PathReport {
    let texts: Vec<(&str, gob_languages::Language, String)> = entries
        .iter()
        .filter_map(|e| {
            let language = gob_languages::Language::detect(&e.path)?;
            read(&e.path).map(|text| (e.path.as_str(), language, text))
        })
        .collect();
    let files: Vec<PathFile<'_>> = texts
        .iter()
        .map(|(path, language, text)| PathFile {
            path,
            language: *language,
            text,
        })
        .collect();
    grimble_lints::err_pass::analyze(&files)
}

/// Run UNITY201, UNITY202, UNITY301 and UNITY302 over the walk (uncached).
// frob:ticket 01M5HGRWG7RDR3DTS7PT08HTWJ
fn unity_report(
    entries: &[gob_walk::FileEntry],
    read: &dyn Fn(&str) -> Option<String>,
) -> PathReport {
    let texts: Vec<(&str, gob_languages::Language, String)> = entries
        .iter()
        .filter_map(|e| {
            let language = gob_languages::Language::detect(&e.path)?;
            read(&e.path).map(|text| (e.path.as_str(), language, text))
        })
        .collect();
    let files: Vec<PathFile<'_>> = texts
        .iter()
        .map(|(path, language, text)| PathFile {
            path,
            language: *language,
            text,
        })
        .collect();
    let setting_texts: Vec<(&str, String)> = entries
        .iter()
        .filter(|e| grimble_lints::unity_pass::is_project_settings(&e.path))
        .filter_map(|e| read(&e.path).map(|text| (e.path.as_str(), text)))
        .collect();
    let settings: Vec<grimble_lints::unity_pass::SettingsFile<'_>> = setting_texts
        .iter()
        .map(|(path, text)| grimble_lints::unity_pass::SettingsFile { path, text })
        .collect();
    grimble_lints::unity_pass::analyze_all(&files, &settings)
}

/// Run COH002 and COH003 over every Rust, Python and TypeScript file of the walk (uncached).
fn coh_report(
    entries: &[gob_walk::FileEntry],
    read: &dyn Fn(&str) -> Option<String>,
    opts: &CohPassOptions,
) -> PathReport {
    let texts: Vec<(&str, gob_languages::Language, String)> = entries
        .iter()
        .filter_map(|e| {
            let language = gob_languages::Language::detect(&e.path)?;
            read(&e.path).map(|text| (e.path.as_str(), language, text))
        })
        .collect();
    let files: Vec<PathFile<'_>> = texts
        .iter()
        .map(|(path, language, text)| PathFile {
            path,
            language: *language,
            text,
        })
        .collect();
    crate::coh_pass::analyze(&files, opts)
}

/// The cache kind of the COH report: it embeds a digest of the vocabularies, so a changed `[coh]` misses.
fn coh_kind(opts: &CohPassOptions) -> String {
    // The version tag invalidates reports cached before COH003 joined the pass; the model's layers
    // are a function of the walk digest, which already keys the artifact.
    let mut text = String::from("layers-v2\u{1f}");
    text.push_str(&opts.coh002.effect_calls.join("\n"));
    text.push('\u{1f}');
    text.push_str(&opts.coh002.trivial.join("\n"));
    text.push('\u{1f}');
    text.push_str(&opts.max_level_spread.to_string());
    format!("coh-{}", gob_walk::Digest::of(text.as_bytes()))
}

/// Run the architecture rules over the walk (graph built from the bound code, uncached).
fn arch_report(
    root: &std::path::Path,
    entries: &[gob_walk::FileEntry],
    table: &GrimbleTable,
    read: &dyn Fn(&str) -> Option<String>,
) -> ArchReport {
    let code = grimble_bind::code::Code::build(root, entries);
    let graph = grimble_bind::edges::build_graph(root, &code);
    let mut deps = gob_symbols::CrateDeps::new(root);
    let crates: BTreeMap<String, String> = entries
        .iter()
        .filter_map(|e| deps.crate_of(&e.path).map(|c| (e.path.clone(), c)))
        .collect();
    grimble_arch::analyze(&ArchInput {
        graph: &graph,
        crates: &crates,
        large_lines: usize::try_from(table.large_lines).unwrap_or(usize::MAX),
        dup_min_tokens: usize::try_from(table.dup_min_tokens).unwrap_or(usize::MAX),
        dup_min_occurrences: usize::try_from(table.dup_min_occurrences).unwrap_or(usize::MAX),
        read,
    })
}

// frob:ticket 01M5KDWHPF5YTVP64PYCXX0FRT
/// Drop each native grimble-ci finding whose rule and file a bound tool (zizmor) also reported.
///
/// Policy: the bound tool stage is authoritative for a (rule, file) pair, because the CI001, CI006,
/// CI007 and CI010 verdicts of `grimble-ci` are lexical fallbacks of the zizmor audits. Line numbers
/// and messages are ignored when matching, since the two sources never agree on them. When the tool
/// reports nothing for the pair (or is absent) the native finding stands.
pub(crate) fn dedupe_ci(raw: Vec<Finding>, ci: &CiReport, files: &FileInterner) -> Vec<Finding> {
    let path_of = |f: &Finding| {
        f.span
            .and_then(|s| files.path(s.file))
            .unwrap_or_default()
            .to_owned()
    };
    let is_ci = |f: &Finding| {
        grimble_ci::rules::METAS
            .iter()
            .any(|d| d.id == f.rule.as_str())
    };
    let native = |f: &Finding| {
        let path = path_of(f);
        ci.findings
            .iter()
            .any(|n| n.rule == f.rule.as_str() && n.file == path && n.message == f.message)
    };
    let tool_pairs: std::collections::BTreeSet<(String, String)> = raw
        .iter()
        .filter(|f| is_ci(f) && !native(f))
        .map(|f| (f.rule.as_str().to_owned(), path_of(f)))
        .collect();
    if tool_pairs.is_empty() {
        return raw;
    }
    raw.into_iter()
        .filter(|f| {
            let dup = is_ci(f)
                && native(f)
                && tool_pairs.contains(&(f.rule.as_str().to_owned(), path_of(f)));
            if dup {
                tracing::info!(rule = %f.rule, file = %path_of(f), "native CI finding dropped: a bound tool reported the same rule for the file");
            }
            !dup
        })
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

/// The architecture and PATH reports of the walk, from the cache when `digest` has them.
#[allow(
    clippy::too_many_lines,
    reason = "one cache lookup, compute and store block per report family"
)]
fn reports(
    cx: &mut CollectCx<'_>,
    digest: &str,
    table: &GrimbleTable,
    coh_opts: &CohPassOptions,
) -> (
    ArchReport,
    PathReport,
    PathReport,
    PathReport,
    PathReport,
    PathReport,
    PathReport,
) {
    // The architecture and PATH reports are pure in the same digest plus `large_lines`, so a
    // hit skips reading and parsing every file (~SNJ3PH5).
    let started = std::time::Instant::now();
    let engine = cx.cache.engine().to_owned();
    // The DUP001 knobs change the arch report, so they are part of its key.
    let arch_kind = format!(
        "arch-{}-{}",
        table.dup_min_tokens, table.dup_min_occurrences
    );
    let arch_key = report_cache::key(&arch_kind, digest, &engine, table.large_lines);
    let path_key = report_cache::key("path", digest, &engine, table.large_lines);
    let arch_hit = cx
        .cache
        .get_artifact(&arch_key)
        .and_then(|b| report_cache::decode_arch(&b));
    let path_hit = cx
        .cache
        .get_artifact(&path_key)
        .and_then(|b| report_cache::decode_path(&b));
    let time_key = report_cache::key("time", digest, &engine, table.large_lines);
    let time_hit = cx
        .cache
        .get_artifact(&time_key)
        .and_then(|b| report_cache::decode_path(&b));
    let pair_key = report_cache::key("pair", digest, &engine, table.large_lines);
    let pair_hit = cx
        .cache
        .get_artifact(&pair_key)
        .and_then(|b| report_cache::decode_path(&b));
    let err_key = report_cache::key("err-v1", digest, &engine, table.large_lines);
    let err_hit = cx
        .cache
        .get_artifact(&err_key)
        .and_then(|b| report_cache::decode_path(&b));
    let unity_key = report_cache::key("unity", digest, &engine, table.large_lines);
    let unity_hit = cx
        .cache
        .get_artifact(&unity_key)
        .and_then(|b| report_cache::decode_path(&b));
    let coh_key = report_cache::key(&coh_kind(coh_opts), digest, &engine, table.large_lines);
    let coh_hit = cx
        .cache
        .get_artifact(&coh_key)
        .and_then(|b| report_cache::decode_path(&b));
    let pair_cached = pair_hit.is_some();
    let err_cached = err_hit.is_some();
    let unity_cached = unity_hit.is_some();
    let (arch_cached, path_cached, time_cached, coh_cached) = (
        arch_hit.is_some(),
        path_hit.is_some(),
        time_hit.is_some(),
        coh_hit.is_some(),
    );
    let (arch, path, time, pair, err, unity, coh) = if let (
        Some(arch),
        Some(path),
        Some(time),
        Some(pair),
        Some(err),
        Some(unity),
        Some(coh),
    ) = (
        arch_hit.clone(),
        path_hit.clone(),
        time_hit.clone(),
        pair_hit.clone(),
        err_hit.clone(),
        unity_hit.clone(),
        coh_hit.clone(),
    ) {
        tracing::info!(digest = %digest, "architecture, path, time, pair, err, unity and coh reports reused from cache");
        (arch, path, time, pair, err, unity, coh)
    } else {
        // One reader for both passes: `Core::text` opens the repository per call, which on
        // a 20k-file walk is the dominant cost of the run.
        let (arch, arch_took, path, path_took, time, pair, err, unity, coh) =
            cx.core.with_content(|reader| {
                let reader = std::cell::RefCell::new(reader);
                let read = |p: &str| reader.borrow_mut().read_text(p).ok();
                let started = std::time::Instant::now();
                let arch = arch_hit
                    .unwrap_or_else(|| arch_report(&cx.core.root, &cx.core.entries, table, &read));
                let arch_took = started.elapsed();
                let started = std::time::Instant::now();
                let path = path_hit.unwrap_or_else(|| path_report(&cx.core.entries, &read));
                let path_took = started.elapsed();
                let time = time_hit.unwrap_or_else(|| time_report(&cx.core.entries, &read));
                let pair = pair_hit.unwrap_or_else(|| pair_report(&cx.core.entries, &read));
                let err = err_hit.unwrap_or_else(|| err_report(&cx.core.entries, &read));
                let unity = unity_hit.unwrap_or_else(|| unity_report(&cx.core.entries, &read));
                let coh = coh_hit.unwrap_or_else(|| coh_report(&cx.core.entries, &read, coh_opts));
                (
                    arch, arch_took, path, path_took, time, pair, err, unity, coh,
                )
            });
        if !arch_cached {
            cx.cache
                .put_artifact(&arch_key, &report_cache::encode_arch(&arch));
        }
        if !path_cached {
            cx.cache
                .put_artifact(&path_key, &report_cache::encode_path(&path));
        }
        if !time_cached {
            cx.cache
                .put_artifact(&time_key, &report_cache::encode_path(&time));
        }
        if !pair_cached {
            cx.cache
                .put_artifact(&pair_key, &report_cache::encode_path(&pair));
        }
        if !err_cached {
            cx.cache
                .put_artifact(&err_key, &report_cache::encode_path(&err));
        }
        if !unity_cached {
            cx.cache
                .put_artifact(&unity_key, &report_cache::encode_path(&unity));
        }
        if !coh_cached {
            cx.cache
                .put_artifact(&coh_key, &report_cache::encode_path(&coh));
        }
        tracing::info!(
            ?arch_took,
            ?path_took,
            "architecture and path reports computed"
        );
        (arch, path, time, pair, err, unity, coh)
    };
    cx.timing.push("architecture", started.elapsed(), false);
    cx.timing.push("path", std::time::Duration::ZERO, false);
    cx.timing.push("time", std::time::Duration::ZERO, false);
    cx.timing.push("pair", std::time::Duration::ZERO, false);
    cx.timing.push("err", std::time::Duration::ZERO, false);
    cx.timing.push("unity", std::time::Duration::ZERO, false);
    cx.timing.push("coh", std::time::Duration::ZERO, false);
    (arch, path, time, pair, err, unity, coh)
}

/// A repo group over the findings of one `grimble-lints` report (`pick` names it on the inputs).
fn report_group(
    id: &'static str,
    metas: Vec<&'static RuleMeta>,
    pick: fn(&GrimbleInputs) -> &PathReport,
) -> RepoGroup<Grimble> {
    RepoGroup::new(
        id,
        metas,
        move |s: &Snapshot<Grimble>, files: &mut FileInterner| {
            pick(&s.inputs)
                .findings
                .iter()
                .cloned()
                .filter_map(|f| f.into_finding(files))
                .collect()
        },
    )
    .counting(move |s| {
        pick(&s.inputs)
            .subjects
            .iter()
            .map(|(rule, n)| (*rule, *n))
            .collect()
    })
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
        let overrides = RuleOverrides::load(&cx.core.root, cx.core.text("grimble.toml"))?;
        for id in overrides.unknown_ids(|id| registry().iter().any(|m| m.id == id)) {
            tracing::warn!(rule = id, "[rules] names no grimble rule; ignored here");
        }
        let model = read_models(&cx.core.root, &cx.core.entries, &table, &mut |p| {
            cx.core.bytes(p)
        });
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
        let coh_table = CohTable::load(&cx.core.root)?;
        let coh_opts = CohPassOptions {
            coh002: Coh002Options::from(&coh_table),
            max_level_spread: u32::try_from(coh_table.max_level_spread).unwrap_or(u32::MAX),
            model: ModelLayers::from_model(&model),
        };
        let (arch, path, time, pair, err, unity, coh) = reports(cx, &digest, &table, &coh_opts);
        let started = std::time::Instant::now();
        let ci = cx.core.with_content(|reader| {
            let reader = std::cell::RefCell::new(reader);
            ci_report(&cx.core.entries, &|p| reader.borrow_mut().read_text(p).ok())
        });
        cx.timing.push("ci", started.elapsed(), false);
        {
            let mut trace = self.trace.lock().unwrap_or_else(PoisonError::into_inner);
            trace.view = Some(Arc::clone(&view));
            trace.languages = languages;
            trace.bindings.clone_from(&binding.bindings);
            trace.bind_cached = bind_cached;
            trace.not_applicable = binding
                .not_applicable
                .iter()
                .chain(&arch.not_applicable)
                .chain(&ci.not_applicable)
                .chain(&path.not_applicable)
                .chain(&time.not_applicable)
                .chain(&pair.not_applicable)
                .chain(&err.not_applicable)
                .chain(&unity.not_applicable)
                .chain(&coh.not_applicable)
                .map(|(rule, why)| ((*rule).to_owned(), why.clone()))
                .collect();
        }
        Ok(Collected {
            shared: GrimbleShared {
                model_files: model.files.len(),
            },
            inputs: GrimbleInputs {
                model,
                view,
                binding,
                arch,
                ci,
                path,
                time,
                pair,
                err,
                unity,
                coh,
                overrides,
            },
            findings: Vec::new(),
        })
    }

    fn rule_set(&self) -> RuleSet<Self> {
        let mut set = RuleSet::new();
        for def in grimble_model::rules::METAS
            .iter()
            .chain(grimble_bind::rules::METAS)
            .chain(grimble_arch::rules::METAS)
            .chain(grimble_ci::rules::METAS)
            .chain(grimble_lints::rules::METAS)
            .chain(crate::rules::METAS)
            .copied()
        {
            set = set.stage_when(def, move |p, snap| inapplicable(p, snap, def));
        }
        set
    }

    fn file_checks(&self) -> Vec<Arc<dyn FileCheck<Self>>> {
        Vec::new()
    }

    fn repo_groups(&self) -> Vec<RepoGroup<Self>> {
        let mut metas = model_metas();
        metas.extend(directive_metas());
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
                binding_metas(),
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
            RepoGroup::new(
                "repo:arch",
                arch_metas(),
                |s: &Snapshot<Self>, files: &mut FileInterner| {
                    s.inputs
                        .arch
                        .findings
                        .iter()
                        .cloned()
                        .filter_map(|f| f.into_finding(files))
                        .collect()
                },
            )
            .counting(|s| {
                s.inputs
                    .arch
                    .subjects
                    .iter()
                    .map(|(rule, n)| (*rule, *n))
                    .collect()
            }),
            RepoGroup::new(
                "repo:ci",
                ci_metas(),
                |s: &Snapshot<Self>, files: &mut FileInterner| {
                    s.inputs
                        .ci
                        .findings
                        .iter()
                        .cloned()
                        .filter_map(|f| f.into_finding(files))
                        .collect()
                },
            )
            .counting(|s| {
                s.inputs
                    .ci
                    .subjects
                    .iter()
                    .map(|(rule, n)| (*rule, *n))
                    .collect()
            }),
            report_group("repo:path", path_metas(), |i| &i.path),
            report_group("repo:time", time_metas(), |i| &i.time),
            report_group("repo:pair", pair_metas(), |i| &i.pair),
            report_group("repo:err", err_metas(), |i| &i.err),
            report_group("repo:unity", unity_metas(), |i| &i.unity),
            report_group("repo:coh", coh_metas(), |i| &i.coh),
        ]
    }

    fn applicable(&self, snap: &Snapshot<Self>, meta: &RuleMeta) -> bool {
        !snap.inputs.binding.not_applicable.contains_key(meta.id)
            && !snap.inputs.arch.not_applicable.contains_key(meta.id)
            && !snap.inputs.ci.not_applicable.contains_key(meta.id)
            && !snap.inputs.path.not_applicable.contains_key(meta.id)
            && !snap.inputs.time.not_applicable.contains_key(meta.id)
            && !snap.inputs.pair.not_applicable.contains_key(meta.id)
            && !snap.inputs.err.not_applicable.contains_key(meta.id)
            && !snap.inputs.unity.not_applicable.contains_key(meta.id)
            && !snap.inputs.coh.not_applicable.contains_key(meta.id)
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
        let mut raw = dedupe_ci(raw, &snap.inputs.ci, files);
        snap.inputs.overrides.apply(&mut raw);
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

#[cfg(test)]
mod tests {
    use super::*;
    use gob_text::{TextRange, TextSize};

    /// A finding of `rule` in `file` at byte `at` with `message`.
    fn finding(
        files: &mut FileInterner,
        rule: &str,
        file: &str,
        at: u32,
        message: &str,
    ) -> Finding {
        let span = Span::new(
            files.intern(file),
            TextRange::new(TextSize::new(at), TextSize::new(at + 1)),
        );
        Finding::new(
            rule.parse().expect("rule id"),
            Severity::Warn,
            Some(span),
            message,
            file,
        )
    }

    /// A native report holding one `rule` finding in `file`.
    fn native(rule: &'static str, file: &str, message: &str) -> CiReport {
        let mut report = CiReport::default();
        report.findings.push(grimble_ci::Verdict {
            rule,
            severity: Severity::Warn,
            file: file.to_owned(),
            range: (10, 11),
            message: message.to_owned(),
            reason: None,
            anchor: file.to_owned(),
        });
        report
    }

    /// A tool and a native finding of one rule and file are reported once, whatever their lines; other pairs stand.
    // frob:ticket 01M5KDWHPF5YTVP64PYCXX0FRT
    // frob:tests crates/grimble-check/src/product.rs::dedupe_ci
    #[test]
    fn tool_finding_wins_over_native_for_the_same_rule_and_file() {
        let mut files = FileInterner::new();
        let wf = ".github/workflows/ci.yml";
        let ci = native("CI001", wf, "lexical");
        let raw = vec![
            finding(&mut files, "CI001", wf, 10, "lexical"),
            finding(&mut files, "CI001", wf, 99, "zizmor says"),
            finding(&mut files, "CI006", wf, 10, "lexical other rule"),
        ];
        let out = dedupe_ci(raw, &ci, &files);
        let msgs: Vec<&str> = out.iter().map(|f| f.message.as_str()).collect();
        assert_eq!(msgs, ["zizmor says", "lexical other rule"]);
    }

    /// With no tool finding the native one stands.
    // frob:ticket 01M5KDWHPF5YTVP64PYCXX0FRT
    // frob:tests crates/grimble-check/src/product.rs::dedupe_ci
    #[test]
    fn native_finding_stands_without_a_tool_finding() {
        let mut files = FileInterner::new();
        let wf = ".github/workflows/ci.yml";
        let ci = native("CI001", wf, "lexical");
        let raw = vec![finding(&mut files, "CI001", wf, 10, "lexical")];
        assert_eq!(dedupe_ci(raw, &ci, &files).len(), 1);
    }
}
