//! `crunk check --report slop`: the de-slop report as a vector of evidence, never one score.
//!
//! Every SLOP rule is a signal. Each signal carries its tier, its status (`clear`, `flagged`,
//! `not_run`) and the findings that are its evidence. A signal that did not run is `not_run`,
//! never `clear` and never a zero. Tiers that did not run are listed with the reason. The report
//! has counts of its parts but no aggregate number: nothing here can be read without the signals.

// frob:ticket 01M4CXTBPEVSYD93X6S90ZRDZ9

use std::collections::BTreeMap;

use crunk_check::CrunkRun;
use crunk_rules::family::CheckTier;
use crunk_rules::registry::Entry;
use gob_rules::{Finding, Severity};
use serde_json::{Value, json};

/// The family prefix whose rules are the signals of this report.
pub const FAMILY: &str = "SLOP";

/// The tiers in order; the report lists each of them.
const TIERS: [CheckTier; 4] = [CheckTier::T0, CheckTier::T1, CheckTier::T2, CheckTier::T3];

/// Why a signal has no verdict.
const NOT_EVALUATED: &str = "the rule did not examine any subject in this run";

/// Why a tier did not run: `crunk check` decides T0 only.
const TIER_NOT_RUN: &str =
    "crunk check decides static (T0) rules only; this tier needs a solve, render or live run";

/// One piece of evidence: a finding, located.
fn evidence_of(run: &CrunkRun, f: &Finding, waived: bool) -> Value {
    let (file, line) = match f.span {
        Some(span) => {
            let path = run.report.files.path(span.file).unwrap_or("").to_owned();
            let start = u32::from(span.range.start());
            let line = if start == 0 {
                0
            } else {
                crate::query::line_of(&run.root, &path, start)
            };
            (Some(path), line)
        }
        None => (None, 0),
    };
    json!({
        "file": file,
        "line": line,
        "severity": format!("{:?}", f.severity).to_lowercase(),
        "message": f.message,
        "waived": waived,
    })
}

/// The signal row for `entry` given the run's findings.
fn signal_of(run: &CrunkRun, entry: &Entry) -> Value {
    let id = entry.id;
    let mine = run.report.findings.iter().filter(|f| f.rule.as_str() == id);
    let (unresolved, resolved): (Vec<&Finding>, Vec<&Finding>) =
        mine.partition(|f| f.severity == Severity::Unresolved);
    let waived = run
        .report
        .suppressed
        .iter()
        .map(|(f, _)| f)
        .filter(|f| f.rule.as_str() == id);
    let mut evidence: Vec<Value> = resolved
        .iter()
        .map(|f| evidence_of(run, f, false))
        .chain(waived.map(|f| evidence_of(run, f, true)))
        .collect();
    // Stable order across runs: by file, then line, then message.
    evidence.sort_by_cached_key(|v| {
        (
            v["file"].as_str().unwrap_or("").to_owned(),
            v["line"].as_u64().unwrap_or(0),
            v["message"].as_str().unwrap_or("").to_owned(),
        )
    });
    let examined = run.report.subjects_examined.get(id).copied();
    // A rule that could not decide, or never examined a subject, has no verdict: not run.
    let (status, reason) = if let Some(f) = unresolved.first() {
        ("not_run", Some(f.message.clone()))
    } else if !evidence.is_empty() {
        ("flagged", None)
    } else if examined.is_none() {
        ("not_run", Some(NOT_EVALUATED.to_owned()))
    } else {
        ("clear", None)
    };
    let tiers: Vec<&str> = entry.tiers.iter().map(|t| t.as_str()).collect();
    tracing::debug!(rule = id, status, evidence = evidence.len(), "slop signal");
    json!({
        "rule": id,
        "slug": entry.slug,
        "summary": entry.summary,
        "tiers": tiers,
        "status": status,
        "reason": reason,
        "subjects_examined": examined,
        "evidence": evidence,
    })
}

/// The tier rows: a tier ran only when at least one of its signals gave a verdict.
fn tiers_of(signals: &[Value]) -> Vec<Value> {
    TIERS
        .iter()
        .map(|tier| {
            let name = tier.as_str();
            let ran = signals.iter().any(|s| {
                s["status"] != "not_run"
                    && s["tiers"]
                        .as_array()
                        .is_some_and(|t| t.iter().any(|x| x == name))
            });
            json!({
                "tier": name,
                "ran": ran,
                "reason": if ran { Value::Null } else { json!(TIER_NOT_RUN) },
            })
        })
        .collect()
}

/// Counts of the signal parts by status. These count signals; they are not a score.
fn counts_of(signals: &[Value]) -> Value {
    let mut by: BTreeMap<&str, usize> = BTreeMap::new();
    for s in signals {
        *by.entry(s["status"].as_str().unwrap_or("not_run"))
            .or_default() += 1;
    }
    json!({
        "signals": signals.len(),
        "flagged": by.get("flagged").copied().unwrap_or(0),
        "clear": by.get("clear").copied().unwrap_or(0),
        "not_run": by.get("not_run").copied().unwrap_or(0),
    })
}

/// Build the slop report for `run` over `entries` (the SLOP rules, any order).
pub fn build(run: &CrunkRun, entries: &[Entry]) -> Value {
    let mut signals: Vec<Value> = entries
        .iter()
        .filter(|e| e.family == FAMILY)
        .map(|e| signal_of(run, e))
        .collect();
    signals.sort_by(|a, b| a["rule"].as_str().cmp(&b["rule"].as_str()));
    let tiers = tiers_of(&signals);
    let counts = counts_of(&signals);
    tracing::info!(signals = signals.len(), "slop report built");
    json!({
        "report": "slop",
        "signals": signals,
        "tiers": tiers,
        "counts": counts,
    })
}
