//! Cache of the architecture and PATH reports, keyed by the same digest as the binding summary.
//!
//! Both passes are pure functions of the walked file contents and a few knobs, and together
//! they cost most of a warm `grimble check` (~SNJ3PH5). A hit skips reading and parsing every
//! file; any change to a walked file, the lock file or a knob changes the digest and misses.
// frob:ticket 01M5BWWMJ7J8Q6G1SRRSNJ3PH5

use std::collections::BTreeMap;

use gob_check::ArtifactKey;
use gob_rules::{Severity, UnresolvedReason};
use grimble_arch::{ArchFinding, ArchReport};
use grimble_lints::pass::{PathFinding, PathReport};
use serde_json::{Value, json};

/// Schema version of the stored payload; bump when the encoding below changes.
const SCHEMA: u32 = 1;

/// The artifact key of a report `kind` (`arch` or `path`) for `digest`, `engine` and `large_lines`.
pub fn key(kind: &str, digest: &str, engine: &str, large_lines: u64) -> ArtifactKey {
    ArtifactKey {
        content_digest: digest.to_owned(),
        producer_identity: format!("grimble-{kind}/report-v{SCHEMA}/{large_lines}/{engine}"),
    }
}

/// The static rule id a stored id names, over the architecture and PATH rule tables.
fn rule_of(id: &str) -> Option<&'static str> {
    grimble_arch::rules::METAS
        .iter()
        .chain(grimble_lints::rules::METAS)
        .map(|d| d.id)
        .find(|r| *r == id)
}

/// One finding in the shared stored shape.
struct Row<'a> {
    rule: &'static str,
    severity: Severity,
    file: &'a str,
    range: (usize, usize),
    message: &'a str,
    reason: Option<&'a UnresolvedReason>,
    anchor: &'a str,
}

/// Encode one finding row.
fn row_json(r: &Row<'_>) -> Value {
    json!({
        "rule": r.rule,
        "severity": r.severity,
        "file": r.file,
        "range": [r.range.0, r.range.1],
        "message": r.message,
        "reason": r.reason.map(UnresolvedReason::code),
        "anchor": r.anchor,
    })
}

/// A decoded finding row.
type Decoded = (
    &'static str,
    Severity,
    String,
    (usize, usize),
    String,
    Option<UnresolvedReason>,
    String,
);

/// Decode one finding row; `None` when it is not one this build wrote.
fn row_of(f: &Value) -> Option<Decoded> {
    let range = f["range"].as_array()?;
    Some((
        rule_of(f["rule"].as_str()?)?,
        serde_json::from_value(f["severity"].clone()).ok()?,
        f["file"].as_str()?.to_owned(),
        (
            usize::try_from(range.first()?.as_u64()?).ok()?,
            usize::try_from(range.get(1)?.as_u64()?).ok()?,
        ),
        f["message"].as_str()?.to_owned(),
        f["reason"].as_str().map(UnresolvedReason::from_code),
        f["anchor"].as_str()?.to_owned(),
    ))
}

/// Encode the subject counts and not-applicable reasons shared by both reports.
fn tail_json(
    subjects: &BTreeMap<&'static str, usize>,
    na: &BTreeMap<&'static str, String>,
) -> (Value, Value) {
    (json!(subjects), json!(na))
}

/// Decode the subject counts and not-applicable reasons.
#[allow(clippy::type_complexity, reason = "one private pair of rule maps")]
fn tail_of(
    doc: &Value,
) -> Option<(
    BTreeMap<&'static str, usize>,
    BTreeMap<&'static str, String>,
)> {
    let mut subjects = BTreeMap::new();
    for (rule, n) in doc["subjects"].as_object()? {
        subjects.insert(rule_of(rule)?, usize::try_from(n.as_u64()?).ok()?);
    }
    let mut na = BTreeMap::new();
    for (rule, why) in doc["not_applicable"].as_object()? {
        na.insert(rule_of(rule)?, why.as_str()?.to_owned());
    }
    Some((subjects, na))
}

/// Encode an [`ArchReport`].
pub fn encode_arch(r: &ArchReport) -> Vec<u8> {
    let findings: Vec<Value> = r
        .findings
        .iter()
        .map(|f| {
            row_json(&Row {
                rule: f.rule,
                severity: f.severity,
                file: &f.file,
                range: f.range,
                message: &f.message,
                reason: f.reason.as_ref(),
                anchor: &f.anchor,
            })
        })
        .collect();
    let (subjects, not_applicable) = tail_json(&r.subjects, &r.not_applicable);
    serde_json::to_vec(&json!({
        "schema": SCHEMA, "findings": findings,
        "subjects": subjects, "not_applicable": not_applicable,
    }))
    .unwrap_or_else(|e| unreachable!("a JSON value encodes: {e}"))
}

