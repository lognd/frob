//! Design-entity digests on evidence records (grmb-spec 12.8 and 17.3, D206, D207).
//!
//! A record made for a ticket that a design entity names with `frob:ticket` stores that entity's
//! `body_digest` from `grimble graph --json`. A record without it is outside every WINDOW, so a
//! missing `grimble`, a repository without a model or an unreadable graph only leaves the field
//! empty; it never fails the capture.

// frob:ticket 01M6BYM60R2RRMEKJ5ZVJ5RP7R

use std::path::{Path, PathBuf};

use frob_ledger::TicketId;
use gob_exec::{Outcome, Program};
use serde_json::Value;

use crate::provider::{builtin_tools, spec};
use crate::record::{DesignDigest, EvidenceRecord};
use crate::workspace::Workspace;

/// The `grimble` binary: the sibling of the running executable, else the one on `PATH`.
pub fn locate_grimble() -> Option<PathBuf> {
    let beside = builtin_tools()
        .into_iter()
        .find(|p| p.file_stem().is_some_and(|s| s == "grimble"));
    beside.or_else(|| which::which("grimble").ok())
}

/// The digests of every entity in a `grimble graph --json` envelope whose `frob:ticket` directive names `ticket`.
pub fn bound_digests(graph: &Value, ticket: &str) -> Vec<DesignDigest> {
    let entities = graph["data"]["entities"]
        .as_array()
        .or_else(|| graph["entities"].as_array());
    let mut out = Vec::new();
    for e in entities.into_iter().flatten() {
        let names_ticket = e["directives"].as_array().is_some_and(|ds| {
            ds.iter().any(|d| {
                d["verb"] == "ticket"
                    && d["args"].as_str().is_some_and(|a| {
                        a.split(|c: char| c.is_whitespace() || c == ',')
                            .any(|t| t == ticket)
                    })
            })
        });
        let (Some(anchor), Some(digest)) = (e["anchor"].as_str(), e["body_digest"].as_str()) else {
            if names_ticket {
                tracing::debug!(ticket, entity = %e["anchor"], "bound entity has no body_digest; skipped");
            }
            continue;
        };
        if names_ticket {
            out.push(DesignDigest {
                entity: anchor.to_owned(),
                body_digest: digest.to_owned(),
            });
        }
    }
    out
}

/// Run `grimble graph --json` with the binary `grimble` in the work tree and return the digests bound to `ticket`; empty on any failure.
pub fn digests_with(ws: &Workspace, grimble: &Path, ticket: TicketId) -> Vec<DesignDigest> {
    let program = Program::Hook {
        path: grimble.to_path_buf(),
    };
    let args = vec!["graph".to_owned(), "--json".to_owned()];
    let out = match ws
        .runner()
        .run(&spec(program, args, &ws.root, ws.timeout()))
    {
        Ok(out) => out,
        Err(e) => {
            tracing::warn!(error = %e, "grimble graph could not run; record gets no design digest");
            return Vec::new();
        }
    };
    if out.status != Outcome::Exited(0) {
        tracing::debug!(status = ?out.status, "grimble graph did not succeed (no model?); no design digest");
        return Vec::new();
    }
    match serde_json::from_str::<Value>(&out.stdout_raw) {
        Ok(doc) => bound_digests(&doc, &ticket.to_string()),
        Err(e) => {
            tracing::warn!(error = %e, "grimble graph printed no JSON; record gets no design digest");
            Vec::new()
        }
    }
}

/// Directories the model-source scan never enters (dependency and build trees; dot-directories are skipped too).
const SKIPPED_DIRS: [&str; 3] = ["target", "node_modules", "vendor"];

/// True when some `.grmb` model file under `dir` mentions `needle`; a repository without one needs no `grimble` run.
fn model_mentions(dir: &Path, needle: &str) -> bool {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return false;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        let Ok(kind) = entry.file_type() else {
            continue;
        };
        if kind.is_dir() {
            let name = entry.file_name();
            let skipped = name.as_encoded_bytes().starts_with(b".")
                || SKIPPED_DIRS.iter().any(|d| name == *d);
            if !skipped && model_mentions(&path, needle) {
                return true;
            }
        } else if kind.is_file()
            && path.extension().is_some_and(|e| e == "grmb")
            && gob_fs::text_matches(&path, |t| t.contains(needle))
        {
            return true;
        }
    }
    false
}

/// Store on `record` the `body_digest` of each design entity bound to `ticket`, when `grimble` is available.
pub fn stamp(ws: &Workspace, ticket: TicketId, record: &mut EvidenceRecord) {
    if !model_mentions(&ws.root, &ticket.to_string()) {
        tracing::debug!(ticket = %ticket, "no .grmb model names the ticket; grimble not spawned");
        return;
    }
    let Some(grimble) = locate_grimble() else {
        tracing::debug!("no grimble binary; record gets no design digest");
        return;
    };
    record.design = digests_with(ws, &grimble, ticket);
    tracing::info!(ticket = %ticket, entities = record.design.len(), "design digests stored on evidence");
}

#[cfg(test)]
mod tests {
    use super::{bound_digests, model_mentions};

    // frob:ticket 01M6C6NBJSSAVBR59RBMPWW9VP
    // frob:tests crates/frob-evidence/src/design.rs::model_mentions
    #[test]
    fn only_a_grmb_file_naming_the_ticket_triggers_the_scan() {
        let dir = tempfile::tempdir().expect("tempdir");
        assert!(!model_mentions(dir.path(), "T1"));
        std::fs::write(dir.path().join("a.rs"), "frob:ticket T1").unwrap();
        assert!(!model_mentions(dir.path(), "T1"));
        std::fs::create_dir(dir.path().join("sub")).unwrap();
        std::fs::write(dir.path().join("sub/m.grmb"), "// frob:ticket T1\n").unwrap();
        assert!(model_mentions(dir.path(), "T1"));
        assert!(!model_mentions(dir.path(), "T2"));
    }

    // frob:ticket 01M6C5CMP9SFX0910Q9QAMB4T3
    // frob:tests crates/frob-evidence/src/design.rs::bound_digests
    #[test]
    fn every_bound_entity_digest_is_found_in_the_serialized_design_list() {
        let entity = |anchor: &str, digest: &str| {
            serde_json::json!({"anchor": anchor, "body_digest": digest,
                "directives": [{"verb": "ticket", "args": "T1"}]})
        };
        let graph = serde_json::json!({"data": {"entities": [
            entity("a.md#one", "blake3:aa"),
            entity("a.md#two", "blake3:bb"),
            entity("a.md#three", "blake3:cc"),
        ]}});
        let list = serde_json::to_value(bound_digests(&graph, "T1")).expect("ser");
        let found = |anchor: &str| {
            list.as_array()
                .into_iter()
                .flatten()
                .find(|d| d["entity"] == anchor)
                .map(|d| d["body_digest"].clone())
        };
        assert_eq!(found("a.md#one"), Some("blake3:aa".into()));
        assert_eq!(found("a.md#two"), Some("blake3:bb".into()));
        assert_eq!(found("a.md#three"), Some("blake3:cc".into()));
    }
}
