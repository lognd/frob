//! LARGE001: units longer than the `large_lines` knob.

// frob:ticket 01M3Z7141TW2H3HXJRK1QBHP7T

use std::collections::BTreeMap;

use gob_rules::Severity;
use gob_symbols::{SymbolGraph, SymbolKind};

use crate::{LARGE, Verdict};

/// True for the kinds whose length is a design smell: callables and type definitions.
fn is_sized(kind: SymbolKind) -> bool {
    matches!(
        kind,
        SymbolKind::Function
            | SymbolKind::Method
            | SymbolKind::Struct
            | SymbolKind::Enum
            | SymbolKind::Trait
            | SymbolKind::Class
            | SymbolKind::Interface
            | SymbolKind::Record
    )
}

/// Findings for units over `limit` lines, and how many units were measured.
pub(crate) fn check(
    graph: &SymbolGraph,
    limit: usize,
    read: &dyn Fn(&str) -> Option<String>,
) -> (Vec<Verdict>, usize) {
    let mut by_file: BTreeMap<&str, Vec<&gob_symbols::SymbolRecord>> = BTreeMap::new();
    for rec in graph.records().filter(|r| is_sized(r.kind)) {
        by_file.entry(rec.symref.path()).or_default().push(rec);
    }
    let mut findings = Vec::new();
    let mut measured = 0;
    for (path, recs) in by_file {
        let Some(text) = read(path) else {
            tracing::warn!(path, "LARGE001 skipped an unreadable file");
            continue;
        };
        for rec in recs {
            let (start, end) = (
                usize::try_from(u32::from(rec.span.start())).unwrap_or(usize::MAX),
                usize::try_from(u32::from(rec.span.end())).unwrap_or(usize::MAX),
            );
            let Some(body) = text.as_bytes().get(start..end) else {
                tracing::warn!(path, start, end, "LARGE001 span is outside the file text");
                continue;
            };
            measured += 1;
            let lines = body.split(|&b| b == b'\n').count();
            if lines > limit {
                tracing::debug!(unit = %rec.symref, lines, limit, "LARGE001 unit over the limit");
                findings.push(Verdict::fire(
                    LARGE,
                    Severity::Error,
                    (path, (start, end)),
                    format!(
                        "`{}` is {lines} lines long, over the limit of {limit}",
                        rec.symref.name().unwrap_or("unit")
                    ),
                    rec.symref.to_string(),
                ));
            }
        }
    }
    (findings, measured)
}
