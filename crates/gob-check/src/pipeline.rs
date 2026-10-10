//! The check pipeline (rules.md section 4): collect once, run rules, resolve exceptions, report.

use std::path::Path;
use std::time::Instant;

use gob_cache::Cache;
use gob_rules::{Finding, Fingerprint, Registry, Rule, RuleDef, RuleMeta, Severity};
use gob_text::FileInterner;

use crate::applicability::{FileFacts, RuleRef, resolve};
use crate::config::{CheckTable, PerfTable};
use crate::core::walk_core;
use crate::defs::{self, Live};
use crate::error::CheckError;
use crate::filecheck::{opaque_binary, run_file_checks};
use crate::fix;
use crate::options::RunOptions;
use crate::packages::{Affected, Workspace};
use crate::product::{CollectCx, Collected, Product, ScopeView, Snapshot};
use crate::repo::run_repo_rules;
use crate::report::{CheckReport, Counts, FixOutcome, Tally, Timing};
use crate::required::{mark_annotations, zero_subjects};
use crate::rules::{Perf001, Read001};
use crate::status::{
    FidelityReport, SubjectStatus, is_binary, opaque_finding_for, unreadable_finding,
};
use crate::telemetry;
use crate::tools::{ToolRun, applicable_stages, start_tools};

/// The engine fingerprint scoping every cached rule result: binary identity plus `EXTRACTOR_VERSION`.
///
/// The rule's own version is already part of each per-file and repo-rule key,
/// so a result is reused only by the same build, extractor and rule version.
pub(crate) fn engine_fingerprint() -> String {
    format!(
        "{}/extractor-v{}",
        gob_cache::default_engine(),
        gob_symbols::EXTRACTOR_VERSION
    )
}

/// Whether a rule survives the `--only` filter.
fn matches_only(only: &[String], family: &str, id: &str) -> bool {
    only.is_empty() || only.iter().any(|o| o == family || o == id)
}

// frob:ticket 01M4FH7QN0DHJD45C4HC8N7M9Q
/// True when `name` (upper-case) is a family or id of one of the product's own rules.
fn known_here<P: Product>(product: &P, name: &str) -> bool {
    let set = product.rule_set();
    Registry::global()
        .iter()
        .filter(|m| product.includes(m))
        .any(|m| m.family == name || m.id == name)
        || set.defs().any(|d| d.family == name || d.id == name)
}

// frob:ticket 01M4FH7QN0DHJD45C4HC8N7M9Q
/// The family of a rule id: its leading letters (`COLOR001` is `COLOR`).
fn family_of_id(id: &str) -> &str {
    id.trim_end_matches(|c: char| c.is_ascii_digit())
}

/// Normalize `--only` entries and reject names the product's rules do not use.
///
/// A product that [defers](Product::defers_unknown_only) unknown names keeps them: an external
/// product may own them, and the run refuses them after the external stages report their rules.
fn validate_only<P: Product>(product: &P, only: &[String]) -> Result<Vec<String>, CheckError> {
    only.iter()
        .map(|raw| {
            let name = raw.trim().to_ascii_uppercase();
            if known_here(product, &name) || product.defers_unknown_only() {
                Ok(name)
            } else {
                Err(CheckError::UnknownFamily(raw.clone()))
            }
        })
        .collect()
}

/// Final order: by file, offset, rule, message; spanless findings last.
fn sort_findings(findings: &mut [Finding], files: &FileInterner) {
    findings.sort_by_cached_key(|f| {
        (
            f.span.is_none(),
            f.span.and_then(|s| files.path(s.file)).map(str::to_owned),
            f.span.map(|s| u32::from(s.range.start())),
            f.rule.to_string(),
            f.message.clone(),
        )
    });
}

/// Apply the product's exceptions to `raw`, then keep what `--only` selects.
fn resolve_exceptions<P: Product>(
    product: &P,
    snap: &Snapshot<P>,
    files: &FileInterner,
    raw: Vec<Finding>,
    only: &[String],
    timing: &mut Timing,
) -> (Vec<Finding>, Vec<(Finding, gob_rules::Exception)>) {
    let started = Instant::now();
    let resolved = product.resolve_exceptions(snap, files, raw);
    timing.push("exceptions", started.elapsed(), true);
    let keep = |f: &Finding| matches_only(only, f.rule.family(), f.rule.as_str());
    let findings = resolved.findings.into_iter().filter(|f| keep(f)).collect();
    let suppressed = resolved
        .suppressed
        .into_iter()
        .filter(|(f, _)| keep(f))
        .collect();
    (findings, suppressed)
}

