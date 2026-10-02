//! The gob-cache `repo_rule` helper: findings per (inputs digest, rule id, rule version).

use gob_cache::Cache;
use gob_rules::{RuleMeta, Severity};
use gob_text::{FileInterner, Span, TextRange, TextSize};
use serde::{Deserialize, Serialize};

use crate::rules::Raw;

/// One cached finding, free of interner ids.
#[derive(Serialize, Deserialize)]
struct Stored {
    severity: Severity,
    span: Option<(String, u32, u32)>,
    message: String,
    anchor: String,
}

/// The cache key digest: the inputs digest with the rule version folded in.
fn key(inputs_digest: &str, meta: &RuleMeta) -> String {
    let mut h = blake3::Hasher::new();
    h.update(inputs_digest.as_bytes());
    h.update(&meta.version.to_le_bytes());
    h.finalize().to_hex().to_string()
}

/// Looks up the findings of `meta` for `inputs_digest`; a miss or bad payload is `None`.
pub(crate) fn load(
    cache: &Cache,
    inputs_digest: &str,
    meta: &'static RuleMeta,
    files: &mut FileInterner,
) -> Option<Vec<Raw>> {
    let bytes = cache.get_repo_rule(&key(inputs_digest, meta), meta.id)?;
    let stored: Vec<Stored> = match serde_json::from_slice(&bytes) {
        Ok(s) => s,
        Err(err) => {
            tracing::warn!(rule = meta.id, %err, "cached findings undecodable");
            return None;
        }
    };
    tracing::debug!(rule = meta.id, count = stored.len(), "repo rule cache hit");
    Some(
        stored
            .into_iter()
            .map(|s| Raw {
                meta,
                severity: s.severity,
                span: s.span.map(|(path, a, b)| {
                    Span::new(
                        files.intern(&path),
                        TextRange::new(TextSize::new(a), TextSize::new(b)),
                    )
                }),
                message: s.message,
                anchor: s.anchor,
            })
            .collect(),
    )
}

/// Stores the findings of `meta` for `inputs_digest`, best-effort.
pub(crate) fn store(
    cache: &Cache,
    inputs_digest: &str,
    meta: &'static RuleMeta,
    files: &FileInterner,
    raws: &[Raw],
) {
    let stored: Vec<Stored> = raws
        .iter()
        .map(|r| Stored {
            severity: r.severity,
            span: r.span.and_then(|s| {
                files.path(s.file).map(|p| {
                    (
                        p.to_owned(),
                        u32::from(s.range.start()),
                        u32::from(s.range.end()),
                    )
                })
            }),
            message: r.message.clone(),
            anchor: r.anchor.clone(),
        })
        .collect();
    match serde_json::to_vec(&stored) {
        Ok(bytes) => cache.put_repo_rule(&key(inputs_digest, meta), meta.id, &bytes),
        Err(err) => tracing::warn!(rule = meta.id, %err, "findings not serializable"),
    }
}
