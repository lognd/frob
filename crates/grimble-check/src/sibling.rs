//! The `gob.sibling/1` document (sibling-contract 3): what `grimble check --json` prints as `data`.
//!
//! [`sibling_document`] builds exactly the shape of `docs/schemas/sibling.json` from one
//! [`GrimbleRun`]. Fields grimble cannot fill yet are emitted in their schema-legal empty
//! form and listed in the crate docs: `bindings` is empty until G11 owns the binding
//! relation, entity digests are null, `anchor`/`entity` on a finding are null because
//! `check_model` does not expose them, and `not_applicable_rules` is empty until CAP lands.

use std::collections::BTreeMap;

use gob_diagnostics::{FindingRecord, MemorySources, severity_label};
use gob_rules::{Finding, Registry, Severity};
use gob_text::SourceText;
use serde_json::{Value, json};

use crate::config::blake3_tagged;
use crate::fidelity::fidelity_json;
use crate::GrimbleRun;

/// The contract name and major this build implements.
pub const SCHEMA_VERSION: &str = "gob.sibling/1";

/// Polarity symbol of `rule` (`P+` when the registry does not know it).
fn polarity_of(rule: &str) -> &'static str {
    Registry::global()
        .by_id(rule)
        .map_or("P+", |m| m.polarity.symbol())
}

/// Unresolved reason code of a finding: the required mark decides, else `fidelity`.
fn reason_of(f: &Finding) -> Option<&'static str> {
    use gob_rules::RequiredReason::{AnnotationRequired, SiblingMissing, ZeroSubjects};
    (f.severity == Severity::Unresolved).then(|| match &f.required {
        Some(ZeroSubjects { .. }) => "vacuous",
        Some(AnnotationRequired { .. }) => "annotation-required",
        Some(SiblingMissing { .. }) => "incompatible",
        None => "fidelity",
    })
}

/// A resolver of `file:line:column` over the files the findings point into.
fn sources_of(run: &GrimbleRun) -> MemorySources {
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
        if let Ok(text) = std::fs::read_to_string(run.root.join(path))
            && let Ok(src) = SourceText::new(text)
        {
            sources.insert(span.file, path, src);
        }
    }
    sources
}

fn finding_json(run: &GrimbleRun, sources: &MemorySources, f: &Finding) -> Value {
    let record = FindingRecord::from_finding(f, sources, Registry::global());
    let mut v = serde_json::to_value(&record)
        .unwrap_or_else(|e| unreachable!("a finding record serializes: {e}"));
    let rule = f.rule.as_str();
    let object = v
        .as_object_mut()
        .unwrap_or_else(|| unreachable!("a finding record is an object"));
    object.insert("polarity".to_owned(), json!(polarity_of(rule)));
    object.insert(
        "subjects_examined".to_owned(),
        json!(run.report.subjects_examined.get(rule).copied().unwrap_or(0)),
    );
    object.insert("reason".to_owned(), json!(reason_of(f)));
    object.insert("maybe".to_owned(), json!(Vec::<String>::new()));
    object.insert("anchor".to_owned(), Value::Null);
    object.insert("entity".to_owned(), Value::Null);
    object.insert("remedy".to_owned(), Value::Null);
    object.insert(
        "range".to_owned(),
        f.span.map_or(Value::Null, |s| {
            json!({"start": u32::from(s.range.start()), "end": u32::from(s.range.end())})
        }),
    );
    debug_assert_eq!(severity_label(f.severity), record.severity);
    v
}

fn rules_json(run: &GrimbleRun) -> Vec<Value> {
    let count = |rule: &str, sev: Option<Severity>| {
        run.report
            .findings
            .iter()
            .filter(|f| f.rule.as_str() == rule && sev.is_none_or(|s| f.severity == s))
            .count()
    };
    run.report
        .subjects_examined
        .iter()
        .map(|(rule, subjects)| {
            json!({
                "rule": rule,
                "polarity": polarity_of(rule),
                "subjects_examined": subjects,
                "findings": count(rule, None),
                "suppressed": run.report.suppressed.iter().filter(|(f, _)| f.rule.as_str() == rule).count(),
                "unresolved": count(rule, Some(Severity::Unresolved)),
            })
        })
        .collect()
}

/// The `exceptions` array: every parsed exception with how many findings it parked this run.
pub fn exceptions_json(run: &GrimbleRun) -> Vec<Value> {
    let mut suppresses: BTreeMap<&str, usize> = BTreeMap::new();
    for id in run.parks.values() {
        *suppresses.entry(id.as_str()).or_default() += 1;
    }
    run.view
        .exceptions
        .iter()
        .map(|e| {
            json!({
                "id": e.id,
                "kind": e.kind,
                "rule": e.rule,
                "on": e.on,
                "file": e.file,
                "line": e.line,
                "because": e.because,
                "until": e.until,
                "ticket": e.ticket,
                "exit_state": if e.ticket.is_some() { "unresolved_exit" } else { "evaluated" },
                "status": Value::Null,
                "suppresses": suppresses.get(e.id.as_str()).copied().unwrap_or(0),
            })
        })
        .collect()
}

/// The sibling document of `run` (the `data` of the check envelope).
pub fn sibling_document(run: &GrimbleRun) -> Value {
    let sources = sources_of(run);
    let key = |f: &Finding| crate::product::park_key(f, &run.report.files);
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
        .map(|(f, _)| {
            json!({
                "finding": finding_json(run, &sources, f),
                "exception": run.parks.get(&key(f)).cloned().unwrap_or_default(),
            })
        })
        .collect();
    let mut doc = json!({
        "schema_version": SCHEMA_VERSION,
        "product": crate::config::PRODUCT,
        "product_version": env!("CARGO_PKG_VERSION"),
        "compute_digest": run.compute.digest(),
        "compute": run.compute.to_value(),
        "invocation": {
            "verb": "check",
            "root": ".",
            "ticket_scope": run.ticket_scope,
            "base": run.base,
        },
        "fidelity": fidelity_json(&run.languages),
        "rules": rules_json(run),
        "findings": findings,
        "suppressed": suppressed,
        "exceptions": exceptions_json(run),
        "entities": run.view.entities_json(),
        "bindings": Vec::<Value>::new(),
        "timing": {"elapsed_ms": run.elapsed_ms},
    });
    if run.has_config {
        // No pack is loaded yet, so the used-pack list is empty; its digest is that of `[]`.
        let object = doc
            .as_object_mut()
            .unwrap_or_else(|| unreachable!("the document is an object"));
        object.insert("packs".to_owned(), json!(Vec::<Value>::new()));
        object.insert("packs_digest".to_owned(), json!(blake3_tagged(b"[]")));
    }
    doc
}
