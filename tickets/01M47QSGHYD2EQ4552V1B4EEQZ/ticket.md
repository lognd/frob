+++
id = "01M47QSGHYD2EQ4552V1B4EEQZ"
title = "gob-product: Product trait with generic check, doctor and workspace verbs; crunk and grimble on it"
type = "story"
category = "todo"
priority = "high"
points = 8
parent = "01M47QSB9W3BVYZ4NPRVX11TG4"
reporter = "lognd"
created = "2026-10-06T04:33:16Z"
updated = "2026-10-06T04:33:16Z"
scope = ["crates/gob-product/**", "crates/crunk/**", "crates/grimble/**", "Cargo.toml", "Cargo.lock"]

[[links]]
kind = "blocked-by"
target = "01M47QSFS0VP9DET37MBVCRKXA"

[[acceptance]]
text = "crunk/src/check.rs, grimble/src/check.rs and their doctor/workspace duplicates are gone, replaced by Product impls"
bound = false

[[acceptance]]
text = "crunk and grimble --help, check and doctor transcripts are unchanged (existing snapshot and verb tests pass)"
bound = false

[[acceptance]]
text = "a test product implemented in the gob-product test suite gets check and doctor with no extra code"
bound = false
+++

products.md section 7. New crate crates/gob-product above gob-check and gob-cli: a Product trait (name, config root, run a check over a workspace, extra doctor rows, extra verbs) and generic check, doctor and workspace-discovery verbs plus a main entry. The crunk and grimble binaries become a Product impl plus registration of their own extra verbs (grimble fmt, init, ack, exceptions). CLI output must not change.
