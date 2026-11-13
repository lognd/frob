//! Gathers the [`RenderLedger`] STATE004 reads from the gallery manifest (`gallery/manifest.json`).

// frob:ticket 01M7A3AHXFBFA5WT97NRGJWYQ4

use std::path::Path;

use crunk_gallery::manifest::{self, Manifest};
use crunk_rules::render_ledger::RenderLedger;
use crunk_spec::DesignSpec;

/// Where the gallery keeps its manifest, relative to the project root (the `crunk gallery` default).
pub const MANIFEST_PATH: &str = "gallery/manifest.json";

/// The ledger for `spec` from the manifest under `root`; `None` when no manifest exists yet.
///
/// An unreadable or invalid manifest yields a ledger whose `unreadable` says why, so STATE004
/// reports it as unresolved rather than as every cell missing.
pub fn gather(root: &Path, spec: &DesignSpec) -> Option<RenderLedger> {
    let path = root.join(MANIFEST_PATH);
    let text = match std::fs::read_to_string(&path) {
        Ok(text) => text,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            tracing::info!(path = %path.display(), "render ledger: no gallery manifest; STATE004 does not apply");
            return None;
        }
        Err(e) => {
            tracing::warn!(path = %path.display(), error = %e, "render ledger: manifest unreadable");
            return Some(unreadable(format!("cannot read {MANIFEST_PATH}: {e}")));
        }
    };
    Some(match manifest::parse(&text) {
        Ok(manifest) => from_manifest(&manifest, spec),
        Err(e) => {
            tracing::warn!(error = %e, "render ledger: manifest invalid");
            unreadable(format!("{MANIFEST_PATH}: {e}"))
        }
    })
}

/// The ledger of `spec`'s cells that `manifest` holds a render for (a v1 row covers every state).
pub fn from_manifest(manifest: &Manifest, spec: &DesignSpec) -> RenderLedger {
    let mut ledger = RenderLedger::default();
    for (screen, state, platform) in spec.cell_triples() {
        if manifest
            .find(&screen, &state, &platform)
            .is_some_and(|e| e.render.is_some())
        {
            ledger.record(&screen, &state, &platform);
        }
    }
    tracing::debug!(cells = ledger.rendered.len(), "render ledger gathered");
    ledger
}

fn unreadable(why: String) -> RenderLedger {
    RenderLedger {
        unreadable: Some(why),
        ..RenderLedger::default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn spec() -> DesignSpec {
        let dir = tempfile::tempdir().expect("tempdir");
        let preset = crunk_spec::presets::preset("default").expect("preset");
        let platform = "\n[[platform]]\nid = \"desk\"\nrenderer = \"web\"\nengine = \"chromium\"\nviewport = { width = 1280, height = 800 }\n";
        std::fs::write(dir.path().join("crunk.toml"), format!("{preset}{platform}"))
            .expect("write");
        crunk_spec::load_spec(dir.path()).expect("spec")
    }

    // frob:tests crates/crunk-check/src/render_ledger.rs::gather
    #[test]
    fn missing_manifest_gathers_no_ledger_and_bad_one_is_unreadable() {
        let dir = tempfile::tempdir().expect("tempdir");
        let spec = spec();
        assert!(gather(dir.path(), &spec).is_none());
        std::fs::create_dir_all(dir.path().join("gallery")).expect("mkdir");
        std::fs::write(dir.path().join(MANIFEST_PATH), "not json").expect("write");
        let ledger = gather(dir.path(), &spec).expect("ledger");
        assert!(ledger.unreadable.is_some());
    }

    // frob:tests crates/crunk-check/src/render_ledger.rs::from_manifest
    #[test]
    fn only_cells_with_a_render_are_recorded() {
        let spec = spec();
        let triples = spec.cell_triples();
        let Some((screen, state, platform)) = triples.first().cloned() else {
            return;
        };
        let doc = serde_json::json!({"version": 3, "cells": [
            {"screen": screen, "state": state, "platform": platform,
             "render": {"path": "a.png", "sha256": "0".repeat(64)}}
        ]});
        let manifest = manifest::parse(&doc.to_string()).expect("parse");
        let ledger = from_manifest(&manifest, &spec);
        assert!(ledger.has(&screen, &state, &platform));
        assert_eq!(ledger.rendered.len(), 1);
        assert!(
            from_manifest(
                &Manifest {
                    version: 3,
                    entries: vec![]
                },
                &spec
            )
            .rendered
            .is_empty()
        );
    }
}
