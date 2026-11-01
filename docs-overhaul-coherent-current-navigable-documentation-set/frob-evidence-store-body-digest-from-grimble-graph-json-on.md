+++
id = "01M6BYM60R2RRMEKJ5ZVJ5RP7R"
title = "frob-evidence: store body_digest from grimble graph --json on records bound to a design entity"
type = "task"
category = "in-progress"
priority = "low"
points = 3
parent = "01M69J39HA547HNNCMCAMNDCCT"
reporter = "lognd"
created = "2026-11-01T16:21:03Z"
updated = "2026-11-01T17:39:32Z"
labels = ["grimble"]
scope = ["crates/frob-evidence/src/record.rs", "crates/frob-evidence/src/store.rs", "crates/frob-evidence/src/verbs.rs", "crates/frob-evidence/tests/**", "crates/frob-evidence/src/provider.rs"]

[[acceptance]]
text = "frob evidence and attestation records bound to a design entity store that entity's body_digest from grimble graph --json (grmb-spec 12.8 WINDOW, PM048, D207); records without it are outside every WINDOW (parent AC3)"
bound = false
+++
