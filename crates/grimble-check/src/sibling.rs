//! The `gob.sibling/1` document (sibling-contract 3): what `grimble check --json` prints as `data`.
//!
//! [`sibling_document`] builds exactly the shape of `docs/schemas/sibling.json` from one
//! [`GrimbleRun`]. Fields grimble cannot fill yet are emitted in their schema-legal empty
//! form and listed in the crate docs: entity digests are null, `anchor`/`entity` on a finding are null because
//! `check_model` does not expose them, and `not_applicable_rules` lists only the SYS rules the model gives nothing to (CAP adds more).

use std::collections::{BTreeMap, HashSet};

use gob_check::sibling::{PacksField, SiblingInput, document};
use gob_rules::{Finding, Severity};
use serde_json::{Value, json};

use crate::GrimbleRun;
use crate::config::blake3_tagged;
use crate::fidelity::fidelity_json;

pub use gob_check::sibling::SCHEMA_VERSION;

/// Unresolved reason code of a finding: the required mark decides, else its typed reason, else `fidelity`.
fn reason_of(f: &Finding) -> Option<String> {
    use gob_rules::RequiredReason::{
        AnnotationRequired, EvaluationFailed, SiblingMissing, ToolFailed, ZeroSubjects,
    };
    (f.severity == Severity::Unresolved).then(|| match &f.required {
        Some(ZeroSubjects { .. }) => "vacuous".to_owned(),
        Some(AnnotationRequired { .. }) => "annotation-required".to_owned(),
        Some(SiblingMissing { .. }) => "incompatible".to_owned(),
        Some(ToolFailed { .. }) => "tool-failed".to_owned(),
        Some(EvaluationFailed { .. }) => "evaluation-failed".to_owned(),
        None => f
            .reason
            .as_ref()
            .and_then(grimble_bind::Reason::from_typed)
            .map_or("fidelity", grimble_bind::Reason::code)
            .to_owned(),
    })
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
    let key = |f: &Finding| crate::product::park_key(f, &run.report.files);
    let not_applicable: HashSet<String> = run.not_applicable.keys().cloned().collect();
    let na_list: Vec<String> = run.not_applicable.keys().cloned().collect();
    document(&SiblingInput {
        product: crate::config::PRODUCT,
        product_version: env!("CARGO_PKG_VERSION"),
        root: &run.root,
        report: &run.report,
        compute: &run.compute,
        ticket_scope: run.ticket_scope.as_deref(),
        base: run.base.as_deref(),
        elapsed_ms: run.elapsed_ms,
        fidelity: fidelity_json(&run.languages, &na_list),
        not_applicable: &not_applicable,
        reason: &reason_of,
        exception_of: &|f| run.parks.get(&key(f)).cloned().unwrap_or_default(),
        exceptions: exceptions_json(run),
        entities: run.view.entities_json(),
        bindings: run.bindings.clone(),
        // Repository packs (atoms only) are the used packs; a built-in is compiled in and not listed.
        packs: run.has_config.then(|| {
            let packs: Vec<serde_json::Value> = run
                .loaded_packs
                .iter()
                .map(|(name, version, digest)| {
                    serde_json::json!({"name": name, "version": version, "digest": digest})
                })
                .collect();
            let digest = blake3_tagged(
                serde_json::Value::Array(packs.clone())
                    .to_string()
                    .as_bytes(),
            );
            PacksField { packs, digest }
        }),
    })
}
