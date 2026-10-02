//! The check pipeline (rules.md section 4): collect once, run rules, resolve exceptions, report.

use std::path::Path;
use std::time::Instant;

use frob_lease::LeaseConfig;
use frob_obligations::apply_exceptions;
use gob_cache::Cache;
use gob_rules::{Finding, Fingerprint, Registry, Rule, RuleMeta, Severity};
use gob_text::FileInterner;

use crate::config::{CheckTable, PerfTable};
use crate::error::CheckError;
use crate::filecheck::{FileCheck, builtin_checks, run_file_checks};
use crate::fix;
use crate::options::CheckOptions;
use crate::repo::run_repo_rules;
use crate::report::{CheckReport, Counts, FixOutcome, Stats, Timing};
use crate::rules::Perf001;
use crate::scope;
use crate::snapshot::{self, Snapshot};
use crate::telemetry;
use crate::tools::run_tools;

/// Whether a rule survives the `--only` filter.
fn matches_only(only: &[String], family: &str, id: &str) -> bool {
    only.is_empty() || only.iter().any(|o| o == family || o == id)
}

/// Normalize `--only` entries and reject names the registry does not know.
fn validate_only(only: &[String]) -> Result<Vec<String>, CheckError> {
    let registry = Registry::global();
    only.iter()
        .map(|raw| {
            let name = raw.trim().to_ascii_uppercase();
            let known = registry.iter().any(|m| m.family == name || m.id == name);
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

/// Give every finding the same fingerprint scheme: rule, file path (or none), message.
///
/// Cached findings do not keep their original anchor, so fresh and cached
/// results are normalized alike; that is what makes a warm run byte-identical.
fn refingerprint(findings: &mut [Finding], files: &FileInterner) {
    for f in findings {
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

/// One full evaluation of the built-in rules (no tool stages, no fixes).
fn pass(
    root: &Path,
    opts: &CheckOptions,
    table: &CheckTable,
    perf: &PerfTable,
    only: &[String],
) -> Result<CheckReport, CheckError> {
    let mut timing = Timing::default();
    let mut stats = Stats::default();
    let mut warnings = Vec::new();
    let cache = Cache::open(&root.join(".frob"));
    let snap: Snapshot = snapshot::collect(root, table, &cache, opts, &mut timing, &mut stats)?;

    let lease_cfg = match &opts.lease {
        Some(c) => c.clone(),
        None => LeaseConfig::load(root)?,
    };
    let scope = match &opts.ticket {
        Some(reference) => Some(scope::resolve(
            &snap,
            reference,
            table.ticket_hops,
            lease_cfg.clone(),
        )?),
        None => None,
    };

    let wanted = |m: &RuleMeta| matches_only(only, m.family, m.id);
    let mut raw: Vec<Finding> = Vec::new();

    let started = Instant::now();
    let mut checks: Vec<std::sync::Arc<dyn FileCheck>> = builtin_checks();
    checks.extend(opts.extra_checks.iter().cloned());
    checks.retain(|c| c.rules().iter().any(|m| wanted(m)));
    let paths: Vec<String> = match &scope {
        Some(s) => s.files.iter().cloned().collect(),
        None => snap.entries.iter().map(|e| e.path.clone()).collect(),
    };
    stats.files_checked = paths.len();
    let stage = run_file_checks(&snap, &cache, &checks, &paths);
    stats.file_hits = stage.hits;
    stats.file_misses = stage.misses;
    raw.extend(stage.findings);
    let in_scope = |f: &Finding| match (&scope, f.span) {
        (Some(s), Some(span)) => snap
            .ack
            .files
            .path(span.file)
            .is_some_and(|p| s.files.contains(p)),
        _ => true,
    };
    raw.extend(snap.scan_findings.iter().filter(|f| in_scope(f)).cloned());
    timing.push("file-rules", started.elapsed(), true);

    let mut files = snap.ack.files.clone();
    raw.extend(run_repo_rules(
        &snap,
        &cache,
        &mut files,
        &wanted,
        &mut stats,
        &mut timing,
    ));

    if let Some(s) = &scope {
        let started = Instant::now();
        let base = opts.base.clone().unwrap_or_else(|| table.base.clone());
        raw.extend(scope::ticket_rules(
            &snap,
            s,
            &base,
            &lease_cfg.shared_files,
        ));
        timing.push("ticket-rules", started.elapsed(), true);
    }

    let started = Instant::now();
    let resolved = apply_exceptions(&snap.obligations(), &files, raw);
    timing.push("exceptions", started.elapsed(), true);
    let keep = |f: &Finding| matches_only(only, f.rule.family(), f.rule.as_str());
    let mut findings: Vec<Finding> = resolved.findings.into_iter().filter(|f| keep(f)).collect();
    let suppressed = resolved
        .suppressed
        .into_iter()
        .filter(|(f, _)| keep(f))
        .collect();

    if let Some(f) = perf_finding(perf, &timing, only) {
        warnings.push("PERF001: time budget exceeded".to_owned());
        findings.push(f);
    }

    Ok(CheckReport {
        findings,
        suppressed,
        files,
        timing,
        stats,
        fix: None,
        warnings,
        ticket: scope.map(|s| s.handle),
        fail_on: opts.fail_on.unwrap_or(table.fail_on),
    })
}

/// Run the whole check for the repository at `root`.
///
/// Collects inputs once, evaluates per-file rules (cached per file digest),
/// repo rules (cached per inputs digest), applies exceptions, then runs the
/// `[[check.tool]]` stages outside the time budget. With `opts.fix` the
/// Deterministic fixes are written and the pipeline runs once more.
///
/// # Errors
///
/// [`CheckError`] for a bad `frob.toml`, a failed walk, a malformed lock, an
/// unknown `--only` name, an unresolvable `--ticket`, a refused `--fix` or a
/// fix that cannot be written. Findings are never errors.
pub fn run(root: &Path, opts: &CheckOptions) -> Result<CheckReport, CheckError> {
    let table = CheckTable::load(root)?;
    let perf = PerfTable::load(root)?;
    if opts.fix && table.fix_requires_scope && opts.ticket.is_none() {
        return Err(CheckError::FixNeedsScope);
    }
    let only = validate_only(&opts.only)?;
    let mut report = pass(root, opts, &table, &perf, &only)?;
    if opts.fix {
        let applied = fix::apply(root, &report.findings, &report.files)?;
        if !applied.applied.is_empty() {
            tracing::info!(
                fixes = applied.applied.len(),
                "fixes applied; re-running once"
            );
            report = pass(root, opts, &table, &perf, &only)?;
        }
        report.fix = Some(FixOutcome {
            applied: applied.applied,
            skipped_overlap: applied.skipped_overlap,
            remaining: report.findings.len(),
        });
    }
    if !opts.skip_tools && matches_only(&only, "TOOL", "TOOL001") {
        report
            .findings
            .extend(run_tools(root, &table.tool, &mut report.timing));
    }
    refingerprint(&mut report.findings, &report.files);
    sort_findings(&mut report.findings, &report.files);
    if table.telemetry && !opts.skip_telemetry {
        telemetry::append(
            root,
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