/// The cargo packages `files` touch (and their reverse dependencies), read from the walked manifests.
fn affected_packages(
    root: &Path,
    manifests: &[String],
    files: &std::collections::BTreeSet<String>,
) -> Affected {
    Workspace::load(root, manifests).affected(files)
}

/// Start the `[[check.tool]]` stages in the background unless skipped or filtered out by `--only`.
///
/// They read the tree, not the rule results, so they overlap the in-process stages.
fn begin_tools(
    root: &Path,
    opts: &RunOptions,
    table: &CheckTable,
    only: &[String],
    scope_files: Option<&std::collections::BTreeSet<String>>,
    manifests: &[String],
) -> Option<ToolRun> {
    let wanted = only.is_empty()
        || only
            .iter()
            .any(|o| o.starts_with("TOOL") || o.starts_with("CI"));
    if opts.skip_tools || !wanted {
        return None;
    }
    let affected = scope_files
        .filter(|_| {
            table
                .tool
                .iter()
                .any(|t| t.args.iter().any(|a| a == "{packages}"))
        })
        .map(|files| affected_packages(root, manifests, files));
    start_tools(
        root,
        &applicable_stages(&table.tool, scope_files, affected.as_ref()),
    )
}

/// Join the background tool stages and keep the findings a scope allows.
fn tool_stages(
    run: Option<ToolRun>,
    scope_files: Option<&std::collections::BTreeSet<String>>,
    timing: &mut Timing,
    files: &mut FileInterner,
) -> Vec<Finding> {
    let Some(run) = run else {
        return Vec::new();
    };
    let found = run.finish(timing, files);
    // Spanless findings (a missing tool) always stand; located ones obey a scope.
    found
        .into_iter()
        .filter(|f| match (scope_files, f.span) {
            (Some(s), Some(span)) => files.path(span.file).is_some_and(|p| s.contains(p)),
            _ => true,
        })
        .collect()
}

/// Give every finding the same fingerprint scheme: rule, file path (or none), message.
///
/// Cached findings do not keep their original anchor, so fresh and cached
/// results are normalized alike; that is what makes a warm run byte-identical.
fn refingerprint(
    findings: &mut [Finding],
    files: &FileInterner,
    kept: &std::collections::HashMap<gob_rules::Fingerprint, String>,
) {
    for f in findings
        .iter_mut()
        .filter(|f| !kept.contains_key(&f.fingerprint))
    {
        let anchor = f
            .span
            .and_then(|s| files.path(s.file))
            .unwrap_or_default()
            .to_owned();
        f.fingerprint = Fingerprint::compute(&f.rule, &anchor, &f.message);
    }
}

/// `PERF001` when the budget is enforced and the budgeted stages exceeded it.
fn perf_finding(perf: &PerfTable, timing: &Timing, only: &[String]) -> Option<Finding> {
    if !(perf.enforce
        && timing.budget_ms() > perf.budget_ms
        && matches_only(only, "PERF", "PERF001"))
    {
        return None;
    }
    let slowest = timing
        .stages
        .iter()
        .filter(|s| s.budgeted)
        .max_by_key(|s| s.ms)
        .map_or_else(String::new, |s| {
            format!("; slowest stage `{}` took {} ms", s.name, s.ms)
        });
    Some(Finding::new(
        Perf001
            .meta()
            .rule_id()
            .unwrap_or_else(|e| unreachable!("derive validates the id: {e}")),
        Severity::Warn,
        None,
        format!(
            "built-in stages took {} ms, over the {} ms budget{slowest}",
            timing.budget_ms(),
            perf.budget_ms
        ),
        "budget",
    ))
}

