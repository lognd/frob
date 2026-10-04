//! The `gob.sibling/1` document (sibling-contract 3): what `crunk check --json` prints as `data`.

use gob_diagnostics::{FindingRecord, MemorySources};
use gob_rules::{Finding, Registry, Severity};
use gob_text::SourceText;
use serde_json::{Value, json};

use crate::{CrunkRun, PRODUCT};

/// The contract name and major this build implements.
pub const SCHEMA_VERSION: &str = "gob.sibling/1";

/// A resolver of `file:line:column` over the files the findings point into.
fn sources_of(run: &CrunkRun) -> MemorySources {
    let mut sources = MemorySources::new();
    let mut seen = std::collections::HashSet::new();
    let all = run
        .report
        .findings
        .iter()
        .chain(run.report.suppressed.iter().map(|(f, _)| f));
    for f in all {
        let Some(span) = f.span else { continue };
        if !seen.insert(span.file) {
            continue;
        }
        let Some(path) = run.report.files.path(span.file) else {
            continue;
        };
        let text =
            std::fs::read(run.root.join(path)).map(|b| String::from_utf8_lossy(&b).into_owned());
        if let Ok(text) = text
            && let Ok(src) = SourceText::new(text)
        {
            sources.insert(span.file, path, src);
        }
    }
    sources
}

fn finding_json(run: &CrunkRun, sources: &MemorySources, f: &Finding) -> Value {
    let record = FindingRecord::from_finding(f, sources, Registry::global());
    let mut v = serde_json::to_value(&record)
        .unwrap_or_else(|e| unreachable!("a finding record serializes: {e}"));
    let rule = f.rule.as_str();
    let polarity = Registry::global()
        .by_id(rule)
        .map_or("P+", |m| m.polarity.symbol());
    let object = v
        .as_object_mut()
        .unwrap_or_else(|| unreachable!("a finding record is an object"));
    object.insert("polarity".to_owned(), json!(polarity));
    object.insert(
        "subjects_examined".to_owned(),
        json!(run.report.subjects_examined.get(rule).copied().unwrap_or(0)),
    );
    object.insert(
        "reason".to_owned(),
        if f.severity == Severity::Unresolved {
            json!("fidelity")
        } else {
            Value::Null
        },
    );
    object.insert("maybe".to_owned(), json!(Vec::<String>::new()));
    object.insert("anchor".to_owned(), Value::Null);
    object.insert("entity".to_owned(), Value::Null);
    object.insert("remedy".to_owned(), Value::Null);
    object.insert(
        "range".to_owned(),
        f.span.map_or(
            Value::Null,
            |s| json!({"start": u32::from(s.range.start()), "end": u32::from(s.range.end())}),
        ),
    );
    v
}

/// The sibling document of `run` (the `data` of the check envelope).
pub fn sibling_document(run: &CrunkRun) -> Value {
    let sources = sources_of(run);
    let findings: Vec<Value> = run
        .report
        .findings
        .iter()
        .map(|f| finding_json(run, &sources, f))
        .collect();
    let suppressed: Vec<Value> = run
        .report
        .suppressed
        .iter()
        .map(|(f, _)| json!({"finding": finding_json(run, &sources, f), "exception": ""}))
        .collect();
    let rules: Vec<Value> = run
        .report
        .subjects_examined
        .iter()
        .map(|(rule, subjects)| {
            json!({
                "rule": rule,
                "polarity": Registry::global().by_id(rule).map_or("P+", |m| m.polarity.symbol()),
                "subjects_examined": subjects,
                "findings": run.report.findings.iter().filter(|f| f.rule.as_str() == rule).count(),
                "suppressed": run.report.suppressed.iter().filter(|(f, _)| f.rule.as_str() == rule).count(),
                "unresolved": run.report.findings.iter().filter(|f| f.rule.as_str() == rule && f.severity == Severity::Unresolved).count(),
            })
        })
        .collect();
    json!({
        "schema_version": SCHEMA_VERSION,
        "product": PRODUCT,
        "product_version": env!("CARGO_PKG_VERSION"),
        "compute_digest": gob_config::compute_digest(&run.compute),
        "compute": run.compute.to_value(),
        "invocation": {
            "verb": "check",
            "root": ".",
            "ticket_scope": run.ticket_scope,
            "base": run.base,
        },
        "fidelity": Vec::<Value>::new(),
        "rules": rules,
        "findings": findings,
        "suppressed": suppressed,
        "exceptions": Vec::<Value>::new(),
        "entities": Vec::<Value>::new(),
        "bindings": Vec::<Value>::new(),
        "timing": {"elapsed_ms": run.elapsed_ms},
    })
}
