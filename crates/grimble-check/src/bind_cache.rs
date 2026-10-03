//! The cached outcome of binding: what `grimble check` reads of B, keyed by everything binding reads.
//!
//! Binding folds every walked file and builds relation, owners and drift, which is most of a
//! cold run. `check` only needs the rows of B (as document items), the SYS findings and the
//! subject counts, so those are stored as one artifact under a digest of the walk, the lock and
//! the `[grimble]` knobs. The engine fingerprint of the cache is part of the producer identity,
//! so another build never reuses the result.

// frob:ticket 01M403Q1W4PMWRM8GXPRS10WX7
// frob:ticket 01M404FZ1G52F6QMYYGS3AFCP4

use std::collections::BTreeMap;
use std::path::Path;

use gob_check::ArtifactKey;
use gob_rules::Severity;
use gob_walk::FileEntry;
use grimble_bind::{BindFinding, Binding};
use serde_json::{Value, json};

use crate::config::{GrimbleTable, PRODUCT};

/// Schema version of the stored payload; bump when the encoding below changes.
const SCHEMA: u32 = 2;

/// What `grimble check` keeps of a [`Binding`]: document rows, SYS findings and subject counts.
#[derive(Debug, Clone, Default, PartialEq)]
pub struct BindSummary {
    /// The rows of B as sibling `bindings` items.
    pub bindings: Vec<Value>,
    /// Findings of the SYS rules.
    pub findings: Vec<BindFinding>,
    /// Subjects examined per rule.
    pub subjects: BTreeMap<&'static str, usize>,
    /// Rules whose whole scope is `NotApplicable` on this model, with the reason.
    pub not_applicable: BTreeMap<&'static str, String>,
}

impl BindSummary {
    /// Reduce a freshly built [`Binding`] to what `check` reads.
    pub fn of(binding: &Binding) -> Self {
        Self {
            bindings: binding.bindings_json(),
            findings: binding.findings.clone(),
            subjects: binding.subjects.clone(),
            not_applicable: binding
                .not_applicable
                .iter()
                .map(|(rule, why)| (*rule, (*why).to_owned()))
                .collect(),
        }
    }

    /// Encode as the artifact payload.
    pub fn encode(&self) -> Vec<u8> {
        let findings: Vec<Value> = self
            .findings
            .iter()
            .map(|f| {
                json!({
                    "rule": f.rule,
                    "severity": f.severity,
                    "file": f.file,
                    "range": f.range,
                    "message": f.message,
                    "anchor": f.anchor,
                })
            })
            .collect();
        let doc = json!({
            "schema": SCHEMA,
            "bindings": self.bindings,
            "findings": findings,
            "subjects": self.subjects,
            "not_applicable": self.not_applicable,
        });
        serde_json::to_vec(&doc).unwrap_or_else(|e| unreachable!("a JSON value encodes: {e}"))
    }

    /// Decode an artifact payload; `None` for any payload this build did not write.
    pub fn decode(bytes: &[u8]) -> Option<Self> {
        let doc: Value = serde_json::from_slice(bytes).ok()?;
        if doc["schema"] != SCHEMA {
            return None;
        }
        let rule_of = |s: &str| grimble_bind::RULES.iter().copied().find(|r| *r == s);
        let mut findings = Vec::new();
        for f in doc["findings"].as_array()? {
            let range = match f["range"].as_array() {
                Some(r) => Some((
                    usize::try_from(r.first()?.as_u64()?).ok()?,
                    usize::try_from(r.get(1)?.as_u64()?).ok()?,
                )),
                None => None,
            };
            findings.push(BindFinding {
                rule: rule_of(f["rule"].as_str()?)?,
                severity: serde_json::from_value::<Severity>(f["severity"].clone()).ok()?,
                file: f["file"].as_str().map(str::to_owned),
                range,
                message: f["message"].as_str()?.to_owned(),
                anchor: f["anchor"].as_str()?.to_owned(),
            });
        }
        let mut subjects = BTreeMap::new();
        for (rule, n) in doc["subjects"].as_object()? {
            subjects.insert(rule_of(rule)?, usize::try_from(n.as_u64()?).ok()?);
        }
        let mut not_applicable = BTreeMap::new();
        for (rule, why) in doc["not_applicable"].as_object()? {
            not_applicable.insert(rule_of(rule)?, why.as_str()?.to_owned());
        }
        Some(Self {
            bindings: doc["bindings"].as_array()?.clone(),
            findings,
            subjects,
            not_applicable,
        })
    }
}

/// Digest of everything binding reads: each walked file, the lock file and the `[grimble]` knobs.
pub fn digest(root: &Path, entries: &[FileEntry], table: &GrimbleTable) -> String {
    let mut h = blake3::Hasher::new();
    for e in entries {
        h.update(e.path.as_bytes());
        h.update(b"\0");
        h.update(e.digest.as_bytes());
    }
    h.update(b"\0lock\0");
    match std::fs::read(root.join(gob_lock_name())) {
        Ok(bytes) => {
            h.update(&bytes);
        }
        Err(_) => {
            h.update(b"absent");
        }
    }
    h.update(
        format!(
            "\0{:?}|{:?}|{}|{}",
            table.models, table.modeled, table.strict, table.rename_min_tokens
        )
        .as_bytes(),
    );
    h.finalize().to_hex().to_string()
}

/// The lock file name of the product (`grimble.lock`).
fn gob_lock_name() -> String {
    format!("{PRODUCT}.lock")
}

/// The artifact key of the binding result for `digest` under cache `engine`.
pub fn key(digest: &str, engine: &str) -> ArtifactKey {
    ArtifactKey {
        content_digest: digest.to_owned(),
        producer_identity: format!("grimble-bind/summary-v{SCHEMA}/{engine}"),
    }
}