/// One Unresolved per repo rule that reads comments or directives while opaque text files exist.
///
/// A directive in an adapter-less file is never scanned, so an absence-style
/// repo rule cannot claim the repository is clean; the finding names the count.
fn opaque_repo_findings<P: Product>(
    product: &P,
    snap: &Snapshot<P>,
    wanted: &dyn Fn(&RuleMeta) -> bool,
    declared: &[RuleRef],
    fidelity: &mut FidelityReport,
) -> Vec<Finding> {
    let mut opaque: Vec<&str> = Vec::new();
    for e in &snap.core.entries {
        let Some(info) = product.file_info(&snap.shared, &e.path) else {
            continue;
        };
        if info.is_opaque()
            && !product.scans_text(&e.path)
            && !opaque_binary(&snap.core.root, &e.path, &info)
        {
            opaque.push(&e.path);
        }
    }
    if opaque.is_empty() {
        return Vec::new();
    }
    let mut out = Vec::new();
    let mut groups = product.repo_groups();
    groups.extend(crate::repo::builtin_groups::<P>(Vec::new()));
    let rules: Vec<RuleRef> = groups
        .iter()
        .flat_map(|g| g.metas.iter())
        .filter(|m| wanted(m))
        .map(|m| RuleRef::of_meta(m))
        .chain(declared.iter().copied())
        .collect();
    for rule in rules {
        // Only a rule that reads comments is unresolved on opaque text (capability rules are not applicable).
        let facts = FileFacts::opaque_text(&gob_symbols::ParseStatus::NotParsed);
        if !matches!(resolve(&rule.applies, &facts), SubjectStatus::Unresolved(_)) {
            continue;
        }
        tracing::info!(
            rule = rule.id,
            files = opaque.len(),
            "repo rule unresolved on opaque text"
        );
        fidelity.add_unresolved("opaque", rule.id, 1);
        out.push(opaque_finding_for(rule.id, &opaque));
    }
    out
}

// frob:ticket 01M42M1KK02KFZG39CXKAD47SZ
/// One required Unresolved `READ001` per walked file nobody could read, counted in `fidelity`.
///
/// Sources: files over `size_cap` (the walk) and files the product's analysis
/// failed to read or decode. A file excluded by `[check] exclude` is never
/// walked, so it never appears; an oversized file with a binary extension is
/// declared binary and is not reported. Scope does not filter these: a file
/// no gate read must stay visible whatever the run examined.
fn unreadable_findings<P: Product>(
    product: &P,
    snap: &Snapshot<P>,
    only: &[String],
    fidelity: &mut FidelityReport,
) -> Vec<Finding> {
    let mut skipped: Vec<_> = snap
        .core
        .skipped
        .iter()
        .filter(|s| !is_binary(&s.path, &[]))
        .cloned()
        .collect();
    skipped.extend(product.unreadable(&snap.shared));
    skipped.sort_by(|a, b| a.path.cmp(&b.path));
    skipped.dedup_by(|a, b| a.path == b.path);
    let emit = matches_only(only, "READ", "READ001");
    skipped
        .iter()
        .map(|s| {
            tracing::warn!(path = %s.path, kind = s.kind.as_str(), detail = %s.detail, "READ001: file not read");
            fidelity.add_skipped(s.kind);
            unreadable_finding(&Read001::META, snap.core.index.ids.get(&s.path).copied(), s)
        })
        .filter(|_| emit)
        .collect()
}