/// Decode an [`ArchReport`]; `None` for a payload this build did not write.
pub fn decode_arch(bytes: &[u8]) -> Option<ArchReport> {
    let doc: Value = serde_json::from_slice(bytes).ok()?;
    if doc["schema"] != SCHEMA {
        return None;
    }
    let findings = doc["findings"]
        .as_array()?
        .iter()
        .map(|f| {
            let (rule, severity, file, range, message, reason, anchor) = row_of(f)?;
            Some(ArchFinding {
                rule,
                severity,
                file,
                range,
                message,
                reason,
                anchor,
            })
        })
        .collect::<Option<Vec<_>>>()?;
    let (subjects, not_applicable) = tail_of(&doc)?;
    Some(ArchReport {
        findings,
        subjects,
        not_applicable,
    })
}

/// Encode a [`PathReport`].
pub fn encode_path(r: &PathReport) -> Vec<u8> {
    let findings: Vec<Value> = r
        .findings
        .iter()
        .map(|f| {
            row_json(&Row {
                rule: f.rule,
                severity: f.severity,
                file: &f.file,
                range: f.range,
                message: &f.message,
                reason: f.reason.as_ref(),
                anchor: &f.anchor,
            })
        })
        .collect();
    let (subjects, not_applicable) = tail_json(&r.subjects, &r.not_applicable);
    serde_json::to_vec(&json!({
        "schema": SCHEMA, "findings": findings,
        "subjects": subjects, "not_applicable": not_applicable,
    }))
    .unwrap_or_else(|e| unreachable!("a JSON value encodes: {e}"))
}

/// Decode a [`PathReport`]; `None` for a payload this build did not write.
pub fn decode_path(bytes: &[u8]) -> Option<PathReport> {
    let doc: Value = serde_json::from_slice(bytes).ok()?;
    if doc["schema"] != SCHEMA {
        return None;
    }
    let findings = doc["findings"]
        .as_array()?
        .iter()
        .map(|f| {
            let (rule, severity, file, range, message, reason, anchor) = row_of(f)?;
            Some(PathFinding {
                rule,
                severity,
                file,
                range,
                message,
                reason,
                anchor,
            })
        })
        .collect::<Option<Vec<_>>>()?;
    let (subjects, not_applicable) = tail_of(&doc)?;
    Some(PathReport {
        findings,
        subjects,
        not_applicable,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A report with every field populated, for the round trips.
    fn path_report() -> PathReport {
        PathReport {
            findings: vec![PathFinding {
                rule: "PATH001",
                severity: Severity::Error,
                file: "a/b.rs".into(),
                range: (3, 9),
                message: "m".into(),
                reason: Some(UnresolvedReason::Vacuous),
                anchor: "x".into(),
            }],
            subjects: BTreeMap::from([("PATH001", 4)]),
            not_applicable: BTreeMap::from([("PATH002", "none".to_owned())]),
        }
    }

    // frob:tests crates/grimble-check/src/report_cache.rs::encode_path
    #[test]
    fn path_report_round_trips() {
        let r = path_report();
        assert_eq!(decode_path(&encode_path(&r)), Some(r));
    }

    // frob:tests crates/grimble-check/src/report_cache.rs::encode_arch
    #[test]
    fn arch_report_round_trips() {
        let r = ArchReport {
            findings: vec![ArchFinding {
                rule: "CYCLE001",
                severity: Severity::Error,
                file: "c.rs".into(),
                range: (0, 1),
                message: "cycle".into(),
                reason: None,
                anchor: "a".into(),
            }],
            subjects: BTreeMap::from([("CYCLE001", 2)]),
            not_applicable: BTreeMap::new(),
        };
        assert_eq!(decode_arch(&encode_arch(&r)), Some(r));
    }

    // frob:tests crates/grimble-check/src/report_cache.rs::decode_arch
    #[test]
    fn foreign_payload_is_a_miss() {
        assert_eq!(decode_arch(b"{\"schema\":99}"), None);
        assert_eq!(decode_path(b"not json"), None);
    }
}
