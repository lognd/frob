//! Ratchet: every rule id a tool stage emits is declared in `gob_rules::tool_stage_ids`
//! (org audit R5).
#![allow(
    clippy::disallowed_methods,
    reason = "a source scan reads the disk, not a walked Core"
)]

// frob:ticket 01M61MM4H8E5N93CRKFTREB77M
use std::collections::BTreeSet;
use std::fs;
use std::path::Path;

use gob_rules::tool_stage_ids::{FROB_IDS, NATIVE_IDS, is_declared_stage_id};

/// Every id-shaped string literal in the non-test part of gob-check's `tool_parse.rs`.
fn emitted_ids() -> BTreeSet<String> {
    let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("../gob-check/src/tool_parse.rs");
    let text = fs::read_to_string(path).expect("tool_parse.rs readable");
    let body = text.split("#[cfg(test)]").next().unwrap_or(&text);
    let mut out = BTreeSet::new();
    for piece in body.split('"').skip(1).step_by(2) {
        let shaped = piece.starts_with(|c: char| c.is_ascii_uppercase())
            && piece
                .chars()
                .all(|c| c.is_ascii_uppercase() || c.is_ascii_digit())
            && piece.chars().rev().take_while(char::is_ascii_digit).count() >= 3;
        if shaped {
            out.insert(piece.to_owned());
        }
    }
    out
}

#[test]
fn every_emitted_tool_stage_id_is_declared() {
    let emitted = emitted_ids();
    assert!(emitted.len() > 20, "scan found too few ids: {emitted:?}");
    let undeclared: Vec<&String> = emitted
        .iter()
        .filter(|id| !is_declared_stage_id(id))
        .collect();
    assert!(
        undeclared.is_empty(),
        "tool-stage ids emitted but not declared in gob_rules::tool_stage_ids: {undeclared:?}"
    );
}

#[test]
fn every_declared_tool_stage_id_is_still_emitted() {
    let emitted = emitted_ids();
    let stale: Vec<&&str> = FROB_IDS
        .iter()
        .chain(NATIVE_IDS)
        .filter(|id| !emitted.contains(**id))
        .collect();
    assert!(
        stale.is_empty(),
        "declared but no longer emitted: {stale:?}"
    );
}
