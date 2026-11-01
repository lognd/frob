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

/// Store on `record` the `body_digest` of each design entity bound to `ticket`, when `grimble` is available.
pub fn stamp(ws: &Workspace, ticket: TicketId, record: &mut EvidenceRecord) {
    let Some(grimble) = locate_grimble() else {
        tracing::debug!("no grimble binary; record gets no design digest");
        return;
    };
    record.design = digests_with(ws, &grimble, ticket);
    tracing::info!(ticket = %ticket, entities = record.design.len(), "design digests stored on evidence");
}