/// One full evaluation of the rules (no tool-less shortcuts, no fixes).
#[allow(
    clippy::too_many_lines,
    reason = "the stage order of rules.md section 4 reads best as one function"
)]
fn pass<P: Product>(
    product: &P,
    root: &Path,
    opts: &RunOptions,
    table: &CheckTable,
    perf: &PerfTable,
    only: &[String],
) -> Result<CheckReport, CheckError> {
    let mut tally = Tally::default();
    let mut warnings = Vec::new();
    // frob:ticket 01M42B6T28RX9PVM3X6TSK0M4Y
    let cache = Cache::open_shared(root, &product.state_dir()).with_engine(engine_fingerprint());
    let core = walk_core(
        root,
        table,
        &product.state_dir(),
        &mut tally.timing,
        &mut tally.stats,
    )?;
    let Collected {
        shared,
        inputs,
        findings: collected,
    } = product.collect(&mut CollectCx {
        core: &core,
        table,
        cache: &cache,
        timing: &mut tally.timing,
        stats: &mut tally.stats,
    })?;
    let snap = Snapshot::<P> {
        core,
        shared,
        inputs,
        findings: collected,
    };
    let core_digests = snap.core.index.digests.clone();
    let scope = match &opts.scope {
        Some(reference) => Some(product.resolve_scope(&snap, table, reference)?),
        None => None,
    };
    let scope_files = scope.as_ref().map(ScopeView::files);
    let manifests: Vec<String> = snap
        .core
        .entries
        .iter()
        .filter(|e| e.path == "Cargo.toml" || e.path.ends_with("/Cargo.toml"))
        .map(|e| e.path.clone())
        .collect();
    let tools = begin_tools(root, opts, table, only, scope_files, &manifests);
    product.start_external(&snap, table, scope_files);

    let wanted = |m: &RuleMeta| matches_only(only, m.family, m.id);
    let wanted_def = |d: &RuleDef| matches_only(only, d.family, d.id);
    let set = product.rule_set();
    let live = Live::select(product, &snap, &set, &wanted_def);
    let wanted_rule = |f: &Finding| matches_only(only, f.rule.family(), f.rule.as_str());
    let mut raw: Vec<Finding> = Vec::new();

    let started = Instant::now();
    let mut checks = product.file_checks();
    checks.retain(|c| c.rules().iter().any(|m| wanted(m)));
    let paths: Vec<String> = match scope_files {
        Some(files) => files.iter().cloned().collect(),
        None => snap.core.entries.iter().map(|e| e.path.clone()).collect(),
    };
    tally.stats.files_checked = paths.len();
    let stage = run_file_checks(product, &snap, &cache, &checks, &live.file_refs(), &paths);
    tally.stats.file_hits = stage.hits;
    tally.stats.file_misses = stage.misses;
    raw.extend(stage.findings);
    tally.fidelity = stage.fidelity;
    live.report_inapplicable(&mut tally);
    for (rule, n) in stage.subjects {
        tally.subjects.insert(rule.to_owned(), n);
    }
    if scope_files.is_none() {
        // A full run examined every file: a rule that examined none has a real zero. A scoped
        // run may simply hold no file the rule applies to, so it records only positive counts.
        for meta in checks.iter().flat_map(|c| c.rules()).filter(|m| wanted(m)) {
            tally.subjects.entry(meta.id.to_owned()).or_insert(0);
        }
    }
    raw.extend(defs::run_file_rules(
        product,
        &snap,
        &cache,
        &live,
        &paths,
        &stage.blocked,
        scope_files.is_some(),
        &mut tally,
    ));
    let in_scope = |f: &Finding| match (scope_files, f.span) {
        (Some(s), Some(span)) => snap
            .core
            .files
            .path(span.file)
            .is_some_and(|p| s.contains(p)),
        _ => true,
    };
    raw.extend(snap.findings.iter().filter(|f| in_scope(f)).cloned());
    tally.timing.push("file-rules", started.elapsed(), true);

    let mut files = snap.core.files.clone();
    raw.extend(run_repo_rules(
        product,
        &snap,
        &cache,
        &mut files,
        &wanted,
        &mut tally,
        table,
        scope_files.is_some(),
    ));

    raw.extend(defs::run_repo_rules(
        product, &snap, &cache, &live, &mut files, &mut tally,
    ));

    raw.extend(opaque_repo_findings(
        product,
        &snap,
        &wanted,
        &live.repo_refs(),
        &mut tally.fidelity,
    ));
    raw.extend(unreadable_findings(
        product,
        &snap,
        only,
        &mut tally.fidelity,
    ));

    if let Some(s) = &scope {
        let started = Instant::now();
        let scoped = product.scoped_rules(&snap, s, table);
        raw.extend(scoped.findings);
        for (rule, n) in scoped.subjects {
            tally.subjects.insert(rule.to_owned(), n);
        }
        tally.timing.push("scope-rules", started.elapsed(), true);
    }

    let must_measure: Vec<&'static RuleMeta> = Registry::global()
        .iter()
        .filter(|m| m.must_measure && product.includes(m) && wanted(m))
        .collect();
    raw.extend(
        zero_subjects(&must_measure, &tally.subjects, &|m| {
            product.applicable(&snap, m)
        })
        .into_iter()
        .filter(|f| wanted_rule(f)),
    );

    raw.extend(defs::zero_subjects(
        &set,
        &wanted_def,
        &live.inapplicable,
        &tally.subjects,
    ));

    // Tool findings join the raw set so exceptions apply to them like native ones.
    raw.extend(tool_stages(
        tools,
        scope_files,
        &mut tally.timing,
        &mut files,
    ));

    let external = product.join_external(&snap, &mut files, &mut tally.timing);
    // frob:ticket 01M4FH7QN0DHJD45C4HC8N7M9Q
    if let Some(name) = only.iter().find(|n| {
        !known_here(product, n)
            && !external
                .rule_ids
                .iter()
                .any(|id| id == *n || family_of_id(id) == n.as_str())
    }) {
        return Err(CheckError::UnknownFamily(name.clone()));
    }
    raw.extend(external.findings);
    for (label, row) in external.languages {
        tally.fidelity.languages.insert(label, row);
    }
    warnings.extend(external.warnings);

    // frob:ticket 01M4FG5RCDA668CK81QT54E67N
    let raw = crate::status::merge_opaque_notices(raw);
    let (mut findings, mut suppressed) =
        resolve_exceptions(product, &snap, &files, raw, only, &mut tally.timing);
    suppressed.extend(external.suppressed);

    if let Some(f) = perf_finding(perf, &tally.timing, only) {
        warnings.push("PERF001: time budget exceeded".to_owned());
        findings.push(f);
    }

    Ok(CheckReport {
        findings,
        suppressed,
        files,
        digests: core_digests,
        timing: tally.timing,
        stats: tally.stats,
        fix: None,
        warnings,
        scope: scope.map(|s| s.label().to_owned()),
        fail_on: opts.fail_on.unwrap_or(table.fail_on),
        fail_on_unresolved: table.fail_on_unresolved,
        subjects_examined: tally.subjects,
        fidelity: tally.fidelity,
        namespaces: external.namespaces,
        siblings: external.siblings,
    })
}

