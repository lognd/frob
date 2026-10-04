//! The check pipeline (rules.md section 4): collect once, run rules, resolve exceptions, report.

use std::path::Path;
use std::time::Instant;

use gob_cache::Cache;
use gob_rules::{Finding, Fingerprint, Registry, Rule, RuleMeta, Severity};
use gob_text::FileInterner;

use crate::config::{CheckTable, PerfTable};
use crate::core::walk_core;
use crate::error::CheckError;
use crate::filecheck::{opaque_binary, run_file_checks};
use crate::fix;
use crate::options::RunOptions;
use crate::product::{CollectCx, Collected, Product, ScopeView, Snapshot};
use crate::repo::run_repo_rules;
use crate::report::{CheckReport, Counts, FixOutcome, Tally, Timing};
use crate::required::{mark_annotations, zero_subjects};
use crate::rules::{Perf001, Read001};
use crate::status::{FidelityReport, Need, is_binary, need_of, opaque_finding, unreadable_finding};
use crate::telemetry;
use crate::tools::run_tools;

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

/// Normalize `--only` entries and reject names the product's rules do not use.
fn validate_only<P: Product>(product: &P, only: &[String]) -> Result<Vec<String>, CheckError> {
    let registry = Registry::global();
    only.iter()
        .map(|raw| {
            let name = raw.trim().to_ascii_uppercase();
            let known = registry
                .iter()
                .filter(|m| product.includes(m))
                .any(|m| m.family == name || m.id == name);
            if known {
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

/// Run the `[[check.tool]]` stages unless skipped or filtered out by `--only`.
fn tool_stages(
    root: &Path,
    opts: &RunOptions,
    table: &CheckTable,
    only: &[String],
    scope_files: Option<&std::collections::BTreeSet<String>>,
    timing: &mut Timing,
    files: &mut FileInterner,
) -> Vec<Finding> {
    let wanted = only.is_empty()
        || only
            .iter()
            .any(|o| o.starts_with("TOOL") || o.starts_with("CI"));
    if opts.skip_tools || !wanted {
        return Vec::new();
    }
    let found = run_tools(root, &table.tool, timing, files);
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
    for meta in groups
        .iter()
        .flat_map(|g| g.metas.iter())
        .filter(|m| wanted(m))
    {
        if need_of(meta.id).is_none_or(|n| n.need != Need::EveryTextArtifact) {
            continue;
        }
        tracing::info!(
            rule = meta.id,
            files = opaque.len(),
            "repo rule unresolved on opaque text"
        );
        fidelity.add_unresolved("opaque", meta.id, 1);
        out.push(opaque_finding(meta, &opaque));
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
    product.start_external(&snap, table, scope_files);

    let wanted = |m: &RuleMeta| matches_only(only, m.family, m.id);
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
    let stage = run_file_checks(product, &snap, &cache, &checks, &paths);
    tally.stats.file_hits = stage.hits;
    tally.stats.file_misses = stage.misses;
    raw.extend(stage.findings);
    tally.fidelity = stage.fidelity;
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
        product, &snap, &cache, &mut files, &wanted, &mut tally, table,
    ));

    raw.extend(opaque_repo_findings(
        product,
        &snap,
        &wanted,
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

    // Tool findings join the raw set so exceptions apply to them like native ones.
    raw.extend(tool_stages(
        root,
        opts,
        table,
        only,
        scope_files,
        &mut tally.timing,
        &mut files,
    ));

    let external = product.join_external(&snap, &mut files, &mut tally.timing);
    raw.extend(external.findings);
    for (label, row) in external.languages {
        tally.fidelity.languages.insert(label, row);
    }
    warnings.extend(external.warnings);

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
        let applied = fix::apply(root, &report.findings, &report.files, &report.digests)?;
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
        telemetry::append(
            root,
            &product.state_dir(),
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
