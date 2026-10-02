//! Cache payloads: findings as JSON free of interner ids (paths instead).

use gob_rules::{Finding, Fix, FixKind, RuleId, Severity, TextEdit};
use gob_text::{FileId, FileInterner, Span, TextRange, TextSize};
use serde::{Deserialize, Serialize};

/// One edit of a stored fix.
#[derive(Serialize, Deserialize)]
struct StoredEdit {
    path: String,
    start: u32,
    end: u32,
    replacement: String,
}

/// A stored fix.
#[derive(Serialize, Deserialize)]
struct StoredFix {
    kind: FixKind,
    title: String,
    edits: Vec<StoredEdit>,
}

/// A stored finding; the fingerprint is not kept (the pipeline recomputes it).
#[derive(Serialize, Deserialize)]
struct StoredFinding {
    rule: String,
    severity: Severity,
    span: Option<(String, u32, u32)>,
    message: String,
    fix: Option<StoredFix>,
}

fn range(start: u32, end: u32) -> TextRange {
    TextRange::new(TextSize::new(start), TextSize::new(end))
}

/// Serialize `findings` for the cache; spans whose file the interner does not know are dropped.
pub(crate) fn encode(findings: &[Finding], files: &FileInterner) -> Vec<u8> {
    let stored: Vec<StoredFinding> = findings
        .iter()
        .map(|f| StoredFinding {
            rule: f.rule.to_string(),
            severity: f.severity,
            span: f.span.and_then(|s| {
                files.path(s.file).map(|p| {
                    (
                        p.to_owned(),
                        u32::from(s.range.start()),
                        u32::from(s.range.end()),
                    )
                })
            }),
            message: f.message.clone(),
            fix: f.fix.as_ref().map(|fix| StoredFix {
                kind: fix.kind,
                title: fix.title.clone(),
                edits: fix
                    .edits
                    .iter()
                    .filter_map(|e| {
                        files.path(e.file).map(|p| StoredEdit {
                            path: p.to_owned(),
                            start: u32::from(e.range.start()),
                            end: u32::from(e.range.end()),
                            replacement: e.replacement.clone(),
                        })
                    })
                    .collect(),
            }),
        })
        .collect();
    serde_json::to_vec(&stored).unwrap_or_else(|e| unreachable!("stored findings serialize: {e}"))
}

/// Rebuild findings from a cache payload; `None` when it is undecodable or names an unknown file.
pub(crate) fn decode(
    bytes: &[u8],
    mut file_id: impl FnMut(&str) -> Option<FileId>,
) -> Option<Vec<Finding>> {
    let stored: Vec<StoredFinding> = match serde_json::from_slice(bytes) {
        Ok(s) => s,
        Err(err) => {
            tracing::warn!(%err, "cached findings undecodable");
            return None;
        }
    };
    let mut out = Vec::with_capacity(stored.len());
    for s in stored {
        let rule: RuleId = s.rule.parse().ok()?;
        let span = match &s.span {
            Some((path, a, b)) => Some(Span::new(file_id(path)?, range(*a, *b))),
            None => None,
        };
        let anchor = s
            .span
            .as_ref()
            .map_or("", |(p, _, _)| p.as_str())
            .to_owned();
        let mut finding = Finding::new(rule, s.severity, span, s.message, &anchor);
        if let Some(fix) = s.fix {
            let mut edits = Vec::with_capacity(fix.edits.len());
            for e in fix.edits {
                edits.push(TextEdit {
                    file: file_id(&e.path)?,
                    range: range(e.start, e.end),
                    replacement: e.replacement,
                });
            }
            finding = finding.with_fix(Fix {
                kind: fix.kind,
                title: fix.title,
                edits,
            });
        }
        out.push(finding);
    }
    Some(out)
}