/// Run the whole check of `product` for the repository at `root`.
///
/// Walks once, lets the product collect its inputs, evaluates per-file rules
/// (cached per file digest) and repo rules (cached per inputs digest), applies
/// the product's exceptions, then runs the `[[check.tool]]` stages outside the
/// time budget. With `opts.fix` the Deterministic fixes are written and the
/// pipeline runs once more.
///
/// # Errors
///
/// [`CheckError`] for a bad config table, a failed walk, a failed product
/// collection, an unknown `--only` name, an unresolvable scope, a refused
/// `--fix` or a fix that cannot be written. Findings are never errors.
pub fn run<P: Product>(
    product: &P,
    root: &Path,
    opts: &RunOptions,
) -> Result<CheckReport, CheckError> {
    let table = CheckTable::load(root, product.name())?;
    let perf = PerfTable::load(root, product.name())?;
    if opts.fix && table.fix_requires_scope && opts.scope.is_none() {
        return Err(CheckError::FixNeedsScope);
    }
    let only = validate_only(product, &opts.only)?;
    let mut report = pass(product, root, opts, &table, &perf, &only)?;
    if opts.fix {
        let raw = fix::raw_digests(root, &report.findings, &report.files);
        let applied = fix::apply(root, &report.findings, &report.files, &report.digests, &raw)?;
        if !applied.applied.is_empty() {
            tracing::info!(
                fixes = applied.applied.len(),
                "fixes applied; re-running once"
            );
            report = pass(product, root, opts, &table, &perf, &only)?;
        }
        report.fix = Some(FixOutcome {
            applied: applied.applied,
            skipped_overlap: applied.skipped_overlap,
            skipped_invalid: applied.skipped_invalid,
            rolled_back: applied.rolled_back,
            remaining: report.findings.len(),
        });
    }
    refingerprint(&mut report.findings, &report.files, &report.namespaces);
    mark_annotations(&mut report.findings);
    sort_findings(&mut report.findings, &report.files);
    if table.telemetry && !opts.skip_telemetry {
        let at = opts
            .clock
            .as_ref()
            .map_or_else(|| gob_time::Clock::now(&gob_time::SystemClock), |c| c.now());
        // frob:ticket 01M4FD0EP322SV5ZNXD5SQT8RX
        telemetry::append(
            at,
            &product.telemetry_dir(root),
            &report.timing,
            &report.stats,
            Counts::of(&report.findings),
        );
    }
    tracing::info!(
        findings = report.findings.len(),
        budget_ms = report.timing.budget_ms(),
        tools_ms = report.timing.tools_ms(),
        "check finished"
    );
    Ok(report)
}
