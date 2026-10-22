+++
id = "01M5H16QQT8R5N9162DMQE4F44"
title = "gob-dev still imports frob-check, frob-cli and frob-mirror (remaining SYS013 layering inversion after ~M8WETW7)"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T05:26:39Z"
updated = "2026-10-22T22:32:10Z"
scope = ["crates/gob-dev/**", "crates/frob-docgen/**", "Cargo.toml", "Cargo.lock", "design/**", "docs/design/boundaries.md", "docs/migration/v1-import.md", "docs/guides/upgrade-from-v1.md", "docs/design/migration.md", "docs/design/README.md", "crates/frob-evidence/src/import_v1.rs"]

[[acceptance]]
text = "gob-dev has no frob-* dependency in cargo tree"
bound = true

[[acceptance]]
text = "docs naming cargo dev import-v1-tickets point at the frob-evidence example"
bound = true
+++

Follow-up of ~M8WETW7, which moved the v1 importer (and the frob-ledger/frob-evidence imports) out of gob-dev into frob-evidence. gob-dev still depends on frob-check (products.rs rule indexes, ci.rs ToolStage), frob-cli (lib.rs cli(), verb tests) and frob-mirror (render/schemas.rs issue projection schema) for doc generation. Invert via data the frob side registers or a generator binary living on the frob side, then drop the layering.rs allow rows and any remaining gob->frob flow. Also: docs/migration/v1-import.md and docs/guides/upgrade-from-v1.md still name the old 'cargo dev import-v1-tickets' command; now 'cargo run -p frob-evidence --example import_v1' (could not edit docs/** under ~M8WETW7: held by another lease).
