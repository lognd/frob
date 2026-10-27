+++
id = "01M5N948TQFB9364996468DHJ3"
title = "Hoist shared presence and attester logic out of grimble and frob-evidence"
type = "chore"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-23T21:02:04Z"
updated = "2026-10-27T02:58:41Z"
scope = ["crates/grimble/**", "crates/frob-evidence/**"]
+++

grimble::presence duplicates frob-evidence/src/attestation.rs because grimble cannot link frob-evidence; found while working ~N2GX6NN. Move into a gob-level crate.
